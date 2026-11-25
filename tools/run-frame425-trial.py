#!/usr/bin/env python3
"""Run the reviewed passive measurement and independently restore."""

import argparse
from hashlib import sha256
from importlib import import_module
import json
from types import SimpleNamespace

import frame423_log as marker_log
import frame419_log as timeline


scope = import_module('prepare-frame425')
AUTHORITY = 'standing-bounded-temporary-60Hz-grant-2026-11-21'
WORDING = '继续用0419，先查清GPU完成确认为什么错过翻页截止，修完按每秒实际显示的新画面数复测，把60Hz跑稳。下拉搜索和键盘单独查提交前那109ms的延迟，修好后临时刷入让我再试一下。'


def approval_fields(ready, flags=scope.FLAGS):
    return dict.fromkeys(flags,True) | dict(source=AUTHORITY,user_answer=WORDING,
        user_answer_sha256=sha256(WORDING.encode()).hexdigest(), plan_sha256=ready['install_plan_sha256'],
        trial_plan_sha256=ready['trial_plan_sha256'],image_sha256=ready['image_sha256'])


def record_grant(base=scope.BASE, trial=scope.TRIAL, flags=scope.FLAGS):
    ready,review = (scope.load(base / name) for name in ('ready.json','final-review.json'))
    scope.require(not any((base / name).exists() for name in ('approval.json','execution'))
                  and review['state'] == f'reviewed-frame{int(trial)}-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  'trial has no current review')
    scope.phase.save(base / 'approval.json',approval_fields(ready,flags))


def check_consent(approval, ready, plan, *, trial, flags):
    scope.require(trial == scope.TRIAL and flags == scope.FLAGS and approval == approval_fields(ready)
                  and approval['plan_sha256'] == plan['install_plan_sha256'],
                  'passive trial authorization or exact image differs')


def marker_score(raw, userspace, plan):
    producer = marker_log.marker_log(userspace,calibrate_ids=False)
    second = marker_log.SECOND
    begin = producer['start'] + second
    score = marker_log.observer.measure(raw,plan,score_begin=begin)
    score['whole_interval'] = timeline.whole_interval(raw,score,plan)
    ticks = [tick for _,tick,_ in producer['callbacks']]
    score['callbacks_per_fixed_second'] = [sum(begin+i*second <= tick < begin+(i+1)*second for tick in ticks)
                                          for i in range(score['score_seconds'])]
    return score


def after_restore(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  'independent restoration must precede scoring')
    log = execution / 'kernel.log'
    userspace = execution / 'springboard-new.log'
    raw = log.read_text()
    try:
        scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1,'passive kernel identity missing')
        score = marker_score(raw,userspace.read_text(),plan)
    except (ValueError,KeyError) as error:
        result.update(state='0425-marker-unverified-root-restored',measurement_error=str(error))
        return
    evidence = dict(kernel_log_sha256=scope.sha(log), springboard_log_sha256=scope.sha(userspace),
                    independent_restore_sha256=scope.sha(execution / 'independent-restore.json'))
    scope.phase.save(execution / 'marker-output.json',dict(score,**evidence))
    result.update(comparison='marker-output.json',physical_FPS_qualified=score['completely_measured_seconds']==30,
                  completely_measured_seconds=score['completely_measured_seconds'],
                  stable_60_fps_observed=score['stable_60_fps_observed'])
    try:
        diagnostic = timeline.measure(raw,score,plan)
        scope.require(len(json.dumps(diagnostic,indent=2)) < 524_288,'passive timing report exceeds reserve')
    except (ValueError,KeyError) as error:
        result.update(state='0425-marker-measured-native-timeline-unverified-root-restored',timeline_error=str(error))
        return
    scope.phase.save(execution / 'passive-completion.json',dict(diagnostic,**evidence))
    result.update(state=scope.SUCCESS,native_timeline='passive-completion.json',
                  exact_native_cutoffs=diagnostic['native_deadline_comparison']['exact_requested_target'],
                  exact_writer_joins_in_score=diagnostic['exact_writer_joins_in_score'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-actual-request',action='store_true')
    if parser.parse_args().record_actual_request:
        record_grant()
        return 0
    plan,approval,budget = import_module('run-frame347-trial').authorization(
        SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
        expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,scope.BASE / 'execution',
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__ == '__main__':
    raise SystemExit(main())
