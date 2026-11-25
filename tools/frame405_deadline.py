"""Classify moving-frame misses using bounded DPU and raw EOP receipts."""

from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
import re

import frame344_log as trace
from frame357_display import BOUND
from frame357_replay import TOTAL_LINES, END_LINE
from frame358_display import LOCK_RETRY, PROBE, RESULTS


@dataclass(frozen=True)
class Completion:
    ticket: int
    fence: int
    frame: int
    line: int
    stroke: int
    last_pending_begin: int
    first_match_end: int


def writers(rows):
    swaps = trace.indexed((r for r in rows[trace.SWAP] if not r.flags and r.c),
                         lambda r:r.id,'accepted display generation')
    claims = trace.indexed(rows[BOUND],lambda r:r.id,'display producer claim')
    writes = trace.indexed((r for r in rows[trace.WRITER] if r.b),
                          lambda r:r.b>>32,'bound display writer')
    issue, eop, visible = (trace.indexed(rows[k],lambda r:r.id,'native fence')
                           for k in (trace.ISSUE,trace.EOP,trace.READY))
    for generation, rec in writes.items():
        claim, swap = claims[generation], swaps[generation]
        trace.require((claim.a,claim.b,swap.c)==(rec.b,rec.c,(rec.c<<32)|rec.a) and
                      swap.tick<=claim.tick<=issue[rec.id].tick<=rec.tick,
                      'motion writer has no exact ordered producer claim')
    return swaps,writes,issue,eop,visible


def completion_samples(raw,rows,strokes):
    count,lost = map(int,trace.one(r'^SWEET EOP405: samples=(\d+) lost=(\d+)$',raw,'raw EOP header'))
    lines = re.findall(r'^EOP405 ([a-f0-9 ]+)$',raw,re.M)
    trace.require(len(lines)==count and 0<=count<=256 and lost==0,'raw EOP capture exceeds its scope')
    samples = [Completion(*(int(word,16) for word in line.split())) for line in lines]
    _,bound,issue,eop,visible = writers(rows)
    prior_fence, prior_sample = 0,0
    for item in samples:
        writer = bound[item.ticket>>32]
        begin,end = item.last_pending_begin,item.first_match_end
        observed = eop.get(item.fence)
        last_tick = end or begin
        trace.require(item.fence>prior_fence and last_tick>prior_sample and
                      (item.ticket,item.fence)==(writer.b,writer.id) and
                      0<=item.line<TOTAL_LINES and 3<=item.stroke<=13 and
                      strokes[item.stroke-1][0]<=last_tick<=strokes[item.stroke-1][1]+672_000 and
                      (not end or begin<end) and issue[writer.id].tick<=last_tick and
                      (not begin or not observed or begin<observed.tick) and
                      (item.fence not in visible or observed is not None),
                      'raw EOP sample lacks exact issue identity or ordered bounds')
        prior_fence,prior_sample = item.fence,last_tick
    return trace.indexed(samples,lambda item:item.fence,'sampled raw EOP')


def motion_scans(scans,measurement):
    lanes = {(workload,w['stroke']):w for workload in ('ordinary','slow_drag')
             for w in measurement['moving_GPU'][workload]['windows']}
    return [s for s in scans if s['phase']=='active' and
            (lane:=lanes.get((s['workload'],s['stroke']))) is not None and
            lane['first_scan']<=s['frame']<=lane['last_scan']]


def repeat_deadlines(rows,scans,latches,measurement,raw_samples):
    swaps,bound,issues,eops,ready = writers(rows)
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'DPU edge')
    probes = trace.indexed(rows[PROBE],lambda r:r.id,'DPU probe scan')
    retries = trace.indexed(rows[LOCK_RETRY],lambda r:r.id,'DPU retry scan')
    present_scans = sorted(latches)
    cutoff_line = END_LINE-192  # Same last line accepted by the private page flip.
    repeats = []
    for scan in motion_scans(scans,measurement):
        if scan['crc']!='repeated':
            continue
        frame = scan['frame']
        left, right = edges[(frame-1)&0xffffffff], edges[frame]
        trace.require(left.flags==right.flags==1 and left.b<right.a,
                      'repeat has no consecutive hardware brackets')
        early,late = (((TOTAL_LINES-cutoff_line)*getattr(left,boundary)+
                       cutoff_line*getattr(right,boundary))//TOTAL_LINES for boundary in ('a','b'))
        ix = bisect_left(present_scans,frame)
        generation = latches[present_scans[ix-1]]['generation'] if ix else 0
        candidates = []
        for swap in swaps.values():
            if swap.id<=generation or swap.tick>early:
                continue
            writer = bound.get(swap.id)
            candidate = dict(generation=swap.id,swap_tick=swap.tick,stage='no_exact_writer')
            if writer:
                fence = writer.id
                issue = issues[fence].tick
                guard, cache = (table[fence].tick if fence in table else None for table in (eops,ready))
                stage = ('awaiting_issue' if issue>early else 'awaiting_guarded_EOP' if guard is None or guard>early
                         else 'awaiting_cache_visibility' if cache is None or cache>early else 'cache_visible')
                candidate.update(fence=fence,issue_tick=issue,guarded_EOP_tick=guard,cache_visible_tick=cache,stage=stage)
                if sample := raw_samples.get(fence):
                    lower, upper = sample.last_pending_begin,sample.first_match_end
                    candidate.update(last_pending_begin=lower or None,raw_match_end=upper or None,
                        raw_EOP_at_cutoff=('ready_by_earliest_cutoff' if upper and upper<=early else
                                           'pending_past_latest_cutoff' if lower>late else 'unresolved'))
            candidates.append(candidate)
        probe, retry = probes.get(left.id),retries.get(left.id)
        repeats.append(dict(workload=scan['workload'],stroke=scan['stroke'],scan=frame,
            cutoff_ticks=[early,late],same_crc_confirmed_latch=frame in latches,
            preceding_latch_generation=generation,probe=RESULTS[probe.flags] if probe else None,
            retry=RESULTS[retry.flags] if retry else None,candidates=candidates))
    buckets = {}
    order = ('no_accepted_swap','no_exact_writer','awaiting_issue','awaiting_guarded_EOP',
             'awaiting_cache_visibility','cache_visible','same_crc_latch')
    for row in repeats:
        candidates = row['candidates']
        stage = ('same_crc_latch' if row['same_crc_confirmed_latch'] else
                 max((c['stage'] for c in candidates),key=order.index,default='no_accepted_swap'))
        row['strongest_observed_candidate'] = stage
        timing = {c.get('raw_EOP_at_cutoff') for c in candidates if c['stage']=='awaiting_guarded_EOP'}
        if stage=='awaiting_guarded_EOP':
            row['raw_EOP_at_cutoff'] = ('ready_by_earliest_cutoff' if 'ready_by_earliest_cutoff' in timing else
                'pending_past_latest_cutoff' if timing=={'pending_past_latest_cutoff'} else 'unresolved')
        counts = buckets.setdefault(row['workload'],Counter())
        counts[stage] += 1
        if 'raw_EOP_at_cutoff' in row:
            counts[row['raw_EOP_at_cutoff']] += 1
    return dict(repeats_by_stage={k:dict(v) for k,v in buckets.items()},repeats=repeats,
        cutoff_line=cutoff_line,raw_EOP_observations=len(raw_samples),
        scope='Exact GPU word only. Cache visibility, readable surface version and latch are separate checks.')
