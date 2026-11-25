"""Decode independent 0376 display, live-message and guarded-copy lanes."""

from base64 import b64decode
from collections import Counter
import re
from struct import Struct

import frame344_log as frame
import frame374_native_ca as native
from frame373_receipts import decode_with_unmatched

DISPLAY_BYTES = 164_000
DISPLAY_THREADS = 32
PACKET_BYTES = 110_000
PACKET_THREADS = 64
COPY_CAP = 32
LONG_COPY_TICKS = 96_000
COPY_LEAD_NS = 6_700_000
RECEIPT_TOLERANCE_NS = 2_000
COMMON_ID = 40002
PREFIX = Struct('<IHBBB')
U32 = Struct('<I')
COPY = re.compile(r'^SWEET F376 C: attempt=(\d+) begin=(\d+) end=(\d+) cpu_begin=(\d+) cpu_end=(\d+)$')
DISPLAY_KINDS = {native.BEGIN,native.END,native.ANNOTATION,native.FRAME_INFO,native.RENDER_TIME,
                 native.VSYNC,native.VSYNC_UPDATE,native.DRIVER_TARGET,native.DRIVER_DELIVERY}


def read_uleb(data, offset):
    value = 0
    for shift in range(0,35,7):
        frame.require(offset<len(data), 'truncated packet delta')
        current = data[offset]
        value |= (current & 0x7f)<<shift
        offset += 1
        if current<0x80:
            frame.require(value<=0xffffffff and (shift==0 or current), 'invalid packet delta')
            return value, offset
    raise ValueError('packet delta exceeds 32 bits')


def compact_rows(data, count):
    offset = 0
    for _ in range(count):
        frame.require(offset+PREFIX.size<=len(data), 'truncated packet identity')
        send,serial,source,dest,tag = PREFIX.unpack_from(data,offset)
        offset += PREFIX.size
        if tag == 4:
            frame.require(offset+U32.size<=len(data), 'truncated uncommon packet ID')
            message, = U32.unpack_from(data,offset)
            frame.require(not COMMON_ID<=message<COMMON_ID+4, 'noncanonical packet ID')
            offset += U32.size
        else:
            frame.require(tag<4, 'invalid common packet ID')
            message = COMMON_ID+tag
        post,offset = read_uleb(data,offset)
        done,offset = read_uleb(data,offset)
        yield serial,message,send,post,done,source,dest
    frame.require(offset==len(data), 'trailing bytes in compact transport block')


def display_lane(raw, start, end, *, byte_limit=DISPLAY_BYTES):
    events = native.decode(raw,start,end)
    kinds = Counter(row.kind for row in events)
    threads,size = map(int,frame.one(r'^SWEET F374 F: rows=\d+ threads=(\d+) bytes=(\d+) lost=0$',
                                     raw,'0376 display capacity'))
    frame.require(threads<=DISPLAY_THREADS and size<=byte_limit and
                  set(kinds)<=DISPLAY_KINDS and all(kinds[k] for k in
                  (native.FRAME_INFO,native.DRIVER_TARGET,native.DRIVER_DELIVERY)),
                  'FrameInfo lane unavailable or outside its independent budget')
    return events,dict(wire_bytes=size,threads=threads,kinds={native.NAMES[k]:v for k,v in kinds.items()})


def packet_lane(raw, n, d, *, byte_limit=PACKET_BYTES, require_no_transport_errors=True,
                allow_refused_prefix=False):
    blocks = re.findall(r'^SWEET F376 P \d+ \d+ ([A-Za-z0-9+/=]+)$',raw,re.M)
    size = sum(len(b64decode(line,validate=True)) for line in blocks)
    frame.require(blocks and 0<size<=byte_limit,'transport length or reservation differs')
    transport = decode_with_unmatched(raw,n,d,block_type='F376 P',read_rows=compact_rows,
                                      thread_cap=PACKET_THREADS,allow_refused_prefix=allow_refused_prefix)
    if not transport['losses'].get('unexported_tail'):
        count,declared = map(int,frame.one(r'^SWEET F376 P footer: rows=(\d+) bytes=(\d+)$',raw,'packet footer'))
        frame.require(count==transport['paired_exact_receipts'] and size==declared,'transport footer differs')
    else:
        frame.require(not re.search(r'^SWEET F376 P footer:',raw,re.M),'ambiguous packet export status')
    if require_no_transport_errors:
        frame.require(not any(transport['losses'][key] for key in
                      ('cap_saturation','tagging_errors','unmatched_without_timestamp')), 'transport lane incomplete')
    return dict(transport,wire_bytes=size)


def copy_tails(raw, attempts, start, end, n, d):
    frame.require((n,d)==(625,12), 'copy runtime clock differs')
    rows,lost = map(int,frame.one(r'^SWEET F376 C footer: rows=(\d+) lost=(\d+)$',raw,'copy runtime footer'))
    lines = COPY.findall(raw)
    frame.require(len(lines)==rows<=COPY_CAP and lost==0, 'copy timing records lost')
    valid = {(row['attempt'],layer['copy_start_tick'],layer['copy_end_tick']) for row in attempts
             for layer in row['layers']}
    observed = set()
    report = []
    for text in lines:
        attempt,begin,finish,on_begin,on_end = map(int,text)
        key = (attempt,begin,finish)
        frame.require(key not in observed and start<=begin<finish<end and
                      finish-begin>=LONG_COPY_TICKS and on_begin<=on_end,
                      'invalid copy runtime interval or identity')
        observed.add(key)
        wall = (finish-begin)*n/d
        accounted = (on_end-on_begin)*n/d
        report.append(dict(attempt=attempt,begin_tick=begin,end_tick=finish,wall_ns=wall,
                           thread_runtime_upper_ns=accounted,
                           wall_minus_runtime_lower_ns=max(0,wall-accounted),
                           matches_scored_guarded_copy=key in valid))
    return report
