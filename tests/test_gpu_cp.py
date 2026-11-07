#!/usr/bin/env python3
"""Actual first A619 CP engine: guarded memory/MMIO/firmware submission model."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source153-codex')))/'bsd/dev'
F=R/'tests/fixtures/gpu-cp/cp_host.c';names=['gauguin_gpu_cp','gauguin_gpu_memory','gauguin_gmu_memory']
inputs=[F,*[D/(n+suffix) for n in names for suffix in ['.c','.h']],*[D/(n+'.h') for n in ['gauguin_gpu_core','gauguin_gpu_start','gauguin_gpu_smmu','gauguin_gmu_smmu']]]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-cp-') as tmp:
 b=Path(tmp)/'test';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-I'+str(D),*[str(D/(n+'.c')) for n in names],str(F),'-o',str(b)],env=env,check=True);subprocess.run([str(b)],env=env,check=True)
 if os.environ.get('GPU_CP_TRACE_DIR'):
  out=Path(os.environ['GPU_CP_TRACE_DIR']);out.mkdir(exist_ok=False)
  for scenario in range(5):
   with (out/('scenario'+str(scenario)+'.log')).open('x') as f:subprocess.run([str(b),str(scenario)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
