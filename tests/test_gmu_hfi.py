#!/usr/bin/env python3
"""Actual HFI transport: native layouts, wrap, ordering and fault injection."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source121-codex')))/'bsd/dev'
sources=[D/'gauguin_gmu_hfi.c',D/'gauguin_gmu_memory.c']
fixture=R/'tests/fixtures/gmu-hfi/hfi_host.c'
inputs=sources+[D/'gauguin_gmu_hfi.h',D/'gauguin_gmu_memory.h',fixture]
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-hfi-') as temporary:
    binary=Path(temporary)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),
        *map(str,sources),str(fixture),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
