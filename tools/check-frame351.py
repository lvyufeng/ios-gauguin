#!/usr/bin/env python3
"""Verify native policy boundaries, measured baseline joins and restore ordering."""

from collections import defaultdict
from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as frames
import frame349_log as crc
import frame350_queue as queue
import frame351_display as display
from frame351_scope import BASE, FOCUS, REFERENCE, RELEASE_NS, WORK, expected_plan, load, require, sha


def check():
    out=BASE/'frame-host';out.mkdir()
    stage=import_module('prepare-frame344')
    source=BASE/'native-kernel/source/bsd/dev'
    inputs=[Path(__file__),source/'gauguin_blank351.h',source/'gauguin_ui_trace_board.c']
    fixtures=('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking','dpu350_preimage','dpu351_blanking')
    for name in fixtures:
        fixture=WORK/'tests/fixtures'/f'{name}.c'
        target=out/name
        subprocess.run(['clang','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                        '-I'+str(source),str(fixture),'-o',str(target)],check=True,timeout=90)
        subprocess.run([str(target)],check=True,timeout=20)
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

    plan=expected_plan(); mechanics=import_module('check-core342-pipeline'); controls=[]
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        mechanics.control_fixture(out,plan,case,controls)
    run=import_module('run-frame351-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                        static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected restoration error')
    else:
        raise ValueError('analysis ran before independent readback')

    source_inputs=run.previous.trace_inputs(REFERENCE)
    core,submits,_=source_inputs
    raw=(REFERENCE/'kernel.log').read_text()
    scan=crc.analyze(raw,submits['submits'],core['rows'],preserve_data_preimage=True,extra_kinds=(display.PRESENT,))
    report=display.analyze(raw,scan)
    hw=scan['hardware']
    phases=report['phases']
    observed=[phases[name]['signature_counts']['changed'] for name in ('active','release')]
    require(hw['edges']==270 and hw['release_cadence']['edges']==182 and observed==[83,77] and
            scan['misr']['qualified'] and scan['crc_frame_calibration']['lag_frames']==0 and
            phases['active']['signature_counts']['repeat_without_present_attempt']==123 and
            phases['active']['signature_counts']['repeat_with_refused_read_guard']==56 and
            phases['active']['signature_counts']['repeat_without_attempt_but_new_swap']==16,
            'restored 0350 CRC, vblank or present alignment differs')
    waits=queue.analyze(*source_inputs,scan,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
    require([s['wait_max_ns'] for s in waits['focus']]==[35_763_073,37_803_073] and waits['matched_submits']==738,
            '0350 focused release waits differ')

    # A certified blank receipt must be supported by a copy in its attempt.
    e=frames.Event
    mock=defaultdict(list,{
        frames.COPY:[e(1,60,frames.COPY,8,0,50,60,1080*2400*4)],
        display.PRESENT:[e(2,65,display.PRESENT,42,1,8,2500,(4878<<32)|4000)]})
    single=dict(attempts=[dict(attempt_tick=45,result_tick=70)])
    proof,=next(display.correspond_attempts(mock,single))['blanking_proofs']
    require(proof['disposition']=='verified-blank','bounded receipt not joined')
    mock[display.PRESENT][0]=e(2,65,display.PRESENT,42,1,8,2500,(4878<<32)|4878)
    try:
        next(display.correspond_attempts(mock,single))
    except ValueError:
        pass
    else:
        raise ValueError('decoder certified a deadline-crossing copy')

    stage.save(out/'0350-present-baseline.json',report)
    stage.save(out/'0350-queue-release.json',waits)
    inputs += [out/'unit-tests.log',out/'0350-present-baseline.json',out/'0350-queue-release.json']
    result=dict(state='0351-checked-blanking-policy-and-measured-replay',
                 unit_tests=count,c_fixtures=len(fixtures),controls=controls,control_models=len(controls),
                 independent_readback_precedes_analysis=True,reference_vblank_intervals=[270,182],
                 reference_changes=observed,focus_strokes=list(FOCUS),reference_script_joins=len(submits['submits']),
                 native_device_commands=0,device_writes=0,boot_attempts=0,
                 input_pins={str(path):sha(path) for path in inputs})
    stage.save(out/'result.json',result)
    print({k:v for k,v in result.items() if k not in ('controls','input_pins')})


if __name__=='__main__':
    check()
