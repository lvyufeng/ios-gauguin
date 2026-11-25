#!/usr/bin/env python3
"""Restore and verify 0377 before analyzing copy phases and three-way scanout."""

from collections import defaultdict
from importlib import import_module
from itertools import zip_longest

import frame344_log as trace
from frame364_analysis import motion_deadlines, motion_io_join, producer_intervals, score
from frame369_swap_timing import observe
from frame372_transport import snapshot_handoff, workload_scope
from frame374_native_ca import envelope
from frame375_receipts import align_requests
from frame376_capture import display_lane
import frame377_capture as capture
from kernel342_log import ring_status

scope = import_module('prepare-frame377')
previous = import_module('run-frame376-trial')
audit376 = import_module('audit-frame376-partial')
runner = previous.runner
boundary = previous.boundary
load,require = scope.load,scope.require


def indexed_phases(scans):
    lanes = defaultdict(list)
    for scan in scans:
        lanes[scan['workload'],scan['stroke'],scan['phase']].append(scan)
    return lanes


def paired_ordinals(trials):
    data = {trial:indexed_phases(rows) for trial,rows in trials.items()}
    keys = next(iter(data.values())).keys()
    require(all(lane.keys()==keys for lane in data.values()),'trial comparison lacks a workload or phase')
    fields = ('frame','crc','crc_signatures','generation','native_swap_id','requested_tick','system_actual_tick','vblank_ticks')
    return [dict(workload=workload,stroke=stroke,phase=phase,ordinal=index,scans={
        name:({k:scan.get(k) for k in fields} if scan else None)
        for name,scan in zip(data,pair,strict=True)})
        for workload,stroke,phase in keys
        for index,pair in enumerate(zip_longest(*(lane[workload,stroke,phase] for lane in data.values())),1)]


def guarded_comparison(frame, display, drag, moving, rows):
    timing, = rows[trace.TIMING]
    attempts = list(trace.indexed((*display['attempts'],*drag['attempts']),
                                  lambda row:row['attempt'],'scored attempts').values())
    edges,refinements = boundary.refine_post_copy_edges(rows,dict(attempts=attempts),timing)
    ordinary,unknown = previous.partial375.refine(frame,display,edges,timing)
    slow,slow_unknown = previous.partial375.refine(moving,drag,edges,timing)
    return edges,refinements,ordinary,slow,unknown+slow_unknown,attempts


