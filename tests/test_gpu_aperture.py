#!/usr/bin/env python3
"""Actual fixed four-scalar GPU aperture engine, bounds and continuations."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent;D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source145-codex')))/'bsd/dev'
F=R/'tests/fixtures/gpu-aperture/aperture_host.c';S=D/'gauguin_gpu_aperture.c';inputs=[F,S,S.with_suffix('.h')];pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-aperture-') as tmp:
 b=Path(tmp)/'test';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-I'+str(D),str(S),str(F),'-o',str(b)],env=env,check=True);subprocess.run([str(b)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
