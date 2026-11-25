#!/usr/bin/env python3
"""Verify the built source, retention interleavings and post-score latch gate."""

from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as trace
import frame354_display as ready
from frame357_display import BOUND, CALIBRATION, CALIBRATION_GAP, MARKERS, calibration, compare
from frame357_replay import report
from frame356_scope import REF355
from frame357_scope import BASE, P356, REF356, WORK, expected_plan, load, require, sha


def function(source, name):
    match = re.search(r'(?m)^'+re.escape(name)+r'\(',source)
    require(match is not None,'projected kernel method not found: '+name)
    body = source.index('\n{',match.start())
    return source[match.start():source.index('\n}',body)+2]


def projected_source(out):
    source = BASE/'native-kernel/source'
    parent = P356/'native-kernel/source'
    framebuffer = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
    driver = 'iokit/Kernel/arm/GauguinGPU.cpp'
    before = (parent/framebuffer).read_text()
    after = (source/framebuffer).read_text()
    require(function(after,'AppleCLCD::present')==function(before,'AppleCLCD::present') and
        (source/'bsd/dev/gauguin_gpu_runtime.c').read_bytes()==(parent/'bsd/dev/gauguin_gpu_runtime.c').read_bytes() and
        (source/'bsd/dev/gauguin_copy356.h').read_bytes()==(parent/'bsd/dev/gauguin_copy356.h').read_bytes(),
        'read guard, whole-row copy or native GPU issue changed')
    touch = 'bsd/dev/sweet_touch.c'
    after_touch = (source/touch).read_text()
    previous_touch = (parent/touch).read_text()
    require(after_touch.replace('#include "gauguin_calibration357.h"\n','').replace(
        '\t\tif (sweet_script_wake_mode) sweet_frame357_calibrate_after_script();\n','')==previous_touch,
        'script changed outside its post-completion calibration trigger')
    driver_src = (source/driver).read_text()
    complete = driver_src.split('IOReturn GauguinGPUUserClient::finishPending(',1)[1].split('::clientClose(',1)[0]
    submit = driver_src.split('IOReturn GauguinGPUUserClient::submit(',1)[1]
    for body,anchors in (
        (complete,('F344_EOP','flush_dcache64(ptr','fPendingQueue->completed=fPendingQueueFence',
                   'F344_READY','sweet_fb357_finish_writer(fPendingDisplayTicket')),
        (submit,('b->pending=true','sweet_fb357_claim_writer','sweet_gpu_runtime_issue(addresses',
                 'r->fence=++q->issued'))):
        positions = [body.index(term) for term in anchors]
        require(positions==sorted(positions),'escrow, issue, cache visibility or completion order differs')
    wire = out/'frame357-records.inc'
    start = after.index('struct sweet_fb_frame {')
    end = after.index('static void sweet_fb_frame_release',start)
    recsize, = re.findall(r'^#define SWEET_FB_SWAP_REC_SIZE\s+(\S+)',after,re.M)
    layers, = re.findall(r'^#define SWEET_FB_LAYERS\s+(\S+)',after,re.M)
    wire.write_text(f'#define SWEET_FB_SWAP_REC_SIZE {recsize}\n#define SWEET_FB_LAYERS {layers}\n'+after[start:end])
    methods = (
        ('static uint32_t','get32'),('static void','sweet_fb_frame_release'),
        ('static void','sweet_fb_frame_move'),('static void','sweet_fb_frame_retire'),
        ('static void','sweet_fb_retired_release'),
        ('extern "C" bool','sweet_fb357_claim_writer'),('extern "C" void','sweet_fb357_finish_writer'),
        ('void','AppleCLCD::clearReadyTicketLocked'),('uint64_t','AppleCLCD::pendingTicketLocked'),
        ('sweet_fb_frame *','AppleCLCD::boundFrameLocked'),('void','AppleCLCD::replacePendingLocked'),
        ('uint64_t','AppleCLCD::watchPendingReadyLocked'),('bool','AppleCLCD::collectIssuedLocked'),
        ('bool','AppleCLCD::blankEnabledLocked'),('bool','AppleCLCD::waitingForReadyLocked'),
        ('bool','AppleCLCD::takeHeldFrameLocked'),('void','AppleCLCD::cancelHeldFramesLocked'),
        ('void','AppleCLCD::invalidateHeldRetryLocked'),('void','AppleCLCD::finishHeldFrame'),
    )
    projection = out/'frame357-projection.inc'
    projection.write_text('\n\n'.join(f'{prefix}\n{function(after,name)}' for prefix,name in methods)+'\n')
    fixture = WORK/'tests/fixtures/dpu357_retention.cpp'
    binary = out/'dpu357_retention'
    dev = source/'bsd/dev'
    subprocess.run(['xcrun','clang++','-O1','-g','-std=c++17','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-I'+str(dev),'-I'+str(out),str(fixture),'-o',str(binary)],
                   check=True,timeout=60)
    log = out/'dpu357_retention.log'
    log.write_text(subprocess.check_output([str(binary)],text=True,timeout=15))
    return [source/framebuffer,source/driver,source/touch,dev/'gauguin_ui_trace_board.c',
            dev/'gauguin_ready357.h',dev/'gauguin_calibration357.h',wire,projection,fixture,log]


