#!/usr/bin/env python3
"""Execute the frozen 0369 trial once under the standing 60 Hz grant."""

import argparse
import hashlib
from importlib import import_module
from types import SimpleNamespace

from frame369_analysis import analyze
from frame367_route import decode as decode_route

scope = import_module('prepare-frame369')
prior = import_module('run-frame366-trial')
scorer = prior.scorer
EXEC = scope.BASE/'execution'


def check_consent(approval,ready,plan,*,trial,flags):
    wording = prior.STANDING_INSTRUCTION
    scope.require(trial==scope.TRIAL and all(approval.get(flag) is True for flag in flags) and
        not approval.get('fixture_only') and approval.get('source')=='actual-user-60Hz-standing-grant' and
        approval.get('provenance')=='direct-standing-user-instruction' and approval.get('user_answer')==wording and
        approval.get('user_answer_sha256')==hashlib.sha256(wording.encode()).hexdigest() and
        approval.get('plan_sha256')==ready['install_plan_sha256'] and
        approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
        approval.get('image_sha256')==plan['image_sha256'] and
        scope.load(scope.RESCUE/'scoped-scan-audit.json')['stable_60_fps_qualified'] is False,
        'standing user grant differs from the frozen 0369 effects')


def after_restore(execution,plan,result,before,code):
    origin = scope.RESCUE/'score'
    history = scope.load(origin/'frame-pacing-0365-0368.json')['0368']
    scorer.after_restore(execution,plan,result,before,code,trial=scope.TRIAL,refs={'0368':origin},
        history={'0368':history},success='0369-original-strokes-measured-root-restored')
    if not result.get('frame_trace_complete'):
        return
    try:
        proof = scope.load(execution/'independent-restore.json')
        c4_path = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
        scope.require(proof['files'][c4_path]['fork']['extents']==scope.C4_EXTENTS,'C4 readback layout differs')
        route = decode_route((execution/'kernel.log').read_text())
        scope.require(route['route'] and route['route']['pipe']=='VIG0','0369 inherited route differs')
        report = analyze(execution)
        control = scope.load(scope.RESCUE/'scoped-scan-audit.json')
        report.update(route=route['route'], reference_0368={key:control[key] for key in ('ordinary','warm_active','slow_drag')})
        scorer.prior.timeline.write(execution/'scoped-swap-timing-0369.json',report,3_500_000)
    except (KeyError,ValueError) as error:
        result.update(state='0369-swap-timing-unqualified-root-restored',swap_timing_error=str(error))
        return
    measured = report['swap_timing']
    result.update(state=scope.SUCCESS,frame_score_state=result['state'],
        verified_warm_motion=report['warm_active'], verified_slow_motion={
            k:v for k,v in report['slow_drag'].items() if k!='identity'},
        stable_60_fps_observed=report['stable_60_fps_qualified'],
        swap_timing={k:v for k,v in measured.items() if k not in ('swap_timing','no_swap_detail')})


def main(check_gate=False):
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
            expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0369 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0369 exact standing grant and frozen inputs verified. Zero device IO.',flush=True)
        return 0
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,EXEC,
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(cli.parse_args().check_gate))
