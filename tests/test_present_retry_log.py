#!/usr/bin/env python3
"""Check bounded retry accounting and reject the real0331 non-retry log."""
from pathlib import Path
import hashlib
import importlib.util
import json

WORK = Path(__file__).resolve().parents[1]
STATE = WORK / 'research/tmp/present-retry-332'
SOURCE = WORK / 'tools/analyze-present-retry-log.py'
spec = importlib.util.spec_from_file_location('present_retry_log', SOURCE)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def snapshot(s=0, replaced=0, consumed=0, retired=0, canceled=0, rejected=0, pending=0, active=0,
             requeued=0, newer=0, retry_canceled=0, exhausted=0):
    return (f'SWEET FB HOLD: submitted={s} replaced={replaced} consumed={consumed} retired={retired} canceled={canceled} rejected={rejected} pending={pending} active={active}\n'
            f'SWEET FB RETRY332: requeued={requeued} newer={newer} canceled={retry_canceled} exhausted={exhausted}; max_retries=8\n')


def main():
    start = parser.ENABLE + '\n' + snapshot()
    valid = start + snapshot(s=1, consumed=1, active=1) + snapshot(s=1, consumed=1, pending=1, requeued=1)
    valid += snapshot(s=1, consumed=2, retired=1, requeued=1)
    bounded = valid + snapshot(s=4, consumed=15, retired=4, requeued=11, newer=1, retry_canceled=1, exhausted=1)
    for text in (valid, bounded):
        result = parser.analyze(text)
        assert result['active'] and result['policy_qualified'] and not result['errors']
        assert not result['physical_fps_qualified']
    bad = [
        '', valid.replace(parser.ENABLE, ''), parser.ENABLE + '\n' + valid,
        valid.replace('max_retries=8', 'max_retries=9'),
        valid.replace('submitted=1', 'submitted=-1'),
        valid.replace('submitted=1', 'submitted=' + str(2**64)),
        valid.replace('pending=1', 'pending=2'),
        valid.replace('consumed=2', 'consumed=3'),
        valid.replace('retired=1', 'retired=2'),
        valid.replace('requeued=1', 'requeued=2'),
        valid + snapshot(),
        start + snapshot(s=1, consumed=10, retired=1, requeued=9),
        start + snapshot(s=1, consumed=2, retired=1, requeued=1, exhausted=1),
        start + snapshot(s=1, consumed=2, retired=1, requeued=1, newer=1, retry_canceled=1),
        start + snapshot(s=1, consumed=1, retired=1),
        start + snapshot(s=1, consumed=1, pending=1, requeued=1),
        start + snapshot(s=1, consumed=2, active=1, requeued=1),
        valid + 'SWEET FB RETRY332: broken\n',
        valid + 'SWEET FB HOLD: broken\n',
        valid + snapshot().splitlines()[0] + '\n',
        valid + snapshot().splitlines()[1] + '\n',
        parser.ENABLE + '\n' + snapshot(s=1, consumed=2, retired=1, requeued=1),
    ]
    for index, text in enumerate(bad):
        assert not parser.analyze(text)['active'], index
    original = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331/execution/kernel.log')
    assert not parser.analyze(original.read_text(errors='replace'))['active']
    paths = [Path(__file__), SOURCE, original]
    result = dict(state='passed-PRESENT332-retry-record-parser', positive_cases=2,
        negative_cases=len(bad) + 1, actual331_log_rejected=True, device_commands=0,
        input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    with (STATE / 'retry-log-test.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
