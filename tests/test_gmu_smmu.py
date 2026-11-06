#!/usr/bin/env python3
"""Actual SMMU transaction: independent ATOS walks and failure injection."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source126-codex')))/'bsd/dev'
sources=[D/'gauguin_gmu_smmu.c',D/'gauguin_gmu_memory.c']
fixture=R/'tests/fixtures/gmu-smmu/smmu_host.c'
inputs=sources+[D/'gauguin_gmu_smmu.h',D/'gauguin_gmu_memory.h',fixture]
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-smmu-') as temporary:
    binary=Path(temporary)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),
        *map(str,sources),str(fixture),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
