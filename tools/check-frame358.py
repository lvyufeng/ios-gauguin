#!/usr/bin/env python3
"""Validate the probe against the built source and restored 0357 traces."""

from dataclasses import replace
from importlib import import_module
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import frame344_log as trace
import frame349_log as scanout
import frame352_display as copy
import frame354_display as ready
from frame357_display import BOUND, CALIBRATION, calibration
from frame358_audit import audit, BASE, P357, REF357, PROBE, WORK, load, require, sha
from frame358_display import KINDS, probe_joins


def verify_source(out):
    parent = P357/'native-kernel/source'
    src = BASE/'native-kernel/source'
    driver = 'iokit/Kernel/arm/GauguinGPU.cpp'
    fb = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
    unchanged = ('bsd/dev/gauguin_gpu_runtime.c','bsd/dev/gauguin_copy356.h','bsd/dev/sweet_touch.c',
                 'bsd/dev/gauguin_ready357.h','bsd/dev/gauguin_calibration357.h')
    require(all(sha(src/p)==sha(parent/p) for p in unchanged),'carried GPU runtime, copy, touch or retention changed')
    projection = import_module('check-frame357')
    require(projection.function((src/fb).read_text(),'AppleCLCD::present')==
            projection.function((parent/fb).read_text(),'AppleCLCD::present'),'actual read guard or panel copy changed')
    before, after = [(p/driver).read_text() for p in (parent,src)]
    native = 'IOReturn GauguinGPUUserClient::finishPending('
    require(after[after.index(native):]==before[before.index(native):],
            'native completion, submission or escrow protocol changed')
    block = projection.function((src/fb).read_text(),'AppleCLCD::observePendingReady')
    call = block.index('GauguinGPUSurfaceReadyFence(')
    require(block.rfind('IOLockUnlock(fLock);',0,call)>block.index('surface->retain()') and
            call<block.index('surface->release()'), 'probe can run under display lock or with a borrowed surface')

    projection.BASE=BASE
    inputs = projection.projected_source(out)
    helper = 'extern "C" uint32_t GauguinGPUSurfaceReadyFence('
    start = after.index(helper)
    inc = out/'frame358-gpu-probe.inc'
    inc.write_text(after[start:after.index('\n}',start)+2]+'\n')
    fixture = WORK/'tests/fixtures/dpu358_probe.cpp'
    binary = out/'dpu358_probe'
    subprocess.run(['xcrun','clang++','-O1','-g','-std=c++17','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-I'+str(src/'bsd/dev'),'-I'+str(out),str(fixture),'-o',str(binary)],
                   check=True,timeout=60)
    log = out/'dpu358_probe.log'
    log.write_text(subprocess.check_output([str(binary)],text=True,timeout=15))
    return [*inputs,*[src/p for p in unchanged],src/'bsd/dev/gauguin_probe358.h',src/'bsd/dev/gauguin_ui_trace.c',
            src/'bsd/dev/gauguin_frame344.h',inc,fixture,log]


