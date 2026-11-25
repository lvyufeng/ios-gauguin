#!/usr/bin/env python3
"""Keep hardware paths unchanged while exercising the expanded cached selector sampler."""
from pathlib import Path
import argparse,importlib.util,os,subprocess,tempfile

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--reference',type=Path,required=True);a=ap.parse_args();r=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('sampler',r/'tests/test_gpu_api_perf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    path=Path('iokit/Kernel/arm/GauguinGPU.cpp');new=(a.source/path).read_text();old=(a.reference/path).read_text()
    for sig in ['IOReturn GauguinGPUUserClient::submit(', 'IOReturn GauguinGPUUserClient::surface(',
                'IOReturn GauguinGPUUserClient::add(', 'bool GauguinGPUUserClient::drop(',
                'IOReturn GauguinGPUUserClient::clientMemoryForType(', 'extern "C" bool GauguinGPUHeartbeat(']:
        assert m.extract(new,sig)==m.extract(old,sig),sig
    for name in ['gauguin_gmu_board.c','gauguin_gpu_runtime.c','gauguin_gpu_runtime.h']:
        assert(a.source/'bsd/dev'/name).read_bytes()==(a.reference/'bsd/dev'/name).read_bytes(),name
    for sig in ['IOReturn GauguinGPUUserClient::clientClose(', 'IOReturn GauguinGPUUserClient::externalMethod(']:
        body=m.extract(new,sig)
        assert body.index('IOLockLock(gLock)')<body.index('gapi_begin(')<body.index('gapi_end(')<body.index('IOLockUnlock(gLock)')
    helper=new[new.index('/* All mutable samples'):new.index('\nstatic bool physicalPage(')]
    with tempfile.TemporaryDirectory(prefix='metal-bootstrap-profile-')as d:
        d=Path(d);unit=d/'sampler.cpp';unit.write_text(m.HOST.replace('@HELPER@',helper))
        env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
        subprocess.run(['xcrun','clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-pedantic',
                        '-fsanitize=address,undefined',str(unit),'-o',str(d/'sampler')],env=env,check=True)
        subprocess.run([str(d/'sampler')],env=env,check=True)
    print('unchanged hardware/surface/VM bodies and expanded cached profile verified against242; host only')

if __name__=='__main__':main()
