#!/usr/bin/env python3
"""Link actual 0338 C API to the proven unchanged SURF334 ASan core units."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'
SURFACE=MAIN/'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'
OWNER=MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
UNITS=['pm4','gpu','command','compute','texture','render','link','compiler','metallib','fake_gpu','iokit_transport']
SCENARIOS=['blocked-front','completion-first','notification-allocation','meter','notice-owner-release',
           'synchronous','success','allocation','submission','refusal','worker-exception']


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--ownership-receipt',type=Path)
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v1/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=a.prepared.resolve();p=json.loads(prepared.read_text())
    old=SURFACE/'core-host-v1/result.json';r=json.loads(old.read_text())
    assert r['state']=='SURF334-full-core-host-equivalence-and-ownership-passed'
    spec=importlib.util.spec_from_file_location('ownership338',OWNER/'tools/check-metal-owned-recording.py')
    contracts=importlib.util.module_from_spec(spec);spec.loader.exec_module(contracts)
    objects=[SURFACE/'core-host-v1/candidate'/(u+'.o') for u in UNITS]
    pins={str(q):sha(q) for q in [prepared,old,Path(__file__),WORK/'tests/fixtures/core_async338.cpp',
                                   OWNER/'tests/fixtures/metal_owned_recording.cpp',*objects]}
    # Private C API and its declarations are the only existing changed core
    # files. These real linked units compile the exact unchanged candidate334
    # sources; no replacement model of the GPU, completion queue or buffers.
    old_source=json.loads((SURFACE/'prepared-v1/result.json').read_text())
    for u in UNITS:
        name='src/'+u+'.cpp';q=Path(p['sources']['baseline'])/name
        assert sha(q)==old_source['source_pins']['candidate'][name]
    for variant in ('baseline','candidate'):
        for name,digest in p['source_pins'][variant].items():
            q=Path(p['sources'][variant])/name;assert sha(q)==digest;pins[str(q)]=digest
    out.mkdir();result=dict(state='0338-core-host-running',input_pins=pins,steps=[],device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        proc=subprocess.run(argv,capture_output=True,timeout=120,env={**os.environ,
            'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        log=out/(name+'.log');log.write_bytes(proc.stdout+proc.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=proc.returncode,log=str(log),sha256=sha(log)))
        save();assert proc.returncode==0,(name,proc.stderr[-1600:])
        assert b'ERROR: AddressSanitizer' not in proc.stderr and b'runtime error:' not in proc.stderr
        return proc.stdout
    common=['clang++','-std=c++17','-O2','-gline-tables-only','-fno-omit-frame-pointer','-pthread',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all',
        '-DHAKIOS_METAL_TARGET_A619','-I'+str(OWNER/'tests/fixtures')]
    try:
        if a.ownership_receipt:
            prior=json.loads(a.ownership_receipt.read_text())
            for name,digest in prior['input_pins'].items():
                if name in (str(Path(__file__)),str(WORK/'tests/fixtures/core_async338.cpp')):continue
                assert sha(name)==digest,name
            assert all(any(s['name']==v+'-ownership-'+case and s['exit']==0 for s in prior['steps'])
                       for v in ('baseline','candidate') for case in contracts.SCENARIOS)
            result['reused_ownership_receipt']=dict(path=str(a.ownership_receipt.resolve()),
                sha256=sha(a.ownership_receipt),unchanged_original_harness_and_actual_core_inputs=True)
            pins[str(a.ownership_receipt.resolve())]=sha(a.ownership_receipt)
        for variant in (('candidate',) if a.ownership_receipt else ('baseline','candidate')):
            source=Path(p['sources'][variant]);flags=[*common,'-I'+str(source/'include'),'-I'+str(source/'src')]
            fixtures=[] if a.ownership_receipt else [('ownership',OWNER/'tests/fixtures/metal_owned_recording.cpp')]
            if variant=='candidate':fixtures.append(('async338',WORK/'tests/fixtures/core_async338.cpp'))
            for name,fixture in fixtures:
                obj=out/(variant+'-'+name+'.o');binary=out/(variant+'-'+name)
                run([*flags,'-c',str(fixture),'-o',str(obj)],variant+'-compile-'+name)
                run([*flags,*map(str,objects),str(obj),'-framework','IOKit','-framework','CoreFoundation','-o',str(binary)],variant+'-link-'+name)
                scenarios=contracts.SCENARIOS if name=='ownership' else SCENARIOS
                for scenario in scenarios:
                    stdout=run([str(binary),scenario],variant+'-'+name+'-'+scenario)
                    assert ('PASS'+('338' if name=='async338' else '')+' '+scenario).encode() in stdout
        result.update(state='0338-core-host-ownership-and-notification-passed',
            original_ownership_scenarios_per_variant=len(contracts.SCENARIOS),new_notification_scenarios=len(SCENARIOS),
            sanitizers=['address','undefined'],actual_core_units_reused=UNITS,
            notification_failure_falls_back_without_refailing_recording=True,physical_FPS_qualified=False)
    except BaseException as error:result.update(state='0338-core-host-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(q)==d for q,d in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