def wire_and_publication_models():
    raw = (REF357/'kernel.log').read_text()
    prior_capacity = 'SWEET F344: armed window=45s capacity=16384'
    require(raw.count(prior_capacity)==1,'0357 capture scope differs')
    extended = raw.replace(prior_capacity,prior_capacity.replace('16384','20480')+
                           '\nSWEET F358 PROBE: first_line=1728 limit=1024')
    before,_,_,_ = trace.parse(extended,extra_kinds=(52,53,*KINDS))
    cap = 600
    count = sum(map(len,before.values()))
    last = max((row for group in before.values() for row in group),key=lambda row:row.seq)
    fixture = re.sub(r'(^SWEET F344 [HF]: count=)\d+',lambda m:m[1]+str(count+cap),extended,flags=re.M)
    rows = ''.join(f'SWEET F344 E {count+i:x} {last.tick:x} 3c {i:x} 1 1 0 {last.tick:x}\n'
                   for i in range(1,cap+1))
    where = fixture.index('SWEET F344 F:')
    shaped = fixture[:where]+rows+fixture[where:]
    parsed,_,_,_ = trace.parse(shaped,extra_kinds=(52,53,*KINDS))
    require(16384<count+cap<20480 and len(parsed[PROBE])==cap,'larger ring cannot be decoded')
    for bad in (shaped.replace('capacity=20480','capacity=16384'),
                shaped.replace('first_line=1728','first_line=1792'),
                re.sub(r'(^SWEET F344 [HF]: count=)\d+',r'\g<1>20480',shaped,flags=re.M)):
        try:trace.parse(bad,extra_kinds=(52,53,*KINDS))
        except ValueError:pass
        else:raise ValueError('bad 0358 capture bound was accepted')

    frame = load(REF357/'frame-scanout-analysis.json')
    old = copy.analyze(raw,frame,extra_kinds=ready.KINDS+(58,59))
    selection = ready.analyze(raw,old,binding_kind=BOUND,extra_kinds=(59,))
    completed = {r.id:r for r in before[trace.EOP]}
    visible = {r.id:r for r in before[trace.READY]}
    edges = {r.id:r for r in before[trace.VBLANK]}
    victim = next(r for r in selection['joins'] if r.get('following_hardware_frame',{}).get('classification')=='changed' and
                  r['guarded'] and edges[r['target_frame']].b<completed[r['fence']].tick and
                  visible[r['fence']].tick<r['ready_tick'])
    fence,gen = victim['fence'],victim['generation']
    probe = trace.Event(visible[fence].seq,visible[fence].tick,PROBE,victim['target_frame'],4,
        (gen<<32)|victim['surface'],(victim['version']<<32)|fence,completed[fence].tick)
    before[PROBE] = [probe]
    evidence = probe_joins(before,old,selection)
    require(evidence['checks']['all']['published']==1 and
            sum(evidence['exact_same_scan_new_images_by_phase'].values())==1,'synthetic publication cannot join a certified image')
    for invalid in ([replace(probe,b=probe.b+1)],[replace(probe,c=visible[fence].tick+1)],[probe,probe]):
        before[PROBE]=invalid
        try:probe_joins(before,old,selection)
        except ValueError:pass
        else:raise ValueError('altered publication was accepted')
    return dict(expanded_trace_fixture_rows=count+cap,invalid_capture_rejects=3,
                exact_synthetic_publication_join=True,invalid_publication_rejects=3)


def main():
    out=BASE/'frame-host'
    out.mkdir()
    inputs=verify_source(out)
    replay=BASE/'repeat-audit.json'
    require(json.dumps(audit(),indent=2)+'\n'==replay.read_text(),'0357 deadline audit differs')
    synthetic=wire_and_publication_models()
    raw_path=REF357/'kernel.log'
    raw=raw_path.read_text()
    core, identity, _ = import_module('run-frame350-trial').trace_inputs(REF357)
    retained_kinds=(*ready.KINDS,BOUND,CALIBRATION)
    reference=scanout.analyze(raw,identity['submits'],core['rows'],preserve_data_preimage=True,
        extra_kinds=(52,53,*retained_kinds),latch_calibration=calibration,join_tail_copy=True)
    aligned=copy.analyze(raw,reference,extra_kinds=retained_kinds)
    require(reference['crc_frame_calibration']['qualified'] and
            aligned['phases']['active']['verified_full_frame_counts']==dict(changed=104,repeated=164,unknown=0) and
            aligned['phases']['release']['verified_full_frame_counts']==dict(changed=111,repeated=71,unknown=0),
            'tail linkage changed the independently audited 0357 reference')
    references=P357/'frame-host/reference-displays.json'
    ref_result=out/'reference-displays.json'
    ref_result.write_text(json.dumps(load(references)|{'0357':{k:aligned[k] for k in ('phases','windows')}},indent=2)+'\n')
    inputs.extend((raw_path,references,ref_result))
    suites=('test_frame350_log','test_frame349_log','test_frame348_trial','test_frame347_trial',
            'test_frame345_log','test_frame344_log','test_core342_log')
    fixture=Path('research/tmp/io-path-342/core-host-v2/program342-success.log')
    p=WORK/fixture
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((P357.parents[2]/fixture).read_bytes())
    env={**os.environ,'PYTHONPATH':os.pathsep.join(map(str,(WORK/'tools',WORK/'tests')))}
    test=subprocess.run([sys.executable,'-m','unittest','-v',*suites],capture_output=True,text=True,env=env,timeout=90)
    logfile=out/'unit-tests.log'
    logfile.write_text(test.stdout+test.stderr)
    require(test.returncode==0,'decoder regression failed. See '+str(logfile))
    trials=int(re.search(r'Ran (\d+) tests?',test.stderr)[1])
    inputs.extend((Path(__file__),p,logfile,replay,*[WORK/'tests'/f'{n}.py' for n in suites]))
    record=dict(state='0358-host-probe-and-frame-checks-passed',original_guard_and_copy=True,
        native_submit_and_completion_source_identical=True,built_source_ownership_fixture=True,
        built_source_probe_fixture=True,unit_tests=trials,reference_windows=104,zero_device_commands=True,**synthetic,
        input_pins={str(p):sha(p) for p in inputs})
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print({k:v for k,v in record.items() if k!='input_pins'})


if __name__=='__main__':
    main()