def analyze(execution, plan, frame, display, rows, inputs):
    raw = (execution/'kernel.log').read_text()
    ring = ring_status((execution/'kernel.log.bin').read_bytes(),raw)
    require(ring['qualified'],'persistent console is incomplete')
    start,end,n,d = envelope(raw)
    cal = frame['crc_frame_calibration']
    require(frame['frame_trace_complete'] and frame['misr']['qualified'] and cal['qualified'] and
            cal['lag_frames']==0 and cal['marker_pixel_restored'] and len(cal['dedicated_witnesses'])==3,
            'vblank or CRC restoration and calibration are incomplete')
    core,original,io = inputs
    require(core['coverage_qualified'] and original['coverage_qualified'],'Core or IO identity incomplete')
    _,strokes,_,_ = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    require(len(strokes)==13,'original swipe count differs')
    motion = score.parse_motion(raw,strokes,n,d,cal)
    ns = lambda tick:tick*n//d
    drag_io = motion_io_join(io,core,motion,ns)
    options = dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns'])
    moving,drag = score.motion_display(raw,frame,rows,motion,core['rows'],drag_io['submits'],n,d,
                                     display_options=options)
    edges,refinements,ordinary,slow,unknown,attempts = guarded_comparison(frame,display,drag,moving,rows)
    phases = [phase for dpy in (display,drag) for phase in boundary.copy_boundary_audit(rows,dpy,n,d)]
    copy_durations = [layer['copy_ns'] for attempt in attempts for layer in attempt['layers'] if layer['bytes']==trace.FRAME_BYTES]
    wall = dict(full_copies=len(copy_durations),p95_full_copy_ns=trace.quantile(copy_durations,.95),
                p99_full_copy_ns=trace.quantile(copy_durations,.99),longest_copy_ns=max(copy_durations,default=None),
                check_failed=phases)
    try:
        timing = capture.copies(raw,rows,attempts,start,end,n,d)
    except ValueError as error:
        timing = dict(full_capture_qualified=False,error=str(error))
    refined = rows|{trace.VBLANK:list(edges.values())}
    frontend = producer_intervals(execution,refined,display,core['rows'],strokes,n,d,scan_options=options)
    observed = observe(rows,n,d,frontend,begin_threads=True)
    aligned = runner.native_alignment(raw,dict(swap_timing=observed,frontend_cutoffs=frontend),
                                      display,drag,rows,strokes,n,d,motion)
    events,display_stats = display_lane(raw,start,end,byte_limit=capture.DISPLAY_BYTES)
    feedback = align_requests(events,aligned['scans'],aligned['matches'],rows[trace.SWAP],
        trace.indexed(rows[trace.VBLANK],lambda row:row.id,'physical vblank'),n,d,
        tolerance_ns=plan['frame_info_provider']['clock_match_tolerance_ns'])
    crc = {(workload,interval['frame']):interval['signatures']
           for workload,bands in (('ordinary',ordinary),('slow_drag',slow))
           for _,window in bands for interval in window['intervals']}
    for scan in aligned['scans']:
        scan['crc_signatures'] = crc[scan['workload'],scan['frame']]
    drag_stages = motion_deadlines(refined,drag,core,drag_io,ns,n/d,scan_options=options,allow_unbounded=True)
    try:
        packets = capture.pack_stats(raw,n,d)
        workload = workload_scope(packets,strokes,motion)
        handoff = snapshot_handoff(raw,packets,observed['swap_timing'],load(scope.CA_RANGES)['ranges'])
        rate = score.RATE
        callbacks = rate.summarize(rate.parse((execution/'springboard-new.log').read_text()),
            ns(motion['samples'][0][1])//1000,ns(motion['samples'][-1][2])//1000+250_000)
        waits = previous.transaction_wait(frontend,aligned['matches'],packets,n,d,repeats=drag_stages['repeats'],
            callbacks=callbacks['input']['callback_spans'],motion_start_ns=ns(motion['samples'][0][1]))
        transport = dict(wire_bytes=packets['wire_bytes'],table=packets['table'],counters=packets['counters'],
            losses=packets['losses'],unmatched=packets['unmatched_receipts'],workload=workload,handoff=handoff,waits=waits,
            qualified=bool(workload['complete_13_and_fixed_drag'] and not packets['table']['bucket_full']))
    except ValueError as error:
        transport = dict(qualified=False,error=str(error))
    swap_ticks = [row.tick for row in rows[trace.SWAP] if not row.flags and row.c]
    counts = {name:previous.pacing.cadence(bands,swap_ticks,ns)
              for name,bands in previous.scan_groups(ordinary,slow).items()}
    older = load(scope.COMPARISON)
    p375 = load(scope.P375/'partial-audit-0375.json')
    histories = older['comparison']
    guard = audit376.guard_comparison(ordinary,slow,rows,options)
    old_copy = {name:{key:value for key,value in details.items() if key!='copy_runtime'}
                for name,details in histories['copy'].items()}
    physical = bool(not unknown and not phases)
    stable = physical and all(counts[key]['scans']['repeated']==0 and
        counts[key]['new_images_per_second_bounds'][0]>=59 for key in ('ordinary_active','warm_active','slow_drag'))
    native = aligned['summary']['native_capture_covers_workloads'] and all(
        row['FrameInfo_roundtrip'] for row in feedback['active'].values())
    aligned.update(frame_info=feedback,capture=display_stats,unknown_scans=unknown,refined_edges=refinements)
    return dict(metrics=histories['metrics']|{'0377':counts},copy=old_copy|{'0377':wall},
        guard=histories['guard']|{'0377':guard},copy_phases=timing,native=aligned,transport=transport,
        slow_drag=drag_stages,
        per_scan=paired_ordinals({'0375':p375['native_alignment']['scans'],'0376':older['native']['scans'],
                                  '0377':aligned['scans']}),
        hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],ring=ring,
        crc_register=frame['misr'],crc_calibration=cal,
        stable_60_fps_observed=bool(stable),physical_score_qualified=physical,system_present_alignment_qualified=bool(native))


def after_restore(execution,plan,result,before,code):
    collected = runner.prior.collect_after_restore(execution,plan,result,before,code,trial=scope.TRIAL,
        extra_kinds=(runner.PROBE,runner.LOCK_RETRY),join_tail_copy=True,
        display_options=dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns']))
    if collected is None:
        return
    frame,display,_,rows,retained,_,inputs = collected
    try:
        proof = load(execution/'independent-restore.json')
        slots = load(scope.BASE/'slot-delta/install-plan.json')
        require(proof['files'][runner.audit.C4]['fork']['extents']==slots['rows']['c4']['data_extents'] and
            runner.decode_route((execution/'kernel.log').read_text())['route']['pipe']=='VIG0',
            'slot extent or panel route differs')
        report = analyze(execution,plan,frame,display,rows,inputs)
    except (KeyError,ValueError) as error:
        result.update(state='0377-frame-comparison-incomplete-root-restored',frame_error=str(error))
        return
    previous.timeline.write(execution/'scanout-comparison-0375-0377.json',report,5_000_000)
    physical,native = report['physical_score_qualified'],report['system_present_alignment_qualified']
    timing,ipc = report['copy_phases'],report['transport']
    complete = physical and native and timing['full_capture_qualified'] and ipc['qualified']
    result.update(state=scope.SUCCESS if complete else '0377-partially-qualified-root-restored',
        frame_trace_complete=True,dpu_new_content_FPS_qualified=physical,system_present_alignment_qualified=native,
        stable_60_fps_observed=report['stable_60_fps_observed'],
        hardware_refresh_hz_bounds=report['hardware_refresh_hz_bounds'],compared=report['metrics'],
        copy=report['copy']['0377'],copy_phases={k:v for k,v in timing.items() if k!='rows'},
        ipc={k:ipc[k] for k in ('qualified','counters','table','error') if k in ipc},
        frame_info=report['native']['frame_info'],fence_and_lifetime_verified=retained['issued_with_exact_claim'])


if __name__=='__main__':
    raise SystemExit(runner.main(scope,after_restore_fn=after_restore))
