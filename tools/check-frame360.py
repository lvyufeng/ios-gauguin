#!/usr/bin/env python3
"""Verify the 0360 linked source, read protection and restored pacing baselines."""

from importlib import import_module
import json
from pathlib import Path
import subprocess

import frame344_log as trace
from frame351_display import PRESENT
import frame352_display as copy
import frame354_display as ready
from frame357_display import BOUND, CALIBRATION
from frame358_audit import PROBE
from frame358_display import KINDS
from frame359_scope import P358, WORK, load, require, sha

pacing = import_module('audit-frame-pacing')

BASE = WORK/'research/tmp/frame-360'
PATCH = WORK/'xnu/patches/0274-gauguin-pin-completed-surface-read.patch'
DRIVER = 'iokit/Kernel/arm/GauguinGPU.cpp'
DISPLAY = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
SURFACE = 'iokit/Kernel/arm/SweetSurface.h'


def check_source(out):
    build = load(BASE/'native-kernel/build-manifest.json')
    source = Path(build['source'])
    old = P358/'native-kernel/source'
    changed = {str(p.relative_to(old)) for p in old.rglob('*') if p.is_file() and
               sha(p)!=sha(source/p.relative_to(old))}
    added = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and
             not (old/p.relative_to(source)).exists()}
    require(build['state']=='0360-native-ARM64-linked' and build['inputs_unchanged'] and
            build['baseline_reproduced_except_uuid'] and sha(build['kernel'])==build['kernel_sha256'] and
            build['input_pins'][str(PATCH)]==sha(PATCH) and changed=={DRIVER,DISPLAY,SURFACE} and
            added=={'bsd/dev/gauguin_read360.h'}, 'kernel identity or source scope differs')
    previous, candidate = ((root/DRIVER).read_text() for root in (old,source))
    lifecycle = 'bool GauguinGPUUserClient::initWithTask('
    require(candidate[candidate.index(lifecycle):]==previous[previous.index(lifecycle):],
            'native submit, completion, allocation or ownership path changed')
    previous, display = ((root/DISPLAY).read_text() for root in (old,source))
    require(previous.replace('SweetSurfaceGPURead gpuRead(s);',
                             'SweetSurfaceGPURead gpuRead(s, fastBlank ? version : UINT32_MAX);')==display,
            'copy boundary, input or ready selection changed')
    surface = (source/SURFACE).read_text()
    start = surface.index('class SweetSurfaceGPURead ')
    adapter = surface[start:surface.index('\n};',start)+3]
    prefix = ('extern "C" uint32_t ', 'static void ', 'extern "C" uint32_t ', 'extern "C" void ')
    symbols = ('GauguinGPUSurfaceState','setSurfaceGPUState','GauguinGPUSurfaceBegin','GauguinGPUSurfaceEnd')
    implementation = []
    for kind,name in zip(prefix,symbols,strict=True):
        start = candidate.index('\n'+kind+name+'(')+1
        implementation.append(candidate[start:candidate.index('\n}',start)+2])
    projected = out/'frame360-read.inc'
    projected.write_text('\n\n'.join([*implementation,adapter])+'\n')
    binary = out/'dpu360_read'
    subprocess.run(['xcrun','--sdk','macosx','clang++','-O1','-g','-std=c++17',
                    '-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(source/'bsd/dev'),'-I'+str(out),
                    str(WORK/'tests/fixtures/dpu360_read.cpp'),'-o',str(binary)],check=True,timeout=60)
    subprocess.run([str(binary)],check=True,timeout=15)
    return build['kernel_sha256']


def check_decoder(execution):
    raw = (execution/'kernel.log').read_text()
    frame = load(execution/'frame-scanout-analysis.json')
    display = copy.analyze(raw,frame,extra_kinds=KINDS)
    selection = ready.analyze(raw,display,binding_kind=BOUND,extra_kinds=(CALIBRATION,PROBE))
    eligible = {r['attempt'] for r in selection['joins'] if r['guarded'] and
                r.get('following_hardware_frame',{}).get('phase')=='active'}
    attempt = next(a for a in display['attempts'] if a['attempt'] in eligible and len(a['read_guards'])==1 and
                   a['read_guards'][0]['surface_ready_tick']<=a['read_guards'][0]['locked_tick'])
    guard, = attempt['read_guards']
    rows,*_ = trace.parse(raw,extra_kinds=(PRESENT,copy.WAKE,*KINDS))
    original, = (r for r in rows[trace.LOCK] if r.id==guard['surface'] and r.a==guard['queued_tick'])

    def wire(fields):
        return 'SWEET F344 E '+' '.join(f'{value:x}' for value in fields)

    identity = (original.seq,original.tick,original.kind,original.id)
    tail = (original.a,original.b,original.c)
    candidate = raw.replace(wire((*identity,original.flags,*tail)),
                            wire((*identity,trace.LOCK_SURFACE_RESERVATION,*tail)),1)
    require(candidate!=raw,'no fixture read reservation wire record')
    adapted = copy.analyze(candidate,frame,extra_kinds=KINDS)
    require(ready.analyze(candidate,adapted,binding_kind=BOUND,extra_kinds=(CALIBRATION,PROBE))==selection,
            'valid surface reservation changed exact present/CRC identity')
    checked = next(a for a in adapted['attempts'] if a['attempt']==attempt['attempt'])
    observed, = checked['read_guards']
    require(observed['surface_reservation'],'reservation evidence disappeared')
    observed['fence'] += 1
    try:
        ready.analyze(candidate,adapted,binding_kind=BOUND,extra_kinds=(CALIBRATION,PROBE))
    except ValueError as error:
        require('reservation differs' in str(error),'unexpected causal guard rejection')
    else:
        raise ValueError('reservation for the wrong native fence was accepted')
    return candidate


def main():
    out = BASE/'frame-host'
    out.mkdir(exist_ok=True)
    kernel = check_source(out)
    before,after = pacing.references()
    check_decoder(after)
    trials = [pacing.audit(path) for path in (before,after)]
    require([r['active']['scans'] for r in trials]==[
        dict(changed=113,repeated=156,unknown=0),dict(changed=93,repeated=175,unknown=0)] and
        [r['active_read_guards_crossing_deadline'] for r in trials]==[9,25] and
        [r['active_separate_recorded_writer_overlap'] for r in trials]==[
            dict(runtime_issue=4,surface_cache_flush=2),dict(runtime_issue=15,surface_cache_flush=5)] and
        [r['active_same_version_changed_next_scan'] for r in trials]==[3,2],
        'pacing replay differs from the archived CRC, guard or IO evidence')
    receipt = dict(state='0360-host-verified', kernel_sha256=kernel,
        read_guard_concurrency_and_lifetime=True, exact_writer_decoder=True, device_commands=0,
        trials=trials)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='trials'},indent=2))


if __name__=='__main__':
    main()
