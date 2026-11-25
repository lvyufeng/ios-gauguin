#!/usr/bin/env python3
"""Run the reviewed 0419 marker once and restore before scoring."""

import argparse
from hashlib import sha256
from importlib import import_module
from types import SimpleNamespace

import frame423_log


scope = import_module('prepare-frame423')
AUTHORITY = 'standing-bounded-temporary-60Hz-grant-2026-11-21'
WORDING = '继续，用0419临时上机跑32秒逐帧探针，再单独复测下拉搜索和输入法卡顿。按每秒实际显示的新画面数查掉帧原因，先把60Hz跑稳。'


def record_grant():
    base = scope.BASE
    ready, review = (scope.load(base / name) for name in ('ready.json','final-review.json'))
    scope.require(not any((base / name).exists() for name in ('approval.json','execution'))
                  and review['state'] == 'reviewed-frame423-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  '0423 has no current review')
    scope.phase.save(base / 'approval.json', dict.fromkeys(scope.FLAGS,True) | dict(
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
                  '0423 authorization or exact image differs')


def observe_restored(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  'independent restoration must precede marker scoring')
    log = execution / 'kernel.log'
    userspace = execution / 'springboard-new.log'
    raw = log.read_text()
    try:
        scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1, '0419 kernel identity missing')
        user_log = userspace.read_text()
        producer = frame423_log.marker_log(user_log)
        score = frame423_log.observer.measure(raw,plan,score_begin=producer['start'] + frame423_log.SECOND)
    except (ValueError, KeyError) as error:
        result.update(state='0423-marker-unverified-root-restored',measurement_error=str(error))
        return
    evidence = dict(kernel_log_sha256=scope.sha(log), springboard_log_sha256=scope.sha(userspace),
                    independent_restore_sha256=scope.sha(execution / 'independent-restore.json'))
    try:
        observed = frame423_log.measure(raw,user_log,plan)
    except (ValueError, KeyError) as error:
        scope.phase.save(execution / 'output-crc-during-probe.json', dict(score, **evidence,
            marker_identity_qualified=False, callbacks_in_32_seconds=len(producer['callbacks']),
            new_output_images=frame423_log.timeline.whole_interval(raw,score,plan)))
        result.update(state='0423-marker-identity-unverified-root-restored',measurement_error=str(error),
                      comparison='output-crc-during-probe.json', completely_measured_seconds=score['completely_measured_seconds'])
        return
    name = 'marker-scanout.json'
    scope.phase.save(execution / name, dict(observed, **evidence))
    result.update(state=scope.SUCCESS, comparison=name, physical_FPS_qualified=True,
                  completely_measured_seconds=30, stable_60_fps_observed=observed['scanout']['stable_60_fps_observed'])


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
        trial=scope.TRIAL,after_restore=observe_restored,success_state=scope.SUCCESS)


if __name__ == '__main__':
    raise SystemExit(main())
