#!/usr/bin/env python3
"""Separate screen response onset from cadence once the image is changing."""

import argparse
from collections import Counter
from importlib import import_module
import json
from pathlib import Path

from frame364_analysis import motion_deadlines, score, trace

pacing = import_module('audit-frame-pacing')
boundaries = import_module('audit-frame366-restored')


def ready_shift_bound(misses, events, ns):
    accepted = trace.indexed((r for r in events[trace.SWAP] if not r.flags and r.c),
                             lambda r:r.id,'eligible generation')
    writers = trace.indexed((r for r in events[trace.WRITER] if r.b),
                            lambda r:r.b>>32,'generation writer')
    visible = trace.indexed(events[trace.READY],lambda r:r.id,'visible fence')
    needed = {}
    considered = set()
    for miss in misses:
        if miss['stroke']<3 or not miss['next_swap_within_stroke_tail']:
            continue
        gen = miss['next_swap']['generation']
        considered.add(gen)
        writer = writers.get(gen)
        ready = visible.get(writer.id) if writer else None
        if not ready:
            continue
        swap = accepted[gen]
        trace.require(swap.c==((writer.c<<32)|writer.a),'next ready frame uses another source')
        lead = max(0,ns(max(swap.tick,ready.tick))-miss['deadline_ns'])
        needed[gen] = min(needed.get(gen,lead),lead)
    return dict(unique_next_swap_generations=len(considered),with_exact_ready_fence=len(needed),
        minimum_advance_ns_by_generation=needed,one_scan_advance_candidates=sum(n<=16_666_667 for n in needed.values()),
        two_scan_advance_candidates=sum(n<=33_333_334 for n in needed.values()),
        interpretation=('Arithmetic release bounds hold the observed writer identities fixed. '
            'Each generation is counted once. Earlier ready time is a prerequisite for, and '
            'does not establish, a safe copy or a distinct image.'))


