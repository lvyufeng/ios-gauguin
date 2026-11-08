#!/usr/bin/env python3
"""Focused actual runtime/wire checks. No full kernel or hardware claim."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('GPU_USER_SOURCE',str(R/'.deps-cache/p0-20261105/source177-codex/bsd/dev')))
F=R/'tests/fixtures/gpu-user/runtime_host.c'
files=[Path(__file__),F,D/'gauguin_gpu_runtime.c',D/'gauguin_gpu_runtime.h']
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with tempfile.TemporaryDirectory(prefix='gpu-user-') as tmp:
    binary=Path(tmp)/'runtime'
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),
        str(D/'gauguin_gpu_runtime.c'),str(F),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'inputs changed'
