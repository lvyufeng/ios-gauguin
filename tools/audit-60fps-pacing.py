#!/usr/bin/env python3
"""Replay completed 0350, 0355 and 0356 captures without device I/O."""

import json
import re
from collections import Counter, defaultdict

import frame344_log as trace
import frame354_display as ready
from frame356_scope import BASE, REF350, REF355, check_references, load, sha

TRIALS = {'0350': REF350, '0355': REF355, '0356': BASE/'execution'}
RESULT_356 = '33427c7e9b16abf9a0ef4f0023d2b2f536c84a5617b9c4b813bd29d3d48c94be'
PROOF_356 = '1ae043c6e6450727f38e74621ebe8d28a50f78d0f155ee8db6f1d1dd410d90d8'
PHASES = ('active', 'release')


def stats(values):
    return dict(samples=len(values), median=trace.quantile(values, .50),
                p95=trace.quantile(values, .95), maximum=max(values, default=None))


def job_key(row):
    return row['queue'], row['ticket'], row['job']


def swap_cohort(swaps, history, rows, attempts, scale):
    """Follow an accepted generation through the end of the captured trace."""
    next_swaps = {left.id: right for left, right in zip(history, history[1:])}
    writers = defaultdict(list)
    for row in rows[trace.WRITER]:
        writers[row.a, row.c].append(row)
    completed = trace.indexed(rows[trace.READY], lambda row: row.id, 'visible native fence')
    promos = trace.indexed(rows[ready.PROMOTE], lambda row: row.id, 'latch promotion')
    taken = {row.a for row in rows[ready.TAKE]}
    copied = {row['generation'] for row in attempts if row['layers']}
    counts = Counter()
    until_visible = []
    for swap in swaps:
        if swap.b != 1 or not swap.c:
            counts['other_swap_shape'] += 1
            continue
        surface, version = swap.c & 0xffffffff, swap.c >> 32
        ticket = (swap.id << 32) | surface
        candidates = writers[surface, version]
        matched = [row for row in candidates if row.b == ticket]
        successor = next_swaps.get(swap.id)
        if not candidates:
            counts['no_expected_surface_version_seen'] += 1
        elif not matched:
            counts['expected_version_with_other_or_no_ticket'] += 1
            if successor and (candidates[0].tick, candidates[0].seq) > (successor.tick, successor.seq):
                counts['unmatched_writer_receipt_after_successor'] += 1
        else:
            event, = matched
            counts['same_ticket_writer'] += 1
            fence = completed.get(event.id)
            if not fence:
                counts['matched_writer_without_visible_fence'] += 1
            else:
                until_visible.append((fence.tick-event.tick)*scale)
                if successor and (successor.tick, successor.seq) < (fence.tick, fence.seq):
                    counts['successor_accepted_before_visible_fence'] += 1
                    trace.require(swap.id not in promos, 'overwritten waiter still promoted')
        if swap.id in promos:
            counts['promoted'] += 1
        if swap.id in taken:
            counts['selected'] += 1
        if swap.id in copied:
            counts['copied'] += 1
    return dict(accepted_generations=len(swaps), counts=dict(counts),
                writer_receipt_to_observed_visibility_ns=stats(until_visible))


