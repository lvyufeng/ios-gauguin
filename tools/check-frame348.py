#!/usr/bin/env python3
"""Check read-only counter motion, restore ordering and both baselines without device IO."""

from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import frame345_log as scanout
from frame348_scope import BASE, LOG_PATHS, P346, P347, REFERENCES, WORK, expected_plan, load, require, sha


def check():
    out = BASE/'frame-host'
    out.mkdir()
    stage = import_module('prepare-frame344')
    source = BASE/'native-kernel/source/bsd/dev'
    inputs = [Path(__file__),source/'gauguin_scanout345.h']
    for name in ('dpu345_status','dpu346_counter','dpu348_motion'):
        fixture = WORK/'tests/fixtures'/f'{name}.c'
        binary = out/name
        subprocess.run(['clang','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                        '-I'+str(source),str(fixture),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=20)
        inputs.append(fixture)

    unit = ('test_frame348_trial','test_frame347_trial','test_frame345_log','test_frame344_log','test_core342_log')
    env = {**os.environ,'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests = subprocess.run([sys.executable,'-m','unittest','-v',*unit],
                           capture_output=True,text=True,env=env,timeout=90)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    require(tests.returncode==0, '0348 host tests failed. See '+str(out/'unit-tests.log'))
    count = int(re.search(r'Ran (\d+) tests?',tests.stderr)[1])
    inputs.extend(WORK/'tests'/f'{name}.py' for name in unit)

    pipeline = import_module('check-core342-pipeline')
    controls = []
    plan = expected_plan()
    cases = ('success','post-capture-failure','independent-failure','restore-rollback',
             'install-rollback','final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch')
    for label in cases:
        pipeline.control_fixture(out,plan,label,controls)
    require(len(controls)==len(cases), 'executor model controls missing')

    run = import_module('run-frame348-trial')
    analyzer = import_module('analyze-core342')
    baselines = {}
    for trial,parent in (('0346',P346),('0347',P347)):
        ref,digest = REFERENCES[trial]
        require(sha(ref/'result.json')==digest, 'replay result provenance differs')
        verdict = load(ref/'result.json')
        before = load(parent/'execution/fresh-before/result.json')
        frozen = load(parent/'trial-plan.json')
        names = ('kernel.log','kernel.log.bin','observer.log','independent-restore.json','springboard-new.log',
                 *(before['files'][path]['output']+'.current' for path in LOG_PATHS))
        inputs.extend(ref/name for name in names)
        with TemporaryDirectory(prefix=trial+'-replay-',dir=out) as folder:
            replay = Path(folder)
            for name in names:
                os.link(ref/name,replay/name)
            analyzer.analyze_saved(replay,frozen,verdict,before,0)
            require(verdict['state']==run.timeline.CORE_PASSED, 'replayed core collection refused')
            rows = load(replay/'core-wait-execution-analysis.json')['rows']
            joins = load(replay/'kernel-IO-identity-analysis.json')['submits']
            frame = scanout.analyze((replay/'kernel.log').read_text(),joins,rows)
            summary = run.compared_trial(replay,verdict,frame,rows,joins)
            release = summary['warm_lanes']['first_250ms_after_release']
            baselines[trial] = dict(exact_joins=len(joins),linked_layers=frame['core_linked_layers'],
                                    release=release)
            if trial=='0347':
                run.compare(replay,verdict,frame,rows,joins)
                report = load(replay/'comparison-0346-0347.json')['trials']
                require(report['0348']['warm_lanes']==report['0347']['warm_lanes'] and
                        report['0348']['frames']==report['0347']['frames'] and
                        report['0347']['queues']['full_script']['count']==721 and
                        report['0346']['queues']['full_script']['count']==730,
                        'three-way timing and software frame joins differ in replay')
    require(baselines['0346']['linked_layers']==403 and baselines['0347']['linked_layers']==355 and
            baselines['0346']['release']['recording_and_commit_ns']['p95']==14_971_195 and
            baselines['0347']['release']['recording_and_commit_ns']['p95']==18_401_719,
            'corrected reference timing or frame counts differ')
    stage.save(out/'0346-0347-reference.json',baselines)
    result = dict(state='0348-read-only-counters-and-three-way-replay-passed',unit_tests=count,c_fixtures=3,
                  control_models=len(controls),controls=controls,
                  baseline_exact_joins={k:v['exact_joins'] for k,v in baselines.items()},
                  independent_readback_precedes_analysis=True,
                  input_pins={str(path):sha(path) for path in inputs},device_commands=0,device_writes=0,boot_attempts=0)
    stage.save(out/'result.json',result)
    print({key:value for key,value in result.items() if key!='input_pins'})


if __name__=='__main__':
    check()
