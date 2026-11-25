#!/usr/bin/env python3
"""Exercise the real one-in-flight runtime with typed CPU-only seams."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import uuid

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    default_root=Path(os.environ['XNU_SOURCE']) if 'XNU_SOURCE' in os.environ else None
    ap.add_argument('--candidate-root',type=Path,default=default_root)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    if args.candidate_root is None:ap.error('--candidate-root or XNU_SOURCE is required')
    if args.out is None:args.out=repo/'research/tmp'/('gpu-issued-runtime-'+uuid.uuid4().hex)
    candidate=args.candidate_root.resolve()
    out=args.out.resolve()
    assert out.is_relative_to(repo/'research/tmp') and not out.exists()
    dev=candidate/'bsd/dev'
    baseline=repo/'tests/fixtures/gpu-user/runtime_host.c'
    extra=repo/'tests/fixtures/gpu-user/issued_fence_host.c'
    source=dev/'gauguin_gpu_runtime.c'
    header=dev/'gauguin_gpu_runtime.h'
    inputs=[Path(__file__).resolve(),baseline,extra,source,header]
    pins={str(path):sha(path) for path in inputs}
    text=baseline.read_text()
    assert text.count('int main(void)')==1
    body=text.replace('int main(void)','static int baseline_main(void)',1)+extra.read_text()
    out.mkdir(parents=True)
    unit=out/'issued-host.c'
    unit.write_text(body)
    binary=out/'issued-host'
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
             UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    compile=['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',
             '-I',str(dev),str(unit),str(source),'-o',str(binary)]
    with (out/'compile.log').open('x') as stream:
        subprocess.run(compile,stdout=stream,stderr=subprocess.STDOUT,check=True,env=env)
    with (out/'run.log').open('x') as stream:
        subprocess.run([str(binary)],stdout=stream,stderr=subprocess.STDOUT,
                       check=True,env=env,timeout=30)
    log=(out/'run.log').read_text()
    assert log.count('PASS: ')==2 and 'issued/pending/completed/deadline/wrap' in log
    assert all(sha(Path(name))==digest for name,digest in pins.items())
    result=dict(state='passed-actual-runtime-issued-fence-host',
                input_pins=pins,inputs_unchanged=True,
                composite_source_sha256=sha(unit),run_log_sha256=sha(out/'run.log'),
                sanitizer='address,undefined',device_commands=0,
                hardware_qualified=False,
                scope='real C runtime and typed ring/memory callbacks; no IB or GPU emulation')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':main()
