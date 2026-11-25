#!/usr/bin/env python3
"""Run the sustained 60 Hz workload once and count displayed content after restoration."""

import argparse
from bisect import bisect_left
from hashlib import sha256
from importlib import import_module
from itertools import pairwise
import re
from types import SimpleNamespace

import frame344_log as frame
import frame349_log as crc


scope = import_module('prepare-frame417')
runner = import_module('run-core342-trial')
frame_timing = import_module('run-frame416-trial').frame_timing
AUTHORITY = 'standing-bounded-temporary-60Hz-grant-2026-11-21'
WORDING = '可以 就这么做 记的把安卓刷新率的方案进行参考'
SECOND = 19_200_000
SCORE = 'sustained-scanout.json'


def record_grant():
    base = scope.BASE
    ready, review = (scope.load(base / name) for name in ('ready.json', 'final-review.json'))
    scope.require(not (base / 'execution').exists() and not (base / 'approval.json').exists()
                  and review['state'] == 'reviewed-frame417-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  '0417 has no current review')
    scope.save(base / 'approval.json', dict.fromkeys(scope.FLAGS, True) | dict(
        source=AUTHORITY, user_answer=WORDING, user_answer_sha256=sha256(WORDING.encode()).hexdigest(),
        plan_sha256=ready['install_plan_sha256'], trial_plan_sha256=ready['trial_plan_sha256'],
        image_sha256=ready['image_sha256']))


def check_consent(approval, ready, plan, *, trial, flags):
    scope.require(trial == scope.TRIAL and all(approval.get(flag) is True for flag in flags)
                  and not approval.get('fixture_only') and approval.get('source') == AUTHORITY
                  and approval.get('user_answer') == WORDING
                  and approval.get('user_answer_sha256') == sha256(WORDING.encode()).hexdigest()
                  and approval.get('plan_sha256') == plan['install_plan_sha256']
                  and approval.get('trial_plan_sha256') == ready['trial_plan_sha256']
                  and approval.get('image_sha256') == ready['image_sha256'] == plan['image_sha256'],
                  '0417 authorization or exact image differs')


def scan_windows(scans, begin, seconds):
    """Build fixed and overlapping one-second confidence bounds from disjoint edge brackets."""
    bounds = {kind: ([], []) for kind in ('changed', 'repeated', 'unknown')}
    for lower, upper, kind in scans:
        lo, hi = bounds[kind]
        lo.append(lower)
        hi.append(upper)

    def count(start):
        stop = start + SECOND
        overlap = {kind: max(0, bisect_left(lo, stop) - bisect_left(hi, start))
                   for kind, (lo, hi) in bounds.items()}
        lo, hi = bounds['changed']
        certain = max(0, bisect_left(hi, stop) - bisect_left(lo, start))
        return dict(new_frames_min=certain, new_frames_max=overlap['changed'] + overlap['unknown'],
                    repeated_scans=overlap['repeated'], unknown_scans=overlap['unknown'])

    fixed = [dict(second=index + 1, **count(begin + index * SECOND)) for index in range(seconds)]
    end = begin + (seconds - 1) * SECOND
    anchors = {begin, end}
    for lo, hi, _ in scans:
        thresholds = (lo, hi, lo - SECOND, hi - SECOND)
        anchors.update(tick for edge in thresholds for tick in (edge, edge + 1) if begin <= tick <= end)
    complete = [count(tick) for tick in anchors]
    return fixed, dict(anchor_count=len(anchors), minimum_confirmed=min(row['new_frames_min'] for row in complete),
                       maximum_possible=max(row['new_frames_max'] for row in complete),
                       any_unknown=any(row['unknown_scans'] for row in complete))


def display_evidence(raw, plan):
    timing = frame_timing(raw)
    scope.require(timing and timing['reason'] == 1 and timing['records'] < plan['frame_capture']['records']
                  and all(59 <= value <= 61 for value in timing['mean_panel_hz_bounds']),
                  'compact contiguous 60 Hz display capture missing')
    display = 'SWEET F417 DISPLAY: compact CRC and vblank, copies=3072'
    scope.require(raw.splitlines().count(display) == 1, '0417 display profile missing')
    rows = [frame.Event(*(int(col, 16) for col in row.split()))
            for row in re.findall(r'^F344E (.*)$', raw, re.M)]
    scope.require(all(row.kind in (1, frame.VBLANK, frame.CRC, frame.TIMING) for row in rows),
                  '0417 compact trace contains an unexpected event')
    edges = [row for row in rows if row.kind == frame.VBLANK]
    scope.require(all(b.id == a.id + 1 and b.flags == 1 and a.b < b.a for a, b in pairwise(edges)),
                  'hardware scan counters or edge brackets are discontinuous')

    poll, = re.findall(r'^SWEET F345 DPU: stopped=deadline polls=(\d+) configured=1 restored=1 gate=0$', raw, re.M)
    receipt = crc.misr_receipts(raw, dict(polls=int(poll), configured=True, restored=True), edges, 625 / 12,
                               preserve_data_preimage=True)
    scope.require(receipt['qualified'] and receipt['reset']['after'] == 0x01000000, 'MISR cleanup unverified')
    pairs = crc.paired_reads([row for row in rows if row.kind == frame.CRC],
                             {row.id: row for row in edges}, receipt, 625 / 12)
    valid = {scan: pair['signatures'][0] for scan, pair in pairs.items() if pair['agrees']}
    return timing, edges, pairs, valid


def measure(raw, plan, *, score_begin=None):
    timing, edges, pairs, valid = display_evidence(raw, plan)
    first, interval, limit = map(int, frame.one(
        r'^SWEET F417 MOTION: begin=(\d+) interval=(\d+) limit=(\d+)$', raw, 'sustained drag start'))
    last, reports, gap, rc, complete = map(int, frame.one(
        r'^SWEET F417 MOTION: end=(\d+) reports=(\d+) max_gap=(\d+) release_rc=(\d+) complete=([01])$',
        raw, 'sustained drag release'))
    unlocks = re.findall(r'^SWEET UI SCRIPT: end stroke=(\d+) tick=\d+ events=34; HID return only$', raw, re.M)
    motion = plan['sustained_motion']
    warm, seconds = motion['score_after_seconds'], motion['score_seconds']
    begin = first + warm * SECOND if score_begin is None else score_begin
    end = begin + seconds * SECOND
    scope.require(unlocks == ['0'] and interval == SECOND // 100 and limit == motion['position_step_count']
                  and limit == 3300 and 1 < reports <= limit and complete == 1 and rc == 0
                  and motion['duration_ms'] * SECOND // 1000 <= last - first
                  and edges[0].b < first < begin < end < last < edges[-1].a
                  and 'SWEET NVT: observed contact mask=' not in raw,
                  'motion duration, disposition or score coverage differs')

    private = [(int(scan), int(tick)) for scan, tick in re.findall(r'^SWEET F382 L \d+ (\d+) [12] (\d+)$', raw, re.M)]
    original = re.findall(r'^SWEET F382 L 0 \d+ 0 (\d+)$', raw, re.M)
    requests = re.findall(r'^SWEET F382 I 0 \d+ 0 \d+$', raw, re.M)
    drains = re.findall(r'^SWEET F416 DRAIN: cause=(\S+) result=(\S+) polls=(\d+)$', raw, re.M)
    scope.require(private and len(original) == len(requests) == len(drains) == 1
                  and int(original[0]) > max(tick for _, tick in private) and int(original[0]) > end
                  and drains[0][:2] == ('deadline', 'restored') and 1 <= int(drains[0][2]) <= 160,
                  '0416 original front drain is unverified or interrupted the score')
    active_latches = {scan for scan, tick in private if begin <= tick < end}

    scans = []
    repeats = []
    for before, after in pairwise(edges):
        kind = 'unknown'
        if before.id in valid and after.id in valid:
            kind = 'changed' if valid[before.id] != valid[after.id] else 'repeated'
        if kind == 'repeated' and after.a < end and after.b >= begin:
            repeats.append(after.id)
        scans.append((after.a, after.b, kind))
    fixed, sliding = scan_windows(scans, begin, seconds)
    result = dict(panel_timing=timing, crc_pairs=len(pairs), agreeing_crc_pairs=len(valid),
                original_front_latched=True, handback_polls=int(drains[0][2]), original_latch_tick=int(original[0]),
                motion=dict(first_tick=first, last_tick=last, reports=reports, release_verified=True,
                            max_report_gap_ms=gap * 1000 / SECOND),
                score_seconds=seconds, fixed_seconds=fixed, sliding_windows=sliding,
                completely_measured_seconds=sum(row['unknown_scans'] == 0 for row in fixed),
                private_latches_total=len(private), private_latches_in_score=len(active_latches),
                private_latches_after_legacy_limit_in_score=sum(begin <= tick < end for _, tick in private[1024:]),
                repeated_scan_ids=repeats, repeat_with_private_latch=sum(scan in active_latches for scan in repeats),
                stable_60_fps_observed=sliding['minimum_confirmed'] >= 60 and not sliding['any_unknown'])
    if score_begin is not None:
        result['score_begin_tick'] = begin
    return result


def observe_restored(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  '0417 requires independent restoration before reading display evidence')
    path = execution / 'kernel.log'
    raw = path.read_text()
    scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1, '0417 kernel identity missing')
    try:
        observed = measure(raw, plan)
    except ValueError as error:
        result.update(state='0417-sustained-measurement-unverified-root-restored', measurement_error=str(error))
        return
    scope.save(execution / SCORE, dict(observed, kernel_log_sha256=scope.sha(path),
        independent_restore_sha256=scope.sha(execution / 'independent-restore.json')))
    result.update(state=scope.SUCCESS, comparison=SCORE,
        independently_measured_display_scans=True, physical_FPS_qualified=observed['completely_measured_seconds'] == 30,
        completely_measured_seconds=observed['completely_measured_seconds'],
        stable_60_fps_observed=observed['stable_60_fps_observed'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-actual-request', action='store_true')
    if parser.parse_args().record_actual_request:
        record_grant()
        return 0
    plan, approval, budget = import_module('run-frame347-trial').authorization(
        SimpleNamespace(check_consent=check_consent), base=scope.BASE, trial=scope.TRIAL,
        expected=scope.expected_plan, flags=scope.FLAGS, reserve=scope.RESERVE)
    return runner.execute(plan, approval, budget, scope.BASE, scope.BASE / 'execution',
                          trial=scope.TRIAL, after_restore=observe_restored, success_state=scope.SUCCESS)


if __name__ == '__main__':
    raise SystemExit(main())
