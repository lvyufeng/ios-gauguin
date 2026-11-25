#!/usr/bin/env python3
"""Run the frozen 0419 physical search test and independently restore."""

import argparse
from hashlib import sha256
from importlib import import_module
from types import SimpleNamespace

import frame424_log


scope = import_module('prepare-frame424')
authority = import_module('run-frame423-trial')
WORDING = authority.WORDING
AUTHORITY = authority.AUTHORITY


def approval_fields(ready):
    return dict.fromkeys(scope.FLAGS,True) | dict(source=AUTHORITY,user_answer=WORDING,
        user_answer_sha256=sha256(WORDING.encode()).hexdigest(), plan_sha256=ready['install_plan_sha256'],
        trial_plan_sha256=ready['trial_plan_sha256'],image_sha256=ready['image_sha256'])


def record_grant():
    base = scope.BASE
    ready,review = (scope.load(base / name) for name in ('ready.json','final-review.json'))
    scope.require(not any((base / name).exists() for name in ('approval.json','execution'))
                  and review['state'] == 'reviewed-frame424-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  'physical trial has no current review')
    scope.phase.save(base / 'approval.json',approval_fields(ready))


def check_consent(approval, ready, plan, *, trial, flags):
    scope.require(trial == scope.TRIAL and flags == scope.FLAGS and approval == approval_fields(ready)
                  and approval['plan_sha256'] == plan['install_plan_sha256'],
                  'physical test authorization or exact image differs')


def after_restore(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  'independent restoration must precede physical scoring')
    log = execution / 'kernel.log'
    userspace = execution / 'springboard-new.log'
    raw = log.read_text()
    try:
        scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1, '0419 identity missing')
        observed = frame424_log.measure(raw,userspace.read_text(),plan)
    except (ValueError,KeyError) as error:
        result.update(state='0424-physical-Spotlight-unverified-root-restored',measurement_error=str(error))
        return
    name = 'spotlight-scanout.json'
    scope.phase.save(execution / name,dict(observed,kernel_log_sha256=scope.sha(log),
        springboard_log_sha256=scope.sha(userspace),
        independent_restore_sha256=scope.sha(execution / 'independent-restore.json')))
    result.update(state=scope.SUCCESS,comparison=name,
                  fully_scored_seconds=sum(row['unknown_scans'] == 0 for row in observed['fixed_seconds']),
                  opening_candidates=len(observed['openings']),warm_tap_candidates=len(observed['candidate_taps']))


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
