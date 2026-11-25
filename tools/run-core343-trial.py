#!/usr/bin/env python3
"""Run one exact, independently reviewed 0343 trial after new consent."""

import argparse
import importlib.util
import json
import subprocess
import sys

from core343_scope import (APPROVAL_FLAGS, BASE, COMPLETE, HEADER, IMAGE, MAIN, STORAGE_RESERVE,
                           WORK, expected_plan, load, require, sha)

EXEC = BASE / 'execution'


def tool(name):
    spec = importlib.util.spec_from_file_location(name, WORK/'tools'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN = tool('run-core342-trial')


def authorization():
    require(not EXEC.exists(), '0343 one-shot already claimed')
    require((BASE/'approval.json').is_file(), '0343 individual approval absent')
    plan = load(BASE/'trial-plan.json')
    ready = load(BASE/'ready.json')
    review = load(BASE/'final-review.json')
    require(ready['state'] == 'ready-core343-one-shot'
            and ready['pin_count'] == len(ready['input_pins'])
            and ready['trial_plan_sha256'] == sha(BASE/'trial-plan.json')
            and ready['install_plan_sha256'] == sha(BASE/'slot-delta/install-plan.json')
            and ready['image_sha256'] == IMAGE and ready['root_header_sha256'] == HEADER
            and plan == expected_plan(), 'frozen 0343 plan differs')
    approval = load(BASE/'approval.json')
    RUN.check_consent(approval, ready, plan, trial='0343', flags=APPROVAL_FLAGS)
    require(review['state'] == 'reviewed-core343-one-shot'
            and review['ready_sha256'] == sha(BASE/'ready.json')
            and review['trial_plan_sha256'] == ready['trial_plan_sha256']
            and review['all_pins_unchanged'] and review['readback_precedes_capture_checks']
            and review['capture_precedes_CPU_queue_comparison']
            and review['optical_capture_protocol_reviewed']
            and review['device_writes'] == review['boot_attempts'] == 0,
            'independent frozen 0343 review missing or differs')
    for pins in (ready['input_pins'], review['input_pins']):
        for name, digest in pins.items():
            require(sha(name) == digest, 'changed frozen input: ' + name)
    require(ready['input_pins'][plan['image']] == IMAGE and plan['observer_helper'] in ready['input_pins'],
            'observer/image outside frozen scope')
    budget_check = subprocess.run(
        [sys.executable, str(MAIN/'tools/storage-budget.py'), '--planned-bytes', str(STORAGE_RESERVE)],
        capture_output=True, text=True, timeout=600)
    require(budget_check.returncode == 0, 'runtime reserve no longer available')
    budget = json.loads(budget_check.stdout)
    require(budget['admitted'] is True
            and budget['current_accounted_bytes'] + STORAGE_RESERVE <= budget['limit_bytes'],
            'runtime reserve no longer available')
    return plan, approval, budget


def after_restore(execution, plan, verdict, before, code):
    require(verdict['static_root_comparison_passed'], 'static root comparison missing')
    tool('analyze-core342').analyze_saved(execution, plan, verdict, before, code)
    if verdict['state'] != 'CR342-lossless-wait-execution-observed-root-restored':
        verdict['optical_measurement'] = 'withheld-by-collection-gate'
        return
    verdict['comparison_0342'] = tool('compare-runtime343').compare(execution, verdict)
    verdict.update(state=COMPLETE, optical_measurement='awaiting-separate-original-video',
                   physical_FPS_qualified=False)


def main(*, check_gate=False):
    try:
        plan, approval, budget = authorization()
    except (Exception, KeyboardInterrupt) as error:
        print('0343 gate refused before device IO: ' + repr(error), flush=True)
        return 2
    if check_gate:
        print('0343 exact consent and frozen inputs accepted; no device IO', flush=True)
        return 0
    return RUN.execute(plan, approval, budget, BASE, EXEC, trial='0343',
                       after_restore=after_restore, success_state=COMPLETE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate', action='store_true')
    raise SystemExit(main(check_gate=parser.parse_args().check_gate))
