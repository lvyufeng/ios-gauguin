#!/usr/bin/env python3
"""Run the frozen 0376 trial and compare independently restored captures."""

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from importlib import import_module
from itertools import zip_longest

from frame344_log import VBLANK, SWAP, TIMING, FRAME_BYTES, indexed, quantile, require
from frame364_analysis import motion_deadlines, motion_io_join, producer_intervals, score
from frame369_swap_timing import observe
from frame372_transport import PACKET_FAMILY, snapshot_handoff, workload_scope
from frame374_native_ca import envelope
from frame375_receipts import align_requests
from frame376_capture import copy_tails, display_lane, packet_lane

scope = import_module('prepare-frame376')
runner = import_module('run-frame374-trial')
partial375 = import_module('audit-frame375-partial')
boundary = runner.boundaries
pacing = partial375.pacing
timeline = runner.prior.timeline
load = scope.load


def scan_groups(ordinary, slow):
    return dict(ordinary_active=[pair for pair in ordinary if pair[1]['phase']=='active'],
                warm_active=[pair for pair in ordinary if pair[1]['phase']=='active' and pair[1]['stroke']>=3],
                ordinary_release=[pair for pair in ordinary if pair[1]['phase']=='release'],
                slow_drag=slow)


def match_ordinals(previous, current):
    def group(rows):
        grouped = defaultdict(list)
        for row in rows:
            key = row['workload'],row['stroke'],row['phase']
            grouped[key].append(row)
        return grouped

    old,new = group(previous),group(current)
    require(old.keys()==new.keys(), 'comparison lacks an original stroke, phase or fixed drag')
    keys = ('frame','crc','generation','native_swap_id','requested_tick','system_actual_tick')
    return [dict(workload=workload,stroke=stroke,phase=phase,ordinal=i,
                 trials={trial:({k:r.get(k) for k in keys} if r else None)
                         for trial,r in zip(('0375','0376'),pair,strict=True)})
            for (workload,stroke,phase),rows in new.items()
            for i,pair in enumerate(zip_longest(old[workload,stroke,phase],rows),1)]


def transaction_wait(frontend, links, transport, n, d, *, repeats=(), callbacks=(), motion_start_ns=0):
    """Keep exact live-message identities and temporal render bounds in each cutoff."""
    ns = lambda tick: tick*n//d
    renders = {row['generation']:row for row in links if row['render']}
    packets = sorted((row for row in transport['pairs'] if row['message_id'] in PACKET_FAMILY),
                     key=lambda row:row['send_ns'])
    sends = [row['send_ns'] for row in packets]
    callbacks = sorted((row for row in callbacks if not row['flags']&8 and
                        row['returned_us']*1000>=motion_start_ns),key=lambda row:row['returned_us'])
    callback_times = [row['returned_us']*1000 for row in callbacks]
    out = []

    def one(stroke, scan, cutoff, generation, callback):
        upcoming = renders.get(generation)
        begins = ns(upcoming['render']['begin_tick']) if upcoming else None
        swap = ns(upcoming['begin_tick']) if upcoming else None
        returned = callback['returned_us']*1000 if callback else None
        candidates = [] if returned is None or begins is None or begins<returned else [
            dict(serial=row['serial'],send_ns=row['send_ns'],copyout_ns=row['copyout_ns'],
                 receive_thread=row['receiver_thread'],
                 stage=('before_send' if cutoff<row['send_ns'] else
                        'send_before_post' if cutoff<row['post_ns'] else
                        'post_before_copyout' if cutoff<row['copyout_ns'] else 'kernel_delivery_complete'),
                 received_before_render=row['copyout_ns']<=begins)
            for row in packets[bisect_left(sends,returned):bisect_right(sends,begins)]]
        stage = ('unresolved' if begins is None else 'before_render' if cutoff<begins else
                 'render_before_SwapBegin' if cutoff<swap else 'after_SwapBegin')
        return dict(stroke=stroke,scan=scan,cutoff_ns=cutoff,generation=generation,stage=stage,
                    callback_id=callback['id'] if callback else None,callback_return_ns=returned,
                    following_render_ns=begins,callback_to_following_render_ns=begins-returned
                    if returned is not None and begins is not None else None,
                    same_transaction_render_verified=False,candidate_message_receipts=candidates)

    for row in frontend['details']:
        following = row['next_swap'] if row['next_swap_within_stroke_tail'] else None
        out.append(one(row['stroke'],row['scan'],row['deadline_ns'],following['generation'] if following else None,
                       row['returned_main_callback']))
    for row in repeats:
        if row['cutoff_ns'] is None:
            continue
        index = bisect_right(callback_times,row['cutoff_ns'])
        following = row['next_certified_copy']
        out.append(one(None,row['frame'],row['cutoff_ns'],following['generation'] if following else None,
                       callbacks[index-1] if index else None))
    summary = {}
    for name,lane in (('ordinary', [row for row in out if row['stroke'] is not None]),
                      ('warm', [row for row in out if row['stroke'] is not None and row['stroke']>=3]),
                      ('slow_drag', [row for row in out if row['stroke'] is None])):
        spans = [r['callback_to_following_render_ns'] for r in lane
                 if r['callback_to_following_render_ns'] is not None and r['callback_to_following_render_ns']>=0]
        summary[name] = dict(stages=dict(Counter(row['stage'] for row in lane)),with_callback_and_render=len(spans),
            p50_callback_to_following_render_ns=quantile(spans,.5),
            p95_callback_to_following_render_ns=quantile(spans,.95),
            timely_message_candidates=sum(any(m['stage']=='kernel_delivery_complete'
                for m in r['candidate_message_receipts']) for r in lane))
    return dict(summary=summary,exact_transaction_render_joins=0,cutoffs=out,
                scope='Stable serial identifies send, post and copyout. Callback and render share only timing '
                      'unless QuartzCore exposes the application and included context for the serial.')


