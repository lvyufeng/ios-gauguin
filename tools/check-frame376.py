#!/usr/bin/env python3
"""Replay the retained 0375 display lane and production 0376 compact writer."""

import base64
import ctypes
from importlib import import_module
from math import ceil
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from frame344_log import require, parse
import frame374_native_ca as native
import frame376_capture as current
from frame373_receipts import decode_with_unmatched

scope = import_module('prepare-frame376')
audit = import_module('audit-frame375-partial')


def exercise_wire():
    raw = (scope.P373/'execution/kernel.log').read_text()
    _,_,n,d = native.envelope(raw)
    reference = decode_with_unmatched(raw,n,d)
    q = ctypes.c_uint64
    u = ctypes.c_uint32
    b = ctypes.c_uint8
    with TemporaryDirectory() as directory:
        src = Path(directory)/'wire.c'
        lib = src.with_suffix('.dylib')
        src.write_text('''
#include "gauguin_frame376_wire.h"
#include "gauguin_blank352.h"

unsigned packet(uint8_t *out, uint64_t base, uint32_t serial, uint32_t message,
    uint64_t send, uint64_t post, uint64_t copyout, uint8_t source, uint8_t receiver)
{
    return f376_pack_pair(out, base, serial, message, send, post, copyout, source, receiver);
}

bool in_window(uint32_t line, uint32_t end)
{
    return scan352_can_copy(line, end);
}
''')
        include = scope.BASE/'native-kernel/source/bsd/dev'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-dynamiclib','-I',str(include),
                        str(src),'-o',str(lib)],check=True)
        c = ctypes.CDLL(str(lib))
        c.packet.argtypes = [ctypes.POINTER(b),q,u,u,q,q,q,b,b]
        c.packet.restype = ctypes.c_uint
        c.in_window.argtypes = [u,u]
        c.in_window.restype = ctypes.c_bool
        controls = 0
        for line,end,expected in ((2479,4878,False),(2480,4878,True),
                                   (2644,4878,True),(2645,4878,False),
                                   (2656,4878,False),(4900,4898,False),(2480,4911,False)):
            require(c.in_window(line,end)==expected,'production blanking admission differs')
            controls += 1
        scratch = (b*23)()
        for invalid in ((1,0,40002,2,3,4,0,0),(3,1,40002,2,3,4,0,0),
                        (1,1,40002,2,4,3,0,0),(1,1,40002,2,3,1<<34,0,0)):
            require(c.packet(scratch,*invalid)==0,'native codec accepted invalid pair')
            controls += 1
        for invalid in (b'', bytes(9)+b'\x80\x00\x00', bytes(8)+b'\x09\x00\x00',
                        bytes(9)+b'\xff\xff\xff\xff\x10\x00'):
            try:
                list(current.compact_rows(invalid,1))
            except ValueError:
                controls += 1
            else:
                raise ValueError('decoder accepted malformed packet')
        old_mapping = {int(thread):int(index) for index,thread in
            re.findall(r'^SWEET F372 D: index=(\d+) tid=(\d+)$',raw,re.M)}
        pairs = reference['pairs']
        blocks = []
        total = 0
        for cursor in range(0,len(pairs),64):
            block = bytearray()
            available = pairs[cursor:cursor+64]
            for row in available:
                fields = (reference['window_ticks'][0], row['serial'],row['message_id'],row['send_tick'],
                          row['post_tick'],row['copyout_tick'],old_mapping[row['sender_thread']],
                          old_mapping[row['receiver_thread']])
                length = c.packet(scratch,*fields)
                require(0<length<=len(scratch),'native compact record size differs')
                block.extend(scratch[:length])
            blocks.append(f'SWEET F376 P {cursor} {len(available)} '+base64.b64encode(block).decode())
            total += len(block)
        encoded = re.sub(r'^SWEET F372 B .*$', '', raw, flags=re.M)+'\n'+'\n'.join(blocks)+(
            f'\nSWEET F376 P footer: rows={len(pairs)} bytes={total}\n')
        capture = current.packet_lane(encoded,n,d)
        require(capture['pairs']==pairs and capture['unmatched_receipts']==reference['unmatched_receipts'],
                'wire lost or changed identity or time')
    return dict(same_pairs=len(pairs),wire_bytes=total,controls=controls)


