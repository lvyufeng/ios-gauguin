#!/usr/bin/env python3
"""Exercise 0377's actual row copy, bounded key ownership and timestamp codec."""

import base64
from importlib import import_module
from math import ceil
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame344_log import ATTEMPT, COPY, FRAME_BYTES, RESULT, Event, require
from frame374_native_ca import EVENT_LIMIT
import frame376_capture as preceding
import frame377_capture as capture

scope = import_module('prepare-frame377')

NATIVE = r'''
#include "gauguin_copy377.h"
#include "gauguin_frame376_wire.h"
#include "gauguin_frame377_slots.h"

#include <array>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>

static void check_surface(unsigned alignment)
{
    const size_t height = SCAN352_HEIGHT;
    const size_t source_stride = SCAN352_SOURCE_STRIDE;
    const size_t destination_stride = SCAN352_PANEL_STRIDE;
    std::vector<uint8_t> source(source_stride * height + 128, 0x13);
    std::vector<uint8_t> dest(destination_stride * height + 128, 0xee);
    auto *from = source.data() + alignment;
    auto *to = dest.data() + alignment;
    for (size_t y = 0; y < height; ++y) {
        for (size_t x = 0; x < destination_stride; ++x)
            from[y * source_stride + x] = (13 * y + 7 * x + (x >> 8)) & 255;
        scan377_copy_row(to + y * destination_stride, from + y * source_stride);
    }
    for (size_t y = 0; y < height; ++y) {
        assert(memcmp(to + y * destination_stride, from + y * source_stride, destination_stride) == 0);
        for (size_t x = destination_stride; x < source_stride; ++x)
            assert(from[y * source_stride + x] == 0x13);
    }
    for (size_t i = 0; i < alignment; ++i) assert(dest[i] == 0xee);
    for (size_t i = alignment + destination_stride * height; i < dest.size(); ++i) assert(dest[i] == 0xee);
}

static void check_bucket()
{
    struct f377_keys bucket{};
    std::array<int, F377_IPC_WAYS> ways{};
    std::array<std::thread, F377_IPC_WAYS> threads;
    std::array<uint32_t, F377_IPC_WAYS> payload{};
    std::atomic<bool> start{};
    for (unsigned i = 0; i < threads.size(); ++i) {
        threads[i] = std::thread([&, i] {
            while (!start.load(std::memory_order_acquire)) std::this_thread::yield();
            const int way = f377_reserve(&bucket);
            assert(way >= 0);
            ways[i] = way;
            assert(f377_lookup(&bucket, 16 * (i + 1)) < 0);
            payload[way] = i + 1;
            f377_publish(&bucket, way, 16 * (i + 1));
        });
    }
    start.store(true,std::memory_order_release);
    for (auto &thread : threads) thread.join();
    assert(f377_reserve(&bucket) < 0);
    for (unsigned i = 0; i < ways.size(); ++i) {
        assert(f377_lookup(&bucket, 16 * (i + 1)) == ways[i] && payload[ways[i]] == i + 1);
        assert(!f377_release(&bucket, ways[i], 0x1000));
    }
    assert(f377_release(&bucket, ways[0], 16));
    const int reused = f377_reserve(&bucket);
    assert(reused == ways[0] && f377_lookup(&bucket,16) < 0);
    f377_publish(&bucket, reused, 0x1000);
    assert(!f377_release(&bucket, reused, 16) && f377_lookup(&bucket,0x1000) == reused);
    for (unsigned i = 1; i < ways.size(); ++i)
        assert(f377_release(&bucket, ways[i], 16 * (i + 1)));
    assert(f377_release(&bucket, reused, 0x1000));
}

int main()
{
    assert(scan352_can_copy(2480, 4878));
    assert(scan352_can_copy(3044, 4878));
    assert(!scan352_can_copy(3045, 4878));
    assert(!scan352_can_copy(2479, 4878));
    assert(!scan352_can_copy(4880, 4878));
    check_surface(0);
    check_surface(16);
    check_surface(32);
    for (unsigned i = 0; i < 64; ++i) check_bucket();
    uint8_t row[F377_COPY_ROW];
    assert(!f377_pack_copy(row, 1000, 0, 1100, 2000, 2050, 951));
    assert(!f377_pack_copy(row, 1000, 1, 1100, 1000, 2050, 951));
    assert(!f377_pack_copy(row, 1000, 1, 1100, 2000, 1999, 951));
    assert(!f377_pack_copy(row, 1000, UINT16_MAX + 1, 1100, 2000, 2050, 951));
    assert(f377_pack_copy(row, 1000, 1, 1100, 2000, 2050, 951));
    assert(fwrite(row, 1, sizeof(row), stdout) == sizeof(row));
    return 0;
}
'''


