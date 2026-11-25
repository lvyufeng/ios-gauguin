#!/usr/bin/env python3
"""Do not label missing, partial, inconsistent or inactive mapping evidence active."""
import hashlib
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
SOURCE = WORK/'tools/analyze-map-query-log.py'
spec = importlib.util.spec_from_file_location('map_log', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    initial = 'SWEET GPU MAP324: enabled=1 service=1 ordinary-unsubmitted-owner-only\n'
    header = 'SWEET GPU API PERF: valid=1 pending=0 selector=0 queue_ns=0 held_ns=0; completed prefix, elapsed CPU clock only\n'
    api = 'SWEET GPU API PERF: selector=100 calls=10 failures=1 queue_ns=30 held_ns=40 max_held_ns=20 wait_ns=5; held excludes unlocked wait\n'
    final = 'SWEET GPU MAP324: calls=10 fast=6 waited=3 failures=1 valid=1; descriptor-only\n'
    kernel = initial+header+api+final
    good = module.analyze(kernel)
    assert good['active'] and good['counters_qualified'] and good['counters']['fast'] == 6
    assert not good['physical_fps_qualified']
    inactive = module.analyze(kernel.replace('fast=6', 'fast=0'))
    assert inactive['counters_qualified'] and not inactive['active']
    cases = ['', header+api+final, initial+header+api, kernel+initial, kernel+final,
             kernel+header, kernel+api, kernel+ 'SWEET GPU MAP324: malformed\n',
             kernel.replace('enabled=1', 'enabled=0'), kernel.replace('service=1', 'service=0'),
             kernel.replace('valid=1', 'valid=0'), kernel.replace('pending=0', 'pending=1'),
             initial+header+api+final.replace('calls=10', 'calls=11'),
             initial+header+api+final.replace('failures=1', 'failures=0'),
             kernel.replace('fast=6', 'fast=10'), kernel.replace('waited=3', 'waited=5'),
             kernel.replace('failures=1', 'failures=11'), kernel.replace('max_held_ns=20', 'max_held_ns=41'),
             kernel.replace('calls=10', 'calls=0'), kernel.replace('fast=6', 'fast=-1'),
             kernel.replace('queue_ns=30', 'queue_ns=18446744073709551616'),
             kernel.replace('selector=100', 'selector=101'), kernel.replace('descriptor-only', 'unknown')]
    for broken in cases:
        assert not module.analyze(broken)['active'], broken
    receipt = dict(state='passed-MAP324-counter-consistency-parser', positive_cases=2,
                   negative_cases=len(cases), synthetic_fixture_only=True, device_commands=0,
                   input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (SOURCE, Path(__file__).resolve())})
    with (WORK/'research/tmp/gesture-sample-328/map-log-test.json').open('x') as stream:
        json.dump(receipt, stream, indent=2);stream.write('\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
