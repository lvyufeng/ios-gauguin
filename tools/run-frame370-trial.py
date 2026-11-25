#!/usr/bin/env python3
"""Run the frozen BackBoard SwapWait capture under the standing grant."""

import hashlib
from importlib import import_module
from types import SimpleNamespace

from frame364_analysis import score, trace
from frame369_analysis import analyze
from frame370_swap_wait import decode, join_issue
from frame367_route import decode as decode_route

scope = import_module('prepare-frame370')
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
        approval.get('image_sha256')==plan['image_sha256'],'standing grant differs from 0370')


def after_restore(execution,plan,result,before,code):
    original = scope.REFERENCE
    history = scope.load(original/'frame-pacing-0368-0369.json')['0369']
    scorer.after_restore(execution,plan,result,before,code,trial=scope.TRIAL,refs={'0369':original},
        history={'0369':history},success='0370-original-strokes-measured-root-restored')
    if not result.get('frame_trace_complete'):
        return
    try:
        proof = scope.load(execution/'independent-restore.json')
        c4_path = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
        scope.require(proof['files'][c4_path]['fork']['extents']==scope.parent.C4_EXTENTS,'C4 extent proof differs')
        raw = (execution/'kernel.log').read_text()
        route = decode_route(raw)['route']
        scope.require(route and route['pipe']=='VIG0','0370 inherited route differs')
        frames,_,_,_ = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
        waits = join_issue(decode(frames),frames)
        scoped = analyze(execution)
        scoped['route'] = route
        scorer.prior.timeline.write(execution/'scoped-swap-timing-0370.json',scoped,3_500_000)
        scorer.prior.timeline.write(execution/'swap-wait-0370.json',waits,1_000_000)
    except (KeyError,ValueError) as error:
        result.update(state='0370-swap-wait-or-motion-unqualified-root-restored',swap_wait_error=str(error))
        return
    result.update(state=scope.SUCCESS,frame_score_state=result['state'],verified_warm_motion=scoped['warm_active'],
        verified_slow_motion={key:value for key,value in scoped['slow_drag'].items() if key!='identity'},
        stable_60_fps_observed=scoped['stable_60_fps_qualified'],
        swap_wait={key:value for key,value in waits.items() if key!='samples'})


def main():
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
            expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0370 refused before device IO: '+repr(error),flush=True)
        return 2
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,EXEC,
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
