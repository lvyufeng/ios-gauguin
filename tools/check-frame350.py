#!/usr/bin/env python3
"""Check the exact CRC preimage, focused queue replay and restore ordering offline."""

from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as events
import frame349_log as crc
import frame350_queue as queue
from frame350_scope import BASE, REFERENCE, WORK, expected_plan, load, require, sha


def check():
    out = BASE/'frame-host'
    out.mkdir()
    stage = import_module('prepare-frame344')
    source = BASE/'native-kernel/source/bsd/dev'
    inputs = [Path(__file__),source/'gauguin_scanout345.h',source/'gauguin_ui_trace_board.c']
    fixtures = ('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking','dpu350_preimage')
    for name in fixtures:
        fixture = WORK/'tests/fixtures'/f'{name}.c'
        binary = out/name
        subprocess.run(['clang','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                       '-I'+str(source),str(fixture),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=20)
        inputs.append(fixture)
    suites = ('test_frame350_log','test_frame349_log','test_frame348_trial','test_frame347_trial','test_frame345_log',
              'test_frame344_log','test_core342_log')
    env = {**os.environ,'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests = subprocess.run([sys.executable,'-m','unittest','-v',*suites],
                           capture_output=True,text=True,env=env,timeout=90)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    require(tests.returncode==0,'decoder tests failed. See '+str(out/'unit-tests.log'))
    count = int(re.search(r'Ran (\d+) tests?',tests.stderr)[1])
    inputs.extend(WORK/'tests'/f'{name}.py' for name in suites)
    inputs.append(WORK/'research/tmp/io-path-342/core-host-v2/program342-success.log')

    controls = []
    pipeline = import_module('check-core342-pipeline')
    plan = expected_plan()
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        pipeline.control_fixture(out,plan,case,controls)
    run = import_module('run-frame350-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                       static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected analysis gate rejection')
    else:
        raise ValueError('candidate analyzer ran before independent readback')

    raw = (REFERENCE/'kernel.log').read_text()
    rows,_,numer,denom = events.parse(raw)
    core,submits,kernel = run.trace_inputs(REFERENCE)
    replay = crc.analyze(raw,submits['submits'],core['rows'])
    hardware = replay['hardware']
    intervals = [hardware['edges'],hardware['release_cadence']['edges']]
    require(intervals==[270,182] and replay['misr']['arm']['preimage']==crc.DATA_INPUT and
            replay['misr']['total_writes']==replay['misr']['pairs']==0 and replay['core_linked_layers']==324 and
            hardware['usable_windows']==hardware['release_cadence']['usable_windows']==13,
            'restored 0349 replay differs')
    profile = queue.analyze(core,submits,kernel,replay)
    require(profile['matched_submits']==726 and [s['stroke'] for s in profile['focus']]==[3,11] and
            [s['wait_max_ns'] for s in profile['focus']]==[32_800_989,26_761_666] and
            profile['wait_category_sum_ns']['render']==150_471_130 and
            profile['wait_category_sum_ns']['commit']==40_219_844 and
            profile['focus'][0]['tail'][0]['exact_predecessor_commits'][0]['kernel_token']==715,
            'focused queue predecessor reference differs')
    stage.save(out/'0349-queue-tail.json',profile)

    fixtures = import_module('check-frame349')
    trials = []
    for lag in (0,1):
        text = fixtures.with_model_signatures(raw,rows,numer/denom,lag,preserve_data_preimage=True)
        model = crc.analyze(text,submits['submits'],core['rows'],preserve_data_preimage=True)
        hw = model['hardware']
        require([hw['edges'],hw['release_cadence']['edges']]==intervals and
                hw['hardware_refresh_hz_bounds']==hardware['hardware_refresh_hz_bounds'] and
                model['crc_frame_calibration']['qualified'] and model['crc_frame_calibration']['lag_frames']==lag and
                model['misr']['qualified'] and model['misr']['preimage_confirmed'] and
                model['misr']['reset']['after']==crc.DATA_INPUT and model['core_linked_layers']==324,
                '0350 wire model failed frame attribution, restoration or cadence')
        require(queue.analyze(core,submits,kernel,model)==profile,'CRC mode changes boot-local queue identity')
        for period,count_expected in zip((hw,hw['release_cadence']),intervals):
            require(sum(period[key] for key in ('changed','repeated','unknown'))==count_expected and
                    period['scanout_partial_coverage_fps_bounds'] is not None and
                    not period['uninterrupted_60_fps_observed'],'partial classified intervals are inconsistent')
        trials.append(dict(lag_frames=lag,witnesses=len(model['crc_frame_calibration']['witnesses']),
                           pairs=model['misr']['pairs']))
    stage.save(out/'0349-replay-with-modeled-crc.json',dict(fixture_only=True,reference_vblank_intervals=intervals,
                                                         exercised_crc=trials))
    inputs += [out/'0349-queue-tail.json',out/'0349-replay-with-modeled-crc.json',out/'unit-tests.log']
    result = dict(state='0350-offline-preimage-cadence-and-restore-checked',unit_tests=count,c_fixtures=5,
                  controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
                  reference_vblank_intervals=intervals,reference_script_joins=len(submits['submits']),
                  crc_replay_phases=[row['lag_frames'] for row in trials],focus_strokes=[3,11],
                  input_pins={str(path):sha(path) for path in inputs},device_commands=0,device_writes=0,boot_attempts=0)
    stage.save(out/'result.json',result)
    print({key:value for key,value in result.items() if key not in ('input_pins','controls')})


if __name__=='__main__':
    check()
