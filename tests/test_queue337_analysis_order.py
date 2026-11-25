#!/usr/bin/env python3
"""Retain strict timeline rejection after restoration and BC335 diagnostics."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import types

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/queue-loss-337'
RUNNER = WORK / 'tools/run-sb-cadence-trial.py'
PARENT = WORK.parent / 'gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333/execution'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [PARENT / name for name in ('kernel.log', 'backboardd.log.current', 'springboard-new.log', 'result.json')]
    pins = {str(p): sha(p) for p in [*paths, RUNNER, Path(__file__).resolve(), WORK / 'tools/analyze-sb-cadence.py']}
    tree = ast.parse(RUNNER.read_text())
    body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    guarded = next(n for n in body.body if isinstance(n, ast.Try))
    joint = next(n for n in guarded.body if isinstance(n, ast.If) and
                 isinstance(n.test, ast.Compare) and ast.unparse(n.test) == 'bounds != (None, None)')
    spec = importlib.util.spec_from_file_location('joint', WORK / 'tools/analyze-sb-cadence.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    saved, result = {}, {}
    context = dict(bounds=(1, 2), EXEC=BASE, before={'files':{'/private/var/log/backboardd.log':{'output':'unused'}}},
                   backboard=paths[1].read_text(errors='replace'), kernel=paths[0].read_text(errors='replace'),
                   sb_text=paths[2].read_text(errors='replace'), joint_log=module, result=result,
                   joint_error=None, save=lambda p, data: saved.update({p.name: data}))
    # Run the exact production try/except with the real 0333 logs. File reading
    # above that block is omitted; the strict analyzer itself is unchanged.
    block = next(n for n in joint.body if isinstance(n, ast.Try))
    exec(compile(ast.Module(body=[block], type_ignores=[]), str(RUNNER), 'exec'), context)
    assert 'malformed tl: M record' in context['joint_error']
    assert 'cadence-analysis-rejected.json' in saved and 'cadence-analysis.json' not in saved
    assert result['cadence_analysis_error'] == context['joint_error']
    final_guard = next(n for n in guarded.body if isinstance(n, ast.Expr) and
                       isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == 'require' and
                       ast.unparse(n.value.args[0]) == 'joint_error is None')
    before_guard = ast.unparse(ast.Module(body=guarded.body[:guarded.body.index(final_guard)], type_ignores=[]))
    for name in ('surface-retire-analysis.json', 'stage-cache-analysis.json', 'c4-queue-analysis.json',
                 'submit-reject-analysis.json', 'process-sample-analysis.json', 'bo-allocation-analysis.json',
                 'queue-identity-analysis.json','collection-analysis.json','queue-backlog-analysis.json'):
        assert name in before_guard
    assert before_guard.index("'collection-analysis.json'") < before_guard.index("'queue-backlog-analysis.json'")
    restore_index = before_guard.index("restored = True")
    assert restore_index < before_guard.index("'surface-retire-analysis.json'")
    def require(ok, why):
        if not ok:
            raise ValueError(why)
    context['require'] = require
    try:
        exec(compile(ast.Module(body=[final_guard], type_ignores=[]), str(RUNNER), 'exec'), context)
    except ValueError as error:
        assert 'strict cadence analysis rejected' in str(error)
    else:
        raise AssertionError('failed timeline accepted')
    assert json.loads(paths[3].read_text())['state'] == 'trial-incomplete-or-failed'
    assert all(sha(Path(p)) == digest for p, digest in pins.items())
    receipt = dict(state='Q337-collection-before-backlog-and-strict-failure-after-restore',
                   actual333_negative_timeline_refused=True, original333_result_unchanged=True,
                   surface_and_cache_diagnostics_before_final_failure=True,
                   restoration_precedes_analysis=True, input_pins=pins, device_commands=0)
    with (BASE / 'analysis-order-test.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
