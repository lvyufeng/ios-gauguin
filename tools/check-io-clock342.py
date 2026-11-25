#!/usr/bin/env python3
"""ASan/UBSan IO CPU bounds, busy/sleep, failure and thread isolation tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/io-path-342'
CASES=['bounds','failures','busy','sleep','threads','partitions']


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v3/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());source=Path(prepared['sources']['candidate'])
    fixture=WORK/'tests/fixtures/program_clock342.cpp';pins={str(p.resolve()):sha(p) for p in (Path(__file__),fixture,WORK/'tests/fixtures/iokit_accounting342.cpp',a.prepared)}
    for name,h in prepared['source_pins']['candidate'].items():
        p=source/name;assert sha(p)==h;pins[str(p)]=h
    out.mkdir();r=dict(state='0342-scratch-host-running',steps=[],input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=90,env={**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        r['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)));save()
        assert p.returncode==0,(name,p.stderr[-2400:]);return p.stdout
    flags=['clang++','-std=c++17','-O2','-gline-tables-only','-fno-omit-frame-pointer','-pthread','-Wall','-Wextra','-Werror',
        '-fsanitize=address,undefined','-fno-sanitize-recover=all','-DHAKIOS_METAL_TARGET_A619','-I'+str(source/'include'),'-I'+str(source/'src')]
    try:
        run([*flags,str(fixture),'-o',str(out/'clock342')],'compile')
        for case in CASES:assert ('PASS342 '+case).encode() in run([str(out/'clock342'),case],case)
        run([*flags,str(WORK/'tests/fixtures/iokit_accounting342.cpp'),'-framework','IOKit','-framework','CoreFoundation','-o',str(out/'iokit342')],'compile-iokit-wrapper')
        assert b'PASS342 iokit-wrapper' in run([str(out/'iokit342')],'iokit-wrapper')
        r.update(state='0342-thread-CPU-bracketing-and-busy-sleep-host-passed',scenarios=len(CASES)+1,actual_production_IO_wrapper_tested=True,sanitizers=['address','undefined'],physical_FPS_qualified=False)
    except BaseException as e:r.update(state='0342-scratch-host-failed',error=repr(e));raise
    finally:r['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('steps','input_pins')},indent=2))


if __name__=='__main__':main()
