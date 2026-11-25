#!/usr/bin/env python3
"""Check the 0349 codec, independent restore order and measured vblank replay offline."""

from bisect import bisect_right
from importlib import import_module
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as frames
import frame345_log as baseline
import frame349_log as current
from frame349_scope import BASE, REFERENCE, WORK, expected_plan, load, require, sha


def with_model_signatures(text, rows, scale, lag, *, preserve_data_preimage=False):
    edges = rows[frames.VBLANK]
    for i in range(3,len(edges)):
        if all(b.flags==1 and 14_300_000<=(b.b-a.b)*scale<=19_000_000 and
               (b.b-b.a)*scale<=3_200_000 and b.c<4910//4
               for a,b in zip(edges[i-3:i],edges[i-2:i+1])):
            break
    gate_edge = edges[i]
    if preserve_data_preimage:
        i += 1
        require(current.qualified_edge(edges,edges[i].id,edges[i].c,4,scale), 'second tested edge missing')
    arm = edges[i]
    copies = sorted((row.b,row.seq) for row in rows[frames.COPY])
    copy_ends = [end for end,_ in copies]
    pairs = []
    for j in range(i+2,len(edges)-1):
        edge = edges[j]
        physical = edges[j-lag]
        before = bisect_right(copy_ends,physical.a)
        signature = copies[before-1][1] if before else 0
        start = edge.b+int((2752-edge.c)*16_600_000/(4910*scale))
        second = int(1_200_000/scale)
        ticks = (second<<40)|(320<<20)|320
        pairs.append(frames.Event(0,start+second+350,frames.CRC,edge.id,2752|(3100<<13),
                                  (signature<<32)|signature,start,ticks))
    records = sorted([*pairs,*(row for group in rows.values() for row in group)],
                     key=lambda row:(row.tick,row.seq))
    modeled = re.sub(r'^SWEET F344 E .*$', '',text,flags=re.M)
    modeled = re.sub(r'^(SWEET F344 [HF]: count=)[0-9]+',lambda m:m[1]+str(len(records)),modeled,flags=re.M)
    modeled = modeled.replace('configured=0 restored=1 gate=0','configured=1 restored=1 gate=0')
    poll = re.search(r'^SWEET F345 DPU: stopped=deadline polls=(\d+)',modeled,re.M)[1]
    if preserve_data_preimage:
        modeled = re.sub(r'^SWEET F349 (?:ARM|RESET): .*$','',modeled,flags=re.M)
        modeled += (f'\nSWEET F350 PRE: read=1 poll=80 frame={gate_edge.id} line={gate_edge.c}'
                    f' streak=3 value=1000000\nSWEET F350 PRE: read=2 poll=100 frame={arm.id}'
                    f' line={arm.c} streak=4 value=1000000\n')
    preimage = '1000000' if preserve_data_preimage else '0'
    streak = 4 if preserve_data_preimage else 3
    modeled += (f'\nSWEET F349 ARM: poll=100 frame={arm.id} line={arm.c} streak={streak}'
                f' preimage={preimage} readback=81000101 writes=2\n')
    modeled += (f'SWEET F349 RESET: poll={poll} readable=1 before=81000301 after={preimage} writes=4 fault=0 '
                f'pairs={len(pairs)} not_ready=0 rejected=0\n')
    return modeled+''.join('SWEET F344 E '+' '.join(f'{x:x}' for x in
        (seq,row.tick,row.kind,row.id,row.flags,row.a,row.b,row.c))+'\n' for seq,row in enumerate(records,1))


