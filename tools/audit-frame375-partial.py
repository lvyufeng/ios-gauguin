#!/usr/bin/env python3
"""Audit independently restored 0375 without accepting its incomplete trial score."""

import argparse
from collections import Counter
from importlib import import_module
import json
from pathlib import Path
import re

import frame344_log as frame
from frame364_analysis import motion_deadlines, motion_io_join, producer_intervals, score
from frame369_swap_timing import observe
import frame374_native_ca as native
from frame375_receipts import align_requests, since_callback
from kernel342_log import ring_status

base = import_module('run-frame375-trial')
runner = base.runner
pacing = import_module('audit-frame-pacing')
boundary = runner.boundaries
load, require, sha = base.scope.load, base.scope.require, base.scope.sha


def retained_events(raw):
    """Validate all serialised rows while retaining original loss accounting."""
    header = frame.one(r'^(SWEET F374 H: version=2 active=1 start=\d+ end=\d+ captured=)(\d+)$',
                       raw,'0375 native header')
    footer = frame.one(r'^(SWEET F374 F: rows=(\d+) threads=\d+ bytes=\d+ lost=)(\d+)$',
                       raw,'0375 native footer')
    captured,rows,lost = map(int,(header[1],footer[1],footer[2]))
    require(rows==native.EVENT_LIMIT and 0<lost==captured-rows,'0375 capture failure differs')
    # Decode a transient envelope of just the serialised rows. Never replace
    # on-disk receipts or treat omitted native events as evidence of absence.
    subset = raw.replace(''.join(header),header[0]+str(rows)).replace(footer[0]+footer[2],footer[0]+'0')
    start,end,n,d = native.envelope(raw)
    events = native.decode(subset,start,end)
    coverage = dict(captured=captured, retained=rows, omitted=lost, complete=False,
                    latest_retained_tick=events[-1].tick,
                    last_retained_seconds=(events[-1].tick-start)*n/d/1e9,
                    retained_kinds=dict(Counter(native.NAMES[event.kind] for event in events)))
    return subset,events,coverage


def refine(frame_report, display, edges, timing):
    certs = score.copy.copy_certificates(display['attempts'],edges,timing)
    paired = list(zip(frame_report['hardware']['windows'],display['windows'],strict=True))
    unknown = []
    for window,lane in paired:
        for source,scan in zip(window['outputs'],lane['intervals'],strict=True):
            relation = scan['crc_relation']
            if (scan['after_copy_boundary_check']=='unknown' and relation in ('changed','repeated') and
                (proofs := score.copy.resolve_overlap(source,certs))):
                scan.update(after_copy_boundary_check=relation,certified_blanking_overlaps=proofs)
            if scan['after_copy_boundary_check']=='unknown':
                unknown.append(dict(stroke=lane['stroke'],phase=lane['phase'],scan=scan['frame'],
                                    reason=source.get('reason')))
    return paired,unknown


