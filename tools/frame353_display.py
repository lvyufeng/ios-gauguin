"""Validate the held readiness observation and its subsequent scan selection."""

from bisect import bisect_right
from collections import defaultdict

import frame344_log as trace
import frame351_display as present
import frame352_display as copy

READY, TAKE = 54, 55
KINDS = (READY, TAKE)
UNKNOWN_FRAME = (1<<64)-1
MASK32 = (1<<32)-1


def ready_joins(rows, attempts):
    marked = defaultdict(list)
    for row in rows[READY]:
        marked[row.id].append(row)
    completed = trace.indexed(rows[trace.READY],lambda row:row.id,'GPU completion')
    swaps = trace.indexed(rows[trace.SWAP],lambda row:row.id,'swap generation')
    accepted = [row for row in rows[trace.SWAP] if row.flags==0]
    accepted_order = [(row.tick,row.seq) for row in accepted]
    taken = trace.indexed(rows[TAKE],lambda row:row.id,'ready frame selection')
    measured = trace.indexed(attempts,lambda row:row['attempt'],'measured frame selection')
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'hardware frame edge')
    hardware_frames = set()
    joined = []
    for attempt in attempts:
        take = taken.get(attempt['attempt'])
        receipts = attempt['blanking_proofs']
        trace.require(not receipts or take is not None,'blanking copy has no ready selection')
        if take is None:
            continue
        swap = swaps.get(attempt['generation'])
        latest = bisect_right(accepted_order,(take.tick,take.seq))-1
        history = [r for r in marked[take.a] if (r.tick,r.seq)<(take.tick,take.seq)]
        mark = history[-1] if history else None
        edge = edges.get(take.c)
        trace.require(swap and latest>=0 and swap==accepted[latest] and
                      mark and swap.tick<=mark.tick<=take.tick<=attempt['attempt_tick'] and
                      mark.id==take.a==attempt['generation'] and
                      mark.a and mark.flags in (0,1) and edge and edge.flags==1 and take.c not in hardware_frames,
                      'selection lacks earlier readiness, a unique hardware slot or the latest valid swap')
        trace.require(take.b==mark.c and (take.b==UNKNOWN_FRAME or 0<=take.b<=MASK32),
                      'readiness frame differs from its selection')
        delta = None if take.b==UNKNOWN_FRAME else (take.c-take.b)&MASK32
        trace.require((delta is None or delta<(1<<31)) and take.flags==int(bool(delta)),
                      'invalid cross-frame selection or marker')
        if not mark.flags:
            fence = completed.get(mark.b)
            trace.require(fence and fence.tick<=mark.tick,'async readiness lacks GPU completion')
        else:
            trace.require(mark.b==0,'poll readiness carried a fence')
        guards = attempt['read_guards']
        trace.require(all(p['frame']==take.c and p['surface']==mark.a for p in receipts) and
                      all(any(g['accepted'] and g['surface']==layer['surface']==mark.a for g in guards)
                          for layer in attempt['layers']), 'copy lacks target-slot or fresh GPU read evidence')
        hardware_frames.add(take.c)
        joined.append(dict(attempt=take.id,generation=take.a,surface=mark.a,fence=mark.b or None,
            observation='probe' if mark.flags else 'GPU-completion',observed_frame=None if delta is None else mark.c,
            target_frame=take.c,frame_delay=delta,ready_tick=mark.tick,take_tick=take.tick,
            carried=bool(delta),copied=bool(attempt['layers']),
            verified_blank=any(p['disposition']=='verified-blank' for p in receipts)))
    trace.require(len(joined)==sum(identifier in measured for identifier in taken),'ready-selection joins differ')
    return joined


def analyze(text, aligned):
    rows,_,numer,denom = trace.parse(text,extra_kinds=(present.PRESENT,copy.WAKE,*KINDS))
    trace.require(not rows[copy.WAKE],'same-slot 0352 wake wire in cross-frame mode')
    joined = ready_joins(rows,aligned['attempts'])
    summary = {}
    for phase in ['active','release','all']:
        ids = {i for w in aligned['windows'] if w['phase']==phase
               for item in w['intervals'] for i in item['present_attempts']}
        sample = joined if phase=='all' else [row for row in joined if row['attempt'] in ids]
        carried = [row for row in sample if row['carried']]
        summary[phase] = dict(selections=len(sample),GPU_completion_selections=sum(row['observation']=='GPU-completion' for row in sample),
            cross_frame_selections=len(carried),cross_frame_copies=sum(row['copied'] for row in carried),
            cross_frame_verified_copies=sum(row['verified_blank'] for row in carried),
            ready_to_selection_p95_ns=trace.quantile([(row['take_tick']-row['ready_tick'])*numer/denom for row in sample],.95))
    return dict(phases=summary,ready_receipts=len(rows[READY]),selection_receipts=len(rows[TAKE]),joins=joined)
