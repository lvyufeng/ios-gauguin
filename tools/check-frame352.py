#!/usr/bin/env python3
"""Model the optional display event and reread both measured baselines."""

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
import frame352_display as display
from frame352_scope import BASE, FOCUS, REF350, REF351, RELEASE_NS, WORK
from frame352_scope import check_references, expected_plan, load, require, sha


def wake_model():
    row = trace.Event
    prior = dict(attempt=11,read_guards=[dict(accepted=False,surface=7,fence=91,
                    resolved_tick=120,surface_ready_tick=140)])
    retry = dict(attempt=12,layers=[],blanking_proofs=[])
    rows = defaultdict(list,{
        trace.ATTEMPT:[row(1,110,trace.ATTEMPT,11,0,3,50,1),row(5,160,trace.ATTEMPT,12,1,3,50,1)],
        trace.RESULT:[row(2,125,trace.RESULT,11,0,0,1,0)],
        trace.READY:[row(3,140,trace.READY,91,0,0,0,0)],
        display.WAKE:[row(4,150,display.WAKE,12,0,(11<<32)|7,91,84)],
    })
    edges={84:row(0,101,trace.VBLANK,84,1,95,100,25)}
    found,=display.check_wakes(rows,[prior,retry],edges)
    require(found['initial_attempt']==11 and found['retry_attempt']==12,'ready-to-retry match failed')
    bad = [
        replace(rows[display.WAKE][0],b=92),
        replace(rows[display.WAKE][0],a=(11<<32)|8),
        replace(rows[display.WAKE][0],c=85),
        replace(rows[display.WAKE][0],tick=130),
    ]
    for event in bad:
        rows[display.WAKE]=[event]
        try:
            display.check_wakes(rows,[prior,retry],edges)
        except ValueError:
            continue
        raise ValueError('accepted an unmatched GPU-ready retry')

    mock=defaultdict(list,{
        trace.COPY:[row(1,60,trace.COPY,8,0,50,60,trace.FRAME_BYTES)],
        present.PRESENT:[row(2,62,present.PRESENT,42,5,8,3044,(4878<<32)|4400)],
    })
    frame=dict(attempts=[dict(attempt_tick=45,result_tick=65)])
    variant=lambda:next(present.correspond_attempts(mock,frame,copy_budget_ns=5_500_000,allow_paired_copy=True))
    proof,=variant()['blanking_proofs']
    require(proof['paired_copy'] and proof['disposition']=='verified-blank','missing paired copy proof')
    mock[present.PRESENT][0]=replace(mock[present.PRESENT][0],b=3045)
    try:
        variant()
    except ValueError:
        return len(bad)+2
    raise ValueError('accepted a copy beyond the budgeted line')


def replay():
    check_references()
    previous=import_module('run-frame350-trial')
    displays,waits,inputs={}, {}, []
    for trial, reference in (('0350',REF350),('0351',REF351)):
        source=previous.trace_inputs(reference)
        core,submits,_=source
        raw=(reference/'kernel.log').read_text()
        frame=scanout.analyze(raw,submits['submits'],core['rows'],preserve_data_preimage=True,extra_kinds=(present.PRESENT,))
        report=present.analyze(raw,frame)
        summaries=report['phases']
        expected=(83,77) if trial=='0350' else (28,36)
        require(frame['misr']['qualified'] and frame['crc_frame_calibration']['lag_frames']==0 and
                tuple(summaries[p]['signature_counts']['changed'] for p in ('active','release'))==expected and
                len(report['windows'])==26,'historical display comparison differs')
        for phase, metrics in summaries.items():
            attempts={a for w in report['windows'] if w['phase']==phase for x in w['intervals'] for a in x['present_attempts']}
            durations=[l['copy_ns'] for a in report['attempts'] if a['attempt'] in attempts for l in a['layers']]
            metrics.update(copy_p95_ns=trace.quantile(durations,.95),copied_layers=len(durations))
        if trial=='0351':
            checked=display.analyze(raw,frame)
            require(checked['independently_bounded_copies']==189 and
                    checked['phases']['active']['verified_full_frame_counts']==dict(changed=28,repeated=240,unknown=0) and
                    checked['phases']['release']['verified_full_frame_counts']==dict(changed=36,repeated=145,unknown=0),
                    '0351 independently bounded copies differ')
            for phase in summaries:
                summaries[phase]['verified_full_frame_counts']=checked['phases'][phase]['verified_full_frame_counts']
        displays[trial]=dict(phases=summaries,windows=report['windows'])
        waits[trial]=queue.analyze(*source,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
        inputs.extend(reference/f'{name}.json' for name in (
            'core-wait-execution-analysis','kernel-IO-identity-analysis','kernel-IO-analysis'))
    require([s['wait_max_ns'] for s in waits['0350']['focus']]==[35_763_073,37_803_073] and
            [s['wait_max_ns'] for s in waits['0351']['focus']]==[5_179_323,9_229_740],
            'tail comparison differs')
    return displays,waits,inputs


def check():
    out=BASE/'frame-host'
    out.mkdir()
    stage=import_module('prepare-frame344')
    dev=BASE/'native-kernel/source/bsd/dev'
    fixtures=('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking','dpu350_preimage','dpu351_blanking','dpu352_ready_copy')
    inputs=[Path(__file__),dev/'gauguin_blank352.h',dev/'gauguin_ui_trace_board.c']
    for name in fixtures:
        fixture=WORK/'tests/fixtures'/f'{name}.c'
        program=out/name
        subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                        '-I'+str(dev),str(fixture),'-o',str(program)],check=True,timeout=90)
        subprocess.run([str(program)],check=True,timeout=20)
        inputs.append(fixture)
    disassembly = subprocess.check_output(['xcrun','llvm-objdump','-d',
        str(BASE/'native-kernel/SweetFramebuffer.o')],text=True,timeout=30)
    require(len(re.findall(r'\bstnp\s+x\d+,\s+x\d+,[^\n]+',disassembly))>=8,'ARM64 paired stores absent')

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
    model_checks=wake_model()
    plan=expected_plan()
    mechanics=import_module('check-core342-pipeline')
    controls=[]
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        mechanics.control_fixture(out,plan,case,controls)
    run=import_module('run-frame352-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                        static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected restoration error')
    else:
        raise ValueError('analysis ran before independent readback')
    stage.save(out/'reference-displays.json',displays)
    stage.save(out/'reference-release-queues.json',waits)
    inputs += reference_inputs+[out/'reference-displays.json',out/'reference-release-queues.json',out/'unit-tests.log']
    result=dict(state='0352-checked-GPU-ready-policy-copy-and-measured-replay',unit_tests=count,c_fixtures=len(fixtures),
        ready_models=model_checks,controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
        performance_baseline='0350',prior_output_changes=[[83,77],[28,36]],reference_windows=52,
        focus_strokes=list(FOCUS),native_device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(path):sha(path) for path in inputs})
    stage.save(out/'result.json',result)
    print({k:v for k,v in result.items() if k not in ('controls','input_pins')})


if __name__=='__main__':
    check()
