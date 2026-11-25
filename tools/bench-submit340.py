#!/usr/bin/env python3
"""Actual Gpu::submit A/B with identical recording transport; no device/IO latency claim."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/draw-submit-340'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());source=Path(prepared['sources']['candidate']);fixture=WORK/'tests/fixtures/submit_bench340.cpp'
    pins={str(p.resolve()):sha(p) for p in (Path(__file__),fixture,a.prepared)}
    for name,h in prepared['source_pins']['candidate'].items():p=source/name;assert sha(p)==h;pins[str(p)]=h
    out.mkdir();r=dict(state='0340-Gpu-submit-host-benchmark-running',steps=[],input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,text=True,timeout=120);log=out/(name+'.log');log.write_text(p.stdout+p.stderr)
        r['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)));save()
        assert p.returncode==0,(name,p.stderr[-2000:]);return p.stdout
    flags=['clang++','-std=c++17','-O2','-pthread','-Wall','-Wextra','-Werror','-DHAKIOS_METAL_TARGET_A619','-I'+str(source/'include'),'-I'+str(source/'src')]
    try:
        results={}
        for enabled,label in ((0,'control'),(1,'candidate')):
            binary=out/label
            run([*flags,'-DGAUGUIN_REUSE340_ENABLED='+str(enabled),str(source/'src/gpu.cpp'),str(fixture),'-o',str(binary)],label+'-compile')
            stdout=run([str(binary)],label+'-run');assert 'PASS340 actual-Gpu-submit' in stdout
            results[label]=[json.loads(s.removeprefix('BENCH340 ')) for s in stdout.splitlines() if s.startswith('BENCH340 ')]
            assert len(results[label])==3
        comparisons=[]
        for old,new in zip(results['control'],results['candidate']):
            assert (old['unique'],old['uses'],old['wire_checksum'])==(new['unique'],new['uses'],new['wire_checksum'])
            assert new['capacity_growths_measured']==0 and new['comparisons']<old['comparisons']
            comparisons.append(dict(unique=new['unique'],uses=new['uses'],wire_identical=True,old_comparisons=old['comparisons'],new_comparisons=new['comparisons'],
                old_BO_prepare_median_ns=old['BO_prepare_median_ns'],new_BO_prepare_median_ns=new['BO_prepare_median_ns'],
                observed_host_BO_prepare_ratio=old['BO_prepare_median_ns']/new['BO_prepare_median_ns']))
        r.update(state='0340-actual-Gpu-submit-ordered-reuse-host-benchmark-passed',host=platform.platform(),results=results,comparisons=comparisons,
            actual_production_Gpu_submit_compiled=True,recording_transport_only=True,real_IO_measured=False,
            command_index0_and_flags_and_error_fence_and_reentrant_pointer_lifetime_verified=True,
            all_BO_maps_and_handles_closed=True,physical_FPS_qualified=False,
            scope='Host CPU microbenchmark on synthetic duplicate-heavy BO lists; instrumentation is equal. No phone/driver/GPU timing or isolated device speedup claim.')
    except BaseException as e:r.update(state='0340-host-submit-benchmark-failed',error=repr(e));raise
    finally:r['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('steps','input_pins','results')},indent=2))


if __name__=='__main__':main()
