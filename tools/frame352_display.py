"""Check GPU-ready retries and reconcile scanout with certified copies."""

from collections import Counter
import re

import frame344_log as trace
import frame351_display as present
from frame352_scope import COPY_BUDGET_NS

WAKE = 53


def check_wakes(rows, attempts, edges):
    taken = trace.indexed(rows[trace.ATTEMPT],lambda row:row.id,'present attempt')
    completed = trace.indexed(rows[trace.READY],lambda row:row.id,'GPU visibility')
    ended = trace.indexed(rows[trace.RESULT],lambda row:row.id,'present result')
    measured = trace.indexed(attempts,lambda row:row['attempt'],'measured present')
    event_joins = []
    slots = set()
    for event in trace.indexed(rows[WAKE],lambda row:row.id,'GPU-ready wake attempt').values():
        if event.id not in measured:
            continue
        retry = measured[event.id]
        prior_id, surface = event.a>>32,event.a&0xffffffff
        attempt, first, previous_end = taken.get(event.id),taken.get(prior_id),ended.get(prior_id)
        ready, edge = completed.get(event.b),edges.get(event.c)
        trace.require(event.flags==0 and surface and ready and edge and edge.flags==1 and
                      attempt and first and previous_end and previous_end.b==1 and
                      first.id<attempt.id and first.a==attempt.a and attempt.flags==first.flags+1 and
                      edge.b<=first.tick<=previous_end.tick<=event.tick<=attempt.tick and
                      first.tick<=ready.tick<=event.tick and event.c not in slots,
                      'GPU-ready retry lacks original refusal, same-slot identity or completion')
        slots.add(event.c)
        if prior_id in measured:
            guards = [g for g in measured[prior_id]['read_guards'] if not g['accepted'] and g['surface']==surface and
                      g['surface_ready_tick'] is not None and g['resolved_tick']<=g['surface_ready_tick']<=ready.tick]
            same_writer = any(g['fence']==event.b and g['surface_ready_tick']==ready.tick for g in guards)
            # A newer completion can replace the queued signal for the same ticket.
            later_writer = any(w.a==surface and w.id==event.b and
                any(g['surface_ready_tick']<=w.tick<=ready.tick for g in guards) for w in rows[trace.WRITER])
            trace.require(same_writer or later_writer,'GPU-ready retry does not match the original surface writer and guard')
        trace.require(all(proof['frame']==event.c for proof in retry['blanking_proofs']),
                      'GPU-ready retry copied or deferred in a different slot')
        event_joins.append(dict(initial_attempt=prior_id,retry_attempt=event.id,generation=attempt.a,
            surface=surface,fence=event.b,frame=event.c,ready_tick=ready.tick,wake_tick=event.tick,
            has_copy=bool(retry['layers']),blanking_proofs=retry['blanking_proofs']))
    return event_joins


def copy_certificates(attempts, edges, timing):
    certificates = {}
    for attempt in attempts:
        for layer in attempt['layers']:
            matching = [p for p in attempt['blanking_proofs'] if p['disposition']=='verified-blank' and
                        p['surface']==layer['surface']]
            trace.require(len(matching)<=1,'ambiguous copy boundary')
            if not matching:
                continue
            proof, = matching
            left = edges.get(proof['frame'])
            right = edges.get((proof['frame']+1)&0xffffffff)
            begin,end = layer['copy_start_tick'],layer['copy_end_tick']
            if (left and right and right.flags==left.flags==1 and left.b<=begin<end<=right.a and
                    timing.c<proof['begin_line']<=proof['finish_line']<proof['end_guard_line']<=timing.a):
                key = (attempt['attempt'], layer['surface'], begin, end)
                trace.require(key not in certificates,'duplicate copy boundary')
                certificates[key] = proof
    return certificates


def resolve_overlap(entry, certificates):
    if entry.get('reason')!='possible-mid-scan-copy' or entry['step']!=1:
        return []
    known = []
    for copy in entry['overlapping_copies']:
        link = copy['link']
        if not link:
            return []
        key = (link['attempt'],copy['surface'],copy['start_tick'],copy['end_tick'])
        proof = certificates.get(key)
        if not proof or proof['frame'] not in (entry['frame'],entry['previous_frame']):
            return []
        known.append(dict(copy_seq=copy['seq'],attempt=link['attempt'],**proof))
    return known


def analyze(text, frame, *, extra_kinds=(), copy_budget_ns=COPY_BUDGET_NS):
    rows,_,_,_ = trace.parse(text,extra_kinds=(present.PRESENT,WAKE,*extra_kinds))
    alignment = present.analyze(text,frame,copy_budget_ns=copy_budget_ns,allow_paired_copy=True,extra_kinds=(WAKE,*extra_kinds))
    opening = re.findall(r'^SWEET F352 READY: event=([01]) budget=(\d+)$',text,re.M)
    trace.require(len(opening)<=1 and all(int(budget)==copy_budget_ns for _,budget in opening),
                  'invalid GPU-ready event source configuration')
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'vblank frames')
    wakes = check_wakes(rows,alignment['attempts'],edges)
    timing, = rows[trace.TIMING]
    certificates = copy_certificates(alignment['attempts'],edges,timing)
    phase_totals = {phase:Counter() for phase in alignment['phases']}
    phase_attempts = {phase:set() for phase in alignment['phases']}
    for window, joined in zip(frame['hardware']['windows'],alignment['windows'],strict=True):
        trace.require((window['window'],window['stroke']+1)==(joined['phase'],joined['stroke']),
                      'display and stroke alignment differs')
        for entry,detail in zip(window['outputs'],joined['intervals'],strict=True):
            trace.require((entry['previous_frame'],entry['frame'])==(detail['previous_frame'],detail['frame']),
                          'display interval identity differs')
            phase_attempts[joined['phase']].update(detail['present_attempts'])
            proofs = resolve_overlap(entry,certificates)
            checked = detail['crc_relation'] if proofs else entry['classification']
            detail.update(after_copy_boundary_check=checked,certified_blanking_overlaps=proofs)
            phase_totals[joined['phase']][checked] += entry['step']
    for phase, counts in phase_totals.items():
        aligned = alignment['phases'][phase]
        timed_copies, paired_copies, late_deferrals = [], [], 0
        for attempt in alignment['attempts']:
            if attempt['attempt'] not in phase_attempts[phase]:
                continue
            copies = [layer['copy_ns'] for layer in attempt['layers']]
            timed_copies.extend(copies)
            if any(proof['paired_copy'] for proof in attempt['blanking_proofs']):
                paired_copies.extend(copies)
            late_deferrals += sum(p['disposition']=='deferred' and p['end_guard_line']>0 and
                                  (p['end_guard_line']-p['begin_line'])*present.MIN_LINE_NS<copy_budget_ns
                                  for p in attempt['blanking_proofs'])
        aligned.update(verified_full_frame_counts={k:counts[k] for k in ('changed','repeated','unknown')},
            copy_p95_ns=trace.quantile(timed_copies,.95),paired_copy_p95_ns=trace.quantile(paired_copies,.95),
            paired_copies=len(paired_copies),late_deferrals=late_deferrals,
            GPU_ready_retries=sum(row['retry_attempt'] in phase_attempts[phase] for row in wakes))
    paired_count = sum(proof['paired_copy'] for attempt in alignment['attempts'] for proof in attempt['blanking_proofs'])
    return dict(alignment,ready_event_configured=bool(opening and opening[0][0]=='1'),
                wake_joins=wakes,paired_copies=paired_count,independently_bounded_copies=len(certificates))
