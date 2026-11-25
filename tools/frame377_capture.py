"""Verify phase timing for full guarded copies and the bounded live IPC table."""

from base64 import b64decode, b64encode
import re
from struct import Struct

import frame344_log as frame
import frame376_capture as base

DISPLAY_BYTES = 155_000
PACKET_BYTES = 104_000
COPY_BUDGET_NS = 5_500_000
COPY_CAP = 1024
COPY_BLOCK = 32
COPY_ROW = Struct('<HIIII')
BLOCK = re.compile(r'^SWEET F377 C (\d+) (\d+) ([A-Za-z0-9+/]+={0,2})$',re.M)


def pack_stats(raw, n, d):
    transport = base.packet_lane(raw,n,d,byte_limit=PACKET_BYTES,require_no_transport_errors=False)
    buckets,ways,spill,full = map(int,frame.one(
        r'^SWEET F377 IPC: buckets=(\d+) ways=(\d+) spill=(\d+) full=(\d+)$',raw,'0377 IPC table'))
    counts = transport['counters']
    frame.require((buckets,ways)==(4096,4) and not counts['evicted'] and not counts['busy'] and
                  spill+full<=counts['sent'], 'IPC table configuration or counters differ')
    return dict(transport,table=dict(buckets=buckets,ways=ways,additional_ways_used=spill,bucket_full=full))


def wire_rows(raw):
    size,lost = map(int,frame.one(r'^SWEET F377 C footer: rows=(\d+) lost=(\d+)$',raw,'copy phase footer'))
    frame.require(size<=COPY_CAP, 'copy phase reservation exceeded')
    rows = []
    for ordinal,count,encoded in BLOCK.findall(raw):
        ordinal,count = int(ordinal),int(count)
        frame.require(ordinal==len(rows) and 0<count<=COPY_BLOCK and ordinal+count<=size and
                      (count==COPY_BLOCK or ordinal+count==size), 'missing or oversized copy phase block')
        data = b64decode(encoded,validate=True)
        frame.require(len(data)==count*COPY_ROW.size and b64encode(data).decode()==encoded,
                      'copy phase wire length or padding differs')
        rows.extend(COPY_ROW.iter_unpack(data))
    frame.require(len(rows)==size,'copy phase record count differs')
    return rows,lost


def copies(raw, rows, attempts, start, end, n, d):
    records,lost = wire_rows(raw)
    body = frame.indexed((row for row in rows[frame.COPY] if row.c==frame.FRAME_BYTES),
                         lambda row:(row.a,row.b),'full framebuffer copy timestamp')
    began = frame.indexed(rows[frame.ATTEMPT],lambda row:row.id,'attempt entry')
    ended = frame.indexed(rows[frame.RESULT],lambda row:row.id,'attempt return')
    recorded = set()
    exports = []
    scale = n/d
    for attempt,offset,stores,barrier,cpu in records:
        first = start+offset
        last = first+stores+barrier
        copy = body.get((first,last))
        frame.require(attempt not in recorded and start<=first<last<end and copy and
                      attempt in began and attempt in ended and began[attempt].tick<=first and
                      last<=copy.tick<=ended[attempt].tick,
                      'copy timing does not match the full F344 copy and attempt interval')
        recorded.add(attempt)
        exports.append(dict(attempt=attempt,surface=copy.id,begin_tick=first,stores_tick=first+stores,end_tick=last,
            read_write_body_ns=stores*scale,barrier_envelope_ns=barrier*scale,total_ns=(stores+barrier)*scale,
            thread_runtime_upper_ns=cpu*scale,wall_minus_thread_runtime_lower_ns=max(0,stores+barrier-cpu)*scale))
    scored = {a['attempt'] for a in attempts if any(p['paired_copy'] and p['disposition']!='deferred'
        for p in a['blanking_proofs']) and any(l['bytes']==frame.FRAME_BYTES for l in a['layers'])}
    unmatched = sorted(scored-recorded)
    quantiles = {}
    for key in ('read_write_body_ns','barrier_envelope_ns','total_ns','thread_runtime_upper_ns'):
        values = [row[key] for row in exports]
        quantiles[key] = dict(p50=frame.quantile(values,.5),p95=frame.quantile(values,.95),
            p99=frame.quantile(values,.99),max=max(values,default=None))
    return dict(records=len(exports),lost=lost,missing_scored_attempts=unmatched,full_capture_qualified=bool(
        exports and not lost and not unmatched),quantiles=quantiles,rows=exports)