def onset(paired,n,d):
    strokes = []
    for w,lane in paired:
        if lane['phase']!='active':
            continue
        matched = [(a,b) for a,b in zip(w['outputs'],lane['intervals'],strict=True)
                   if b['after_copy_boundary_check']=='changed']
        first = matched[0][0] if matched else None
        last = matched[-1][0] if matched else None
        signs = ('edge_lower_tick','edge_upper_tick')
        start = w['start_tick']
        first_ns = [(first[k]-start)*n//d for k in signs] if first else None
        inside = Counter(s['after_copy_boundary_check'] for s in lane['intervals']
                         if first and first['frame']<=s['frame']<=last['frame'])
        strokes.append(dict(stroke=lane['stroke'],first_new_image_frame=first['frame'] if first else None,
                            first_new_image_ns=first_ns,moving_scans=dict(inside)))
    require([r['stroke'] for r in strokes]==list(range(1,14)),'0375 original strokes are incomplete')
    return dict(strokes=strokes)


def callback_residuals(events,scans,n,d):
    """Measure the timestamp residual without relaxing the frozen equality gate."""
    wanted = (native.DRIVER_TARGET,native.DRIVER_DELIVERY,native.FRAME_INFO)
    target,delivery,callback = (frame.indexed((e for e in events if e.kind==k),
                                             lambda e:e.args[0],str(k)) for k in wanted)
    matches = {}
    for swap,reported in delivery.items():
        if reported.args[1]>>32 or swap not in callback or swap not in target:
            continue
        actual,requested = callback[swap].args[2:]
        if actual in native.NO_TIMESTAMP or requested in native.NO_TIMESTAMP:
            continue
        matches[swap] = dict(swap_id=swap,actual_minus_edge_upper_ticks=actual-reported.args[3],
                            requested_minus_swap_target_ticks=requested-target[swap].args[2])
    limits = {}
    for field in ('actual_minus_edge_upper_ticks','requested_minus_swap_target_ticks'):
        deltas = [row[field] for row in matches.values()]
        limits[field] = [min(deltas),max(deltas)] if deltas else None
    matched = {}
    for workload in ('ordinary','slow_drag'):
        scored = [s for s in scans if s['workload']==workload and s['phase']=='active' and
                  'driver_actual_tick_bounds' in s and s.get('native_swap_id') in matches]
        misses = Counter('later' if row['physical_minus_target_ns_bounds'][0]>0 else
                         'earlier' if row['physical_minus_target_ns_bounds'][1]<0 else 'edge_ambiguous'
                         for row in scored)
        matched[workload] = dict(exact_identity_callbacks=len(scored),relative_to_target=dict(misses),
            p50_physical_minus_target_ns_bounds=[
                frame.quantile([s['physical_minus_target_ns_bounds'][k] for s in scored],.5)
                for k in (0,1)] if scored else None)
    return dict(retained_callbacks_joined_by_swap=len(matches),limits_in_ticks=limits,
                maximum_absolute_residual_ns=max((abs(delta)*n/d for bounds in limits.values() if bounds
                                                 for delta in bounds),default=None),
                confirmed_physical_scans=matched,rows=list(matches.values()))


def audit(execution):
    result,proof = (load(execution/name) for name in ('result.json','independent-restore.json'))
    require(result['trial']=='0375' and result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'] and all(result['other_log_prefix_preserved'].values()) and
        len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
        proof['misc_original_4096_bytes_match'],'0375 independent restore proof differs')
    f = load(execution/'frame-scanout-analysis.json')
    cal = f['crc_frame_calibration']
    require(f['frame_trace_complete'] and f['misr']['qualified'] and cal['qualified'] and
            cal['lag_frames']==0 and cal['marker_pixel_restored'] and len(cal['dedicated_witnesses'])==3,
            'physical capture or CRC witness is incomplete')
    raw = (execution/'kernel.log').read_text()
    require(ring_status((execution/'kernel.log.bin').read_bytes(),raw)['qualified'],'persistent console differs')
    subset,events,coverage = retained_events(raw)
    rows,strokes,n,d = frame.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    display = score.copy.analyze(raw,f,extra_kinds=score.KINDS)
    timing, = rows[frame.TIMING]
    edges,_ = boundary.refine_post_copy_edges(rows,display,timing)
    ordinary,unknown = refine(f,display,edges,timing)
    refined_rows = rows | {frame.VBLANK:list(edges.values())}
    core,orig,io = import_module('run-frame350-trial').trace_inputs(execution)
    require(core['coverage_qualified'] and orig['coverage_qualified'],'Core or IO identity is incomplete')
    motion = score.parse_motion(raw,strokes,n,d,cal)
    drag_io = motion_io_join(io,core,motion,lambda tick:tick*n//d)
    moving,drag = score.motion_display(raw,f,rows,motion,core['rows'],drag_io['submits'],n,d)
    drag_pairs,drag_unknown = refine(moving,drag,edges,timing)
    on = onset(ordinary,n,d)
    frontend = producer_intervals(execution,refined_rows,display,core['rows'],strokes,n,d)
    scoped = dict(swap_timing=observe(rows,n,d,frontend,begin_threads=True),frontend_cutoffs=frontend)
    ca = runner.native_alignment(subset,scoped,display,drag,rows,strokes,n,d,motion)
    ca['summary']['native_capture_covers_workloads'] = False
    feedback = align_requests(events,ca['scans'],ca['matches'],rows[frame.SWAP],
                             frame.indexed(rows[frame.VBLANK],lambda x:x.id,'physical scan'),n,d)
    residuals = callback_residuals(events,ca['scans'],n,d)
    upstream = since_callback(events,ca['matches'],frontend,on,n,d)
    swap_ticks = [x.tick for x in rows[frame.SWAP] if not x.flags and x.c]
    groups = {'ordinary_active':[p for p in ordinary if p[1]['phase']=='active'],
              'warm_active':[p for p in ordinary if p[1]['phase']=='active' and p[1]['stroke']>=3],
              'ordinary_release':[p for p in ordinary if p[1]['phase']=='release'],
              'slow_drag':drag_pairs}
    physical = {name:pacing.cadence(pairs,swap_ticks,lambda tick:tick*n//d)
                for name,pairs in groups.items()}
    slow_repeat_stages = motion_deadlines(rows,drag,core,drag_io,lambda tick:tick*n//d,n/d)
    pins = {name:sha(execution/name) for name in ('result.json','independent-restore.json','kernel.log',
             'kernel.log.bin','frame-scanout-analysis.json','core-wait-execution-analysis.json',
             'kernel-IO-analysis.json','kernel-IO-identity-analysis.json')}
    return dict(trial='0375', full_scope_qualified=False, native_retained=coverage, exact_feedback=feedback,
        callback_timestamp_residuals=residuals,slow_drag_repeat_stages=slow_repeat_stages,
        callback_to_render=upstream, onset=on, hardware_refresh_hz_bounds=f['hardware']['hardware_refresh_hz_bounds'],
        physical=physical, unknown_scans=unknown, slow_drag_unknown_scans=drag_unknown,
        unchecked_copies=boundary.copy_boundary_audit(rows,display,n,d)+boundary.copy_boundary_audit(rows,drag,n,d),
        native_alignment=ca,input_pins=pins)


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('execution',type=Path)
    cli.add_argument('output',type=Path)
    args = cli.parse_args()
    report = audit(args.execution)
    with args.output.open('x') as target:
        json.dump(report,target,indent=2)
        target.write('\n')
