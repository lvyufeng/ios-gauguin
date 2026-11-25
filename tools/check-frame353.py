#!/usr/bin/env python3
"""Model generation and scan transitions, and replay 0350/0352."""

from collections import defaultdict
from dataclasses import replace
from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as trace
import frame349_log as scanout
import frame350_queue as queue
import frame351_display as present
import frame352_display as copy
import frame353_display as ready
from frame353_scope import BASE, FOCUS, REF350, REF352, RELEASE_NS, WORK
from frame353_scope import check_references, expected_plan, load, require, sha


def selection_model():
    row = trace.Event
    source = row(3,137,ready.READY,9,0,7,61,82)
    select = row(5,180,ready.TAKE,11,1,9,82,83)
    edge = row(4,158,trace.VBLANK,83,1,150,157,6)
    attempt = dict(attempt=11,generation=9,attempt_tick=185,layers=[dict(surface=7)],
        blanking_proofs=[dict(surface=7,frame=83,disposition='verified-blank')],
        read_guards=[dict(surface=7,accepted=True)])
    original = defaultdict(list,{
        trace.SWAP:[row(1,100,trace.SWAP,9,0,31,1,0)],
        trace.READY:[row(2,133,trace.READY,61,0,0,0,0)],
        trace.VBLANK:[edge],
        ready.READY:[source],ready.TAKE:[select],
    })
    selected, = ready.ready_joins(original,[attempt])
    require(selected['carried'] and selected['verified_blank'] and selected['frame_delay']==1,'cross-frame model failed')
    polled=original|{ready.READY:[replace(source,flags=1,b=0,c=ready.UNKNOWN_FRAME)],
                     ready.TAKE:[replace(select,flags=0,b=ready.UNKNOWN_FRAME)]}
    polled_selection,=ready.ready_joins(polled,[attempt])
    require(polled_selection['observation']=='probe' and polled_selection['observed_frame'] is None,
            'unobserved hardware slot became a carried frame')
    for amendment, sample in (
        ({trace.SWAP:[*original[trace.SWAP],row(7,165,trace.SWAP,10,0,32,1,0)]},attempt),
        ({ready.READY:[]},attempt),
        ({ready.TAKE:[replace(select,flags=0)]},attempt),
        ({ready.TAKE:[replace(select,c=82)]},attempt),
        ({trace.READY:[]},attempt),
        ({},dict(attempt,read_guards=[dict(surface=7,accepted=False)])),
    ):
        try:
            ready.ready_joins(original|amendment,[sample])
        except ValueError:
            continue
        raise ValueError('accepted invalid readiness provenance')
    return 8


def replay():
    check_references()
    prior=import_module('run-frame350-trial')
    displays, waits, inputs = {}, {}, []
    for trial, source, expected in (('0350',REF350,[83,77]),('0352',REF352,[50,51])):
        joined=prior.trace_inputs(source)
        core,submits,_=joined
        raw=(source/'kernel.log').read_text()
        frame=scanout.analyze(raw,submits['submits'],core['rows'],
            preserve_data_preimage=True,extra_kinds=(present.PRESENT,copy.WAKE))
        result=present.analyze(raw,frame) if trial=='0350' else copy.analyze(raw,frame)
        require(frame['misr']['qualified'] and frame['crc_frame_calibration']['lag_frames']==0 and
                [result['phases'][p]['signature_counts']['changed'] for p in ('active','release')]==expected and
                len(result['windows'])==26,'measured reference differs')
        if trial=='0352':
            require(result['paired_copies']==272 and not result['wake_joins'] and result['independently_bounded_copies']==271,
                    '0352 copy or wake evidence differs')
        displays[trial]=dict(phases=result['phases'],windows=result['windows'])
        waits[trial]=queue.analyze(*joined,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
        inputs.extend(source/f'{name}.json' for name in (
            'core-wait-execution-analysis','kernel-IO-identity-analysis','kernel-IO-analysis'))
    require([s['wait_max_ns'] for s in waits['0350']['focus']]==[35_763_073,37_803_073] and
            [s['wait_max_ns'] for s in waits['0352']['focus']]==[10_618_750,6_060_156],'reference focused waits differ')
    return displays,waits,inputs


def check():
    out=BASE/'frame-host'
    out.mkdir()
    save=import_module('prepare-frame344').save
    dev=BASE/'native-kernel/source/bsd/dev'
    fixtures=('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking',
              'dpu350_preimage','dpu351_blanking','dpu352_ready_copy','dpu353_ready_hold')
    inputs=[Path(__file__),dev/'gauguin_ready353.h',dev/'gauguin_ui_trace_board.c']
    for name in fixtures:
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
    displays,waits,reference_inputs=replay()
    ready_models=selection_model()
    plan=expected_plan()
    controls=[]
    mechanics=import_module('check-core342-pipeline')
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        mechanics.control_fixture(out,plan,case,controls)
    run=import_module('run-frame353-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                       static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected restoration error')
    else:
        raise ValueError('analysis ran before independent readback')
    save(out/'reference-displays.json',displays)
    save(out/'reference-release-queues.json',waits)
    inputs += reference_inputs+[out/'reference-displays.json',out/'reference-release-queues.json',out/'unit-tests.log']
    result=dict(state='0353-checked-ready-selection-and-measured-replay',unit_tests=count,c_fixtures=len(fixtures),
        ready_models=ready_models,controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
        performance_baseline='0350',prior_output_changes=[[83,77],[50,51]],reference_windows=52,
        focus_strokes=list(FOCUS),native_device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(path):sha(path) for path in inputs})
    save(out/'result.json',result)
    print({k:v for k,v in result.items() if k not in ('controls','input_pins')})


if __name__=='__main__':
    check()
