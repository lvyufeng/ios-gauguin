#!/usr/bin/env python3
"""Actual GPU global-memory/page-table/CP init constructors with sanitizers."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source144-v2-codex')))/'bsd/dev'
F=R/'tests/fixtures/gpu-memory/memory_host.c';names=['gauguin_gpu_memory','gauguin_gmu_memory']
inputs=[F,*[D/(n+suffix) for n in names for suffix in ['.c','.h']]]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-memory-') as tmp:
 b=Path(tmp)/'test';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-I'+str(D),*[str(D/(n+'.c')) for n in names],str(F),'-o',str(b)],env=env,check=True);subprocess.run([str(b)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
