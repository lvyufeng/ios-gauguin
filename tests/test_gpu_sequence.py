#!/usr/bin/env python3
"""Actual bounded three-job native core under a hostile model, no GPU emulation."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source172-codex')))/'bsd/dev'
S=Path(os.environ.get('GPU_SEQUENCE_SOURCE',str(D)))
F=R/'tests/fixtures/gpu-sequence/sequence_host.c'
names=['gauguin_gpu_draw','gauguin_gpu_unsecure','gauguin_gpu_cp','gauguin_gpu_data','gauguin_gpu_memory','gauguin_gmu_memory']
inputs=[Path(__file__),F,F.with_name('native_words.h'),F.with_name('native_provenance.json'),S/'gauguin_gpu_sequence.c',S/'gauguin_gpu_sequence.h',S/'gauguin_gpu_sequence_native.h',D/'gauguin_gpu_draw_native.h',*[D/(n+s) for n in names for s in ('.c','.h')]]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-sequence-') as tmp:
    binary=Path(tmp)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(S),'-I'+str(D),str(S/'gauguin_gpu_sequence.c'),*[str(D/(n+'.c')) for n in names],str(F),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
    if os.environ.get('GPU_SEQUENCE_TRACE_DIR'):
        out=Path(os.environ['GPU_SEQUENCE_TRACE_DIR']);out.mkdir(exist_ok=False)
        for i in range(5):
            with (out/('scenario'+str(i)+'.log')).open('x') as f:subprocess.run([str(binary),str(i)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
