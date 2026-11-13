#!/usr/bin/env python3
"""Compile the actual user-client escrow methods with CPU-only IOKit seams."""

import argparse
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path


METHODS=('reapClosed','finishPending')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def extract(source,name):
    marker='GauguinGPUUserClient::'+name+'('
    assert source.count(marker)==1,name
    start=source.rfind('\n',0,source.index(marker))+1
    opening=source.index('{',source.index(marker))
    depth=0
    for at in range(opening,len(source)):
        if source[at]=='{':depth+=1
        elif source[at]=='}':
            depth-=1
            if not depth:return source[start:at+1]
    raise ValueError('unclosed user-client method '+name)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    default_root=Path(os.environ['XNU_SOURCE']) if 'XNU_SOURCE' in os.environ else None
    ap.add_argument('--candidate-root',type=Path,default=default_root)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    if args.candidate_root is None:ap.error('--candidate-root or XNU_SOURCE is required')
    if args.out is None:args.out=repo/'research/tmp'/('gpu-async-escrow-'+uuid.uuid4().hex)
    source=args.candidate_root.resolve()/'iokit/Kernel/arm/GauguinGPU.cpp'
    fixture=repo/'tests/fixtures/gpu-user/async_escrow_host.cpp'
    out=args.out.resolve()
    assert out.is_relative_to(repo/'research/tmp') and not out.exists()
    inputs=[Path(__file__).resolve(),source,fixture]
    pins={str(p):sha(p) for p in inputs}
    cpp=source.read_text()
    bodies='\n\n'.join(extract(cpp,name) for name in METHODS)
    helpers=cpp[cpp.index('/* All mutable samples'):cpp.index('\nstatic bool physicalPage(')]
    model=fixture.read_text()
    assert model.count('/* INSERT_REAL_ESCROW_METHODS */')==1
    out.mkdir(parents=True)
    composite=out/'escrow-host.cpp'
    composite.write_text(model.replace('/* INSERT_REAL_ESCROW_METHODS */',bodies)
                        .replace('/* INSERT_REAL_WAIT_HELPERS */',helpers))
    binary=out/'escrow-host'
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
             UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    compile=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-g',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',
             str(composite),'-o',str(binary)]
    with (out/'compile.log').open('x') as stream:
        subprocess.run(compile,stdout=stream,stderr=subprocess.STDOUT,check=True,env=env)
    with (out/'run.log').open('x') as stream:
        subprocess.run([str(binary)],stdout=stream,stderr=subprocess.STDOUT,
                       check=True,env=env,timeout=30)
    log=(out/'run.log').read_text()
    assert 'real escrow completion/timeout/fault/deferred-close assertions' in log
    assert all(sha(Path(path))==digest for path,digest in pins.items())
    result={'state':'passed-actual-user-client-escrow-CPU-host',
            'input_pins':pins,'inputs_unchanged':True,
            'composite_sha256':sha(composite),'run_log_sha256':sha(out/'run.log'),
            'sanitizer':'address,undefined','device_commands':0,
            'hardware_qualified':False,
            'scope':'actual finishPending/reapClosed method bodies with CPU-only board and IOKit seams'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
