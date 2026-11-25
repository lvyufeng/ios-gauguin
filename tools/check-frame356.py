#!/usr/bin/env python3
"""Verify the 0356 guard transcript, row copy, references and restore-order controls."""

from importlib import import_module
import os
from pathlib import Path
import re
from statistics import median
import subprocess
import sys

import frame349_log as scanout
import frame350_queue as queue
import frame351_display as present
import frame352_display as copy
import frame354_display as ready
from frame355_display import inventory, verify_startup
from frame356_display import focus_copy, matched_latencies
from frame356_scope import BASE, FOCUS, P355, REF350, REF355, RELEASE_NS, WORK
from frame356_scope import check_references, expected_plan, require, sha


def run_fixture(out, name, fixture, headers, sources=()):
    runner = out/name
    subprocess.run(['xcrun','clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                    '-I'+str(headers),str(fixture),*map(str,sources),'-o',str(runner)],check=True,timeout=90)
    raw=subprocess.check_output([str(runner)],text=True,timeout=25)
    (out/(name+'.log')).write_text(raw)
    return raw


def verify_latency_fixtures(out, dev):
    old=P355/'native-kernel/source/bsd/dev'
    runtime='gauguin_gpu_runtime.c'
    original=WORK/'tests/fixtures/gpu-user/runtime_host.c'
    ack=WORK/'tests/fixtures/gpu-user/runtime_issue356_host.c'
    copy_fixture=WORK/'tests/fixtures/dpu356_copy.c'
    results=[]
    sync=[]
    for label,source in (('0355',old),('0356',dev)):
        sync.append(run_fixture(out,label+'-runtime',original,source,(source/runtime,)))
        results.append([list(map(int,line.split())) for line in
            run_fixture(out,label+'-acknowledgement',ack,source,(source/runtime,)).splitlines()])
    require(sync[0]==sync[1] and len(results[0])==len(results[1])==2,'synchronous runtime behavior changed')
    counts=[]
    for before,after,reissues in zip(*results,(0,2),strict=True):
        require(before[0]==after[0]==reissues and before[2:]==after[2:],
                'asynchronous register, ring or delay transcript differs')
        counts.append([before[1],after[1]])
    require(counts==[[12,10],[24,16]], 'full checks were not confined to adjacent acknowledgements')
    timings=[list(map(int,line.split())) for line in run_fixture(out,'panel-copy',copy_fixture,dev).splitlines()]
    require(len(timings)==24 and all(len(pair)==2 and min(pair)>0 for pair in timings),'whole-row comparison incomplete')
    paths=[original,ack,copy_fixture,dev/runtime,old/runtime,dev/'gauguin_copy356.h'] + [
           out/(name+'.log') for name in ('0355-runtime','0356-runtime','0355-acknowledgement','0356-acknowledgement','panel-copy')]
    metrics=dict(async_ack_guard_counts=counts,register_and_memory_transcripts_equal=True,copy_block_bytes=288,
                 copy_byte_equality=True,host_write_back_copy_median_ns=list(map(median,zip(*timings))),
                 display_WC_timing_requires_device=True)
    return metrics,paths


def replay():
    check_references()
    prior=import_module('run-frame350-trial')
    displays, waits, timing, inputs = {}, {}, {}, []
    for trial,source,expected in (('0350',REF350,[83,77]),('0355',REF355,[47,80])):
        matched=prior.trace_inputs(source)
        core,submits,_=matched
        raw=(source/'kernel.log').read_text()
        extra=ready.KINDS if trial=='0355' else ()
        frame=scanout.analyze(raw,submits['submits'],core['rows'],
            preserve_data_preimage=True,extra_kinds=(present.PRESENT,copy.WAKE,*extra))
        result=present.analyze(raw,frame) if trial=='0350' else copy.analyze(raw,frame,extra_kinds=extra)
        require(frame['misr']['qualified'] and frame['crc_frame_calibration']['lag_frames']==0 and
            [result['phases'][p]['signature_counts']['changed'] for p in ('active','release')]==expected and
            len(result['windows'])==26,'measured reference differs')
        if trial=='0355':
            select=ready.analyze(raw,result)
            missed=inventory(raw,select)
            require(len(verify_startup(raw)['startup_completions'])==3 and
                missed['phases']['active']['interval_count']==66 and
                missed['phases']['active']['swaps_by_stage']['awaiting_matching_GPU_writer']==51 and
                select['phases']['all']['older_ready_with_newer_swap_verified_copies']==70 and
                result['paired_copies']==271 and result['independently_bounded_copies']==270,
                '0355 startup, readiness or missed swap evidence differs')
            focus=focus_copy(result)
            phase=focus['phases']['active']
            require(phase['counts']['unknown']==1 and phase['copy_boundary_unknown_attempts']==[430],
                    'reference stroke ten must preserve the uncertain boundary')
        displays[trial]=dict(phases=result['phases'],windows=result['windows'])
        waits[trial]=queue.analyze(*matched,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
        timing[trial]=matched_latencies(*matched)
        inputs.extend(source/f'{n}.json' for n in ('core-wait-execution-analysis','kernel-IO-identity-analysis','kernel-IO-analysis'))
    require(timing['0355']['matched_submits']==742 and
            [row['wait_max_ns'] for row in waits['0355']['focus']]==[6_158_073,6_030_729],
            '0355 focus queue latency differs')
    return displays,waits,timing,{'0355':focus},inputs


def check():
    out=BASE/'frame-host'
    out.mkdir()
    save=import_module('prepare-frame344').save
    dev=BASE/'native-kernel/source/bsd/dev'
    cases=('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking','dpu350_preimage',
           'dpu351_blanking','dpu352_ready_copy','dpu353_ready_hold','dpu354_retained_ready')
    inputs=[Path(__file__),dev/'gauguin_ready354.h',dev/'gauguin_ui_trace_board.c']
    for name in cases:
        fixture=WORK/'tests/fixtures'/f'{name}.c'
        run_fixture(out,name,fixture,dev)
        inputs.append(fixture)
    latency,latency_paths=verify_latency_fixtures(out,dev)
    inputs+=latency_paths
    suites=('test_frame350_log','test_frame349_log','test_frame348_trial','test_frame347_trial',
            'test_frame345_log','test_frame344_log','test_core342_log')
    env={**os.environ,'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests=subprocess.run([sys.executable,'-m','unittest','-v',*suites],capture_output=True,text=True,env=env,timeout=90)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    require(tests.returncode==0,'decoder test failure. See '+str(out/'unit-tests.log'))
    count=int(re.search(r'Ran (\d+) tests?',tests.stderr)[1])
    inputs.extend(WORK/'tests'/f'{name}.py' for name in suites)
    inputs.append(WORK/'research/tmp/io-path-342/core-host-v2/program342-success.log')
    displays,waits,timing,focus,refs=replay()
    check355=import_module('check-frame355')
    check354=import_module('check-frame354')
    plan=expected_plan()
    controls=[]
    mechanics=import_module('check-core342-pipeline')
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        mechanics.control_fixture(out,plan,case,controls)
    run=import_module('run-frame356-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                       static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected restoration error')
    else:
        raise ValueError('analysis ran before independent readback')
    for name,value in (('reference-displays',displays),('reference-release-queues',waits),
                       ('reference-latency',timing),('reference-stroke-10-copy',focus)):
        path=out/(name+'.json')
        save(path,value)
        inputs.append(path)
    inputs+=refs+[out/'unit-tests.log']
    result=dict(state='0356-checked-acknowledgement-and-whole-row-copy',unit_tests=count,c_fixtures=12,
        ready_models=check354.selection_model(),startup_models=check355.startup_model(),missed_swap_stages=check355.missed_model(),
        controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
        performance_baseline='0350',prior_output_changes=[[83,77],[47,80]],reference_windows=52,stroke_10_unknown_preserved=True,
        focus_strokes=list(FOCUS),native_device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(path):sha(path) for path in inputs},**latency)
    result['0354_startup_rejected']=True
    save(out/'result.json',result)
    print({k:v for k,v in result.items() if k not in ('controls','input_pins')})


if __name__=='__main__':
    check()
