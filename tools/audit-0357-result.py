#!/usr/bin/env python3
"""Audit the restored 0357 capture and join the final scored CRC to its copy."""

from collections import Counter
from importlib import import_module
import json
from statistics import median

import frame344_log as trace
import frame352_display as copy
import frame354_display as ready
from frame356_display import matched_latencies
from frame356_scope import REF350, REF355
from frame357_display import BOUND, CALIBRATION, KINDS, compare
from frame357_scope import BASE, REF356, load, require, sha

EXEC = BASE/'execution'
run = import_module('run-frame357-trial')
input_traces = import_module('run-frame350-trial').trace_inputs


def recover_tail(raw, frame, rows, strokes, numer, denom, inputs):
    # The post-active CRC in the last scored hardware slot can overlap a
    # blanking copy whose take starts after the nominal software cutoff.
    tail = next(w for w in frame['hardware']['windows'] if (w['stroke'],w['window'])==(12,'release'))
    output = tail['outputs'][-1]
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'hardware edge')
    next_edge = edges[(output['frame']+1)&0xffffffff]
    cutoff = strokes[-1][1]+250_000_000*denom//numer
    require(edges[output['frame']].flags==next_edge.flags==1 and next_edge.a>cutoff,'invalid tail edge')
    original = frame['attempts']
    core,identity,_ = inputs
    extended = trace.software(rows,identity['submits'],core['rows'],strokes[0][0]-25_000_000*denom//numer,
                              next_edge.b,numer,denom)
    require(extended[:len(original)]==original and len(extended)==len(original)+1,'unexpected added attempts')
    extra = extended[-1]
    layer, = extra['layers']
    missing = [r for r in output['overlapping_copies'] if not r['link']]
    unresolved, = missing
    require(output['classification']=='unknown' and cutoff<extra['attempt_tick']<next_edge.a and
            (unresolved['surface'],unresolved['start_tick'],unresolved['end_tick'])==
            (layer['surface'],layer['copy_start_tick'],layer['copy_end_tick']), 'missing exact tail copy')
    unresolved['link'] = dict(generation=extra['generation'],attempt=extra['attempt'],layer=layer)
    frame['attempts'] = extended
    display = copy.analyze(raw,frame,extra_kinds=KINDS)
    selection = ready.analyze(raw,display,binding_kind=BOUND,extra_kinds=(CALIBRATION,))
    resolved = display['windows'][-1]['intervals'][-1]
    require(resolved['frame']==output['frame'] and resolved['after_copy_boundary_check']=='changed' and
            len(resolved['certified_blanking_overlaps'])==2 and
            any(r['attempt']==extra['attempt'] and r['guarded'] and r['copied'] for r in selection['joins']),
            'tail did not pass the existing guard and boundary checks')
    return display,dict(phase='release',stroke=13,previous_classification='unknown',
        hardware_frame=output['frame'],analysis_cutoff_tick=cutoff,
        extended_attempt_end_tick=next_edge.b,attempt=extra['attempt'],native_fence=layer['native_fence'],
        margin_to_next_edge_lower_ns=(next_edge.a-layer['copy_end_tick'])*numer/denom,
        endpoint_proofs=resolved['certified_blanking_overlaps'])


