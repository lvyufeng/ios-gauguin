#!/usr/bin/env python3
"""Real C API/command implementation with ASan/UBSan ownership regressions."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-prof-339'
PRIOR=MAIN/'research/tmp/gauguin-core-async-worktree-20261117/research/tmp/core-async-338'
OLD=MAIN/'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'
OWNER=MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
UNITS=['pm4','gpu','compute','texture','render','link','compiler','metallib','fake_gpu','iokit_transport']
SCENARIOS=['partition','phases','early-phases','nested-unwind','success','allocation','submission','refusal','worker-exception','limits']
ASYNC=['blocked-front','completion-first','notification-allocation','meter','notice-owner-release','synchronous','success','allocation','submission','refusal','worker-exception']


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());source=Path(prepared['sources']['candidate'])
    spec=importlib.util.spec_from_file_location('owned339contracts',OWNER/'tools/check-metal-owned-recording.py')
    contracts=importlib.util.module_from_spec(spec);spec.loader.exec_module(contracts)
    original=OWNER/'tests/fixtures/metal_owned_recording.cpp';inherited=PRIOR.parents[2]/'tests/fixtures/core_async338.cpp'
    assert inherited.exists(),inherited
    objects=[OLD/'core-host-v1/candidate'/(u+'.o') for u in UNITS]
    paths=[Path(__file__),WORK/'tests/fixtures/core_prof339.cpp',a.prepared,original,inherited,*objects]
    pins={str(p):sha(p) for p in paths}
    for folder in ('baseline','candidate'):
        for name,h in prepared['source_pins'][folder].items():
            p=Path(prepared['sources'][folder])/name;assert sha(p)==h;pins[str(p)]=h
    old=json.loads((PRIOR/'core-host-v4/result.json').read_text())
    baseline=PRIOR/'core-host-v4/candidate-ownership';assert baseline.exists()
    for case in contracts.SCENARIOS:
        assert any(s['name']=='candidate-ownership-'+case and s['exit']==0 for s in old['steps'])
    pins[str(PRIOR/'core-host-v4/result.json')]=sha(PRIOR/'core-host-v4/result.json');pins[str(baseline)]=sha(baseline)
    out.mkdir();text=inherited.read_text();assert text.count('int main(int argc,char** argv)')==1
    (out/'inherited-async338.inc').write_text(text.replace('int main(int argc,char** argv)','int inherited338_dispatch(int argc,char** argv)'))
    result=dict(state='0339-core-host-running',steps=[],input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=90,env={**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)))
        save();assert p.returncode==0,(name,p.stderr[-2000:])
        assert b'ERROR: AddressSanitizer' not in p.stderr and b'runtime error:' not in p.stderr
        for line in p.stderr.splitlines():
            if line.startswith(b'GAUGUIN CR339:'):assert len(line)+1<=2048
        return p.stdout
    flags=['clang++','-std=c++17','-O2','-gline-tables-only','-fno-omit-frame-pointer','-pthread','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-fsanitize=address,undefined','-fno-sanitize-recover=all','-DHAKIOS_METAL_TARGET_A619',
        '-I'+str(OWNER/'tests/fixtures'),'-I'+str(source/'include'),'-I'+str(source/'src'),'-I'+str(out)]
    try:
        run([*flags,'-c',str(source/'src/command.cpp'),'-o',str(out/'command.o')],'compile-command')
        for case in contracts.SCENARIOS:assert ('PASS '+case).encode() in run([str(baseline),case],'baseline-ownership-'+case)
        for name,fixture in [('ownership',original),('prof339',WORK/'tests/fixtures/core_prof339.cpp')]:
            obj=out/(name+'.o');binary=out/name
            run([*flags,'-c',str(fixture),'-o',str(obj)],'compile-'+name)
            run([*flags,*map(str,objects),str(out/'command.o'),str(obj),'-framework','IOKit','-framework','CoreFoundation','-o',str(binary)],'link-'+name)
            cases=contracts.SCENARIOS if name=='ownership' else ['old-'+x for x in ASYNC]+SCENARIOS
            for case in cases:
                stdout=run([str(binary),case],name+'-'+case)
                assert ('PASS'+('' if name=='ownership' else ('338' if case.startswith('old-') else '339'))+' '+case.removeprefix('old-')).encode() in stdout
        result.update(state='0339-real-core-ownership-categories-submit-phases-passed',
            ownership_scenarios_per_variant=len(contracts.SCENARIOS),prior_async_scenarios=len(ASYNC),new_profiler_scenarios=len(SCENARIOS),
            no_added_GPU_operations=True,all_other_core_units_reused=UNITS,sanitizers=['address','undefined'],
            submit_success_allocation_native_refusal_recording_refusal_exception_tested=True,
            TLS_nested_unwind_and_category_partition_verified=True,record_saturation_and_line_bound_verified=True,
            physical_FPS_qualified=False)
    except BaseException as error:result.update(state='0339-core-host-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
