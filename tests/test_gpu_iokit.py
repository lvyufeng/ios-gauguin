#!/usr/bin/env python3
"""Run the actual GPU IOUserClient with typed IOKit/physical-memory seams."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
C=Path(os.environ.get('GPU_USER_TREE',str(R/'.deps-cache/p0-20261105/source175-codex')))
F=R/'tests/fixtures/gpu-user/iokit_host.cpp';D=C/'bsd/dev'
S=C/'iokit/Kernel/arm/GauguinGPU.cpp';H=C/'iokit/Kernel/arm/SweetSurface.h'
files=[Path(__file__),F,S,H,D/'gauguin_gpu_runtime.c',D/'gauguin_gpu_runtime.h']
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
def body(p):return re.sub(r'^#include .*\n','',p.read_text(),flags=re.M)
fixture=F.read_text();assert fixture.count('@SOURCE@')==fixture.count('@SURFACE_HEADER@')==1
fixture=fixture.replace('@SURFACE_HEADER@',body(H)).replace('@SOURCE@',body(S))
fixture=fixture.replace('__asm__ volatile("dsb sy" ::: "memory")','__atomic_thread_fence(__ATOMIC_SEQ_CST)')
with tempfile.TemporaryDirectory(prefix='gpu-iokit-') as tmp:
    tmp=Path(tmp);unit=tmp/'test.cpp';unit.write_text(fixture)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    common=['-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D)]
    subprocess.run(['clang','-std=c11',*common,'-c',str(D/'gauguin_gpu_runtime.c'),'-o',str(tmp/'core.o')],env=env,check=True)
    subprocess.run(['clang++','-std=c++17',*common,str(unit),str(tmp/'core.o'),'-o',str(tmp/'test')],env=env,check=True)
    subprocess.run([str(tmp/'test'),'submit'],env=env,check=True)
    subprocess.run([str(tmp/'test'),'sync'],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'inputs changed'
