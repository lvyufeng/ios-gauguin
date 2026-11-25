#!/usr/bin/env python3
"""Validate reuse tags against phase envelopes and cache conservation counters."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-335'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    ui = module('reuse335_ui', WORK / 'tools/ui_trace_log.py')
    parser = module('reuse335_parser', WORK / 'tools/analyze-bo-reuse-log.py')
    def event(kind, flags, a=0, b=0, c=0, token=7, pid=57):
        return dict(kind=kind, id=token, pid=pid, flags=flags, a=a, b=b, c=c)
    fresh = [event(10, 0x42, 101, 102), event(32, 1, 17, 2, 1234), event(32, 2, 16384),
             event(32, 3, 1), event(32, 4), event(32, 5, 16384, 9, 2),
             event(32, 6, 0, 9, 0), event(11, 0, 180, 0x42)]
    reused = fresh[:6] + [event(33, 1, 16384, 9, 2)] + fresh[6:]
    counters = ('SWEET BC335: enabled slots=32 bytes=16777216 max_bo=1048576 zero=1\n'
                'SWEET BC335: hits=1 misses=1 stores=2 evicts=0 aliases=0 valid=1\n'
                'SWEET BC335: slots=1 bytes=16384 connections=1; completed prefix, zeroed owned only\n')
    def log(rows, lost=0, reason=1):
        lines = [f'SWEET UI254 H: version=1 count={len(rows)} reason={reason} lost={lost} start=100 end=1000 numer=1000 denom=1 which=3 gestures=3']
        for i, value in enumerate(rows, 1):
            row = dict(value)
            tick = 102 + 10 * i
            if row['kind'] == 11:
                row['a'] = tick - 2
            lines.append('SWEET UI254 E: ' + f'seq={i} tick={tick} ' + ' '.join(f'{k}={v}' for k, v in row.items()))
        lines.append(f'SWEET UI254 F: count={len(rows)} lost={lost}; CPU-clock capture only')
        return counters + '\n'.join(lines)
    a = parser.analyze(log(fresh), ui)
    b = parser.analyze(log(reused), ui)
    assert a['coverage_qualified'] and a['fresh_backing_requests'] == 1 and a['reused_mapping_requests'] == 0
    assert b['coverage_qualified'] and b['fresh_backing_requests'] == 0 and b['reused_mapping_requests'] == 1
    assert not b['fresh_backing_stages_us']
    assert 'selected_mapping' in b['reused_mapping_stages_us']
    assert 'synchronization_and_return' not in b['reused_mapping_stages_us']
    for args in [dict(lost=1), dict(reason=2)]:
        assert not parser.analyze(log(reused, **args), ui)['coverage_qualified']
    assert not parser.analyze(log(reused[:-1]), ui)['coverage_qualified']
    invalid = []
    for key, value in [('id', 0), ('pid', 0), ('flags', 2), ('a', 0), ('a', 32768), ('b', 10), ('c', 0)]:
        rows = copy.deepcopy(reused)
        rows[6][key] = value
        invalid.append(log(rows))
    invalid += [log(reused[:6] + [reused[6], reused[6]] + reused[7:]),
                log(reused[:5] + [reused[6], reused[5]] + reused[7:]),
                log(reused).replace('stores=2', 'stores=3'),
                log(reused).replace('slots=1', 'slots=33'),
                log(reused).replace('bytes=16384 connections', 'bytes=1 connections'),
                log(reused).replace('connections=1', 'connections=2'),
                log(reused).replace('hits=1', 'hits=0').replace('stores=2', 'stores=1'),
                log(reused).replace('valid=1', 'valid=2'),
                log(reused).replace('zero=1', 'zero=0')]
    for text in invalid:
        try:
            parser.analyze(text, ui)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid reuse evidence accepted')
    assert not parser.analyze(log(reused).replace('valid=1', 'valid=0'), ui)['coverage_qualified']
    old = WORK.parent / 'gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334/execution/kernel.log'
    try:
        parser.analyze(old.read_text(errors='replace'), ui)
    except ValueError as error:
        assert 'activation' in str(error)
    else:
        raise AssertionError('old334 treated as BC335-enabled')
    paths = [Path(__file__).resolve(), WORK / 'tools/ui_trace_log.py', WORK / 'tools/analyze-bo-reuse-log.py',
             WORK / 'tools/analyze-bo-allocation-log.py', old]
    result = dict(state='BC335-phase-tag-and-counter-parser-passed', positive_cases=2,
                  negative_cases=len(invalid), loss_capacity_edges_unqualified=True,
                  reused_phases_not_reported_as_fresh_backing=True, actual334_rejected=True,
                  input_pins={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, device_commands=0)
    with (BASE / 'reuse-log-test.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
