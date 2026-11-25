#!/usr/bin/env python3
"""Actual GMU table/HFI byte emitters: independent walks and sanitizer checks."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source121-codex')))/'bsd/dev'
source=D/'gauguin_gmu_memory.c';header=D/'gauguin_gmu_memory.h'
fixture=R/'tests/fixtures/gmu-memory/memory_host.c'
inputs=[source,header,fixture]
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-memory-') as temporary:
    binary=Path(temporary)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),
        str(source),str(fixture),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
