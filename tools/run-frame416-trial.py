#!/usr/bin/env python3
"""Run the reviewed display-drain preview once and verify recovery."""

import argparse
from hashlib import sha256
from importlib import import_module
import re
from types import SimpleNamespace


scope = import_module('prepare-frame416')
runner = import_module('run-core342-trial')
WORDING = '先修0415卡死的问题，把60Hz跑稳，修好后临时刷入让我再试一下'
AUTHORITY = 'direct-user-60Hz-display-drain-preview-request'


def record_grant():
    base = scope.BASE
    ready, review = (scope.load(base / name) for name in ('ready.json', 'final-review.json'))
    scope.require(not (base / 'execution').exists() and not (base / 'approval.json').exists()
                  and review['state'] == 'reviewed-frame416-one-shot'
                  and review['ready_sha256'] == scope.sha(base / 'ready.json')
                  and ready['trial_plan_sha256'] == scope.sha(base / 'trial-plan.json'),
                  '0416 physical-touch preview has no current review')
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
                  '0416 authorization or exact image differs')


def frame_timing(raw):
    headers = re.findall(r'^SWEET F344 H: count=(\d+) reason=(\d+) lost=(\d+) start=(\d+) end=(\d+) '
                         r'numer=(\d+) denom=(\d+)$', raw, re.M)
    footers = re.findall(r'^SWEET F344 F: count=(\d+) lost=(\d+)$', raw, re.M)
    if len(headers) != 1 or len(footers) != 1:
        return None
    count, reason, lost, start, end, numerator, denominator = map(int, headers[0])
    rows = [tuple(int(column, 16) for column in row.split()) for row in
            re.findall(r'^F344E ([0-9a-f]+(?: [0-9a-f]+){7})$', raw, re.M)]
    if (not 0 < count <= 20_480 or reason not in (1, 2) or lost or
        (numerator, denominator) != (625, 12) or tuple(map(int, footers[0])) != (count, 0) or
        len(rows) != count or any(row[0] != i or not start <= row[1] < end for i, row in enumerate(rows, 1))):
        return None
    edges = sorted((row for row in rows if row[2] == 49), key=lambda row: row[3])
    if len(edges) < 2 or any(row[5] >= row[6] or row[6] > row[1] for row in edges):
        return None
    first, last = edges[0], edges[-1]
    if len({row[3] for row in edges}) != len(edges) or last[5] <= first[6]:
        return None
    scans = last[3] - first[3]
    factor = scans * 1e9 * denominator / numerator
    return dict(reason=reason, records=count, edge_brackets=len(edges),
        mean_panel_hz_bounds=[factor / (last[6] - first[5]), factor / (last[5] - first[6])])


def observe_restored(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  '0416 requires independent restoration before reading display evidence')
    raw = (execution / 'kernel.log').read_text()
    scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1, '0416 kernel identity missing')
    private = re.findall(r'^SWEET F382 L \d+ \d+ [12] (\d+)$', raw, re.M)
    original = list(re.finditer(r'^SWEET F382 L 0 \d+ 0 (\d+)$', raw, re.M))
    requests = re.findall(r'^SWEET F382 I 0 \d+ 0 \d+$', raw, re.M)
    drains = re.findall(r'^SWEET F416 DRAIN: cause=(\S+) result=(\S+) polls=(\d+)$', raw, re.M)
    done = len(drains) == 1 and drains[0][1] == 'restored' and 1 <= int(drains[0][2]) <= 160
    crc_armed = bool(re.search(r'^SWEET F349 ARM:', raw, re.M))
    crc_restored = bool(re.search(r'^SWEET F349 RESET: .* readable=1 .* after=1000000 writes=4 fault=0 ', raw, re.M))
    touch = re.findall(r'^SWEET NVT: observed contact mask=', raw, re.M)
    timing = frame_timing(raw)
    latched = (bool(private) and len(original) == len(requests) == 1
               and int(original[0][1]) > max(map(int, private)))
    tail = raw[original[0].end():] if latched else ''
    present_counts = [int(value) for value in re.findall(r'^SWEET FB HOLD: .* consumed=(\d+)', tail, re.M)]
    result.update(physical_input_ready='starting physical reports' in raw,
        physical_contact_transitions=len(touch),
        physical_contact_transitions_after_original_front=tail.count('SWEET NVT: observed contact mask='),
        guarded_display_preview='SWEET F387 MANUAL: opening guarded display window' in raw,
        private_latches=len(private), original_front_requests=len(requests), original_front_latched=latched,
        display_drain=drains, crc_armed=crc_armed, crc_cleanup_original=crc_restored,
        post_drain_present_attempt_growth=present_counts[-1] - present_counts[0] if present_counts else 0,
        panel_timing=timing, scripted_input_seen='SWEET UI SCRIPT: begin stroke=' in raw)
    if (result['physical_input_ready'] and not result['scripted_input_seen'] and latched
        and done and crc_armed and crc_restored and timing
        and all(59 <= value <= 61 for value in timing['mean_panel_hz_bounds'])):
        result['state'] = scope.SUCCESS
    else:
        result['state'] = '0416-display-drain-unverified-root-restored'


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
