#!/usr/bin/env python3
"""Score independently qualified 0376 display evidence after four IPC evictions."""

import argparse
from base64 import b64decode
from collections import Counter
from importlib import import_module
import re
from unittest.mock import patch

import frame376_capture as capture
from frame373_receipts import decode_with_unmatched
from frame344_log import FRAME_BYTES, SWAP, TIMING, VBLANK, indexed, quantile
from frame364_analysis import motion_deadlines, motion_io_join, producer_intervals
from frame369_swap_timing import observe
from frame372_transport import snapshot_handoff, workload_scope
from frame374_native_ca import envelope
from frame375_receipts import align_requests
from kernel342_log import ring_status

trial = import_module('run-frame376-trial')
scope = trial.scope
load,require,sha = scope.load,scope.require,scope.sha


def partial_packet_lane(raw,n,d):
    transport = decode_with_unmatched(raw,n,d,block_type='F376 P',read_rows=capture.compact_rows,
                                      thread_cap=capture.PACKET_THREADS)
    count,size = map(int,capture.frame.one(r'^SWEET F376 P footer: rows=(\d+) bytes=(\d+)$',
                                          raw,'0376 packet footer'))
    blocks = re.findall(r'^SWEET F376 P \d+ \d+ ([A-Za-z0-9+/=]+)$',raw,re.M)
    require(0<size<=capture.PACKET_BYTES and count==transport['paired_exact_receipts'] and
            sum(len(b64decode(row,validate=True)) for row in blocks)==size,
            'IPC records or exported size differs')
    flags = transport['counters']
    missing = transport['unmatched_receipts']
    require(flags['sent']==flags['copied']+4 and flags['missed']==flags['evicted']==len(missing)==4 and
            not (flags['busy'] or flags['failed'] or transport['losses']['cap_saturation']) and
            all(row['reason']=='no_matching_live_send' and row['outcome']=='completed' for row in missing),
            'IPC losses differ from the four bounded, timestamped evictions')
    return dict(transport,wire_bytes=size)