def calibration_models():
    raw = (REF356/'kernel.log').read_text()
    rows,strokes,numer,denom = trace.parse(raw,extra_kinds=(52,53,54,55,56,57))
    scale = numer/denom
    pairs = {r['frame']:r for r in load(REF356/'frame-scanout-analysis.json')['raw_crc_pairs']}
    edges = {e.id:e for e in rows[trace.VBLANK]}
    end = strokes[-1][1]
    def pair_after(f):
        return pairs[f]['ticks'][1][1]
    candidates = [f for f in sorted(pairs) if (pair_after(f)-end)*scale>=750_000_000 and
        f+35 in pairs and (pair_after(f+32)-end)*scale<1_500_000_000 and
        all(g in pairs and g+1 in edges and
            (edges[g+1].a-pair_after(g)-25)*scale>=1_000_000
            for g in (f+8,f+16,f+24))]
    require(candidates,'no three post-script opportunities in 0356 measured CRC edges')
    pause = candidates[0]
    pixel = 0xaabbccdd
    events = [trace.Event(19000,pair_after(pause)+1,CALIBRATION,pause,1,0,0,0)]
    for step,mask in enumerate(MARKERS,1):
        frame = pause+CALIBRATION_GAP*step
        tick = pair_after(frame)+2
        events.append(trace.Event(19000+step,tick+25,CALIBRATION,(step<<32)|frame,1,tick,tick+20,(pixel<<32)|(pixel^mask)))
    resume = pause+CALIBRATION_GAP*4
    events.append(trace.Event(19004,pair_after(resume)+1,CALIBRATION,(4<<32)|resume,1,0,0,0))
    rows[CALIBRATION] = events
    proofs = []
    for lag in (0,1):
        markers = [pause+8*i+1+lag for i in range(1,4)]
        lane = {frame:dict(read,agrees=True,signatures=[sum(frame>=m for m in markers)]*2)
                for frame,read in pairs.items()}
        proof = calibration(rows,strokes,lane,[],scale)
        require(proof['qualified'] and proof['lag_frames']==lag and len(proof['dedicated_witnesses'])==3,
                'cannot qualify the injected three transitions on observed hardware times')
        proofs.append(dict(lag=lag,witness_frames=[w['expected_scan_frame'] for w in proof['dedicated_witnesses']]))
        for broken in (events[:-1], [events[0],replace(events[1],flags=0),*events[2:]],
                       [*events[:3],replace(events[3],c=events[3].c^1),events[4]]):
            rows[CALIBRATION] = broken
            require(not calibration(rows,strokes,lane,[],scale)['qualified'],'bad calibration was accepted')
        rows[CALIBRATION] = events
        require(not calibration(rows,strokes,lane,
            [dict(start_tick=events[2].a-30,end_tick=events[2].a-1)],scale)['qualified'],
            'unrelated scanout write was accepted within calibration')
    return dict(observed_timing_eligible_pause_frames=len(candidates),synthetic_signature_models=proofs,
        rejected_corrupt_marker_scenarios=8,pause_frame=pause)


