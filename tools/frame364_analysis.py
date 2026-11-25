"""Join measured producer deadlines and sustained-motion writers after restore."""

from bisect import bisect_left, bisect_right
from collections import Counter

import frame362_analysis as score
import kernel342_log as kernel
from frame354_display import PROMOTE, order, ready_joins
from frame357_display import BOUND
from frame358_display import PROBE, RESULTS as PROBE_RESULTS

trace = score.trace
require = trace.require


def core_key(row):
    return row['queue'], row['ticket'], row['job']


def motion_io_join(decoded, core, motion, ns):
    start = ns(motion['samples'][0][1])//1000 - 100_000
    end = ns(motion['samples'][-1][2])//1000 + 250_000
    joined = kernel.join(decoded, core, (start, end), require_program_activity=False)
    require(joined['coverage_qualified'], f"slow-drag IO join is incomplete: {joined['errors']}")
    return joined


def producer_intervals(execution, rows, display, core, strokes, num, den, *, scan_options=None):
    """Observe edges on one clock while keeping the CA transaction anonymous."""
    prior = score.missing_swap(execution,rows,display,core,num,den,strokes,scan_options=scan_options)
    start, end = strokes[0][0]*num//den//1000, strokes[-1][1]*num//den//1000
    parsed = score.RATE.parse((execution/'springboard-new.log').read_text())
    springboard = score.RATE.summarize(parsed,start,end+250_000)
    callbacks = {row['id']:row for row in springboard['input']['callback_spans'] if not row['flags']&8}
    turns = sorted((row for row in springboard['turns']['rows'] if row['observer_order_valid']),
                   key=lambda row:row['after_ca_us'])
    after_times = [row['after_ca_us']*1000 for row in turns]
    require(turns and springboard['input']['watch_covers_window'], 'incomplete main-run-loop coverage')

    writers = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda row:row.b>>32,'bound generation')
    ready = trace.indexed(rows[trace.READY],lambda row:row.id,'visible writer')
    details = []
    for miss in prior['details']:
        cutoff = miss['deadline_ns']
        returns = [callbacks[i] for i in miss['returned_touch_callbacks'] if i in callbacks]
        returned = max(returns,key=lambda row:(row['returned_us'],row['id']),default=None)
        ret_ns = returned['returned_us']*1000 if returned else None
        next_swap = miss['next_swap']
        swap_ns = next_swap['tick']*num//den if next_swap else None
        in_scope = swap_ns is not None and swap_ns <= strokes[miss['stroke']-1][1]*num//den+250_000_000
        observation = None
        if returned:
            candidate = bisect_left(after_times,ret_ns)
            if candidate<len(turns) and after_times[candidate]<=(swap_ns if in_scope else cutoff):
                observation = turns[candidate]
        after_ns = observation['after_ca_us']*1000 if observation else None
        if not returned:
            position = 'no_touch_return_in_cutoff_interval'
        elif after_ns is None:
            position = 'no_CA_observer_after_return_before_next_swap'
        elif after_ns > cutoff:
            position = 'CA_observer_after_cutoff'
        else:
            position = 'CA_observer_before_cutoff_swap_after'
        remaining = None
        if in_scope and returned:
            writer = writers.get(next_swap['generation'])
            visible = ready.get(writer.id) if writer else None
            if visible:
                lag = visible.tick*num//den-swap_ns
                require(lag>=0, 'swap visibility clock regressed')
                remaining = cutoff-ret_ns-lag
        details.append(dict(miss,returned_main_callback=returned,CA_observer=observation,
            next_swap_within_stroke_tail=in_scope,position=position,
            return_to_next_swap_ns=swap_ns-ret_ns if returned and in_scope else None,
            return_to_after_CA_observer_ns=after_ns-ret_ns if returned and observation else None,
            after_CA_observer_to_next_swap_ns=swap_ns-after_ns if in_scope and observation else None,
            hypothetical_visible_slack_ns_if_swap_at_return=remaining))

    def totals(group):
        fields = ('return_to_next_swap_ns','return_to_after_CA_observer_ns','after_CA_observer_to_next_swap_ns')
        near = [row for row in group if row['next_swap_within_stroke_tail'] and
                row['next_swap']['late_ns']*60<=1_000_000_000]
        eligible = [row for row in group if row['hypothetical_visible_slack_ns_if_swap_at_return'] is not None]
        viable = [row for row in eligible if row['hypothetical_visible_slack_ns_if_swap_at_return'] >= 0]
        timings = {}
        for name in fields:
            values = [row[name] for row in group if row[name] is not None]
            timings[name] = dict(samples=len(values),p50=trace.quantile(values,.5),p95=trace.quantile(values,.95))
        return dict(scans=len(group),with_return=sum(bool(row['returned_main_callback']) for row in group),
            positions=dict(Counter(r['position'] for r in group)),next_swap_within_one_refresh=len(near),
            visible_slack_model_evaluable=len(eligible),visible_by_cutoff_in_slack_model=len(viable),
            unique_swaps_in_slack_model=len({row['next_swap']['generation'] for row in viable}),timings_ns=timings)

    return dict(all_strokes=totals(details),warm_strokes_3_to_13=totals([r for r in details if r['stroke']>=3]),
        details=details,scope='Per-cutoff temporal associations. The last completed main-thread touch callback, '
        'an observer ordered near CA, and the next driver-accepted surface swap do not share a CA transaction ID. '
        'The visibility calculation rebases the measured swap-to-visibility lag to callback return and omits '
        'queue interactions, read-guard acquisition and copy scheduling. It is a prioritization scenario.')