def audit_trial(trial, path, aligned):
    result = load(path/'result.json')
    proof = load(path/'independent-restore.json')
    trace.require(result['trial']==trial and result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'] and result['frame_trace_complete'] and
                  len(proof['files'])==6 and proof['journal_empty'], 'missing independently read-back trial')
    raw = (path/'kernel.log').read_text()
    extra = ready.KINDS if trial != '0350' else ()
    rows, strokes, numer, denom = trace.parse(raw, extra_kinds=(52, 53, *extra))
    scale = numer / denom
    frame = load(path/'frame-scanout-analysis.json')
    core = load(path/'core-wait-execution-analysis.json')
    identity = load(path/'kernel-IO-identity-analysis.json')
    io = load(path/'kernel-IO-analysis.json')
    trace.require(len(strokes)==13 and core['coverage_qualified'] and identity['coverage_qualified'] and
                  io['coverage_qualified'], 'incomplete workload or Core and I/O capture')
    linked = trace.indexed(identity['submits'], job_key, 'exact Core submit')
    native = trace.indexed((row for row in io['rows'] if row['selector']==0x46),
                           lambda row: row['token'], 'kernel submit')
    phases = io['phase_names'][str(0x46)]
    gpu_lock = phases.index('GPU_lock')
    runtime = phases.index('runtime_issue')
    copies = [(row.a * scale, row.b * scale) for row in rows[trace.COPY]]
    trace.require(all(left[1]<=right[0] for left,right in zip(copies,copies[1:])), 'copy trace overlaps')
    swaps = [row for row in rows[trace.SWAP] if not row.flags]
    taken = load(path/'ready-selection-analysis.json')['joins'] if extra else []
    attempt_joins = {row['attempt']: row for row in taken}
    full = result['display_phases'] if 'display_phases' in result else aligned['phases']

    beats = [tuple(map(int, match)) for match in re.findall(
        r'^SWEET FB CLOCK: callbacks=(\d+) skipped=(\d+) copies=(\d+) next_beat=(\d+) next_copy=(\d+); software only$',
        raw, re.M)]
    before = [row for row in beats if row[3]<=strokes[0][0]]
    after = [row for row in beats if row[3]>=strokes[-1][1]]
    clock = None
    if before and after:
        start, end = before[-1], after[0]
        clock = dict(callbacks=end[0]-start[0], skipped=end[1]-start[1], announced_next_beat_span_ns=(end[3]-start[3])*scale)

    output = {}
    for phase in PHASES:
        windows = [w for w in frame['hardware']['windows'] if w['window']==phase]
        trace.require(len(windows)==13, 'missing hardware scoring windows')
        spans = [(w['vblank_edges'][0]['edge_upper_tick'], w['vblank_edges'][-1]['edge_upper_tick']) for w in windows]
        elapsed = sum(hi-lo for lo,hi in spans)*scale

        def contains(tick):
            return any(lo<tick<=hi for lo,hi in spans)

        events = dict(accepted_swap=sum(contains(row.tick) for row in swaps))
        for kind, label in ((trace.ISSUE,'writer_issue'),(trace.READY,'fence_visible'),(ready.PROMOTE,'ready_promotion'),
                           (ready.TAKE,'selected_ready'),(trace.ATTEMPT,'present_attempt'),(trace.COPY,'copy_done')):
            events[label] = sum(contains(row.tick) for row in rows[kind])
        arrived = [row for row in swaps if contains(row.tick)]
        gaps = []
        per_stroke = []
        for window,(lo,hi) in zip(windows,spans,strict=True):
            lane = [row.tick for row in swaps if lo<row.tick<=hi]
            local_gaps = [(b-a)*scale for a,b in zip(lane,lane[1:])]
            gaps.extend(local_gaps)
            per_stroke.append(dict(stroke=window['stroke']+1, hardware_intervals=len(window['outputs']),
                accepted_swaps=len(lane), elapsed_ns=(hi-lo)*scale,
                first_accepted_offset_ns=(lane[0]-lo)*scale if lane else None,
                last_accepted_to_end_ns=(hi-lane[-1])*scale if lane else None,
                first_to_last_accepted_ns=sum(local_gaps)))

        jobs = [row for row in core['rows'] if job_key(row) in linked and contains(row['enq_ns']/scale)]
        trace.require(jobs, 'missing matched Core enqueue window')
        waits = [row['start_ns']-row['enq_ns'] for row in jobs]
        issue_ns = []
        lock_ns, shared_with_copy = [], []
        for job in jobs:
            link = linked[job_key(job)]
            driver = native[link['kernel_token']]
            trace.require((link['driver_queue'], link['driver_fence'])==(driver['queue'],driver['fence']),
                          'inconsistent native submit identity')
            measured = driver['phases']
            issue_ns.append(measured[runtime]['wall_ns'])
            lo,hi = (measured[gpu_lock][name] for name in ('begin_ns','end_ns'))
            lock_ns.append(hi-lo)
            common = sum(max(0,min(hi,right)-max(lo,left)) for left,right in copies if left<hi and right>lo)
            if common:
                shared_with_copy.append(common)

        disposition = Counter()
        for attempt in frame['attempts']:
            if not contains(attempt['attempt_tick']):
                continue
            ref = attempt_joins.get(attempt['attempt'])
            if attempt['layers']:
                disposition['copied'] += 1
            elif ref and ref['stale']:
                disposition['stale_version'] += 1
            elif attempt['refused_guards']:
                disposition['read_guard_refusal'] += 1
            else:
                disposition['no_copy_after_other_checks'] += 1
        summary = full[phase]
        certified = summary.get('verified_full_frame_counts', summary.get('full_frame_counts'))
        known_fps = None
        if certified and result.get('crc_frame_calibration', {}).get('qualified'):
            elapsed_hi = sum(window['elapsed_ns_high'] for window in windows)
            elapsed_lo = sum(window['elapsed_ns_low'] for window in windows)
            known_fps = [certified['changed']*1e9/elapsed_hi, (certified['changed']+certified['unknown'])*1e9/elapsed_lo]

        output[phase] = dict(
            hardware_intervals=sum(len(w['outputs']) for w in windows), elapsed_upper_edge_to_upper_edge_ns=elapsed,
            same_window_events=events, same_window_events_per_second={k:v*1e9/elapsed for k,v in events.items()},
            arrival_gap_ns=stats(gaps), first_accepted_offset_ns=stats(
                [r['first_accepted_offset_ns'] for r in per_stroke if r['first_accepted_offset_ns'] is not None]),
            accepted_swaps_between_first_and_last_per_second=len(gaps)*1e9/sum(gaps) if gaps else None,
            accepted_swap_gaps_over_25_ms=sum(gap>25_000_000 for gap in gaps), per_stroke=per_stroke,
            observed_CRC_counts=summary['signature_counts'],
            verified_full_frame_counts=certified, full_frame_rate_bounds=known_fps,
            scanout_CRC_rate=summary['output_updates_per_second'],
            matched_Core_commit_enqueues=len(jobs), core_queue_ns=stats(waits),
            core_owned_busy_share_of_wait=sum(row['busy_wait_ns'] for row in jobs)/sum(waits),
            accumulated_record_and_commit_ns=stats([row['own_exec_ns'] for row in jobs]),
            render_ns=stats([row['exec_ns'][2] for row in jobs]), commit_ns=stats([row['exec_ns'][6] for row in jobs]),
            runtime_issue_ns=stats(issue_ns), gpu_lock_phase_ns=stats(lock_ns),
            gpu_lock_phase_intersection_with_guarded_copy_ns=stats(shared_with_copy),
            summed_lock_phase_ns=sum(lock_ns), summed_copy_intersection_ns=sum(shared_with_copy),
            attempt_results=dict(disposition),
            late_start_deferrals=summary.get('late_deferrals'),
            paired_copy_p95_ns=summary.get('paired_copy_p95_ns'),
            arrival_cohort=swap_cohort(arrived,swaps,rows,frame['attempts'],scale) if extra else None)
    relevant = ('result.json','independent-restore.json','kernel.log','frame-scanout-analysis.json',
                'core-wait-execution-analysis.json','kernel-IO-identity-analysis.json','kernel-IO-analysis.json')
    return dict(phases=output, software_beat_snapshots_over_script=clock,
        crc_latch_qualified=result['crc_frame_calibration']['qualified'],
        input_sha256={name:sha(path/name) for name in relevant})


def main():
    check_references()
    p = TRIALS['0356']
    trace.require(sha(p/'result.json')==RESULT_356 and sha(p/'independent-restore.json')==PROOF_356,
                  '0356 restored result changed')
    path = p/'present-alignment-0350-0355-0356.json'
    alignment = load(path)
    displays = alignment['references'] | {'0356': alignment['current']}
    result = {n:audit_trial(n, trial, displays[n]) for n,trial in TRIALS.items()}
    print(json.dumps(dict(state='0350-0355-0356-offline-pacing-audit', alignment_sha256=sha(path), trials=result,
                         device_commands=0), indent=2))


if __name__=='__main__':
    main()