def check():
    original = scope.load(scope.P375/'partial-audit-0375.json')
    raw = (scope.REFERENCE/'kernel.log').read_text()
    _,events,_ = audit.retained_events(raw)
    rows,strokes,n,d = parse(raw,extra_kinds=(audit.score.PRESENT,audit.score.copy.WAKE,*audit.score.KINDS))
    require(len(strokes)==13 and (n,d)==(625,12),'unsupported reference script or timebase')
    safe = [row for row in rows[audit.score.PRESENT] if row.flags==5]
    old_crossing, = original['unchecked_copies']
    dangerous, = [row for row in rows[audit.score.PRESENT]
                   if row.id==old_crossing['frame'] and row.flags==6 and row.b==old_crossing['begin_line']]
    rejected = (dangerous.c>>32)-dangerous.b
    require(5_500_000<=rejected*3_000<current.COPY_LEAD_NS, 'reference crossing is not excluded')
    trimmed = [row for row in events if row.kind in current.DISPLAY_KINDS]
    wire = sum(native.ROW.size+native.FIELDS[row.kind].size for row in trimmed)
    coverage = original['native_retained']['last_retained_seconds']
    projection = ceil(wire*45/coverage)
    require(projection<current.DISPLAY_BYTES,'separate display wire reservation too small')

    rows32 = ceil(native.EVENT_LIMIT/32)
    rows64 = ceil(10240/64)
    reference_ring = scope.load(scope.REFERENCE/'kernel-IO-analysis.json')['ring']['total_bytes']
    old_native = sum(len(line) for line in raw.encode().splitlines(keepends=True) if b'SWEET F374 ' in line)
    # Include base64 padding, record headers, thread dictionaries, missed
    # receipt details, and timestamps for all 32 retained long copies.
    envelope_overhead = (rows32+rows64)*30 + (
        current.DISPLAY_THREADS+current.PACKET_THREADS)*48 + 64*177 + 32*150 + 1024
    projected_ring = reference_ring-old_native+ceil((current.DISPLAY_BYTES+current.PACKET_BYTES)*4/3)+envelope_overhead
    require(projected_ring<4_194_304,'projected persistent console reservation too small')
    residual = original['callback_timestamp_residuals']['maximum_absolute_residual_ns']
    require(0<residual<current.RECEIPT_TOLERANCE_NS,'provider clock residual exceeds frozen match window')
    review = exercise_wire()
    report = dict(state='0376-offline-verified',patch_sha256=scope.sha(scope.PATCH),native_schema_verified=True,
        controls=review['controls']+5,transport_replay=review,projected_display_wire_bytes=projection,
        old_display_wire_bytes=wire,reference_raw_bytes=reference_ring,projected_ring_bound=projected_ring,
        reference_crossing_rejected=True,reference_crossing_ns=old_crossing['duration_ns'],
        reference_runtime_unknown=True,reference_previously_guarded_starts=len(safe),
        reference_starts_that_would_need_an_earlier_window=sum(
            ((row.c>>32)-row.b)*3000<current.COPY_LEAD_NS for row in safe),
        maximum_prior_clock_residual_ns=residual,
        input_pins={str(path):scope.sha(path) for path in (scope.REFERENCE/'kernel.log',
            scope.P375/'partial-audit-0375.json',scope.P373/'execution/kernel.log',scope.CA_RANGES)},
        device_writes=0,device_boots=0)
    scope.save(scope.HOST,report)
    print(report)


if __name__=='__main__':
    check()