def phase_at_cutoff(core, io, issue_ns, eop_ns, visible_ns, promoted_ns, cutoff):
    if cutoff < core['made_us']*1000:
        return 'before_Core_buffer'
    if cutoff < core['enq_ns']:
        return 'before_Core_commit_enqueue'
    if cutoff < core['start_ns']:
        return 'Core_commit_queue'
    if cutoff < core['io_begin_ns']:
        return 'Core_submit_pre_IO'
    if cutoff < issue_ns:
        names = kernel.PHASES[70]
        phases = [name for name, phase in zip(names,io['phases'],strict=True)
                  if phase['begin_ns']<=cutoff<phase['end_ns']]
        return 'submit_'+phases[0] if phases else 'submit_IO_outside_measured_phase'
    if eop_ns is None or cutoff < eop_ns:
        return 'issued_awaiting_observed_GPU_completion'
    if visible_ns is None or cutoff < visible_ns:
        return 'GPU_completion_to_cache_visibility'
    if promoted_ns is None or cutoff < promoted_ns:
        return 'visible_awaiting_ready_promotion'
    return 'ready_by_cutoff'


def motion_deadlines(rows, display, core, joined, ns, scale, *, scan_options=None, allow_unbounded=False):
    scans = {slot.frame:slot for slot in score.scan_windows(rows[trace.VBLANK],ns,scale,bracketed=True,**(scan_options or {}))}
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'motion edge')
    timing, = rows[trace.TIMING]
    attempts = trace.indexed(display['attempts'],lambda row:row['attempt'],'motion present attempt')
    ready_joins(rows,attempts.values(),binding_kind=BOUND)
    certificates = score.copy.copy_certificates(attempts.values(),edges,timing)
    copies = trace.indexed(certificates.items(),lambda item:(item[1]['frame']+1)&0xffffffff,'motion copy scan')
    visible = trace.indexed(rows[trace.READY],lambda row:row.id,'visible fence')
    eop = trace.indexed(rows[trace.EOP],lambda row:row.id,'completed fence')
    issued = trace.indexed(rows[trace.ISSUE],lambda row:row.id,'native fence')
    claims = trace.indexed(rows[BOUND],lambda row:row.id,'swap reservation')
    writers = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda row:row.b>>32,'bound writer')
    promotions = trace.indexed(rows[PROMOTE],lambda row:row.id,'ready generation')
    probes = trace.indexed(rows[PROBE],lambda row:row.id,'motion probe target')
    submissions = trace.indexed(joined['submits'],lambda row:row['kernel_token'],'slow-drag token')
    cores = trace.indexed(core['rows'],core_key,'recorded Core job')
    swaps = [r for r in rows[trace.SWAP] if not r.flags and r.c]
    require(all(a.id<b.id for a,b in zip(swaps,swaps[1:])), 'accepted swap order changed')
    swap_times = [ns(swap.tick) for swap in swaps]
    accepted = {swap.id:swap for swap in swaps}
    present_starts = trace.indexed(rows[trace.ATTEMPT],lambda row:row.id,'present start')
    copied = sorted((ns(r.tick),present_starts[r.id].a) for r in rows[trace.RESULT] if r.a)
    copied_times = [finished for finished,_ in copied]

    def timeline(swap, cutoff):
        writer = writers.get(swap.id)
        claim = claims.get(swap.id)
        if not writer:
            return dict(generation=swap.id,stage='no_bound_writer_observed' if claim else 'no_writer_claim_observed',
                        relative_ns={'swap':ns(swap.tick)-cutoff})
        issue = issued[writer.id]
        require(claim and (claim.a,claim.b)==(writer.b,writer.c) and swap.c==((writer.c<<32)|writer.a) and
                order(swap)<=order(claim)<=order(issue)<=order(writer),'slow-drag writer reservation differs')
        io = submissions.get(issue.a)
        if io is None:
            return dict(generation=swap.id,native_fence=writer.id,stage='outside_exact_IO_scope',
                        relative_ns={'swap':ns(swap.tick)-cutoff,'native_issue':ns(issue.tick)-cutoff})
        require((issue.b,issue.c)==(io['driver_queue'],io['driver_fence']),'slow-drag native and driver fence disagree')
        core = cores[core_key(io)]
        issue_ns = ns(issue.tick)
        require(core['io_begin_ns']<=issue_ns<=core['io_end_ns'],'native issue outside the exact Core IO span')
        end, seen, promoted = eop.get(writer.id),visible.get(writer.id),promotions.get(swap.id)
        require((seen is None or (end and order(writer)<=order(end)<=order(seen))) and
                (promoted is None or (seen and (promoted.b,promoted.c)==(writer.c,writer.a) and
                 order(seen)<=order(promoted))),
                'slow-drag fence or promotion order changed')
        moments = dict(swap=ns(swap.tick),writer_bound=ns(claim.tick),core_created=core['made_us']*1000,
            core_enqueue=core['enq_ns'],core_commit_begin=core['start_ns'],io_begin=core['io_begin_ns'],
            native_issue=issue_ns,io_return=core['io_end_ns'],core_commit_end=core['end_ns'],
            observed_GPU_completion=ns(end.tick) if end else None,cache_visible=ns(seen.tick) if seen else None,
            ready_promoted=ns(promoted.tick) if promoted else None)
        phase = phase_at_cutoff(core,io,issue_ns,moments['observed_GPU_completion'],moments['cache_visible'],
                                moments['ready_promoted'],cutoff)
        issue_phase = io['phases'][kernel.PHASES[70].index('runtime_issue')]
        return dict(generation=swap.id,surface=writer.a,version=writer.c,native_fence=writer.id,
            core=dict(zip(('queue','ticket','job'),core_key(io),strict=True)),kernel_token=issue.a,
            driver_queue=io['driver_queue'],driver_fence=io['driver_fence'],stage=phase,
            core_commit_queue_ns=core['start_ns']-core['enq_ns'],
            runtime_issue_ns={key:issue_phase[key] for key in ('wall_ns','CPU_lower_ns','CPU_upper_ns')},
            relative_ns={name:(tick-cutoff if tick is not None else None) for name,tick in moments.items()})

    window, = display['windows']
    intervals = window['intervals']
    scored = {interval['frame'] for interval in intervals}
    copied_frames = {}
    for frame,(key,_) in copies.items():
        attempt = attempts[key[0]]
        layer, = [layer for layer in attempt['layers'] if
                  (layer['surface'],layer['copy_start_tick'],layer['copy_end_tick'])==key[1:]]
        if frame in scored:
            require(layer['bytes']==trace.FRAME_BYTES,'scored motion copy is not a full frame')
        fence = layer.get('native_fence')
        token = issued[fence].a if fence is not None else None
        io = submissions.get(token)
        copied_frames[frame] = dict(generation=attempt['generation'],native_fence=fence,kernel_token=token,
            core={name:io[name] for name in ('queue','ticket','job')} if io else None,
            guard_wait_ns=layer['lock_wait_ns'],copy_start_ns=ns(key[2]),copy_end_ns=ns(key[3]))

    frames, repeats = [], []
    for ordinal,interval in enumerate(intervals,1):
        frame, slot = interval['frame'], interval['previous_frame']
        category = interval['after_copy_boundary_check']
        frames.append(dict(ordinal=ordinal,frame=frame,kind=category,CRC=interval['signatures'],
                           certified_copy=copied_frames.get(frame)))
        if category!='repeated':
            continue
        scan = scans.get(slot)
        if scan is None and allow_unbounded:
            repeats.append(dict(frame=frame,scan_slot=slot,cutoff_ns=None,
                                reason='no_conservative_blanking_cutoff',same_CRC_copy=copied_frames.get(frame)))
            continue
        require(scan is not None,'slow-drag repeat has no conservative blanking cutoff')
        preceding = bisect_right(copied_times,scan.opening)-1
        last_copy = copied[preceding][1] if preceding>=0 else 0
        candidates = [timeline(r,scan.deadline) for r in swaps[:bisect_right(swap_times,scan.deadline)] if r.id>last_copy]
        following = next((row['frame'] for row in intervals[ordinal:] if row['frame'] in copied_frames),None)
        next_copy = None
        if following is not None:
            certificate = copied_frames[following]
            swap = accepted.get(certificate['generation'])
            if swap and certificate['native_fence'] is not None:
                next_copy = timeline(swap,scan.deadline)
                require(next_copy.get('native_fence')==certificate['native_fence'],
                        'following copy does not read its exact native writer')
                next_copy.update(frame=following,
                    copy_begin_after_cutoff_ns=certificate['copy_start_ns']-scan.deadline,
                    copy_end_after_cutoff_ns=certificate['copy_end_ns']-scan.deadline)
        probe = probes.get(slot)
        probe_status = (dict(generation=probe.a>>32,result=PROBE_RESULTS[probe.flags],
                             start_after_cutoff_ns=ns(probe.c)-scan.deadline,
                             end_after_cutoff_ns=ns(probe.tick)-scan.deadline) if probe else None)
        repeats.append(dict(frame=frame,scan_slot=slot,cutoff_ns=scan.deadline,previous_copied_generation=last_copy,
                            preblank_probe=probe_status,same_CRC_copy=copied_frames.get(frame),
                            accepted_candidates=candidates,next_certified_copy=next_copy))
    return dict(complete_IO_submits=joined['complete_submit_count'],IO_join_bounds_us=joined['full_script_bounds_us'],
                frames=frames,repeats=repeats,scope='Core, IO, native writer and following guarded copy share exact '
                'boot-local identities. Waiting for observed GPU completion includes observation delay. '
                'An accepted swap without a matching writer has no measured Core-stage attribution.')