def measure(execution, scope_file, *, result=None):
    pacing.check_restored(execution,result=result)
    path = execution/'frame-scanout-analysis.json'
    scan = score.load(path)
    report = score.load(scope_file)
    raw = (execution/'kernel.log').read_text()
    capture = score.copy.analyze(raw,scan,extra_kinds=score.KINDS)
    events,_,numer,denom = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    timing, = events[trace.TIMING]
    edges,_ = boundaries.refine_post_copy_edges(events,capture,timing)
    refined = events | {trace.VBLANK:list(edges.values())}
    core = score.load(execution/'core-wait-execution-analysis.json')
    io = score.load(execution/'kernel-IO-identity-analysis.json')
    trace.require(core['coverage_qualified'] and io['coverage_qualified'],'missing exact writer coverage')
    ns = lambda tick: tick*numer//denom
    swaps = [r for r in events[trace.SWAP] if not r.flags and r.c]
    refine = {(x['stroke'],x['phase'],x['frame']):x['classification'] for x in report['resolved_scans']}
    misses = report['frontend_cutoffs']['details']
    strokes = []
    for window,lane in zip(scan['hardware']['windows'],capture['windows'],strict=True):
        if lane['phase']!='active':
            continue
        index = lane['stroke']
        trace.require(window['stroke']+1==index,'window stroke ordinal differs')
        first_tick, last_tick = window['start_tick'],window['end_tick']
        series = [(o,refine.get((index,'active',o['frame']),a['after_copy_boundary_check']))
                  for o,a in zip(window['outputs'],lane['intervals'],strict=True)]
        changes = [i for i,(_,category) in enumerate(series) if category=='changed']
        first = series[changes[0]][0] if changes else None
        last = series[changes[-1]][0] if changes else None
        if first:
            bounds = [ns(first[k])-ns(first_tick) for k in ('edge_lower_tick','edge_upper_tick')]
            section = Counter(c for _,c in series[changes[0]:changes[-1]+1])
            before_first = Counter(c for _,c in series[:changes[0]])
        else:
            bounds,section,before_first = None,Counter(),Counter(c for _,c in series)
        changing_span = None
        if len(changes)>1 and not section['unknown']:
            changing_span = [
                ns(last['edge_lower_tick'])-ns(first['edge_upper_tick']),
                ns(last['edge_upper_tick'])-ns(first['edge_lower_tick']),
            ]
            trace.require(0<changing_span[0]<=changing_span[1],'changing span edges differ')
        repeat_stages = []
        if index>=3 and changing_span:
            intervals = [dict(row,after_copy_boundary_check=category) for row,(_,category)
                in zip(lane['intervals'][changes[0]:changes[-1]+1],
                       series[changes[0]:changes[-1]+1],strict=True)]
            selected = dict(capture,windows=[dict(lane,intervals=intervals)])
            repeat_stages = motion_deadlines(refined,selected,core,io,ns,numer/denom)['repeats']
            trace.require(len(repeat_stages)==section['repeated'],'moving repeat coverage differs')
        relevant = [m for m in misses if m['stroke']==index]
        no_swap = [dict(frame=m['scan'],since_input_ns=m['deadline_ns']-ns(first_tick),
            phase=('before_first_certified_change' if first and m['deadline_ns']<ns(first['edge_lower_tick'])
                   else 'after_first_change' if first and m['deadline_ns']>=ns(first['edge_upper_tick'])
                   else 'onset_unresolved')) for m in relevant]
        first_swap = next((r for r in swaps if first_tick<=r.tick<=last_tick),None)
        direction = 'up' if index==1 else 'left' if index%2==0 else 'right'
        strokes.append(dict(stroke=index,direction=direction,
            first_new_image_ns=bounds,first_new_image_frame=first['frame'] if first else None,
            earliest_possible_if_unknown_before_first=bool(before_first['unknown']),
            first_accepted_swap_ns=ns(first_swap.tick)-ns(first_tick) if first_swap else None,
            elapsed_ns_first_through_last_new_image=changing_span,
            first_to_last_new_image_scans=dict(section),pre_onset_scans=dict(before_first),
            scans=dict(Counter(c for _,c in series)),no_swap=no_swap,verified_repeat_stages=repeat_stages))
    trace.require([row['stroke'] for row in strokes]==list(range(1,14)),'original workload differs')
    direction = {}
    for name in ('left','right'):
        lane = [r for r in strokes if r['stroke']>=3 and r['direction']==name]
        phases = Counter(item['phase'] for r in lane for item in r['no_swap'])
        verified = [r['first_new_image_ns'] for r in lane if r['first_new_image_ns'] and
                    not r['earliest_possible_if_unknown_before_first']]
        active = Counter()
        repeat_partition = Counter()
        for r in lane:
            active.update(r['first_to_last_new_image_scans'])
            for repeat in r['verified_repeat_stages']:
                stages = sorted({x['stage'] for x in repeat['accepted_candidates']})
                reason = ('safe_copy_same_CRC' if repeat['same_CRC_copy'] else
                          '+'.join(stages) if stages else 'no_eligible_swap')
                repeat_partition[reason] += 1
        spans = [r['elapsed_ns_first_through_last_new_image'] for r in lane]
        rate = None
        if all(spans):
            changes = active['changed']-len(lane)
            rate = [changes*1e9/sum(s[i] for s in spans) for i in (1,0)]
        direction[name] = dict(strokes=len(lane),verified_onset=len(verified),
            first_new_image_p50_ns=[trace.quantile([r[i] for r in verified],.50) for i in (0,1)],
            before_and_after_first_new_image_no_swap=dict(phases),
            first_to_last_new_image_scans=dict(active),new_images_per_second_during_motion_bounds=rate,
            candidate_states_at_moving_repeat_cutoffs=dict(repeat_partition))
    return dict(warm_by_direction=direction,strokes=strokes,
        ready_shift_bound=ready_shift_bound(misses,events,ns),
        interpretation=('Input onset is the first injected report. A changed full-frame CRC is the '
            'first certified new screen image and can include pixels outside the gesture.'))


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('execution',type=Path)
    cli.add_argument('scoped_report',type=Path)
    args = cli.parse_args()
    print(json.dumps(measure(args.execution,args.scoped_report),indent=2))
