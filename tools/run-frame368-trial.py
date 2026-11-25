#!/usr/bin/env python3
"""Observe an inherited display route once, then restore and verify."""

import hashlib
from importlib import import_module
from types import SimpleNamespace

from frame364_analysis import measure
from frame367_route import decode

scope = import_module('prepare-frame368')
previous = import_module('run-frame366-trial')
scorer = previous.scorer
EXEC = scope.BASE/'execution'


def check_consent(approval, ready, plan, *, trial, flags):
    wording = previous.STANDING_INSTRUCTION
    scope.require(trial==scope.TRIAL and all(approval.get(flag) is True for flag in flags) and
        approval.get('fixture_only') is not True and approval.get('source')=='actual-user-60Hz-standing-grant' and
        approval.get('provenance')=='direct-standing-user-instruction' and approval.get('user_answer')==wording and
        approval.get('user_answer_sha256')==hashlib.sha256(wording.encode()).hexdigest() and
        approval.get('plan_sha256')==ready['install_plan_sha256'] and
        approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
        approval.get('image_sha256')==plan['image_sha256'] and
        scope.load(scope.P366/'scoped-scan-audit.json')['stable_60_fps_qualified'] is False,
        'standing user grant differs from the reviewed 0368 scope')


def after_restore(execution, plan, result, before, code):
    history = scope.load(previous.REF365/'frame-pacing-0364-0365.json')['0365']
    scorer.after_restore(execution,plan,result,before,code,trial=scope.TRIAL,refs={'0365':previous.REF365},
        history={'0365':history},success='0368-original-strokes-measured-root-restored')
    if not result.get('frame_trace_complete'):
        return
    try:
        route = decode((execution/'kernel.log').read_text())
        frame = scope.load(execution/'frame-scanout-analysis.json')
        hz = frame['hardware']['hardware_refresh_hz_bounds']
        scope.require(hz and 59<=hz[0]<=hz[1]<=61,'0368 inherited timing differs')
        comparison = scope.load(scope.P366/'scoped-scan-audit.json')
        report = dict(route=route,reference_0366_motion={
            'ordinary':comparison['ordinary_13_strokes'], 'slow':comparison['slow_drag']['scans']})
        if frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified']:
            try:
                current = measure(execution)
                slow = current['slow_drag']
                result.update(sustained_motion_steady_60_qualified=slow['steady_60_qualified'],
                    sustained_motion={key:value for key,value in slow.items() if key!='identity'})
                report.update(current_0368=current['same_13_strokes'],slow_0368=slow)
            except ValueError as error:
                report['frame_comparison_error'] = str(error)
        scorer.prior.timeline.write(execution/'scanout-source-route-0368.json',report,scope.REPORT_BYTES)
        result.update(frame_score_state=result['state'],inherited_scanout_route=route.get('route'),
            display_address_translation_qualified=False,hardware_latch_qualified=False,
            state=scope.SUCCESS if route.get('route') else '0368-source-route-unqualified-root-restored')
    except ValueError as error:
        result.update(state='0368-source-route-unqualified-root-restored',source_route_error=str(error))


def main():
    runner = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
            expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0368 refused before device IO: '+repr(error),flush=True)
        return 2
    return runner.execute(plan,approval,budget,scope.BASE,EXEC,trial=scope.TRIAL,
        after_restore=after_restore,success_state=scope.SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
