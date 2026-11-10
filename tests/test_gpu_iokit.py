#!/usr/bin/env python3
"""Run the actual GPU IOUserClient with typed IOKit/physical-memory seams."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
C=Path(os.environ.get('GPU_USER_TREE') or os.environ.get('XNU_SOURCE') or R/'.deps-cache/p0-20261105/source179-codex')
F=R/'tests/fixtures/gpu-user/iokit_host.cpp';D=C/'bsd/dev'
S=C/'iokit/Kernel/arm/GauguinGPU.cpp';H=C/'iokit/Kernel/arm/SweetSurface.h'
K=C/'iokit/Kernel/arm/SweetSurface.cpp'
files=[Path(__file__),F,S,H,K,D/'gauguin_gpu_runtime.c',D/'gauguin_gpu_runtime.h']
bootstrap=S.parent/'SweetMetalBootstrap.h'
if bootstrap.exists():files.append(bootstrap)
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
def body(p):return re.sub(r'^#include .*\n','',p.read_text(),flags=re.M)
fixture=F.read_text();assert fixture.count('@SOURCE@')==fixture.count('@SURFACE_HEADER@')==1
fixture=fixture.replace('@SURFACE_HEADER@',body(H))
extra=(body(bootstrap)+'\n[[maybe_unused]] static bool PE_parse_boot_argn(const char *,void *,int){return false;}\n[[maybe_unused]] static bool sweet_metal_desktop_enabled(){return false;}\n')if bootstrap.exists()else''
fixture=fixture.replace('@SOURCE@',extra+body(S))
method=re.findall(r'uintptr_t\nSweetSurface::kernelAddress\(\)\n\{[\s\S]*?\n\}',K.read_text())
assert len(method)==1 and fixture.count('@SURFACE_KERNEL_ADDRESS@')==1
fixture=fixture.replace('@SURFACE_KERNEL_ADDRESS@',method[0])
pilot='sweet_eagl_gpu_pilot_caller' in S.read_text()
fixture=fixture.replace('__asm__ volatile("dsb sy" ::: "memory")','__atomic_thread_fence(__ATOMIC_SEQ_CST)')
with tempfile.TemporaryDirectory(prefix='gpu-iokit-') as tmp:
    tmp=Path(tmp);unit=tmp/'test.cpp';unit.write_text(fixture)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    common=['-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D)]
    subprocess.run(['clang','-std=c11',*common,'-c',str(D/'gauguin_gpu_runtime.c'),'-o',str(tmp/'core.o')],env=env,check=True)
    subprocess.run(['clang++','-std=c++17',*common,*(['-DGAUGUIN_GPU_PILOT_HOST=1'] if pilot else []),str(unit),str(tmp/'core.o'),'-o',str(tmp/'test')],env=env,check=True)
    subprocess.run([str(tmp/'test'),'submit'],env=env,check=True)
    subprocess.run([str(tmp/'test'),'sync'],env=env,check=True)
    subprocess.run([str(tmp/'test'),'queues'],env=env,check=True)
    if 'importedPhysicalPage' in S.read_text():
        subprocess.run([str(tmp/'test'),'readonly'],env=env,check=True)
        subprocess.run([str(tmp/'test'),'readonly-fault'],env=env,check=True)
    if os.environ.get('GPU_USER_REQUIRE_SLOTS') or 'GGR_MAX_CLIENT_BUFFERS' in (D/'gauguin_gpu_runtime.h').read_text():
        subprocess.run([str(tmp/'test'),'slots'],env=env,check=True)
    if pilot:
        subprocess.run([str(tmp/'test'),'pilot'],env=env,check=True)
    if os.environ.get('GPU_USER_REQUIRE_LATE_MAP'):
        subprocess.run([str(tmp/'test'),'readonly-unmap'],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'inputs changed'
