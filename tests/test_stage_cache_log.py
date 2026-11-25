#!/usr/bin/env python3
from pathlib import Path
import hashlib
import importlib.util
import json

WORK = Path(__file__).resolve().parents[1]
SOURCE = WORK/'tools/analyze-stage-cache-log.py'
spec = importlib.util.spec_from_file_location('cache_log', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(identifier=1, outcome=1, source=1):
    times = [100, 110, 120, 130, 0, 0, 0, 0, 0, 200]
    if outcome == 2: times[4:7] = [140, 150, 160]
    if outcome in (0, 3): times[4:9] = [140, 150, 160, 170, 180]
    return module.PREFIX+f'id={identifier} thread=1234 key='+('a'*32)+f' known=0 bytes=256 outcome={outcome} source={source} '+ ' '.join(f'{k}={v}' for k, v in zip(module.TIMES, times))+'\n'


def main():
    good = record()+record(2, 2, 2)+record(3, 3, 0)
    result = module.analyze(good)
    assert result['coverage_qualified'] and result['fast_hits'] == result['locked_hits'] == result['compilations'] == 1
    assert not result['physical_FPS_qualified']
    assert module.analyze(''.join(reversed(good.splitlines(True))))['coverage_qualified']
    bad = ['', good+record(), good.replace('id=2 ', 'id=4 '), good.replace('thread=1234', 'thread=0'),
           good.replace('bytes=256', 'bytes=0'), good.replace('id=1 ', 'id=0 '), good.replace('id=1 ', 'id=1025 '),
           good.replace('start=100', 'start=0'), good.replace('ready=110', 'ready=99'),
           good.replace('fast=130', 'fast=210'), good.replace('locking=0', 'locking=140'),
           good.replace('compiled=170', 'compiled=150'), good.replace('outcome=1 source=1', 'outcome=1 source=0'),
           good.replace('outcome=3 source=0', 'outcome=3 source=1'), good.replace('key='+'a'*32, 'key=-'),
           good.replace('known=0', 'known=3'), good.replace('end=200', 'end='+str(1 << 64)),
           good.replace('bytes=256', 'bytes='+str(1 << 64)), good+'GAUGUIN SC323: limit=1 max=1024\n',
           good+'GAUGUIN SC323: broken\n', good+record(4, 0, 0)]
    for text in bad: assert not module.analyze(text)['coverage_qualified']
    assert not module.analyze(good, False)['coverage_qualified']
    actual = (Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-stage-cache-worktree-20261115/research/tmp/stage-cache-323/host-v2/candidate.stderr')).read_text()
    observed = module.analyze(actual)
    assert observed['count'] == 1024 and observed['limit_markers'] == 1
    assert observed['errors'] == {'limit_reached': 1} and not observed['coverage_qualified']
    receipt = dict(state='passed-SC323-branch-clock-coverage-parser', positive_cases=2,
        negative_cases=len(bad)+1, actual_host_records=1024, actual_limit_detected=True,
        input_pins={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (SOURCE, Path(__file__), Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-stage-cache-worktree-20261115/research/tmp/stage-cache-323/host-v2/candidate.stderr'))},
        device_commands=0)
    out = WORK/'research/tmp/gesture-sample-328/stage-log-test.json'
    with out.open('x') as f: json.dump(receipt, f, indent=2); f.write('\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__': main()