def pacing(path, kinds):
    frame = load(path/'frame-scanout-analysis.json')
    rows,_,n,d = trace.parse((path/'kernel.log').read_text(),extra_kinds=(52,53,*kinds))
    scale = n/d
    windows = [w for w in frame['hardware']['windows'] if w['window']=='active']
    spans = [(w['vblank_edges'][0]['edge_upper_tick'],w['vblank_edges'][-1]['edge_upper_tick']) for w in windows]
    within = lambda t: any(a<t<=b for a,b in spans)
    swaps = [row for row in rows[trace.SWAP] if not row.flags]
    arrivals = [r for r in swaps if within(r.tick)]
    timings = []
    for lo,hi in spans:
        stamps = [s.tick for s in arrivals if lo<s.tick<=hi]
        require(stamps,'missing swipe arrivals')
        timings.append((stamps[0]-lo,stamps[-1]-stamps[0],len(stamps)-1))

    issues = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'issue')
    eops = trace.indexed(rows[trace.EOP],lambda r:r.id,'EOP')
    visible = trace.indexed(rows[trace.READY],lambda r:r.id,'visibility')
    require(issues.keys()==eops.keys()==visible.keys() and
            all(ready.order(issue)<ready.order(eops[fence])<ready.order(visible[fence]) for fence,issue in issues.items()) and
            all(left.id<right.id and ready.order(visible[left.id])<ready.order(right)
                for left,right in zip(rows[trace.ISSUE],rows[trace.ISSUE][1:])), 'incomplete or nonserial fence stream')
    writers = {(r.b>>32,r.a,r.c):r for r in rows[trace.WRITER] if r.b}
    successor = {a.id:b for a,b in zip(swaps,swaps[1:])}
    matching = {s.id:w for s in arrivals if (w:=writers.get((s.id,s.c&0xffffffff,s.c>>32)))}
    overtaken = {k for k,w in matching.items() if k in successor and
                 ready.order(successor[k])<ready.order(visible[w.id])}
    promoted = {r.id for r in rows[ready.PROMOTE]}

    core,identity,io = input_traces(path)
    matched = matched_latencies(core,identity,io)
    keys = {(r['queue'],r['ticket'],r['job']) for r in core['rows'] if within(r['enq_ns']/scale)}
    sampled = [r for r in matched['submissions'] if (r['queue'],r['ticket'],r['job']) in keys]
    phase = io['phase_names']['70'].index('GPU_lock')
    locked = {r['token']:r['phases'][phase] for r in io['rows'] if r['selector']==70}
    copies = [(row.a*scale,row.b*scale) for row in rows[trace.COPY]]
    overlap = [sum(max(0,min(q['end_ns'],end)-max(q['begin_ns'],begin)) for begin,end in copies
                   if begin<q['end_ns'] and end>q['begin_ns'])
               for r in sampled if (q:=locked[r['kernel_token']])]
    return dict(active_swaps=len(arrivals),active_swaps_per_second=len(arrivals)*1e9/(sum(b-a for a,b in spans)*scale),
        first_swap_offset_median_ns=median(t[0] for t in timings)*scale,
        first_to_last_swap_rate=sum(t[2] for t in timings)*1e9/(sum(t[1] for t in timings)*scale),
        active_swap_cohort_with_exact_writer=len(matching),active_swap_cohort_overtaken=len(overtaken),
        active_overtaken_promoted=len(overtaken&promoted),completed_native_fences_in_order=len(issues),
        active_core_samples=len(sampled),active_core_wait_p95_ns=trace.quantile([r['core_queue_ns'] for r in sampled],.95),
        active_issue_p95_ns=trace.quantile([r['runtime_issue_wall_ns'] for r in sampled],.95),
        active_driver_lock_waits_overlapping_copy=sum(x>0 for x in overlap),largest_overlap_ns=max(overlap))


def main():
    original = EXEC/'result.json'
    proof_path = EXEC/'independent-restore.json'
    result,proof = load(original),load(proof_path)
    require(result['state']==run.SUCCESS and result['observer_exit']==0 and result['boot_attempts']==1 and
            result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            result['frame_trace_complete'] and all(result['other_log_prefix_preserved'].values()) and
            len(proof['files'])==6 and proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and
            proof['misc_original_4096_bytes_match'] and result['crc_frame_calibration']['qualified'] and
            len(result['crc_frame_calibration']['dedicated_witnesses'])==3,'restore or capture qualification missing')
    raw_path = EXEC/'kernel.log'
    frame_path = EXEC/'frame-scanout-analysis.json'
    raw,frame = raw_path.read_text(),load(frame_path)
    rows,strokes,n,d = trace.parse(raw,extra_kinds=(52,53,*KINDS))
    display,tail = recover_tail(raw,frame,rows,strokes,n,d,input_traces(EXEC))
    issued_path = EXEC/'issued-retention-analysis.json'
    bounded = Counter(r['following_hardware_frame']['phase'] for r in load(issued_path)['verified_candidates']
                      if r['following_hardware_frame']['classification']=='changed')
    references = BASE/'frame-host/reference-displays.json'
    alignment = compare(load(references)|{'0357':display})
    previous_path = EXEC/'present-alignment-0350-0355-0356-0357.json'
    previous = load(previous_path)
    require(len(previous['frames'])==len(alignment['frames']),'score frame count changed')
    differences = [(a,b) for a,b in zip(previous['frames'],alignment['frames'],strict=True) if a!=b]
    require(len(differences)==1 and differences[0][0]['trials']['0357']['kind']=='unknown' and
            differences[0][1]['trials']['0357']['frame']==tail['hardware_frame'],'unrelated score changed')
    alignment['strict_new_frame_rate_bounds'] = previous['strict_new_frame_rate_bounds']|{'0357':run.strict_rate(frame,display)}
    comparison_lanes = {'0355':REF355,'0356':REF356,'0357':EXEC}
    paths = [original,proof_path,raw_path,frame_path,issued_path,previous_path,references,
             REF350/'frame-scanout-analysis.json']
    paths += [p/name for p in comparison_lanes.values() for name in ('kernel.log','frame-scanout-analysis.json',
              'core-wait-execution-analysis.json','kernel-IO-identity-analysis.json','kernel-IO-analysis.json')]
    print(json.dumps(dict(state='0357-independently-restored-output-audit',device_commands=0,
        original_frozen_verdict_retained=True,tail_copy_association=tail,scored_crc_comparison=alignment,
        overtaken_before_completion_new_frames_by_phase=dict(bounded),
        matched_active_pacing={name:pacing(path,KINDS if name=='0357' else ready.KINDS)
                               for name,path in comparison_lanes.items()},
        inputs_sha256={str(path):sha(path) for path in dict.fromkeys(paths)}),indent=2))


if __name__=='__main__':
    main()