def compare_copy(raw, display, drag, rows, clock):
    start,end,n,d = clock
    attempts = list(indexed((*display['attempts'],*drag['attempts']),lambda row:row['attempt'],'scored copy attempt').values())
    tail = copy_tails(raw,attempts,start,end,n,d)
    outside = boundary.copy_boundary_audit(rows,display,n,d)+boundary.copy_boundary_audit(rows,drag,n,d)
    durations = [layer['copy_ns'] for attempt in attempts for layer in attempt['layers'] if layer['bytes']==FRAME_BYTES]
    return dict(full_copies=len(durations),p95_full_copy_ns=quantile(durations,.95),
        p99_full_copy_ns=quantile(durations,.99),longest_copy_ns=max(durations,default=None),
        over_5_ms=sum(duration>=5_000_000 for duration in durations),
        check_failed=outside,copy_runtime=tail)


def analyze(execution,plan,frame,display,rows,inputs):
    raw = (execution/'kernel.log').read_text()
    start,end,n,d = envelope(raw)
    events,display_stats = display_lane(raw,start,end)
    packets = packet_lane(raw,n,d)
    cal = frame['crc_frame_calibration']
    require(frame['frame_trace_complete'] and frame['misr']['qualified'] and cal['qualified'] and
            cal['lag_frames']==0 and cal['marker_pixel_restored'] and len(cal['dedicated_witnesses'])==3,
            'no qualified vblank and three CRC calibration witnesses')
    _,strokes,_,_ = score.trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    core,original,io = inputs
    require(core['coverage_qualified'] and original['coverage_qualified'],'Core or IO collection incomplete')
    motion = score.parse_motion(raw,strokes,n,d,cal)
    workload = workload_scope(packets,strokes,motion)
    require(len(workload['windows'])==14, 'transport does not cover original workloads')
    ns = lambda tick:tick*n//d
    drag_io = motion_io_join(io,core,motion,ns)
    scan_options = dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns'])
    moving,drag = score.motion_display(raw,frame,rows,motion,core['rows'],drag_io['submits'],n,d,
        display_options=scan_options)
    timing, = rows[TIMING]
    edges,_ = boundary.refine_post_copy_edges(rows,dict(attempts=[*display['attempts'],*drag['attempts']]),timing)
    ordinary,unknown = partial375.refine(frame,display,edges,timing)
    slow,drag_unknown = partial375.refine(moving,drag,edges,timing)
    copies = compare_copy(raw,display,drag,rows,(start,end,n,d))
    refined = rows|{VBLANK:list(edges.values())}
    frontend = producer_intervals(execution,refined,display,core['rows'],strokes,n,d,scan_options=scan_options)
    observed = observe(rows,n,d,frontend,begin_threads=True)
    scoped = dict(swap_timing=observed,frontend_cutoffs=frontend)
    aligned = runner.native_alignment(raw,scoped,display,drag,rows,strokes,n,d,motion)
    original_edges = indexed(rows[VBLANK],lambda row:row.id,'original physical edge')
    feedback = align_requests(events,aligned['scans'],aligned['matches'],rows[SWAP],original_edges,n,d,
                              tolerance_ns=plan['frame_info_provider']['clock_match_tolerance_ns'])
    crc = {(kind,interval['frame']):interval['signatures'] for kind,bands in (('ordinary',ordinary),('slow_drag',slow))
           for _,window in bands for interval in window['intervals']}
    for scan in aligned['scans']:
        scan['crc_signatures'] = crc[scan['workload'],scan['frame']]
    drag_stages = motion_deadlines(refined,drag,core,drag_io,ns,n/d,scan_options=scan_options,allow_unbounded=True)
    ranges = load(scope.CA_RANGES)
    handoff = snapshot_handoff(raw,packets,observed['swap_timing']['swap_timing'],ranges['ranges'])
    callbacks = score.RATE.parse((execution/'springboard-new.log').read_text())
    slow_callbacks = score.RATE.summarize(callbacks,ns(motion['samples'][0][1])//1000,
                                         ns(motion['samples'][-1][2])//1000+250_000)
    wait = transaction_wait(frontend,aligned['matches'],packets,n,d,repeats=drag_stages['repeats'],
        callbacks=slow_callbacks['input']['callback_spans'],motion_start_ns=ns(motion['samples'][0][1]))
    swap_ticks = [x.tick for x in rows[SWAP] if not x.flags and x.c]
    metrics = {key:pacing.cadence(bands,swap_ticks,ns) for key,bands in scan_groups(ordinary,slow).items()}
    ref = load(scope.P375/'partial-audit-0375.json')
    delta = dict(per_scan=match_ordinals(ref['native_alignment']['scans'],aligned['scans']),
                 metrics={'0375':ref['physical'],'0376':metrics},copy={'0375':ref['unchecked_copies'],'0376':copies})
    aligned.update(frame_info=feedback,capture=display_stats,unknown_scans=unknown+drag_unknown)
    transport = dict(counters=packets['counters'],wire_bytes=packets['wire_bytes'],
                     unmatched=packets['unmatched_receipts'],workload=workload,handoff=handoff,wait=wait)
    complete = aligned['summary']['native_capture_covers_workloads'] and all(
        row['FrameInfo_roundtrip'] for row in feedback['active'].values())
    physical = not (unknown or drag_unknown or copies['check_failed'])
    stable = physical and all(metrics[key]['scans']['repeated']==0 and
        metrics[key]['new_images_per_second_bounds'][0]>=59 for key in ('ordinary_active','warm_active','slow_drag'))
    return delta,aligned,transport,drag_stages,complete,physical,stable


def after_restore(execution,plan,result,before,code):
    trial = scope.TRIAL
    collected = runner.prior.collect_after_restore(execution,plan,result,before,code,trial=trial,
        extra_kinds=(runner.PROBE,runner.LOCK_RETRY),join_tail_copy=True,
        display_options=dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns']))
    if collected is None:
        return
    frame,display,_,rows,_,_,inputs = collected
    try:
        proof = load(execution/'independent-restore.json')
        installed = load(scope.BASE/'slot-delta/install-plan.json')
        require(proof['files'][runner.audit.C4]['fork']['extents']==installed['rows']['c4']['data_extents'] and
                runner.decode_route((execution/'kernel.log').read_text())['route']['pipe']=='VIG0',
                'original C4 extents or panel route differs')
        delta,aligned,transport,drag,complete,physical,stable = analyze(execution,plan,frame,display,rows,inputs)
    except (KeyError,ValueError) as error:
        result.update(state=f'{trial}-capture-or-comparison-incomplete-root-restored',frame_error=str(error))
        return
    timeline.write(execution/'present-alignment-0375-0376.json',delta,1_800_000)
    timeline.write(execution/'native-CA-scan-alignment-0376.json',aligned,2_000_000)
    timeline.write(execution/'producer-transport-0376.json',transport,3_000_000)
    timeline.write(execution/'slow-drag-identity-0376.json',drag,1_200_000)
    result.update(state=scope.SUCCESS if complete and physical else f'{trial}-partially-qualified-root-restored',
        frame_trace_complete=True,system_present_alignment_qualified=bool(complete),
        dpu_new_content_FPS_qualified=physical,stable_60_fps_observed=stable,
        hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
        crc_register=frame['misr'],crc_calibration=frame['crc_frame_calibration'],
        compared=delta['metrics'],platform_frame_info=aligned['frame_info'],native_CA_trace=aligned['summary'],
        transport_counters=transport['counters'],callback_to_render=transport['wait']['summary'],
        copies={key:value for key,value in delta['copy']['0376'].items() if key!='copy_runtime'})


if __name__=='__main__':
    raise SystemExit(runner.main(scope,after_restore_fn=after_restore))
