#!/usr/bin/env python3
"""Exercise the actual analyzer, capture bounds and restore ordering offline."""

from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from frame347_scope import BASE, LOG_PATHS, P346, REFERENCE, WORK, expected_plan, load, require, sha


def check():
    out = BASE/'frame-host'
    out.mkdir()
    stage = import_module('prepare-frame344')
    source = BASE/'native-kernel/source/bsd/dev'
    fixtures = [WORK/'tests/fixtures'/f'{name}.c' for name in ('dpu345_status','dpu346_counter')]
    for fixture in fixtures:
        binary = out/fixture.stem
        subprocess.run(['clang','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                        '-I'+str(source),str(fixture),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=20)

    module_names = ('test_frame347_trial','test_frame345_log','test_frame344_log','test_core342_log')
    env = {**os.environ,'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests = subprocess.run([sys.executable,'-m','unittest','-v',*module_names],
                           capture_output=True,text=True,env=env,timeout=90)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    require(tests.returncode==0, '0347 host tests failed. See '+str(out/'unit-tests.log'))
    count = int(re.search(r'Ran (\d+) tests?',tests.stderr)[1])

    pipeline = import_module('check-core342-pipeline')
    plan = expected_plan()
    cases = ('success','post-capture-failure','independent-failure','restore-rollback',
             'install-rollback','final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch')
    controls = []
    for label in cases:
        pipeline.control_fixture(out,plan,label,controls)
    require(len(controls)==len(cases), 'executor controls missing')

    frozen = load(P346/'trial-plan.json')
    before = load(P346/'execution/fresh-before/result.json')
    baseline = load(REFERENCE/'result.json')
    run = import_module('run-frame347-trial')
    names = ('kernel.log','kernel.log.bin','observer.log','independent-restore.json','springboard-new.log',
             *(before['files'][path]['output']+'.current' for path in LOG_PATHS))
    with TemporaryDirectory(prefix='0346-replay-',dir=out) as folder:
        replay = Path(folder)
        for name in names:
            os.link(REFERENCE/name,replay/name)
        run.after_restore(replay,frozen,baseline,before,0)
        report = load(replay/'comparison-0346.json')
        a,b = (report[key] for key in ('previous','current'))
        require(a==b and b['queues']['full_script']['count']==730,
                '0346 replay differed after corrected timing analysis')
        lanes = b['warm_lanes']['first_250ms_after_release']
        require(lanes['recording_and_commit_ns']['p95']==14_971_195 and
                lanes['recording_only_ns']['p95']==9_554_019 and lanes['commit_only_ns']['p95']==6_900_833 and
                lanes['warm_jobs']==162 and lanes['warm_jobs_above_60_fps_budget']==1 and
                not b['hardware']['complete_crc_coverage'], 'corrected 0346 reference differs')
        stage.save(out/'baseline-0346.json',b['warm_lanes'])

    inputs = [Path(__file__),source/'gauguin_scanout345.h',*fixtures]
    inputs.extend(WORK/'tests'/f'{name}.py' for name in module_names)
    inputs.extend(REFERENCE/name for name in names)
    result = dict(state='0347-host-capture-order-and-timing-passed',unit_tests=count,control_models=len(controls),
                  controls=controls,baseline_exact_joins=730,independent_readback_precedes_analysis=True,
                  input_pins={str(path):sha(path) for path in inputs},
                  device_commands=0,device_writes=0,boot_attempts=0)
    stage.save(out/'result.json',result)
    print({key:value for key,value in result.items() if key!='input_pins'})


if __name__=='__main__':
    check()
