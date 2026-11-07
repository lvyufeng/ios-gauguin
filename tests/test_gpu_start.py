#!/usr/bin/env python3
"""Actual native MMU/GPU OOB/core engine; faults, stale ACK and callback stops."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent;D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source148-codex')))/'bsd/dev'
F=R/'tests/fixtures/gpu-start/start_host.c';sources=[D/(n+'.c') for n in ['gauguin_gpu_start','gauguin_gpu_memory','gauguin_gmu_memory']]
inputs=[F,*sources,*[p.with_suffix('.h') for p in sources],D/'gauguin_gpu_smmu.h',D/'gauguin_gmu_smmu.h'];pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-start-') as tmp:
 b=Path(tmp)/'test';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-I'+str(D),*map(str,sources),str(F),'-o',str(b)],env=env,check=True);subprocess.run([str(b)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
