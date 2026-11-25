#!/usr/bin/env python3
"""Replay 0383/0384 scanout and separate swipe onset from staging delays."""

from collections import Counter
from importlib import import_module
import json
from statistics import median
from types import SimpleNamespace

import frame344_log as trace
import frame349_log as crc
from frame357_display import calibration
from frame357_replay import TOTAL_LINES
from frame369_swap_timing import decode as swap_timing
from frame372_transport import PACKET_FAMILY
import frame374_native_ca as native
from frame376_capture import packet_lane
from kernel342_log import ring_status

trial = import_module('run-frame384-trial')
feasible = import_module('audit-frame-supply').feasible
scope = trial.scope
EXECUTION = scope.BASE/'execution'
COMPARISON = EXECUTION/'scanout-comparison-0383-0384.json'
PINNED = {
    'result.json': 'a86af5389757fe4ef448674a0ad3a06bfb967133801c01461ad55643c5c28439',
    'independent-restore.json': '616b9f6327318b679c830d596c426a6977d77e747044a578128badc1786bb4d2',
    'scanout-comparison-0383-0384.json': 'ca2f4ef20ec4feadfa5e900b98f24df42dec871db4f2b7d702b82564662cbaa4',
}


def verify_scans(root, report, raw, rows, strokes, scans, latches, edges, n, d):
    terminal = scope.load(root/'result.json')
    proof = scope.load(root/'independent-restore.json')
    trace.require(terminal['restored'] and terminal['independent_restore_verified'] and
        terminal['static_root_comparison_passed'] and terminal['dpu_new_content_FPS_qualified'] and
        len(terminal['other_log_prefix_preserved']) == 4 and all(terminal['other_log_prefix_preserved'].values()) and
        len(proof['files']) == 6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
        proof['misc_original_4096_bytes_match'] and proof['device_writes'] == proof['device_boots'] == 0,
        'independent restoration must qualify before scoring')
    trace.require(ring_status((root/'kernel.log.bin').read_bytes(), raw)['qualified'],
                  'persistent console differs from the archived capture')
    gate = trial.staging.score.scanout.probe(raw, read_only_counts_with_crc=True)
    control = crc.misr_receipts(raw, gate, rows[trace.VBLANK], n/d, preserve_data_preimage=True)
    pairs = crc.paired_reads(rows[trace.CRC], edges, control, n/d)
    offscreen = {tick for _, _, tick in report['page_flips']['staged']}
    front_copies = [dict(seq=row.seq, surface=row.id, start_tick=row.a, end_tick=row.b, link=None)
                    for row in rows[trace.COPY] if row.b not in offscreen]
    witnesses = calibration(rows, strokes, pairs, front_copies, n/d)
    trace.require(control == report['crc_control'] and control['qualified'] and len(pairs) == 2704 and
        all(pair['agrees'] for pair in pairs.values()) and witnesses['qualified'] and witnesses['lag_frames'] == 0 and
        witnesses['marker_pixel_restored'] and witnesses['dedicated_witnesses'] == report['CRC_witnesses'],
        'CRC cleanup, pair agreement or zero-lag witnesses differ')
    for row in scans:
        frame = row['frame']
        edge = edges[frame]
        lower, upper = row['vblank_ticks']
        before, current = (pairs[number]['signatures'][0] for number in (frame-1, frame))
        classification = 'changed' if current != before else 'repeated'
        trace.require(edge.flags == 1 and edge.a <= lower < upper <= edge.b and
            row['crc_signatures'] == [before, current] and row['crc'] == classification and
            (classification == 'repeated' or frame in latches), 'scored scan differs from raw vblank or CRC')


def completion_order(events, latches, edges, n, d, tolerance_ns):
    kinds = (native.DRIVER_TARGET, native.DRIVER_DELIVERY, native.FRAME_INFO)
    target, delivery, feedback = (trace.indexed((e for e in events if e.kind == kind),
                                                lambda e: e.args[0], native.NAMES[kind]) for kind in kinds)
    trace.require(len(delivery) == len(feedback) == len(latches), 'lost or extra private FrameInfo completion')
    ordered = []
    maximum_clock_delta_ticks = 0
    for scan, latch in sorted(latches.items()):
        swap = latch['swap']
        asked, sent, received = target[swap], delivery[swap], feedback[swap]
        edge = edges[scan]
        native_target = asked.args[2]
        actual_delta = abs(received.args[2] - edge.b)
        target_delta = abs(received.args[3] - native_target)
        delta = max(actual_delta, target_delta)
        trace.require(asked.args[1] == latch['generation'] and
            asked.args[3] == (latch['version'] << 32 | latch['surface']) and
            native_target not in native.NO_TIMESTAMP and received.args[2] not in native.NO_TIMESTAMP and
            sent.args[1:] == (scan, edge.a, edge.b) and delta*n <= tolerance_ns*d and
            latch['confirmed_tick'] <= sent.tick <= received.tick,
            'FrameInfo does not match the exact confirmed source, swap or target')
        maximum_clock_delta_ticks = max(maximum_clock_delta_ticks, delta)
        ordered.append((sent.tick, received.tick))
    trace.require(all(first[0] < second[0] and first[1] < second[1] for first, second in zip(ordered, ordered[1:])),
                  'FrameInfo sends or returns are out of latch order')
    return dict(ordered_after_confirmed_latch=len(ordered),
                maximum_timestamp_residual_ns=maximum_clock_delta_ticks*n/d)


