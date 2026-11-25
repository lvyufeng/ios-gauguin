#!/usr/bin/env python3
"""Execute actual production ObjC methods with real deferred core + FakeGpu."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'
OWNER=MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
SURFACE=MAIN/'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'
UNITS=['pm4','gpu','command','compute','texture','render','link','compiler','metallib','fake_gpu','iokit_transport']


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads((BASE/'prepared-v2/result.json').read_text())
    source=Path(prepared['sources']['candidate']);frontend=Path(prepared['sources']['frontend-candidate'])/'HakiosMetalCA.m'
    text=frontend.read_text()
    def part(start,end):
        assert text.count(start)==1
        begin=text.index(start);return text[begin:text.index(end,begin+len(start))]
    callbacks=part('static void\nhm_recorded338','- (void)hakiosTurnAtCommit:')
    turn=part('- (void)hakiosTurnInto:(hakios_metal_cb *)cb\n{','/* A copy a kernel or a pass')
    event=part('- (void)hakiosSignal:(uint64_t)value\n{','- (void)notifyListener:')
    methods=part('- (void)commit\n{','/* abstract in _MTLCommandBuffer')
    for first,last in [('- (void)hakiosDeliver:','- (void)hakiosMarkScheduled'),
                        ('- (void)hakiosMarkScheduled\n{','- (void)hakiosCompletedNow'),
                        ('- (void)hakiosCompletedNow\n{','/* A handler added once'),
                        ('- (void)addScheduledHandler:','- (void)addCompletedHandler:'),
                        ('- (void)addCompletedHandler:','/* --- presenting --- */')]:
        # Method declarations also occur earlier. Extract only implementations.
        start=text.index(first,text.index('/* --- handlers --- */'))
        end=text.index(last,start+len(first));methods+=text[start:end]
    objects=[SURFACE/'core-host-v1/candidate'/(u+'.o') for u in UNITS]
    paths=[Path(__file__),WORK/'tests/fixtures/frontend_factory338.cpp',WORK/'tests/fixtures/frontend_async338.mm',
           BASE/'prepared-v2/result.json',frontend,OWNER/'tests/fixtures/metal_owned_recording.cpp',*objects]
    pins={str(p):sha(p) for p in paths}
    for root in (source,frontend.parent):
        for p in root.rglob('*'):
            if p.is_file():pins[str(p)]=sha(p)
    out.mkdir();(out/'frontend338-callbacks.inc').write_text(callbacks);(out/'frontend338-methods.inc').write_text(methods)
    (out/'frontend338-turn.inc').write_text(turn);(out/'frontend338-event.inc').write_text(event)
    result=dict(state='0338-actual-frontend-host-running',input_pins=pins,steps=[],device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=60,env={**os.environ,
            'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)))
        save();assert p.returncode==0,(name,p.stderr[-2000:])
        assert b'ERROR: AddressSanitizer' not in p.stderr and b'runtime error:' not in p.stderr
        return p.stdout
    flags=['clang++','-std=c++17','-O2','-gline-tables-only','-fno-omit-frame-pointer','-pthread',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all',
        '-DHAKIOS_METAL_TARGET_A619','-I'+str(OWNER/'tests/fixtures'),'-I'+str(source/'include'),
        '-I'+str(source/'src'),'-I'+str(frontend.parent),'-I'+str(out)]
    try:
        for stem,fixture in [('factory',WORK/'tests/fixtures/frontend_factory338.cpp'),
                             ('frontend',WORK/'tests/fixtures/frontend_async338.mm')]:
            run([*flags,'-c',str(fixture),'-o',str(out/(stem+'.o'))],'compile-'+stem)
        binary=out/'frontend338'
        run([*flags,*map(str,objects),str(out/'factory.o'),str(out/'frontend.o'),
             '-framework','Foundation','-framework','Metal','-framework','IOKit','-framework','CoreFoundation','-o',str(binary)],'link')
        for failure in (0,1,2):
            resultText=run([str(binary),str(failure)],'run-'+str(failure))
            assert b'PASS actual frontend338' in resultText
        assert b'PASS actual frontend338' in run([str(binary),'0','event-turn'],'event-turn-dependency')
        assert b'PASS actual frontend338' in run([str(binary),'0','late-notice'],'completion-before-notice-admission')
        result.update(state='0338-production-ObjC-methods-core-FakeGpu-lifetimes-passed',
            scenarios=5,extracted_production_methods=['commit','hm_recorded338','hm_completed','hakiosDeliver',
                'hakiosMarkScheduled','hakiosCompletedNow','addScheduledHandler','addCompletedHandler',
                'hakiosTurnInto','hakiosReached','hakiosWaitFor','hakiosSignal'],
            frontend_two_bodies_retire_while_core_is_gated=True,scheduled_handlers_precede_completed_per_CB=True,
            internal_completion_and_slot_return_FIFO=True,CB_and_queue_final_releases_verified=True,
            exact_core_BO_and_queue_creation_closure_counts=True,sanitizers=['address','undefined'],
            nonempty_event_wait_and_actual_core_rotated_blit_tested=True,
            actual_completion_can_finish_before_notice_admission=True,
            full_Apple_runtime_behavior_qualified=False,physical_FPS_qualified=False)
    except BaseException as error:result.update(state='0338-actual-frontend-host-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==d for p,d in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
