#!/usr/bin/env python3
"""Synthetic cache-transition and complete-kernel-counter consistency checks."""
from pathlib import Path
import hashlib
import importlib.util
import json

WORK = Path(__file__).resolve().parents[1]
SOURCE = WORK/'tools/run-sb-cadence-trial.py'
spec = importlib.util.spec_from_file_location('trial', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    marker = 'GAUGUIN FQ322: unsupported_cached=1 request=64 param=9\n'
    header = 'SWEET GPU API PERF: valid=1 pending=0 selector=0 queue_ns=0 held_ns=0; completed prefix, elapsed CPU clock only\n'
    api = 'SWEET GPU API PERF: selector=40 calls=8 failures=1 queue_ns=30 held_ns=40 max_held_ns=20 wait_ns=5; held excludes unlocked wait\n'
    service = 'SWEET GPU SERVICE: final renewals=598 submitted=10 completed=10 shadow=200; quarantined, no further refresh\n'
    kernel = header+api+service
    good = module.inspect_fault_query_cache(marker, kernel, True)
    assert good['active'] and not good['physical_fps_qualified']
    assert good['counters']['get_param_failures_per_submission'] == .1
    cases = [(marker, kernel, False), ('', kernel, True),
             (marker+marker, kernel, True), (marker.replace('param=9', 'param=3'), kernel, True),
             (marker.replace('cached=1', 'cached=0'), kernel, True),
             (marker+'GAUGUIN FQ322: unexpected\n', kernel, True)]
    for broken in ('', kernel+header, kernel+api, kernel+service,
                   kernel.replace('valid=1', 'valid=0'), kernel.replace('pending=0', 'pending=1'),
                   kernel.replace('failures=1', 'failures=9'), kernel.replace('failures=1', 'failures=0'),
                   kernel.replace('calls=8', 'calls=0'), kernel.replace('max_held_ns=20', 'max_held_ns=41'),
                   kernel.replace('completed=10', 'completed=9'),
                   kernel.replace('submitted=10 completed=10', 'submitted=0 completed=0')):
        cases.append((marker, broken, True))
    for bb, kk, preserved in cases:
        assert not module.inspect_fault_query_cache(bb, kk, preserved)['active']
    result = dict(state='passed-FQ322-transition-and-counter-consistency',
                  positive_cases=1, negative_cases=len(cases), synthetic_fixture_only=True,
                  no_performance_claim_from_transition=True, device_commands=0,
                  input_pins={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (SOURCE, Path(__file__).resolve())})
    out = WORK/'research/tmp/gesture-sample-328/cache-log-test.json'
    with out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
