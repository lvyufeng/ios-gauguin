#!/usr/bin/env python3
"""Check retained readiness, rollback ordering, and replay 0350/0353."""

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
import frame353_display as reference
import frame354_display as ready
from frame354_scope import BASE, FOCUS, REF350, REF353, RELEASE_NS, WORK
from frame354_scope import check_references, expected_plan, load, require, sha


def selection_model():
    row = trace.Event
    swap = row(1,100,trace.SWAP,9,0,31,1,(4<<32)|7)
    writer = row(2,110,trace.WRITER,61,0,7,(9<<32)|7,4)
    completion = row(3,125,trace.READY,61,0,0,0,0)
    mark = row(4,137,ready.READY,9,0,7,61,82)
    promote = row(5,139,ready.PROMOTE,9,0,0,4,7)
    newer_swap = row(6,147,trace.SWAP,10,0,32,1,(4<<32)|8)
    edge = row(7,158,trace.VBLANK,83,1,150,157,6)
    selection = row(8,180,ready.TAKE,11,1,9,82,83)
    guarded = row(9,186,ready.VALIDATE,11,1,7,4,4)
    attempt = dict(attempt=11,generation=9,attempt_tick=185,result_tick=192,retry=0,ready=True,
        layers=[dict(surface=7,native_fence=61,copy_start_tick=188)],
        blanking_proofs=[dict(surface=7,frame=83,disposition='verified-blank')],
        read_guards=[dict(surface=7,accepted=True,resolved_tick=186)])
    original = defaultdict(list,{
        trace.SWAP:[swap,newer_swap],trace.WRITER:[writer],trace.READY:[completion],trace.VBLANK:[edge],
        ready.READY:[mark],ready.PROMOTE:[promote],ready.TAKE:[selection],ready.VALIDATE:[guarded],
    })
    (selected,),_,_=ready.ready_joins(original,[attempt])
    require(selected['waiting_newer_swap'] and selected['verified_blank'] and selected['frame_delay']==1,
            'a newer waiting swap displaced still-valid ready contents')
    polled=original|{ready.READY:[replace(mark,flags=1)]}
    (selected,),_,_=ready.ready_joins(polled,[attempt])
    require(selected['observation']=='probe' and selected['fence']==61,'fenced poll was lost')
    stale=original|{ready.VALIDATE:[replace(guarded,flags=2,c=8)]}
    (selected,),_,_=ready.ready_joins(stale,[dict(attempt,layers=[],blanking_proofs=[],ready=False)])
    require(selected['stale'] and not selected['copied'],'stale contents were not refused')
    newer_mark = replace(mark,id=10,tick=176,a=8,b=62,c=83)
    newer_promotion = replace(promote,id=10,tick=177,a=9,c=8)
    second_writer = row(10,148,trace.WRITER,62,0,8,(10<<32)|8,4)
    second_fence = row(11,170,trace.READY,62,0,0,0,0)
    for amendment, sample in (
        ({trace.WRITER:[replace(writer,b=(10<<32)|7)]},attempt),
        ({trace.WRITER:[replace(writer,c=8)]},attempt),
        ({trace.READY:[]},attempt),
        ({ready.PROMOTE:[replace(promote,tick=115)]},attempt),
        ({ready.VALIDATE:[replace(guarded,flags=2,c=8)]},attempt),
        ({ready.VALIDATE:[]},attempt),
        ({ready.READY:[mark,newer_mark],ready.PROMOTE:[promote,newer_promotion],
          trace.READY:[completion,second_fence],trace.WRITER:[writer,second_writer]},attempt),
    ):
        try:
            ready.ready_joins(original|amendment,[sample])
        except ValueError:
            continue
        raise ValueError('accepted invalid writer or ready-retention provenance')
    return 10


def replay():
    check_references()
    prior=import_module('run-frame350-trial')
    displays, waits, inputs = {}, {}, []
    for trial, source, expected in (('0350',REF350,[83,77]),('0353',REF353,[34,41])):
        joined=prior.trace_inputs(source)
        core,submits,_=joined
        raw=(source/'kernel.log').read_text()
        extra = reference.KINDS if trial=='0353' else ()
        frame=scanout.analyze(raw,submits['submits'],core['rows'],
            preserve_data_preimage=True,extra_kinds=(present.PRESENT,copy.WAKE,*extra))
        result=present.analyze(raw,frame) if trial=='0350' else copy.analyze(raw,frame,extra_kinds=extra)
        require(frame['misr']['qualified'] and frame['crc_frame_calibration']['lag_frames']==0 and
                [result['phases'][p]['signature_counts']['changed'] for p in ('active','release')]==expected and
                len(result['windows'])==26,'measured reference differs')
        if trial=='0353':
            selected=reference.analyze(raw,result)
            require(selected['phases']['all']['cross_frame_verified_copies']==22 and
                    result['phases']['active']['signature_counts']['repeat_without_attempt_but_new_swap']==117 and
                    result['paired_copies']==160 and result['independently_bounded_copies']==160,
                    '0353 ready, copy or missed-present reference differs')
        displays[trial]=dict(phases=result['phases'],windows=result['windows'])
        waits[trial]=queue.analyze(*joined,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
        inputs.extend(source/f'{name}.json' for name in (
            'core-wait-execution-analysis','kernel-IO-identity-analysis','kernel-IO-analysis'))
    require([s['wait_max_ns'] for s in waits['0350']['focus']]==[35_763_073,37_803_073] and
            [s['wait_max_ns'] for s in waits['0353']['focus']]==[4_919_531,5_617_188],'reference focused waits differ')
    return displays,waits,inputs

def check():
    out=BASE/'frame-host'
    out.mkdir()
    save=import_module('prepare-frame344').save
    dev=BASE/'native-kernel/source/bsd/dev'
    fixtures=('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking',
              'dpu350_preimage','dpu351_blanking','dpu352_ready_copy','dpu353_ready_hold','dpu354_retained_ready')
    inputs=[Path(__file__),dev/'gauguin_ready353.h',dev/'gauguin_ready354.h',dev/'gauguin_ui_trace_board.c']
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
    run=import_module('run-frame354-trial')
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
    result=dict(state='0354-checked-retained-GPU-readiness-and-measured-replay',unit_tests=count,c_fixtures=len(fixtures),
        ready_models=ready_models,controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
        performance_baseline='0350',prior_output_changes=[[83,77],[34,41]],reference_windows=52,
        focus_strokes=list(FOCUS),native_device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(path):sha(path) for path in inputs})
    save(out/'result.json',result)
    print({k:v for k,v in result.items() if k not in ('controls','input_pins')})


if __name__=='__main__':
    check()
