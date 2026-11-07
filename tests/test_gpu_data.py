#!/usr/bin/env python3
"""Actual optional GPU user-RW page constructors, sanitizers and unchanged bootstrap."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source163-codex')))/'bsd/dev'
S=Path(os.environ.get('GPU_DATA_SOURCE',str(D)))
F=R/'tests/fixtures/gpu-data/data_host.c'
inputs=[Path(__file__),F,*[S/('gauguin_gpu_data'+s) for s in ('.c','.h')],*[D/(n+s) for n in ('gauguin_gpu_memory','gauguin_gmu_memory') for s in ('.c','.h')]]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-data-') as tmp:
    b=Path(tmp)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-I'+str(S),'-I'+str(D),str(S/'gauguin_gpu_data.c'),str(D/'gauguin_gpu_memory.c'),str(D/'gauguin_gmu_memory.c'),str(F),'-o',str(b)],env=env,check=True)
    subprocess.run([str(b)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
