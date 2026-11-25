#!/usr/bin/env python3
"""Actual C API/render/GPU implementation, ownership and deferred worker regressions."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/draw-submit-340'
PRIOR=MAIN/'research/tmp/gauguin-core-prof-worktree-20261117/research/tmp/core-prof-339'
OLD=MAIN/'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'
OWNER=MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
REUSED=['pm4','compute','texture','link','compiler','metallib','fake_gpu']
CHANGED=['command','render','gpu','iokit_transport']
PROF=['partition','phases','early-phases','nested-unwind','success','allocation','submission','refusal','worker-exception','limits']
ASYNC=['blocked-front','completion-first','notification-allocation','meter','notice-owner-release','synchronous','success','allocation','submission','refusal','worker-exception']


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());source=Path(prepared['sources']['candidate'])
    spec=importlib.util.spec_from_file_location('ownership_contracts340',OWNER/'tools/check-metal-owned-recording.py')
    contracts=importlib.util.module_from_spec(spec);spec.loader.exec_module(contracts)
    original=OWNER/'tests/fixtures/metal_owned_recording.cpp'
    inherited=WORK/'tests/fixtures/core_async338.cpp';prof=WORK/'tests/fixtures/core_prof339.cpp'
    objects=[OLD/'core-host-v1/candidate'/(u+'.o') for u in REUSED]
    baseline=PRIOR/'core-host-v3/ownership';assert baseline.exists()
    paths=[Path(__file__),WORK/'tests/fixtures/core_phase340.cpp',a.prepared,original,inherited,prof,baseline,PRIOR/'core-host-v3/result.json',*objects]
    pins={str(p.resolve()):sha(p) for p in paths}
    for variant in ('baseline','candidate'):
        for name,h in prepared['source_pins'][variant].items():
            p=Path(prepared['sources'][variant])/name;assert sha(p)==h;pins[str(p)]=h
    out.mkdir()
    (out/'inherited-async338.inc').write_text(inherited.read_text().replace('int main(int argc,char** argv)','int inherited338_dispatch(int argc,char** argv)'))
    text=prof.read_text().replace('339','340');assert text.count('int main(int argc,char** argv)')==1
    (out/'inherited-prof340.inc').write_text(text.replace('int main(int argc,char** argv)','int inherited340_dispatch(int argc,char** argv)'))
    result=dict(state='0340-real-core-host-running',steps=[],input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=90,env={**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)));save()
        assert p.returncode==0,(name,p.stderr[-2400:])
        assert b'ERROR: AddressSanitizer' not in p.stderr and b'runtime error:' not in p.stderr
        for line in p.stderr.splitlines():
            if line.startswith(b'GAUGUIN CR340:'):assert len(line)+1<=4096
        return p.stdout
    flags=['clang++','-std=c++17','-O2','-gline-tables-only','-fno-omit-frame-pointer','-pthread','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-fsanitize=address,undefined','-fno-sanitize-recover=all','-DHAKIOS_METAL_TARGET_A619',
        '-I'+str(OWNER/'tests/fixtures'),'-I'+str(source/'include'),'-I'+str(source/'src'),'-I'+str(out)]
    try:
        for unit in CHANGED:run([*flags,'-c',str(source/'src'/(unit+'.cpp')),'-o',str(out/(unit+'.o'))],'compile-'+unit)
        for case in contracts.SCENARIOS:assert ('PASS '+case).encode() in run([str(baseline),case],'baseline339-ownership-'+case)
        for label,fixture in [('ownership',original),('phase340',WORK/'tests/fixtures/core_phase340.cpp')]:
            obj=out/(label+'.o');binary=out/label
            run([*flags,'-c',str(fixture),'-o',str(obj)],'compile-'+label)
            run([*flags,*map(str,objects),*[str(out/(u+'.o')) for u in CHANGED],str(obj),'-framework','IOKit','-framework','CoreFoundation','-o',str(binary)],'link-'+label)
            cases=contracts.SCENARIOS if label=='ownership' else ['old-'+x for x in ASYNC]+PROF+['workspace-owner','workspace-unwind']
            for case in cases:
                stdout=run([str(binary),case],label+'-'+case)
                expected=('PASS ' if label=='ownership' else ('PASS338 ' if case.startswith('old-') else 'PASS340 '))+case.removeprefix('old-')
                assert expected.encode() in stdout
        result.update(state='0340-real-core-ownership-fine-phases-worker-reuse-passed',ownership_scenarios_per_variant=len(contracts.SCENARIOS),
            inherited_async_scenarios=len(ASYNC),inherited_profiler_scenarios=len(PROF),new_State_lifetime_scenarios=2,
            no_added_GPU_operations=True,reused_unchanged_units=REUSED,sanitizers=['address','undefined'],physical_FPS_qualified=False)
    except BaseException as error:result.update(state='0340-real-core-host-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('steps','input_pins')},indent=2))


if __name__=='__main__':main()