def exercise():
    include = scope.BASE/'native-kernel/source/bsd/dev'
    with TemporaryDirectory() as directory:
        source = Path(directory)/'check.cpp'
        target = source.with_suffix('')
        source.write_text(NATIVE)
        subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror','-pthread',
                        '-I',str(include),str(source),'-o',str(target)],check=True)
        packed = subprocess.check_output([str(target)])
    raw = 'SWEET F377 C 0 1 '+base64.b64encode(packed).decode()+'\nSWEET F377 C footer: rows=1 lost=0\n'
    require(capture.wire_rows(raw)==([(1,100,900,50,951)],0),'compiled timestamp codec differs')
    traces = {ATTEMPT:[Event(1,1090,ATTEMPT,1,0,0,0,0)],
              COPY:[Event(2,2055,COPY,5,0,1100,2050,FRAME_BYTES)],
              RESULT:[Event(3,2057,RESULT,1,0,1,0,0)]}
    timings = capture.copies(raw,traces,[],1000,3000,625,12)
    require(timings['full_capture_qualified'] and timings['rows'][0]['stores_tick']==2000 and
            timings['rows'][0]['end_tick']==2050,'synthetic copy phases do not preserve identity or ticks')
    for malformed in (raw.replace('C 0 1','C 1 1'),raw.replace('rows=1','rows=2'),
                      raw.replace('C 0 1','C 0 2')):
        try:
            capture.wire_rows(malformed)
        except ValueError:
            continue
        raise ValueError('malformed copy phase packet was accepted')


def main():
    exercise()
    previous = scope.load(scope.P376/'host-verification.json')
    ref = scope.load(scope.P375/'partial-audit-0375.json')
    raw = (scope.P375/'execution/kernel.log').read_bytes()
    old_trace_size = sum(len(line) for line in raw.splitlines(keepends=True) if b'SWEET F374 ' in line)
    base_bytes = previous['reference_raw_bytes']-old_trace_size
    planned = ceil((capture.DISPLAY_BYTES+capture.PACKET_BYTES+capture.COPY_CAP*capture.COPY_ROW.size)*4/3)
    overhead = (ceil(EVENT_LIMIT/32)+ceil(10240/64)+ceil(capture.COPY_CAP/32))*30 + (
                preceding.DISPLAY_THREADS+preceding.PACKET_THREADS)*48 + 64*177 + 1024
    require(previous['projected_display_wire_bytes']<capture.DISPLAY_BYTES and
            previous['transport_replay']['wire_bytes']<capture.PACKET_BYTES and
            previous['reference_previously_guarded_starts']+1<capture.COPY_CAP and
            base_bytes+planned+overhead<4_194_304,'0377 console or instrumentation caps lack headroom')
    require(ref['unchecked_copies'][0]['duration_ns']>9_000_000,'0375 crossing control differs')
    summary = dict(state='0377-offline-verified',patch_sha256=scope.sha(scope.PATCH),native_schema_verified=True,
        controls=20,full_surface_bytes_verified=True,IPC_overlap_controls_passed=True,
        IPC_concurrent_bucket_repeats=64,exact_body_and_barrier_codec=True,
        projected_ring_bound=base_bytes+planned+overhead,reference_raw_bytes=previous['reference_raw_bytes'],
        prior_copy_samples=previous['reference_previously_guarded_starts']+1,
        cpu_only_memory_test=True,device_writes=0,device_boots=0)
    scope.save(scope.HOST,summary)
    print(summary)


if __name__=='__main__':
    main()
