#!/usr/bin/env python3
"""Exercise the original full copy, sparse instruction probes and wire format."""

from base64 import b64encode
from importlib import import_module
from math import ceil
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame344_log import require
from frame374_native_ca import envelope
import frame378_memory as memory

scope = import_module('prepare-frame378')
runner = import_module('run-frame378-trial')

SOURCE = r'''
#include "gauguin_copy378_probe.h"

#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>

static void check_surface(unsigned alignment)
{
    std::vector<uint8_t> src(SCAN352_SOURCE_STRIDE * SCAN352_HEIGHT + 128, 0x7b);
    std::vector<uint8_t> plain(SCAN352_PANEL_STRIDE * SCAN352_HEIGHT + 128, 0xe3);
    std::vector<uint8_t> probed(plain.size(),0xe3);
    struct f378_probe_deltas deltas{};
    auto *source = src.data() + alignment;
    auto *nominal = plain.data() + alignment;
    auto *sampled = probed.data() + alignment;
    unsigned sample = 0;
    for (unsigned y = 0; y < SCAN352_HEIGHT; ++y) {
        auto *row = source + y * SCAN352_SOURCE_STRIDE;
        for (unsigned x = 0; x < SCAN352_PANEL_STRIDE; ++x) row[x] = (y * 13 + x * 7 + (x >> 6)) & 255;
        scan356_copy_row(nominal + y * SCAN352_PANEL_STRIDE, row);
        if (sample < F378_PROBE_ROWS && y == F378_ROW_FIRST + sample * F378_ROW_STEP) {
            scan378_probe_row(sampled + y * SCAN352_PANEL_STRIDE, row, sample, sample==3, &deltas);
            ++sample;
        } else {
            scan356_copy_row(sampled + y * SCAN352_PANEL_STRIDE, row);
        }
        assert(!memcmp(nominal + y * SCAN352_PANEL_STRIDE, row, SCAN352_PANEL_STRIDE));
        for (unsigned x = SCAN352_PANEL_STRIDE; x < SCAN352_SOURCE_STRIDE; ++x) assert(row[x]==0x7b);
    }
    assert(sample==F378_PROBE_ROWS && plain==probed);
    for (unsigned i = 0; i < alignment; ++i) assert(probed[i]==0xe3);
    for (size_t i = alignment + SCAN352_PANEL_STRIDE * SCAN352_HEIGHT; i < probed.size(); ++i)
        assert(probed[i]==0xe3);
    uint64_t total = deltas.drain;
    for (unsigned i = 0; i < sample; ++i) total += deltas.read[i] + deltas.issue[i];
    assert(total && total < UINT32_MAX);
}

int main()
{
    assert(scan352_can_copy(3044,4878) && !scan352_can_copy(3045,4878));
    assert(f378_probe_class(157056001,1,1)==F378_STROKE2);
    assert(f378_probe_class(166656001,1,1)==0);
    assert(f378_probe_class(336960001,1,142)==F378_STROKE6);
    assert(f378_probe_class(346752001,1,142)==F378_CONTROL);
    assert(f378_probe_class(99,100,71)==0);
    check_surface(0);
    check_surface(16);
    check_surface(32);
    uint8_t out[F378_PROBE_ROW_BYTES];
    struct f378_probe_deltas row{};
    row.read[0]=0x1000000;
    assert(!f378_pack_probe(out,10,F378_STROKE2,&row));
    assert(!f378_pack_probe(out,10,4,&row));
    for (unsigned i = 0; i < F378_PROBE_ROWS; ++i) {
        row.read[i] = i+20;
        row.issue[i] = i+10;
    }
    row.drain = 15;
    assert(f378_pack_probe(out,10,F378_STROKE2,&row));
    assert(fwrite(out,1,sizeof(out),stdout)==sizeof(out));
    return 0;
}
'''


def exercise():
    include = scope.BASE/'native-kernel/source/bsd/dev'
    original = scope.P375/'native-kernel/source/bsd/dev/gauguin_copy356.h'
    require((include/original.name).read_bytes()==original.read_bytes(),'0375 production loop differs')
    require((include/'gauguin_frame377_slots.h').read_bytes()==
            (scope.P377/'native-kernel/source/bsd/dev/gauguin_frame377_slots.h').read_bytes(),
            'four-way IPC slots differ')
    with TemporaryDirectory() as work:
        p = Path(work)/'probe.cpp'
        p.write_text(SOURCE)
        target = p.with_suffix('')
        subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror','-I',str(include),
                        str(p),'-o',str(target)],check=True)
        packed = subprocess.check_output([str(target)])
    fixture = 'SWEET F378 P 0 1 '+b64encode(packed).decode()+'\nSWEET F378 F: rows=1 lost=0 control=0 stroke2=1 stroke6=0\n'
    rows,selected,lost = memory.wire_rows(fixture)
    require(rows==[dict(attempt=10,lane=2,drain_index=2,read_ticks=list(range(20,28)),
                       issue_ticks=list(range(10,18)),drain_ticks=15)] and selected=={1:0,2:1,3:0} and not lost,
            'native phase samples changed on round trip')
    for malformed in (fixture.replace('P 0','P 1'),fixture.replace('rows=1','rows=2'),
                      fixture.replace('stroke2=1','stroke2=32')):
        try:
            memory.wire_rows(malformed)
        except ValueError:
            continue
        raise ValueError('malformed probe block was accepted')


def main():
    exercise()
    prior = scope.load(scope.P377/'host-verification.json')
    worst = prior['projected_ring_bound'] + ceil(sum(memory.LIMITS.values())*memory.PACKED_ROW_BYTES*4/3)
    worst += ceil(sum(memory.LIMITS.values())/memory.BLOCK_SIZE)*30 + 128
    require(worst<4_194_304,'combined console reservation exceeds the measured ring')
    comparison = scope.load(scope.COMPARISON)
    raw = (scope.REFERENCE/'kernel.log').read_text()
    start,_,n,d = envelope(raw)
    _,strokes,_,_ = runner.trace.parse(raw,extra_kinds=(runner.score.PRESENT,runner.score.copy.WAKE,*runner.score.KINDS))
    old = comparison['copy']['0377']['check_failed']
    phase = {row['attempt']:row for row in comparison['copy_phases']['rows']}
    require(len(old)==2 and len(strokes)==13 and (n,d)==(625,12),'old cross-scan evidence differs')
    evidence = []
    for stroke,lane,fail in zip((2,6),(2,3),old,strict=True):
        attempt = fail['attempt']
        tick = phase[attempt]['begin_tick']
        low,high = memory.WINDOWS[lane]
        require(strokes[stroke-1][1]<start+low<=tick<start+high and memory.lane_for(attempt,tick-start)==lane,
                '0378 probe scenario does not cover the 0377 tail')
        evidence.append(dict(stroke=stroke,prior_attempt=attempt,window_ticks_from_arm=[low,high],
                             previous_begin_tick=tick,previous_copy_ns=fail['duration_ns']))
    summary = dict(state='0378-offline-verified',patch_sha256=scope.sha(scope.PATCH),native_schema_verified=True,
        controls=18,full_surface_bytes_verified=True,original_loop_and_probe_bytes_match=True,
        reference_windows_verified=True,reference_tails=evidence,projected_ring_bound=worst,
        reference_raw_bytes=prior['reference_raw_bytes'],device_writes=0,device_boots=0)
    scope.save(scope.HOST,summary)
    print(summary)


if __name__=='__main__':
    main()
