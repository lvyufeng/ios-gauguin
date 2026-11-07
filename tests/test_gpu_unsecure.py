#!/usr/bin/env python3
"""Actual fixed post-ZAP A619 append engine under guarded memory/MMIO seams."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source158-codex')))/'bsd/dev'
U=Path(os.environ.get('GPU_UNSECURE_SOURCE',str(D)))
F=R/'tests/fixtures/gpu-unsecure/unsecure_host.c'
names=['gauguin_gpu_cp','gauguin_gpu_memory','gauguin_gmu_memory']
files=[F,U/'gauguin_gpu_unsecure.c',U/'gauguin_gpu_unsecure.h',*[D/(n+s) for n in names for s in ['.c','.h']],*[D/(n+'.h') for n in ['gauguin_gpu_core','gauguin_gpu_start','gauguin_gpu_smmu','gauguin_gmu_smmu']]]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files};env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-unsecure-') as tmp:
 b=Path(tmp)/'test';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-I'+str(U),'-I'+str(D),str(U/'gauguin_gpu_unsecure.c'),*[str(D/(n+'.c')) for n in names],str(F),'-o',str(b)],env=env,check=True);subprocess.run([str(b)],env=env,check=True)
 if os.environ.get('GPU_UNSECURE_TRACE_DIR'):
  out=Path(os.environ['GPU_UNSECURE_TRACE_DIR']);out.mkdir(exist_ok=False)
  for scenario in range(5):
   with (out/('scenario'+str(scenario)+'.log')).open('x') as f:subprocess.run([str(b),str(scenario)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
