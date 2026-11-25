#!/usr/bin/env python3
"""Compile actual board wrappers with the real runtime and CPU-only seams."""

import argparse
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path


NAMES = ('sweet_gpu_runtime_issue','sweet_gpu_runtime_poll','sweet_gpu_runtime_wait')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def extract(source,name):
    marker='enum ggr_error '+name+'('
    assert source.count(marker)==1, name
    start=source.index(marker)
    opening=source.index('{',start)
    depth=0
    for at in range(opening,len(source)):
        if source[at]=='{':depth+=1
        elif source[at]=='}':
            depth-=1
            if not depth:return source[start:at+1]
    raise ValueError('unclosed board function '+name)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    default_root=Path(os.environ['XNU_SOURCE']) if 'XNU_SOURCE' in os.environ else None
    ap.add_argument('--candidate-root',type=Path,default=default_root)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    if args.candidate_root is None:ap.error('--candidate-root or XNU_SOURCE is required')
    if args.out is None:args.out=repo/'research/tmp'/('gpu-issued-board-'+uuid.uuid4().hex)
    candidate=args.candidate_root.resolve()
    out=args.out.resolve()
    assert out.is_relative_to(repo/'research/tmp') and not out.exists()
    dev=candidate/'bsd/dev'
    baseline=repo/'tests/fixtures/gpu-user/runtime_host.c'
    fixture=repo/'tests/fixtures/gpu-user/issued_board_host.c'
    board=dev/'gauguin_gmu_board.c'
    runtime=dev/'gauguin_gpu_runtime.c'
    header=dev/'gauguin_gpu_runtime.h'
    inputs=[Path(__file__).resolve(),baseline,fixture,board,runtime,header]
    pins={str(p):sha(p) for p in inputs}
    source=board.read_text()
    functions='\n\n'.join(extract(source,name) for name in NAMES)
    text=baseline.read_text()
    assert text.count('int main(void)')==1
    text=text.replace('int main(void)','static int baseline_main(void)',1)
    model=fixture.read_text()
    assert model.count('/* INSERT_REAL_BOARD_FUNCTIONS */')==1
    out.mkdir(parents=True)
    composite=out/'board-host.c'
    composite.write_text(text+model.replace('/* INSERT_REAL_BOARD_FUNCTIONS */',functions))
    binary=out/'board-host'
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
             UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    compile=['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',
             '-I',str(dev),str(composite),str(runtime),'-o',str(binary)]
    with (out/'compile.log').open('x') as stream:
        subprocess.run(compile,stdout=stream,stderr=subprocess.STDOUT,check=True,env=env)
    with (out/'run.log').open('x') as stream:
        subprocess.run([str(binary)],stdout=stream,stderr=subprocess.STDOUT,
                       check=True,env=env,timeout=30)
    log=(out/'run.log').read_text()
    assert 'board issue/poll/wait/route/quarantine assertions' in log
    assert all(sha(Path(name))==digest for name,digest in pins.items())
    result={'state':'passed-actual-board-wrappers-CPU-host',
            'input_pins':pins,'inputs_unchanged':True,
            'composite_sha256':sha(composite),'run_log_sha256':sha(out/'run.log'),
            'sanitizer':'address,undefined','device_commands':0,
            'hardware_qualified':False,
            'scope':'actual board wrapper function bodies and actual runtime under typed CPU-only register/memory callbacks'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
