#!/usr/bin/env python3
"""Run the 0345 preflight models and replay the matched 0344 receipt offline."""

from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import frame344_log as frames
from frame345_scope import ANALYSIS, BASE, P344, WORK, load, require, sha


def check(*, base=BASE, reference=P344, trial='0345', reference_p95=28791.197, extra_tests=()):
    out = base/'frame-host'
    out.mkdir()
    source = base/'native-kernel/source/bsd/dev'
    fixture = WORK/'tests/fixtures/dpu345_status.c'
    binary = out/'dpu-status-host'
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                    '-I'+str(source), str(fixture), '-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
    env = {**os.environ, 'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests = subprocess.run([sys.executable,'-m','unittest','test_frame345_log','test_frame344_log',*extra_tests],
                           capture_output=True,text=True,check=True,env=env)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)

    pipeline = import_module('check-core342-pipeline')
    prior = reference/'execution'
    before = load(prior/'fresh-before/result.json')
    plan = load(reference/'trial-plan.json')
    suite = ('success','post-capture-failure','independent-failure','restore-rollback',
             'install-rollback','final-capture-failure','observer-owner-alive')
    checks = []
    for case in suite:
        pipeline.control_fixture(out,plan,case,checks)
    for case in ('suffix-success','suffix-prefix-mismatch'):
        pipeline.control_fixture(out,dict(plan,verified_log_suffixes_only=True),case,checks)

    with TemporaryDirectory(prefix='prior-replay-',dir=out) as temp:
        directory = Path(temp)
        for name in ('kernel.log','kernel.log.bin','observer.log','springboard-new.log','independent-restore.json',
                     *(row['output']+'.current' for row in before['files'].values()
                       if row.get('output') and (prior/(row['output']+'.current')).exists())):
            path = prior/name
            if not (directory/name).exists():
                os.link(path,directory/name)
        baseline = load(prior/'result.json')
        import_module('analyze-core342').analyze_saved(directory,dict(plan,max_analysis_bytes=ANALYSIS),baseline,before,0)
        require(baseline['state']=='CR342-lossless-wait-execution-observed-root-restored',
                'compact reports cannot reproduce the validated reference')
        metrics = import_module('compare-runtime343').trial_metrics(directory,baseline)
        require(metrics['full_script']['core_queue_wait_us']['p95']==reference_p95, 'reference queue P95 differs')
        _,strokes,numer,denom=frames.parse((directory/'kernel.log').read_text())
        old = load(directory/'core-wait-execution-analysis.json')['rows']
        joins = load(directory/'kernel-IO-identity-analysis.json')['submits']
        release = import_module('run-frame345-trial').phases(old,joins,strokes,numer,denom)['first_250ms_after_release']
        analysis_bytes = sum(p.stat().st_blocks*512 for p in directory.glob('*analysis*.json'))
    from re import search
    unit_count = int(search(r'Ran (\d+) tests?',tests.stdout+tests.stderr)[1])
    result = dict(state=trial+'-DPU-gates-frame-joins-and-control-order-passed',unit_tests=unit_count,
                  input_pins={str(p):sha(p) for p in (source/'gauguin_scanout345.h',fixture,Path(__file__))},
                  model_controls=checks, independent_readback_precedes_analysis=True,
                  baseline_compact_replay_bytes=analysis_bytes, baseline_script_jobs=len(joins),
                  baseline_post_release=release, device_commands=0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    check()
