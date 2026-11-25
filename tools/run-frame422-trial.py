#!/usr/bin/env python3
"""Run the single-argument 0422 phase comparison and verify restoration."""

import argparse
from hashlib import sha256
from importlib import import_module
import re
import json
from types import SimpleNamespace

import frame419_log as timeline


scope = import_module('prepare-frame422')
observer = import_module('run-frame417-trial')
runner = import_module('run-core342-trial')
AUTHORITY = 'standing-bounded-temporary-60Hz-grant-2026-11-21'
WORDING = '继续优化'


def record_grant():
    base = scope.BASE
    ready, review = (scope.load(base / name) for name in ('ready.json', 'final-review.json'))
    scope.require(not (base / 'execution').exists() and not (base / 'approval.json').exists()
                  and review['state'] == f'reviewed-frame{int(scope.TRIAL)}-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  '0422 has no current review')
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
                  '0422 authorization or exact image differs')


def phase_receipt(raw):
    scope.require(raw.splitlines().count(f'SWEET F388 DISPATCH: work_us={scope.WORK_US}') == 1,
                  '0422 measured work phase missing')
    samples = re.findall(
        r'^SWEET F388 P: seq=\d+ scan=\d+ source=\d+ o=\d+ w=(\d+) r=(\d+) p=(\d+) a=(\d+)$',
        raw, re.M)
    footer, = re.findall(
        r'^SWEET F388 F: rows=(\d+) aligned=(\d+) software=(\d+) fallback=(\d+) missed=(\d+) first=\d+ last=\d+$',
        raw, re.M)
    count, aligned, software, fallback, missed = map(int, footer)
    scope.require(0 < count == len(samples) <= 24 and aligned > count
                  and all(ready - wake == scope.WORK_US * 96 // 5 and wake <= issued < ready < edge
                          for wake, ready, edge, issued in (map(int, row) for row in samples)),
                  '0422 observed timer budget differs')
    return dict(work_us=scope.WORK_US, samples=count, aligned=aligned, software=software,
                fallback=fallback, missed=missed)


def observe_restored(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  '0422 requires independent restoration before reading display evidence')
    log = execution / 'kernel.log'
    raw = log.read_text()
    scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1, '0422 kernel identity missing')
    try:
        phase = phase_receipt(raw)
        score = observer.measure(raw, plan)
        score['whole_interval'] = timeline.whole_interval(raw, score, plan)
    except ValueError as error:
        result.update(state='0422-scanout-measurement-unverified-root-restored', measurement_error=str(error))
        return

    evidence = dict(kernel_log_sha256=scope.sha(log),
                    independent_restore_sha256=scope.sha(execution / 'independent-restore.json'))
    scope.save(execution / observer.SCORE, dict(score, **evidence))
    result.update(state='0422-scans-measured-timeline-unverified-root-restored', comparison=observer.SCORE,
                  independently_measured_display_scans=True,
                  physical_FPS_qualified=score['completely_measured_seconds'] == 30,
                  completely_measured_seconds=score['completely_measured_seconds'],
                  stable_60_fps_observed=score['stable_60_fps_observed'])
    try:
        diagnostic = dict(timeline.measure(raw, score, plan), **evidence)
        scope.require(len(json.dumps(diagnostic, indent=2).encode()) + 1 <= 524_288, 'timeline report exceeds reserve')
    except (KeyError, ValueError) as error:
        result['timeline_error'] = str(error)
        return
    name = 'display-deadlines.json'
    scope.save(execution / name, diagnostic)
    baseline = scope.load(scope.P419 / 'execution' / observer.SCORE)
    baseline_deadline = scope.load(scope.P419 / 'execution/display-deadlines.json')
    comparison = {}
    for version, work, sample, deadlines in (
            ('0419', 7200, baseline, baseline_deadline), ('0422', scope.WORK_US, score, diagnostic)):
        comparison[version] = dict(work_us=work, new_images=sample['whole_interval'],
            repeats=len(sample['repeated_scan_ids']), worst_confirmed_second=sample['sliding_windows']['minimum_confirmed'],
            fixed_confirmed_60_seconds=sum(window['new_frames_min'] >= 60 for window in sample['fixed_seconds']),
            copy_p50_ms=deadlines['median_copy_ms'], exact_writer_joins=deadlines['exact_writer_joins_in_score'])
    compared = 'work-phase-comparison.json'
    scope.save(execution / compared, dict(comparison, device_writes_during_analysis=0, phase_receipt=phase))
    result.update(state=scope.SUCCESS, deadline_timeline=name, work_phase_comparison=compared,
                  measured_work_us=scope.WORK_US, exact_writer_joins_in_score=diagnostic['exact_writer_joins_in_score'])


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
