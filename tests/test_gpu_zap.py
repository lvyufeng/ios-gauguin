#!/usr/bin/env python3
"""Actual fixed signed-load engine under typed owner/SCM/time seams."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source156-codex')))/'bsd/dev'
F=R/'tests/fixtures/gpu-zap/engine_host.c'
inputs=[Path(__file__),F,D/'gauguin_gpu_zap.c',D/'gauguin_gpu_zap.h']
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-zap-engine-') as tmp:
    binary=Path(tmp)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(F),str(D/'gauguin_gpu_zap.c'),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
