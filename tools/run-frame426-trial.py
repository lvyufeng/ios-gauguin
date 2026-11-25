#!/usr/bin/env python3
"""Run the local scripted Spotlight comparison and verify recovery."""

import argparse
from importlib import import_module
from types import SimpleNamespace

import frame426_log


scope = import_module('prepare-frame426')
gpu = import_module('run-frame425-trial')


def check_consent(approval, ready, plan, *, trial, flags):
    scope.require(trial == scope.TRIAL and flags == scope.FLAGS and approval == gpu.approval_fields(ready,flags)
                  and approval['plan_sha256'] == plan['install_plan_sha256'],
                  'Spotlight trial authorization differs')


def after_restore(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  'independent verification must precede scoring')
    log,userspace = (execution/name for name in ('kernel.log','springboard-new.log'))
    raw = log.read_text()
    try:
        scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1,'0419 search kernel missing')
        data = frame426_log.measure(raw,userspace.read_text(),plan)
    except (KeyError,ValueError) as error:
        result.update(state='0426-Spotlight-timing-incomplete-root-restored',measurement_error=str(error))
        return
    name = 'Spotlight-before-swap.json'
    scope.phase.save(execution/name,dict(data,kernel_log_sha256=scope.sha(log),
        springboard_log_sha256=scope.sha(userspace),
        independent_restore_sha256=scope.sha(execution/'independent-restore.json')))
    result.update(state=scope.SUCCESS if data['keyboard_reported'] else '0426-Spotlight-keyboard-unconfirmed-root-restored',
                  comparison=name,keyboard_reported=data['keyboard_reported'],
                  verified_keyboard_targets=data['verified_keyboard_targets'],
                  exact_CA_renders=data['exact_CA_renders'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-actual-request',action='store_true')
    if parser.parse_args().record_actual_request:
        gpu.record_grant(scope.BASE,scope.TRIAL,scope.FLAGS)
        return 0
    plan,approval,budget = import_module('run-frame347-trial').authorization(
        SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
        expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,scope.BASE/'execution',
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__ == '__main__':
    raise SystemExit(main())
