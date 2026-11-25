#!/usr/bin/env python3
"""Host-only tests of 0343 gates, compare and optical measurement."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
from unittest.mock import patch

from core343_scope import BASE, P342, REFERENCE, REF_DECODE, expected_plan, load

from importlib.util import module_from_spec, spec_from_file_location


def tool(name):
    spec = spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    value = module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def refused(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError('unqualified input accepted')


def check_optics(optical, out):
    counts = []
    for rate in (120, 240):
        times = [round(i*1_000_000/rate) for i in range(42*rate)]
        assert optical.camera_clock(times)[0] == rate
        refused(lambda: optical.camera_clock(times[:300]+times[301:]))
        still = [0, 600000]
        intervals = [[1200000+2500000*i, 1800000+2500000*i] for i in range(13)]
        layout = dict(still_reference_us=still, visible_strokes_us=intervals)
        script = [dict(begin_us=a+226000000) for a, b in intervals]
        channels = [[0.]*(len(times)-1) for _ in range(3)]
        expected = []
        for stroke, (a,b) in enumerate(intervals):
            events = [i for i, t in enumerate(times) if a <= t < b and i % (rate//60) == 0]
            if stroke == 5:
                del events[9:14]
            expected.append(len(events))
            for i in events:
                channels[0][i-1] = channels[1][i-1] = 14.
        report = optical.measure(times, channels, script, layout, rate, 1_000_000/rate)
        assert [s['visible_updates'] for s in report['strokes']] == expected
        assert report['strokes'][5]['definitely_over_25ms'] == 1
        assert all(not s['definitely_over_25ms'] for s in report['strokes'] if s['stroke'] != 5)
        channels[2][times.index(intervals[4][0])-1] = 15.
        refused(lambda: optical.measure(times, channels, script, layout, rate, 1_000_000/rate))
        counts.append(sum(expected))
    with TemporaryDirectory(prefix='0343-optical-test-', dir=out) as folder:
        clip = Path(folder)/'synthetic.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=s=320x160:r=240:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        str(clip)], check=True, timeout=30)
        w, h, times, rate, _step = optical.probe(clip)
        assert (w, h, len(times), rate) == (320, 160, 240, 240)
        result = optical.decode(clip, w, h, [[0,20,100,12],[110,20,100,12],[220,40,100,12]], len(times))
        assert all(len(channel) == 239 for channel in optical.differences(result))
    return counts


def main():
    out = BASE/'pipeline-343'
    out.mkdir()
    plan = expected_plan()
    runner = tool('run-core343-trial')
    old_pipeline = tool('check-core342-pipeline')
    compare = tool('compare-runtime343')
    optical = tool('measure-runtime343-optical')
    checks = []
    with patch.object(runner.subprocess, 'run', side_effect=AssertionError('before consent')):
        refused(runner.authorization)
    assert not (BASE/'execution').exists()
    checks.append('missing-0343-approval-refused-without-a-device-command')
    parent = load(P342/'approval.json')
    ready = dict(install_plan_sha256=plan['install_plan_sha256'], trial_plan_sha256='fixture')
    for approval in (parent, dict(fixture_only=True)):
        refused(lambda: runner.RUN.check_consent(approval, ready, plan, trial='0343', flags=runner.APPROVAL_FLAGS))
    checks.append('consumed-0342-and-fixture-approval-refused')

    for label in ('success','post-capture-failure','restore-preparation-refusal','restore-rollback',
                  'independent-failure','final-capture-failure','observer-before-launch-failure',
                  'observer-owner-alive','install-rollback','restore-receipt-failure'):
        old_pipeline.control_fixture(out, plan, label, checks)
        if label != 'success':
            assert not list((out/('flow-'+label)/'execution').glob('*.current'))
    checks.append('log-integrity-work-absent-on-failed-restore-or-readback')

    def fake_decode(execution, p, verdict, before, code):
        verdict['state'] = 'CR342-observation-unqualified-root-restored'

    from types import SimpleNamespace
    verdict = dict(static_root_comparison_passed=True)
    with patch.object(runner, 'tool', return_value=SimpleNamespace(analyze_saved=fake_decode)) as loader:
        runner.after_restore(out, plan, verdict, None, 0)
        loader.assert_called_once_with('analyze-core342')
    assert verdict['optical_measurement'] == 'withheld-by-collection-gate'
    checks.append('no-timing-or-optical-interpretation-on-incomplete-collection')

    prior = load(REFERENCE/'result.json')
    metrics = compare.trial_metrics(REFERENCE, prior)
    full = metrics['full_script']
    assert full['count'] == 719 and full['commit_done_us']['p95'] == 53826
    assert full['core_queue_wait_us']['p95'] == 35206.823
    assert full['runtime_issue_CPU_lower_ns']['p95'] == 4542739
    assert full['runtime_issue_CPU_upper_ns']['p95'] == 4545625
    with TemporaryDirectory(prefix='0343-compare-test-', dir=out) as folder:
        fixture = Path(folder)
        for leaf in REF_DECODE:
            (fixture/leaf).symlink_to(REFERENCE/leaf)
        refused(lambda: compare.compare(fixture, dict(prior, independent_restore_verified=False)))
        verdict = dict(prior, static_root_comparison_passed=True)
        result = compare.compare(fixture, verdict)
        assert result['delta_p95_core_queue_wait_us'] == result['delta_p95_commit_done_us'] == 0
        lo, hi = result['delta_runtime_issue_CPU_ns_bounds']['p95']
        assert lo == -hi == -2886
    checks.append('0342-raw-derived-719-joins-and-bounded-CPU-quantiles-reproduced')

    counts = check_optics(optical, out)
    checks.append('optical-120-and-240fps-stalls-camera-gaps-and-actual-decode-tested')
    result = dict(state='0343-shared-executor-comparison-optical-host-tests-passed', checks=checks,
                  optical_synthetic_update_counts=counts, real_optical_capture=False,
                  device_commands=0, device_writes=0, boot_attempts=0)
    with (out/'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