def guard_comparison(ordinary, slow, rows, options):
    """Same workload membership for CRC, accepted swaps and certified copies."""
    accepted = [r for r in rows[SWAP] if not r.flags and r.c]
    active = trial.scan_groups(ordinary,slow)
    groups = {}
    for name,bands in active.items():
        intervals = [(ref['start_tick'],ref['end_tick']) for ref,_ in bands]
        groups[name] = dict(accepted_swaps=sum(any(a<=r.tick<b for a,b in intervals) for r in accepted),
            interval_count=sum(len(lane['intervals']) for _,lane in bands))
    probes = Counter(r.flags for r in rows[trial.runner.PROBE])
    is_paired = [row for row in rows[trial.score.PRESENT] if row.flags in (5,6)]
    return dict(groups=groups,accepted_swaps_over_full_capture=len(accepted),probe_counts=dict(probes),
        paired_copies_over_full_capture=sum(row.flags==5 for row in is_paired),
        unchecked_paired_copies_over_full_capture=sum(row.flags==6 for row in is_paired),
        minimum_copy_lead_ns=options['copy_budget_ns'],
        admission_lines_at_end_line_4878=4878-(options['copy_budget_ns']+2999)//3000+1-2480)


def reference_copy_and_swaps():
    ref = scope.REFERENCE
    raw = (ref/'kernel.log').read_text()
    frame = load(ref/'frame-scanout-analysis.json')
    items = trial.score.KINDS
    rows,strokes,n,d = trial.score.trace.parse(raw,extra_kinds=(trial.score.PRESENT,trial.score.copy.WAKE,*items))
    core,_,io = import_module('run-frame350-trial').trace_inputs(ref)
    display = trial.score.copy.analyze(raw,frame,extra_kinds=items)
    motion = trial.score.parse_motion(raw,strokes,n,d,frame['crc_frame_calibration'])
    drag_io = motion_io_join(io,core,motion,lambda tick:tick*n//d)
    moving,drag = trial.score.motion_display(raw,frame,rows,motion,core['rows'],drag_io['submits'],n,d)
    timing, = rows[TIMING]
    edges,_ = trial.boundary.refine_post_copy_edges(rows,dict(attempts=[*display['attempts'],*drag['attempts']]),timing)
    ordinary,_ = trial.partial375.refine(frame,display,edges,timing)
    slow,_ = trial.partial375.refine(moving,drag,edges,timing)
    durations = [layer['copy_ns'] for scope in (display,drag) for attempt in scope['attempts']
                 for layer in attempt['layers'] if layer['bytes']==FRAME_BYTES]
    return guard_comparison(ordinary,slow,rows,dict(copy_budget_ns=5_500_000)),dict(
        full_copies=len(durations),p95_full_copy_ns=quantile(durations,.95),
        p99_full_copy_ns=quantile(durations,.99),longest_copy_ns=max(durations,default=None))


def correlate(execution, plan, raw, frame, display, rows, strokes, inputs):
    start,end,n,d = envelope(raw)
    events,display_stats = capture.display_lane(raw,start,end)
    packets = partial_packet_lane(raw,n,d)
    cal = frame['crc_frame_calibration']
    require(frame['frame_trace_complete'] and frame['misr']['qualified'] and cal['qualified'] and
            cal['lag_frames']==0 and cal['marker_pixel_restored'] and len(cal['dedicated_witnesses'])==3,
            'exact vblank and restored CRC witnesses required')
    core,original,io = inputs
    require(core['coverage_qualified'] and original['coverage_qualified'],'Core or IO collection incomplete')
    motion = trial.score.parse_motion(raw,strokes,n,d,cal)
    workload = workload_scope(packets,strokes,motion)
    require(len(strokes)==13 and len(workload['windows'])==14,'workload does not cover the frozen script')
    ns = lambda tick: tick*n//d
    drag_io = motion_io_join(io,core,motion,ns)
    options = dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns'])
    moving,drag = trial.score.motion_display(raw,frame,rows,motion,core['rows'],drag_io['submits'],n,d,
                                           display_options=options)
    timing, = rows[TIMING]
    edges,_ = trial.boundary.refine_post_copy_edges(rows,dict(attempts=[*display['attempts'],*drag['attempts']]),timing)
    ordinary,unknown = trial.partial375.refine(frame,display,edges,timing)
    slow,drag_unknown = trial.partial375.refine(moving,drag,edges,timing)
    # Use the original row grammar with multiline anchors. Require the complete,
    # unmodified copy receipt count and respect the same runtime interval checks.
    with patch.object(capture,'COPY',re.compile(capture.COPY.pattern,re.M)):
        copies = trial.compare_copy(raw,display,drag,rows,(start,end,n,d))
    refined = rows|{VBLANK:list(edges.values())}
    frontend = producer_intervals(execution,refined,display,core['rows'],strokes,n,d,scan_options=options)
    observed = observe(rows,n,d,frontend,begin_threads=True)
    aligned = trial.runner.native_alignment(raw,dict(swap_timing=observed,frontend_cutoffs=frontend),
                                           display,drag,rows,strokes,n,d,motion)
    feedback = align_requests(events,aligned['scans'],aligned['matches'],rows[SWAP],
        indexed(rows[VBLANK],lambda row:row.id,'original physical edge'),n,d,
        tolerance_ns=plan['frame_info_provider']['clock_match_tolerance_ns'])
    crc = {(kind,interval['frame']):interval['signatures'] for kind,bands in (('ordinary',ordinary),('slow_drag',slow))
           for _,window in bands for interval in window['intervals']}
    for scan in aligned['scans']:
        scan['crc_signatures'] = crc[scan['workload'],scan['frame']]
    drag_stages = motion_deadlines(refined,drag,core,drag_io,ns,n/d,scan_options=options,allow_unbounded=True)
    handoff = snapshot_handoff(raw,packets,observed['swap_timing'],load(scope.CA_RANGES)['ranges'])
    rate = trial.score.RATE
    callbacks = rate.summarize(rate.parse((execution/'springboard-new.log').read_text()),
        ns(motion['samples'][0][1])//1000,ns(motion['samples'][-1][2])//1000+250_000)
    wait = trial.transaction_wait(frontend,aligned['matches'],packets,n,d,repeats=drag_stages['repeats'],
        callbacks=callbacks['input']['callback_spans'],motion_start_ns=ns(motion['samples'][0][1]))
    # Use the same 5.5 ms deadline as 0375 for the producer comparison.
    # The narrower 0376 window often cannot be bracketed independently.
    front_reference = producer_intervals(execution,refined,display,core['rows'],strokes,n,d)
    drag_reference = motion_deadlines(refined,drag,core,drag_io,ns,n/d,allow_unbounded=True)
    common_wait = trial.transaction_wait(front_reference,aligned['matches'],packets,n,d,
        repeats=drag_reference['repeats'],callbacks=callbacks['input']['callback_spans'],
        motion_start_ns=ns(motion['samples'][0][1]))
    used = [row for row in drag_reference['repeats'] if row['cutoff_ns'] is not None]
    stage_counts = Counter(row['stage'] for repeat in used for row in repeat['accepted_candidates'])
    common = dict(reference_copy_lead_ns=5_500_000,ordinary_cutoffs=len(front_reference['details']),
        slow_drag_repeat_cutoffs=len(used),slow_drag_repeats_with_preexisting_ready_candidate=sum(
            any(row['stage']=='ready_by_cutoff' for row in repeat['accepted_candidates']) for repeat in used),
        slow_drag_repeats_with_no_accepted_candidate=sum(not repeat['accepted_candidates'] for repeat in used),
        slow_drag_candidate_stages=dict(stage_counts),wait=common_wait,slow_drag=drag_reference)
    swap_ticks = [row.tick for row in rows[SWAP] if not row.flags and row.c]
    metrics = {key:trial.pacing.cadence(bands,swap_ticks,ns)
               for key,bands in trial.scan_groups(ordinary,slow).items()}
    ref = load(scope.P375/'partial-audit-0375.json')
    ref_guard,ref_copies = reference_copy_and_swaps()
    new_guard = guard_comparison(ordinary,slow,rows,options)
    delta = dict(per_scan=trial.match_ordinals(ref['native_alignment']['scans'],aligned['scans']),
        metrics={'0375':ref['physical'],'0376':metrics},
        copy={'0375':dict(ref_copies,check_failed=ref['unchecked_copies']),'0376':copies},
        guard={'0375':ref_guard,'0376':new_guard})
    aligned.update(frame_info=feedback,capture=display_stats,unknown_scans=unknown+drag_unknown)
    transport = dict(counters=packets['counters'],wire_bytes=packets['wire_bytes'],
                     unmatched=packets['unmatched_receipts'],workload=workload,handoff=handoff,wait=wait,common_deadline=common)
    complete = aligned['summary']['native_capture_covers_workloads'] and all(
        row['FrameInfo_roundtrip'] for row in feedback['active'].values())
    physical = not (unknown or drag_unknown or copies['check_failed'])
    stable = physical and all(metrics[key]['scans']['repeated']==0 and
        metrics[key]['new_images_per_second_bounds'][0]>=59 for key in ('ordinary_active','warm_active','slow_drag'))
    return delta,aligned,transport,drag_stages,complete,physical,stable


def audit(execution):
    result,proof = (load(execution/name) for name in ('result.json','independent-restore.json'))
    require(result['trial']=='0376' and result['frame_error']=='transport lane incomplete' and
            (result['boot_attempts'],result['observer_exit'],result['recovery_fallbacks'])==(1,0,0) and
            result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            all(result['other_log_prefix_preserved'].values()) and
            len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and not (proof['device_writes'] or proof['device_boots']),
            'audit requires the exact restored 0376 trial with no outstanding device work')
    plan = load(scope.BASE/'trial-plan.json')
    frame = load(execution/'frame-scanout-analysis.json')
    raw = (execution/'kernel.log').read_text()
    require(plan['kernel_banner'] in raw and ring_status((execution/'kernel.log.bin').read_bytes(),raw)['qualified'],
            'exact kernel or lossless persistent console requires verification')
    kinds = (*trial.runner.prior.KINDS,trial.runner.PROBE,trial.runner.LOCK_RETRY)
    rows,strokes,_,_ = trial.score.trace.parse(raw,extra_kinds=(trial.score.PRESENT,trial.score.copy.WAKE,*kinds))
    display = trial.score.copy.analyze(raw,frame,extra_kinds=kinds,
        copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns'])
    inputs = import_module('run-frame350-trial').trace_inputs(execution)
    delta,aligned,transport,drag,native,physical,stable = correlate(
        execution,plan,raw,frame,display,rows,strokes,inputs)
    raw_bytes = ring_status((execution/'kernel.log.bin').read_bytes(),raw)['total_bytes']
    cal = frame['crc_frame_calibration']
    pins = ('result.json','independent-restore.json','kernel.log','kernel.log.bin','frame-scanout-analysis.json',
            'core-wait-execution-analysis.json','kernel-IO-analysis.json','kernel-IO-identity-analysis.json')
    return dict(state='0376-independently-restored-with-partial-IPC-audit',
        frozen_verdict=result['state'],system_present_alignment_qualified=native,physical_score_qualified=physical,
        entire_IPC_capture_qualified=False,stable_60_fps_observed=stable,console_bytes=raw_bytes,
        hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
        crc_calibration=cal,crc_register=frame['misr'],
        comparison=delta,native=aligned,transport=transport,slow_drag=drag,
        input_pins={name:sha(execution/name) for name in pins})


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('output')
    args=cli.parse_args()
    evidence=scope.BASE/'execution'
    report=audit(evidence)
    trial.timeline.write(evidence/args.output,report,7_000_000)
    print({key:value for key,value in report.items() if isinstance(value,(str,bool,int))})