def swipe_waits(root, raw, rows, strokes, scans, latches, events, start, end, n, d):
    first = trial.staging.first_frames(root, raw, rows, strokes, n, d, scans, latches)
    links = native.link_swaps(events, swap_timing(rows, n, d, begin_threads=True), start, end, n, d)
    transport = packet_lane(raw, n, d)
    packets = [p for p in transport['pairs'] if p['message_id'] in PACKET_FAMILY]
    warm_waits, cold = [], []
    for row, (down, up) in zip(first['strokes'], strokes, strict=True):
        ordinal = row['stroke']
        touch = down*n//d
        lane = [scan for scan in scans if scan['workload'] == 'ordinary' and scan['stroke'] == ordinal]
        if ordinal < 3:
            shown = next(scan for scan in lane if scan['crc'] == 'changed')
            latch = latches[shown['frame']]
            linked = links[latch['generation']]['render']
            cold.append(dict(stroke=ordinal, phase=shown['phase'], scan=shown['frame'],
                generation=latch['generation'], release_ns=up*n//d-touch,
                first_change_bounds_ns=[tick*n//d-touch for tick in shown['vblank_ticks']],
                render_begin_ns=linked['begin_tick']*n//d-touch,
                cache_visible_ns=latch['visible_tick']*n//d-touch))
            continue
        times = row['timeline_from_touch_ns']
        render = touch + times['CA_render']
        returned = touch + row['touch_to_first_callback_return_ns']
        selected = [p for p in packets if returned <= p['send_ns'] <= p['copyout_ns'] < render]
        trace.require(not any(returned <= p['take_tick']*n//d < render for p in transport['unmatched_receipts']),
                      'unmatched copyout in warm first-render window')
        warm_waits.append(dict(stroke=ordinal, before_first_render_ns=render-returned,
            cache_visible_to_copy_start_ns=times['start_staging']-times['cache_visible'],
            copy_to_barrier_ns=times['stage_barrier']-times['start_staging'],
            IPC_send_to_copyout_ns=[p['copyout_ns']-p['send_ns'] for p in selected]))
    ipc = [duration for row in warm_waits for duration in row['IPC_send_to_copyout_ns']]
    timing = {key: median(row[key] for row in warm_waits) for key in (
        'before_first_render_ns', 'cache_visible_to_copy_start_ns', 'copy_to_barrier_ns')}
    return first, dict(warm_medians=timing, warm_swipes=warm_waits, cold_first_changes=cold,
        warm_IPC=dict(count=len(ipc), p50_ns=median(ipc), maximum_ns=max(ipc)),
        IPC_scope='Packet-family timing during the callback-to-render interval. Render transaction membership is unknown.')


def drag_deadlines(report, raw, latches, edges, n, d, guard_lines):
    end_line = int(trace.one(r'^SWEET F351 WINDOW: available=1 frame=\d+ end=(\d+)$', raw, 'scan guard end'))
    line = end_line-guard_lines
    output = []
    for miss in report['slow_drag_repeat_waits']:
        scan = miss['frame']
        edge, previous = edges[scan], edges[scan-1]
        latch = latches[scan+1]
        trace.require(edge.flags == previous.flags == 1 and scan not in latches,
                      'slow-drag repeat lacks consecutive edges or has an unchanged private latch')
        a = ((TOTAL_LINES-line)*previous.a + line*edge.a)//TOTAL_LINES
        b = ((TOTAL_LINES-line)*previous.b + line*edge.b)//TOTAL_LINES
        def offset(tick):
            return [(tick-b)*n//d, (tick-a)*n//d]

        output.append(dict(repeated_scan=scan, following_generation=latch['generation'],
            EOP_relative_to_scan_ns=[(latch['eop_tick']-x)*n//d for x in (edge.b, edge.a)],
            cache_visible_relative_to_cutoff_ns=offset(latch['visible_tick']),
            copy_start_relative_to_cutoff_ns=offset(latch['begin']),
            copy_barrier_relative_to_cutoff_ns=offset(latch['tick'])))
    return dict(rows=output, last_issue_line=line,
                scope='The cutoff is interpolated between vblank brackets. There is no sample of the final eligible poll.')


def frame_supply(rows, scans, latches):
    accepted = {row.id: row for row in rows[trace.SWAP] if not row.flags and row.c}
    issues = {row.id: row.tick for row in rows[trace.ISSUE]}
    visible = {row.id: row.tick for row in rows[trace.READY]}
    arrivals = dict(accepted={g: swap.tick for g, swap in accepted.items()}, issue={}, cache_visible={})
    for row in rows[trace.WRITER]:
        generation = row.b >> 32
        swap = accepted.get(generation)
        if swap and swap.c == (row.c << 32 | row.a):
            arrivals['issue'][generation] = issues[row.id]
            if row.id in visible:
                arrivals['cache_visible'][generation] = visible[row.id]

    totals = {name: Counter() for name in ('warm_active', 'warm_motion', 'slow_drag')}

    def add_window(total, lane):
        first, last = lane[0]['frame'], lane[-1]['vblank_ticks'][1]
        preceding = max((scan for scan in latches if scan < first), default=0)
        generation = latches[preceding]['generation'] if preceding else 0
        slots = [SimpleNamespace(end=scan['vblank_ticks'][1]) for scan in lane]
        total['scans'] += len(slots)
        total['changed'] += sum(scan['crc'] == 'changed' for scan in lane)
        for name, ticks in arrivals.items():
            candidates = [(g, tick) for g, tick in ticks.items() if g > generation and tick <= last]
            total[name] += feasible(slots, candidates, generation)

    active = [scan for scan in scans if scan['phase'] == 'active']
    for stroke in range(3, 14):
        lane = [scan for scan in active if scan['workload'] == 'ordinary' and scan['stroke'] == stroke]
        changed = [i for i, scan in enumerate(lane) if scan['crc'] == 'changed']
        add_window(totals['warm_active'], lane)
        add_window(totals['warm_motion'], lane[changed[0]:changed[-1]+1])
    add_window(totals['slow_drag'], [scan for scan in active if scan['workload'] == 'slow_drag'])
    trace.require(all(row['scans'] >= row['accepted'] >= row['issue'] >= row['cache_visible'] >= row['changed']
                      for row in totals.values()), 'optimistic frame supply disagrees with observed scanout')
    return dict(windows=totals, scope='Fix the observed producer timestamps and last earlier latch for each window. '
                'Allow any increasing generation, perfect retention, distinct pixels, zero transfer and the latest vblank bound.')


def audit():
    scope.baseline()
    trace.require(all(scope.sha(EXECUTION/name) == sha for name, sha in PINNED.items()),
                  '0384 terminal receipts or primary comparison changed')
    comparison = scope.load(COMPARISON)
    plan_path = scope.BASE/'trial-plan.json'
    trace.require(scope.sha(plan_path) == scope.load(EXECUTION/'claim.json')['trial_plan_sha256'],
                  'trial plan differs from the one-shot claim')
    plan = scope.load(plan_path)
    tolerance = plan['frame_info_provider']['clock_match_tolerance_ns']
    scans_by_trial, details = {}, {}
    for name, root, path in (
        ('0383', scope.REFERENCE, scope.COMPARISON),
        ('0384', EXECUTION, EXECUTION/'scanout-comparison-0380-0381-0384.json'),
    ):
        report = scope.load(path)
        raw, rows, strokes, n, d, latches, scans = trial.measure(root, report, trial=name)
        edges = trace.indexed(rows[trace.VBLANK], lambda row: row.id, 'hardware edge')
        verify_scans(root, report, raw, rows, strokes, scans, latches, edges, n, d)
        start, end, _, _ = native.envelope(raw)
        events = native.decode(raw, start, end)
        completions = completion_order(events, latches, edges, n, d, tolerance)
        first, waits = swipe_waits(root, raw, rows, strokes, scans, latches, events, start, end, n, d)
        trace.require(first == comparison['first_ordinary_frames'][name] and
                      report['metrics'] == comparison['metrics'][name], 'frozen onset or rates differ')
        details[name] = dict(scored_scans=len(scans), frame_info=completions, first_swipe=waits,
                             supply=frame_supply(rows, scans, latches))
        scans_by_trial[name] = scans
        if name == '0384':
            guard = plan['display_dma']['guard_lines_at_least']
            details[name]['drag_deadlines'] = drag_deadlines(report, raw, latches, edges, n, d, guard)
    pair = trial.parent.parent.parent.paired_ordinals(scans_by_trial)
    trace.require(pair == comparison['per_scan'], 'scan-ordinal comparison differs')
    transitions = {}
    for row in pair:
        key = f"{row['workload']}_{row['phase']}"
        a, b = (s['crc'] if s else 'unpaired' for s in row['scans'].values())
        transitions.setdefault(key, Counter())[f'{a}_to_{b}'] += 1
    return dict(trials=details, comparisons=len(pair), ordinal_transitions=transitions, device_commands=0)


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
