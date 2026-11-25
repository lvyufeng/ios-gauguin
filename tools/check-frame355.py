#!/usr/bin/env python3
"""Check the 0355 startup gate, missed swaps, restore controls, and measured references."""

from collections import defaultdict
from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as trace
from frame354_display import PROMOTE, TAKE
from frame355_display import missed_stages, verify_startup
from frame355_scope import BASE, FOCUS, REF354, WORK, expected_plan, require, sha


def startup_model():
    good = ('SWEET FB EMPTY355: gen=4 swap=4 attempt=4 tick=100 mask=1 surface=0 timed=0 versioned=0 '
            'guards=0 bytes=0 ready=1\nSWEET UI SCRIPT: begin stroke=0 tick=200 origin=synthetic\n')
    qualified = verify_startup(good)
    require(qualified['qualified'] and qualified['startup_completions'][0]['generation']==4,'legacy startup proof differs')
    for broken in (good.split('\n',1)[1],good.replace('timed=0','timed=1'),good.replace('versioned=0','versioned=1'),
                   good.replace('guards=0','guards=1'),good.replace('bytes=0','bytes=4096'),good.replace('tick=100','tick=201'),
                   good+'SWEET PANIC ENTRY: caller=0\n',good.replace('ready=1','ready=0')):
        try:
            verify_startup(broken)
        except ValueError:
            continue
        raise ValueError('accepted an invalid legacy empty-update receipt')
    try:
        verify_startup((REF354/'kernel.log').read_text(errors='replace'))
    except ValueError as error:
        require('panic' in str(error),'the exact 0354 boot failure was not recognized')
    else:
        raise ValueError('0354 startup crash unexpectedly qualified')
    return 9


def missed_model():
    rows = defaultdict(list)
    event = trace.Event
    for i in range(6):
        surface = i+2
        generation = 30+i
        token = (generation<<32)|surface
        rows[trace.SWAP].append(event(i+1,80+i,trace.SWAP,generation,0,generation,1,((4<<32)|surface) if i else 0))
        if i>=2:
            rows[trace.WRITER].append(event(11+i,88+i,trace.WRITER,60+i,0,surface,token,8 if i==2 else 4))
        if i>=4:
            rows[trace.READY].append(event(20+i,95+i,trace.READY,60+i,0,0,0,0))
    rows[PROMOTE] = [event(30,108,PROMOTE,35,0,0,4,7)]
    rows[TAKE] = [event(31,130,TAKE,52,0,35,50,51)]
    rows[trace.VBLANK] = [event(32,111,trace.VBLANK,50,1,109,110,8)]
    window = dict(phase='active',stroke=4,hardware_frame=50,new_generations=list(range(30,36)),
                  new_generations_ready_by_edge=[35])
    result = missed_stages(rows,[window])
    lanes = result['windows'][0]['swaps']
    require([row['stage_at_edge'] for row in lanes]==['empty_or_multi_layer','awaiting_matching_GPU_writer',
        'different_write_version','awaiting_GPU_fence','GPU_fence_complete_awaiting_promotion','ready_without_present_attempt'],
        'missed-swap stage attribution differs')
    require(lanes[-1]['first_timed_take_tick']==130 and result['phases']['active']['interval_count']==1 and
            result['phases']['active']['superseded_by_edge']==5,'later selection or supersession differs')
    return len(lanes)


def check():
    out=BASE/'frame-host'
    out.mkdir()
    save=import_module('prepare-frame344').save
    dev=BASE/'native-kernel/source/bsd/dev'
    cases=('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking','dpu350_preimage',
           'dpu351_blanking','dpu352_ready_copy','dpu353_ready_hold','dpu354_retained_ready')
    inputs=[Path(__file__),dev/'gauguin_ready354.h',dev/'gauguin_ui_trace_board.c',REF354/'kernel.log']
    for name in cases:
        fixture=WORK/'tests/fixtures'/f'{name}.c'
        runner=out/name
        subprocess.run(['xcrun','clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                        '-I'+str(dev),str(fixture),'-o',str(runner)],check=True,timeout=90)
        subprocess.run([str(runner)],check=True,timeout=20)
        inputs.append(fixture)
    suites=('test_frame350_log','test_frame349_log','test_frame348_trial','test_frame347_trial',
            'test_frame345_log','test_frame344_log','test_core342_log')
    env={**os.environ,'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests=subprocess.run([sys.executable,'-m','unittest','-v',*suites],capture_output=True,text=True,env=env,timeout=90)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    require(tests.returncode==0,'decoder test failure. See '+str(out/'unit-tests.log'))
    count=int(re.search(r'Ran (\d+) tests?',tests.stderr)[1])
    inputs.extend(WORK/'tests'/f'{name}.py' for name in suites)
    inputs.append(WORK/'research/tmp/io-path-342/core-host-v2/program342-success.log')
    check354=import_module('check-frame354')
    displays,waits,refs=check354.replay()
    startup_models=startup_model()
    missed_models=missed_model()
    plan=expected_plan()
    controls=[]
    mechanics=import_module('check-core342-pipeline')
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        mechanics.control_fixture(out,plan,case,controls)
    run=import_module('run-frame355-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                       static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected restoration error')
    else:
        raise ValueError('startup analysis ran before independent readback')
    save(out/'reference-displays.json',displays)
    save(out/'reference-release-queues.json',waits)
    inputs+=refs+[out/'reference-displays.json',out/'reference-release-queues.json',out/'unit-tests.log']
    result=dict(state='0355-checked-empty-layer-startup-and-retained-ready-replay',unit_tests=count,c_fixtures=len(cases),
        ready_models=check354.selection_model(),startup_models=startup_models,missed_swap_stages=missed_models,
        controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
        performance_baseline='0350',prior_output_changes=[[83,77],[34,41]],reference_windows=52,
        focus_strokes=list(FOCUS),native_device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(path):sha(path) for path in inputs})
    result['0354_startup_rejected'] = True
    save(out/'result.json',result)
    print({k:v for k,v in result.items() if k not in ('controls','input_pins')})


if __name__=='__main__':
    check()
