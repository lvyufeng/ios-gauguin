#!/usr/bin/env python3
"""Run the authorized 0415 physical-touch preview and verify the rollback."""

import argparse
from hashlib import sha256
from importlib import import_module
import re
from types import SimpleNamespace

scope = import_module('prepare-frame415')
runner = import_module('run-core342-trial')
WORDING = '把最新的0415版本取消冻结刷入，让我实际感受一下'
AUTHORITY = 'direct-user-physical-touch-preview-request'


def record_grant():
    base = scope.BASE
    ready, review = (scope.load(base / name) for name in ('ready.json', 'final-review.json'))
    scope.require(not (base / 'execution').exists() and not (base / 'approval.json').exists()
                  and review['state'] == 'reviewed-frame415-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  '0415 physical-touch preview has no current review')
    scope.save(base / 'approval.json', dict.fromkeys(scope.FLAGS, True) | dict(
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
                  '0415 authorization or exact image differs')


def observe_restored(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  '0415 requires independent restoration before reading preview evidence')
    raw = (execution / 'kernel.log').read_text()
    scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1, '0415 kernel identity missing')
    rows = re.findall(r'^SWEET F415 GPU WRITE: (.*)$', raw, re.M)
    proven = re.findall(r'^slot=([12]) physical=[0-9a-f]{8} fence=[1-9]\d* acquire=(\d+) issue=(\d+) '
                        r'eop=(\d+) release=(\d+) qualified$', '\n'.join(rows), re.M)
    probe_qualified = len(rows) == len(proven) == 2 and {row[0] for row in proven} == {'1', '2'}
    probe_qualified = probe_qualified and all(0 < int(a) <= int(i) <= int(e) <= int(r) for _, a, i, e, r in proven)
    crc_armed = bool(re.search(r'^SWEET F349 ARM:', raw, re.M))
    crc_restored = bool(re.search(r'^SWEET F349 RESET: .* readable=1 .* after=1000000 writes=4 fault=0 ', raw, re.M))
    print('0415 kernel matched. Independent restoration verified.', flush=True)
    result.update(
        physical_input_ready='starting physical reports' in raw,
        physical_contact_transitions=len(re.findall(r'^SWEET NVT: observed contact mask=', raw, re.M)),
        guarded_display_preview='SWEET F387 MANUAL: opening guarded display window' in raw,
        private_latches=len(re.findall(r'^SWEET F382 L \d+ \d+ [12] \d+$', raw, re.M)),
        original_front_latched=bool(re.search(r'^SWEET F382 L 0 \d+ 0 \d+$', raw, re.M)),
        crc_armed=crc_armed, crc_cleanup_original=crc_restored,
        scripted_input_seen='SWEET UI SCRIPT: begin stroke=' in raw,
        GPU_write_probe_receipts=rows, GPU_write_probe_qualified=probe_qualified)
    scope.require(result['physical_input_ready'] and not result['scripted_input_seen'],
                  '0415 physical-only input was not observed')
    scope.require(not crc_armed or crc_restored, '0415 CRC cleanup readback is missing')
    result['state'] = scope.SUCCESS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-actual-request', action='store_true')
    if parser.parse_args().record_actual_request:
        record_grant()
        return 0
    plan, approval, budget = import_module('run-frame347-trial').authorization(
        SimpleNamespace(check_consent=check_consent), base=scope.BASE, trial=scope.TRIAL,
        expected=scope.expected_plan, flags=scope.FLAGS, reserve=scope.RESERVE)
    return runner.execute(plan, approval, budget, scope.BASE, scope.BASE / 'execution',
                          trial=scope.TRIAL, after_restore=observe_restored, success_state=scope.SUCCESS)


if __name__ == '__main__':
    raise SystemExit(main())
