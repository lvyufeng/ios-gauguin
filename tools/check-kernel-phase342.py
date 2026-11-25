#!/usr/bin/env python3
"""Bounded production kernel collector, identity and actual clock conversion."""
import hashlib,json,os,subprocess
from pathlib import Path
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/io-path-342'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=B/'kernel-phase-host-v5';assert not out.exists();out.mkdir()
    source=B/'kernel-prepared-v8/kernel-source/iokit/Kernel/arm';fixture=W/'tests/fixtures/kernel_phase342.cpp'
    inputs=[Path(__file__),fixture,source/'Kernel342.hpp',source/'Phase342.hpp'];pins={str(p):sha(p) for p in inputs}
    binary=out/'collector';args=['clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(source),str(fixture),'-o',str(binary)]
    cases=['enabled','disabled','foreign-thread','capacity','overflow','pending-dump','format','clock-scale','dump-byte-limit'];steps=[]
    for label,argv in [('compile',args)]+[(name,[str(binary),name]) for name in cases]:
        p=subprocess.run(argv,capture_output=True,timeout=90,env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1'))
        (out/(label+'.log')).write_bytes(p.stdout+p.stderr);steps.append(dict(label=label,exit=p.returncode));assert p.returncode==0,(label,p.stderr[-2000:])
    assert all(sha(p)==h for p,h in pins.items())
    result=dict(state='0342-production-kernel-collector-bounds-identity-units-passed',scenarios=len(cases),input_pins=pins,inputs_unchanged=True,steps=steps,device_commands=0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['state'])
if __name__=='__main__':main()