def check():
    out = BASE/'frame-host'
    out.mkdir()
    stage = import_module('prepare-frame344')
    source = BASE/'native-kernel/source/bsd/dev'
    inputs = [Path(__file__),source/'gauguin_scanout345.h',source/'gauguin_ui_trace_board.c']
    for name in ('dpu345_status','dpu346_counter','dpu348_motion','dpu349_blanking'):
        fixture = WORK/'tests/fixtures'/f'{name}.c'
        binary = out/name
        subprocess.run(['clang','-Wall','-Wextra','-Werror','-std=c11','-fsanitize=address,undefined',
                        '-I'+str(source),str(fixture),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=20)
        inputs.append(fixture)
    suites = ('test_frame349_log','test_frame348_trial','test_frame347_trial','test_frame345_log',
              'test_frame344_log','test_core342_log')
    env = {**os.environ,'PYTHONPATH':os.pathsep.join((str(WORK/'tools'),str(WORK/'tests')))}
    tests = subprocess.run([sys.executable,'-m','unittest','-v',*suites],
                           capture_output=True,text=True,env=env,timeout=90)
    (out/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    require(tests.returncode==0, 'decoder tests failed. See '+str(out/'unit-tests.log'))
    count = int(re.search(r'Ran (\d+) tests?',tests.stderr)[1])
    inputs.extend(WORK/'tests'/f'{name}.py' for name in suites)
    inputs.append(WORK/'research/tmp/io-path-342/core-host-v2/program342-success.log')

    controls = []
    pipeline = import_module('check-core342-pipeline')
    plan = expected_plan()
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        pipeline.control_fixture(out,plan,case,controls)
    run = import_module('run-frame349-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                       static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error), 'unexpected analysis gate error')
    else:
        raise ValueError('candidate analyzer ran before independent readback')

    raw = (REFERENCE/'kernel.log').read_text()
    rows,_,numer,denom = frames.parse(raw)
    joins = load(REFERENCE/'kernel-IO-identity-analysis.json')['submits']
    cores = load(REFERENCE/'core-wait-execution-analysis.json')['rows']
    replay = baseline.analyze(raw,joins,cores)
    hw = replay['hardware']
    intervals = [hw['edges'],hw['release_cadence']['edges']]
    require(intervals==[270,181] and len(joins)==728 and replay['core_linked_layers']==379 and
            hw['usable_windows']==hw['release_cadence']['usable_windows']==13,
            'restored 0348 replay differs')
    trials = []
    for lag in (0,1):
        model = current.analyze(with_model_signatures(raw,rows,numer/denom,lag),joins,cores)
        hardware = model['hardware']
        require([hardware['edges'],hardware['release_cadence']['edges']]==intervals and
                hardware['hardware_refresh_hz_bounds']==hw['hardware_refresh_hz_bounds'] and
                model['crc_frame_calibration']['qualified'] and model['crc_frame_calibration']['lag_frames']==lag and
                model['misr']['qualified'] and model['core_linked_layers']==379,
                'dual-read replay changed hardware or queue joins, or failed latch attribution')
        for period,count_expected in zip((hardware,hardware['release_cadence']),intervals):
            require(sum(period[key] for key in ('changed','repeated','unknown'))==count_expected and
                    all(period[key]>0 for key in ('changed','repeated','unknown')) and
                    period['scanout_partial_coverage_fps_bounds'] is not None and
                    not period['uninterrupted_60_fps_observed'], 'model cadence accounting or coverage gate differs')
        trials.append(dict(lag_frames=lag,witnesses=len(model['crc_frame_calibration']['witnesses']),
                           pairs=model['misr']['pairs'],active_counts=[hardware[key] for key in
                           ('changed','repeated','unknown')]))
    stage.save(out/'0348-replay-with-modeled-crc.json',dict(fixture_only=True,reference_vblank_intervals=intervals,
                                                         modeled_crc=trials))
    inputs += [out/'0348-replay-with-modeled-crc.json',out/'unit-tests.log']
    result = dict(state='0349-offline-CRC-frame-and-recovery-checks-passed',unit_tests=count,c_fixtures=4,
                  controls=controls,control_models=len(controls),independent_readback_precedes_analysis=True,
                  reference_script_joins=len(joins),reference_vblank_intervals=intervals,
                  crc_replay_phases=[row['lag_frames'] for row in trials],
                  input_pins={str(path):sha(path) for path in inputs},device_commands=0,device_writes=0,boot_attempts=0)
    stage.save(out/'result.json',result)
    print({key:value for key,value in result.items() if key not in ('input_pins','controls')})


if __name__=='__main__':
    check()
