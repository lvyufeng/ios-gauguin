"""Verify an early guarded wake against the raw completion and exact latch."""

from collections import Counter

import frame344_log as trace
from frame358_display import LOCK_RETRY, PROBE, RAW_PROBE, PROBE_LIMIT, RESULTS
from frame405_deadline import writers


def measure(rows,latches,samples,motion):
    events = rows[RAW_PROBE]
    trace.require(len(rows[PROBE])+len(rows[LOCK_RETRY])+len(events)<=PROBE_LIMIT,
                  'raw and inherited polls exceed their combined quota')
    _,bound,issues,eops,ready = writers(rows)
    scan_by_generation = {latch['generation']:scan for scan,latch in latches.items()}
    before = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'DPU edge')
    seen,receipts = set(),[]
    for record in events:
        ticket = record.a
        generation = ticket>>32
        version,fence = divmod(record.b,1<<32)
        writer = bound[generation]
        sample = samples[writer.id]
        trace.require(record.flags in RESULTS and writer.id not in seen and
                      (writer.b,writer.c)==(ticket,version) and sample.ticket==ticket and
                      sample.first_match_end and sample.first_match_end<=record.c<=record.tick and
                      issues[writer.id].tick<=sample.first_match_end and
                      record.id in before and before[record.id].b<=record.c and
                      ((record.id-sample.frame)&0xffffffff)<=1 and (bool(fence)==(record.flags==4)),
                      'raw wake lacks its exact completion, writer or DPU bracket')
        seen.add(writer.id)
        target = (record.id+1)&0xffffffff
        if fence:
            trace.require(fence==writer.id and record.c<=eops[fence].tick<=ready[fence].tick<=record.tick,
                          'raw wake skipped guarded completion or cache visibility')
        latched = scan_by_generation.get(generation)
        receipt = dict(generation=generation,scan=record.id,fence=writer.id,
            native_guard_result=RESULTS[record.flags],raw_match_end=sample.first_match_end,
            guarded_probe_start_tick=record.c,guarded_probe_finish_tick=record.tick,
            next_scan_latched=bool(fence and latched==target),
            warm_motion=any(w['first_scan']<=target<=w['last_scan'] for w in motion['ordinary']['windows']))
        if fence:
            receipt.update(guarded_EOP_tick=eops[fence].tick,cache_visible_tick=ready[fence].tick)
        receipts.append(receipt)
    return dict(wakes=len(receipts),results=dict(Counter(r['native_guard_result'] for r in receipts)),
        next_scan_latches=sum(r['next_scan_latched'] for r in receipts),
        warm_next_scan_latches=sum(r['next_scan_latched'] and r['warm_motion'] for r in receipts),
        receipts=receipts)
