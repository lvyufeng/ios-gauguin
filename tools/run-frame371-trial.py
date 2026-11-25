#!/usr/bin/env python3
"""Run the reviewed 0371 60 Hz producer transport trial once."""

import hashlib
from importlib import import_module
from types import SimpleNamespace

from frame364_analysis import score, trace
from frame367_route import decode as decode_route
from frame369_analysis import analyze
from frame371_transport import analyze_transport

scope = import_module('prepare-frame371')
prior = import_module('run-frame366-trial')
scorer = prior.scorer
EXEC = scope.BASE/'execution'


def check_consent(approval, ready, plan, *, trial, flags):
    wording = prior.STANDING_INSTRUCTION
    scope.require(trial==scope.TRIAL and all(approval.get(flag) is True for flag in flags) and
        not approval.get('fixture_only') and approval.get('source')=='actual-user-60Hz-standing-grant' and
        approval.get('provenance')=='direct-standing-user-instruction' and approval.get('user_answer')==wording and
        approval.get('user_answer_sha256')==hashlib.sha256(wording.encode()).hexdigest() and
        approval.get('plan_sha256')==ready['install_plan_sha256'] and
        approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
        approval.get('image_sha256')==plan['image_sha256'],'standing grant differs from 0371')


def motion_summary(scoped):
    lanes = {'original_active':scoped['ordinary']['active'],'warm_active':scoped['warm_active'],
             'slow_drag':scoped['slow_drag']}
    keys = ('scans','new_images_per_second_bounds','changed_image_gap_p95_ns','changed_image_longest_gap_ns')
    return {name:{key:lane[key] for key in keys} for name,lane in lanes.items()}


def after_restore(execution, plan, result, before, code):
    original = scope.REFERENCE
    history = scope.load(original/'frame-pacing-0369-0370.json')['0370']
    scorer.after_restore(execution,plan,result,before,code,trial=scope.TRIAL,refs={'0370':original},
        history={'0370':history},success='0371-original-strokes-measured-root-restored')
    if not result.get('frame_trace_complete'):
        return
    try:
        proof = scope.load(execution/'independent-restore.json')
        c4 = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
        scope.require(proof['files'][c4]['fork']['extents']==scope.C4_EXTENTS,'0371 C4 extent proof differs')
        raw = (execution/'kernel.log').read_text()
        route = decode_route(raw)['route']
        scope.require(route and route['pipe']=='VIG0','0371 inherited scanout route differs')
        rows,_,numer,denom = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
        scope.require(not rows.get(trace.SWAP_WAIT),'0370 wait observer still present')
        scoped = analyze(execution,begin_threads=True)
        scoped['route'] = route
        scoped['comparison_0370_0371'] = {
            '0370':motion_summary(scope.load(original/'scoped-swap-timing-0370.json')),
            '0371':motion_summary(scoped),
        }
        scorer.prior.timeline.write(execution/'scoped-swap-timing-0371.json',scoped,3_500_000)
    except (KeyError,ValueError) as error:
        result.update(state='0371-frame-motion-unqualified-root-restored',motion_error=str(error))
        return
    result.update(frame_score_state=result['state'],verified_warm_motion=scoped['warm_active'],
        verified_slow_motion={key:value for key,value in scoped['slow_drag'].items() if key!='identity'},
        stable_60_fps_observed=scoped['stable_60_fps_qualified'])
    try:
        transport = analyze_transport(execution,scoped,raw,rows,numer,denom,scope.load)
        scorer.prior.timeline.write(execution/'producer-transport-0371.json',transport,1_000_000)
    except (KeyError,ValueError) as error:
        result.update(state='0371-hardware-measured-transport-unqualified-root-restored',transport_error=str(error))
        return
    capture = transport['capture']
    result.update(state=scope.SUCCESS,producer_transport_counters=capture['counters'],
        producer_transport_full_scope_observed=capture['full_scope_observed'],
        warm_no_swap_deadlines=transport['warm_strokes_3_to_13'])


def main():
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
            expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0371 refused before device IO: '+repr(error),flush=True)
        return 2
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,EXEC,
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