def retained_claim_model():
    source = (REF355/'kernel.log').read_text()
    rows,_,_,_ = trace.parse(source,extra_kinds=(52,53,*ready.KINDS))
    comparison = REF355/'present-alignment-0350-0353-0355.json'
    attempts = load(comparison)['current']['attempts']
    swaps = {s.id:s for s in rows[trace.SWAP]}
    writers = {(w.id,w.b):w for w in rows[trace.WRITER] if w.b}
    marks = {r.id:r for r in rows[ready.READY]}
    bindings = {}
    for advance in rows[ready.PROMOTE]:
        ticket = advance.id<<32|advance.c
        w = writers[marks[advance.id].b,ticket]
        bindings[advance.id] = trace.Event(w.seq,w.tick-1,BOUND,advance.id,0,ticket,advance.b,0)
    complete = {r.id:r for r in rows[trace.READY]}
    joined,_,_ = ready.ready_joins(rows,attempts)
    # Change only the successor's arrival in a trace where the older frame
    # still passed the real read guard on its genuine recorded take.
    proof = next(r for r in joined if r['waiting_newer_swap'] and r['copied'] and
        r['generation']+1 in swaps and
        bindings[r['generation']].tick+1<complete[marks[r['generation']].b].tick and
        complete[marks[r['generation']].b].tick<swaps[r['generation']+1].tick)
    old, new = proof['generation'], proof['generation']+1
    rows[trace.SWAP] = sorted((replace(s,tick=complete[marks[old].b].tick-1) if s.id==new else s
                               for s in rows[trace.SWAP]),key=ready.order)
    rows[BOUND] = sorted(bindings.values(),key=ready.order)
    accepted,_,_ = ready.ready_joins(rows,attempts,binding_kind=BOUND)
    require(any(r['generation']==old and r['copied'] and r['guarded'] for r in accepted),
            'exact older claim with independent read proof was discarded')
    for binding_kind in (None,BOUND):
        rows[BOUND] = [b for b in bindings.values() if b.id!=old]
        try:
            ready.ready_joins(rows,attempts,binding_kind=binding_kind)
        except ValueError as error:
            require(('exact pre-issue claim' if binding_kind else 'completed watched writer') in str(error),
                    'unexpected retained claim failure: '+str(error))
        else:
            raise ValueError('an older promotion without the new exact claim was accepted')
    return comparison


def main():
    out = BASE/'frame-host'
    out.mkdir()
    save = import_module('prepare-frame344').save
    inputs = projected_source(out)
    require(json.dumps(report(),indent=2)+'\n'==(BASE/'offline-replay.json').read_text(),
            'frozen replay failed byte-exact reproduction')
    inputs.append(BASE/'offline-replay.json')
    inputs.append(retained_claim_model())
    evidence = calibration_models()
    path = out/'calibration-model.json'
    save(path,evidence)
    inputs.append(path)

    old = load(REF356/'present-alignment-0350-0355-0356.json')
    displays = old['references']|{'0356':old['current']}
    # An offline treatment-blind alignment must preserve 0356's unknown
    # hardware content even when mapping comparison slots by ordinal.
    rehearsal = compare(displays|{'0357':deepcopy(old['current'])})
    require(all(r['trials']['0356']['kind']=='unknown' for r in rehearsal['frames'] if r['trials']['0356']),
            '0356 unqualified signatures were presented as verified frames')
    saves = out/'reference-displays.json'
    save(saves,displays)
    inputs.extend((saves,REF356/'present-alignment-0350-0355-0356.json'))
    run = import_module('run-frame357-trial')
    plan = expected_plan()
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                                       static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected pre-readback error')
    else:
        raise ValueError('0357 analyzed before independent restoration proof')

    control = import_module('check-core342-pipeline')
    controls = []
    for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                 'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        control.control_fixture(out,plan,case,controls)
    suites = ('test_frame350_log','test_frame349_log','test_frame348_trial','test_frame347_trial',
              'test_frame345_log','test_frame344_log','test_core342_log')
    case_fixture = Path('research/tmp/io-path-342/core-host-v2/program342-success.log')
    copy = WORK/case_fixture
    copy.parent.mkdir(parents=True,exist_ok=True)
    copy.write_bytes((P356.parents[2]/case_fixture).read_bytes())
    env = {**os.environ,'PYTHONPATH':os.pathsep.join(map(str,(WORK/'tools',WORK/'tests')))}
    output = subprocess.run([sys.executable,'-m','unittest','-v',*suites],capture_output=True,text=True,env=env,timeout=90)
    logfile = out/'unit-tests.log'
    logfile.write_text(output.stdout+output.stderr)
    require(output.returncode==0,'decoder tests failed. See '+str(logfile))
    tests = int(re.search(r'Ran (\d+) tests?',output.stderr)[1])
    inputs.extend([logfile,copy,*[WORK/'tests'/f'{suite}.py' for suite in suites]])
    result = dict(state='0357-offline-checks-passed',checked_actual_kernel_functions=True,
        original_read_guard_and_copy=True,native_order_and_single_FIFOs_preserved=True,unit_tests=tests,
        control_models=len(controls),controls=controls,independent_readback_precedes_analysis=True,
        calibration=evidence,retained_claim_decoder_model=True,reference_windows=78,device_commands=0,
        input_pins={str(p):sha(p) for p in [Path(__file__),*inputs]})
    save(out/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','controls')},indent=2))


if __name__=='__main__':
    main()
