#!/usr/bin/env python3
"""Require producer ordering and retain incomplete/capped lifecycle evidence."""
from pathlib import Path
import hashlib
import importlib.util
import json

WORK = Path(__file__).resolve().parents[1]
PATH = WORK / 'tools/analyze-surface-retire-log.py'
spec = importlib.util.spec_from_file_location('surface_log', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    banner = module.ENABLED + '\n'
    wait = 'GAUGUIN SURF334: wait seq=1 handle=774 surface=7\n'
    end = 'GAUGUIN SURF334: retired seq=1 handle=774 surface=7\n'
    assert module.analyze(banner)['coverage_qualified']  # Zero waits is valid.
    assert not module.analyze(banner)['retire_path_observed']
    paired = module.analyze(banner + wait + end)
    assert paired['coverage_qualified'] and paired['completed_pairs'] == 1
    # Threads may wake in a different order from their wait sequence.
    other = wait.replace('seq=1', 'seq=2').replace('774', '8')
    other_end = end.replace('seq=1', 'seq=2').replace('774', '8')
    assert module.analyze(banner + wait + other + other_end + end)['coverage_qualified']
    negatives = ['', wait + end, banner * 2, banner + end + wait,
                 banner + wait * 2 + end, banner + wait + end * 2,
                 banner + wait, banner + wait + end.replace('774', '775'),
                 banner + wait.replace('seq=1', 'seq=2') + end.replace('seq=1', 'seq=2'),
                 banner + module.LIMIT + '\n', wait + banner + end]
    for text in negatives:
        assert not module.analyze(text)['coverage_qualified']
    assert not module.analyze(banner + wait + end, False)['coverage_qualified']
    for malformed in [wait.replace('seq=1', 'seq=65'), wait.replace('774', '0'),
                      wait.replace('774', '4294967296'), wait.replace('surface=7', 'surface=-1'),
                      wait.rstrip() + ' garbage\n', module.PREFIX + ' ' * 129]:
        try:
            module.analyze(banner + malformed)
        except ValueError:
            pass
        else:
            raise AssertionError('malformed producer record accepted')
    capped = banner + ''.join((wait + end).replace('seq=1', 'seq=' + str(i)) for i in range(1, 65))
    result = module.analyze(capped + module.LIMIT + '\n')
    assert result['active'] and result['capacity_limited'] and not result['coverage_qualified']
    assert result['completed_pairs'] == 64 and len(result['rows']) == 128
    # Current parser cannot invent SURF334 activation in the old phone evidence.
    parent = WORK.parent / 'gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333/execution'
    old = parent / 'backboardd.log.current'
    assert old.is_file()
    assert not module.analyze(old.read_text(errors='replace'))['active']
    receipt = dict(state='SURF334-log-contract-passed', positive_cases=3,
                   unqualified_cases=len(negatives) + 2, malformed_cases=6,
                   actual333_does_not_activate=True, device_commands=0,
                   input_pins={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__).resolve(), PATH, old)})
    out = WORK / 'research/tmp/surface-retire-334/surface-log-test.json'
    with out.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