def measure(execution):
    frame = score.load(execution/'frame-scanout-analysis.json')
    cal = frame['crc_frame_calibration']
    require(frame['frame_trace_complete'] and frame['misr']['qualified'] and cal['qualified'] and
            cal['lag_frames']==0 and cal['marker_pixel_restored'] and len(cal['dedicated_witnesses'])==3,
            'motion identity requires restored CRC control and three independent latch witnesses')
    core = score.load(execution/'core-wait-execution-analysis.json')
    original = score.load(execution/'kernel-IO-identity-analysis.json')
    decoded = score.load(execution/'kernel-IO-analysis.json')
    require(original['coverage_qualified'] and core['coverage_qualified'],'original Core/IO capture is incomplete')
    raw = (execution/'kernel.log').read_text()
    rows,strokes,num,den = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    display = score.copy.analyze(raw,frame,extra_kinds=score.KINDS)
    ns = lambda tick:tick*num//den
    motion = score.parse_motion(raw,strokes,num,den,cal)
    joined = motion_io_join(decoded,core,motion,ns)
    require(not ({r['kernel_token'] for r in original['submits']} & {r['kernel_token'] for r in joined['submits']}),
            'slow drag overlaps original Core/IO score')
    moving,alignment = score.motion_display(raw,frame,rows,motion,core['rows'],joined['submits'],num,den)
    hz = moving['hardware']['hardware_refresh_hz_bounds']
    steady = score.window_metrics(moving,alignment,rows,motion=motion)['active']
    require(hz and 59<=hz[0]<=hz[1]<=61 and steady['known_scans']>=60 and
            steady['scored_span_ns_bounds'][0]>=1000*score.MS,'incomplete 60 Hz slow-drag capture')
    identity = motion_deadlines(rows,alignment,core,joined,ns,num/den)
    require(len(identity['repeats'])==steady['scans']['repeated'], 'missing slow-drag repeat rows')
    return dict(same_13_strokes=score.window_metrics(frame,display,rows),
        driver_copy_motion_cadence=score.driver_cadence(rows,strokes,original['submits'],core['rows'],num,den),
        frontend=producer_intervals(execution,rows,display,core['rows'],strokes,num,den),
        slow_drag=dict(steady,hardware_refresh_hz_bounds=hz,identity=identity,
            steady_60_qualified=(steady['scans']['changed']==steady['completed_copies']==steady['known_scans'] and
                                 not steady['motion_without_definite_HID_change'])))
