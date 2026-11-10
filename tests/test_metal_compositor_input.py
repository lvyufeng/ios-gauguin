#!/usr/bin/env python3
"""Run actual root handoff and compositor task import with typed host IOKit."""
from pathlib import Path
import argparse,hashlib,os,re,subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--old-driver',action='store_true');ap.add_argument('--trace-capture',action='store_true');a=ap.parse_args()
    repo=Path(__file__).resolve().parents[1];a.out.mkdir(parents=True,exist_ok=False)
    gpu=a.source/'iokit/Kernel/arm/GauguinGPU.cpp';d=a.source/'bsd/dev'
    fixtures=repo/'tests/fixtures/gpu-user'
    paths=[Path(__file__),fixtures/'iokit_host.cpp',fixtures/'compositor_input_main.inc',
           gpu,gpu.parent/'SweetSurface.h',gpu.parent/'SweetSurface.cpp',
           gpu.parent/'SweetMetalBootstrap.h',d/'gauguin_gpu_runtime.c',d/'gauguin_gpu_runtime.h']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={p:sha(p)for p in paths}
    strip=lambda p:re.sub(r'^#include .*\n','',p.read_text(),flags=re.M)
    fixture=(fixtures/'iokit_host.cpp').read_text().split('int main(int argc,char **argv)')[0]
    fixture=fixture.replace('@SURFACE_HEADER@',strip(gpu.parent/'SweetSurface.h'))
    method=re.findall(r'uintptr_t\nSweetSurface::kernelAddress\(\)\n\{[\s\S]*?\n\}',(gpu.parent/'SweetSurface.cpp').read_text())
    assert len(method)==1
    fixture=fixture.replace('@SURFACE_KERNEL_ADDRESS@',method[0])
    seam='''
static bool bootstrap_host_mode;
[[maybe_unused]] static bool sweet_metal_desktop_enabled(){return bootstrap_host_mode;}
[[maybe_unused]] static bool PE_parse_boot_argn(const char *,void *,int){return false;}
'''
    fixture=fixture.replace('@SOURCE@',strip(gpu.parent/'SweetMetalBootstrap.h')+seam+strip(gpu))
    fixture=fixture.replace('__asm__ volatile("dsb sy" ::: "memory")','__atomic_thread_fence(__ATOMIC_SEQ_CST)')
    body=(fixtures/'compositor_input_main.inc').read_text()
    if a.trace_capture:
        body=body.replace('int main(','int ownership_main(')
        body+='''
int main(int argc,char **argv) {
    int rc=ownership_main(argc,argv);if(rc)return rc;
    unsigned started=0,ended=0,surfaces=0;
    std::map<uint64_t,gut_event> begins;
    for(const auto &e:host_ui_events) {
        if(e.kind==GUT_SUBMIT_BEGIN){assert(e.id&&e.a&&e.b);++started;begins[e.id]=e;}
        if(e.kind==GUT_SURFACE){assert(begins.count(e.id)&&e.a&&(e.flags==1||e.flags==2||e.flags==3));++surfaces;}
        if(e.kind==GUT_SUBMIT_END){assert(begins.count(e.id));++ended;if(!e.flags)assert(e.b&&e.c);}
    }
    assert(started==submit_calls&&ended==started);
    if(!strcmp(argv[1],"desktop"))assert(surfaces==30);
    printf("PASS actual GPU trace boundaries: %u submits, %u surface edges; hardware mocked\\n",started,surfaces);
    return 0;
}
'''
    unit=a.out/'input.cpp';unit.write_text(fixture+body)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(d)]
    def run(args,name,expected=0):
        with(a.out/(name+'.log')).open('x')as stream:
            p=subprocess.run(list(map(str,args)),env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
        assert p.returncode==expected,(name,p.returncode,expected)
    run(['xcrun','clang','-std=c11',*flags,'-c',d/'gauguin_gpu_runtime.c','-o',a.out/'runtime.o'],'compile-runtime')
    run(['xcrun','clang++','-std=c++17',*flags,'-DGAUGUIN_GPU_PILOT_HOST=1',
         *(['-DGUT_GPU_CAPTURE=1']if a.trace_capture else[]),
         *(['-DGAUGUIN_DESKTOP_INPUT_OLD_DRIVER=1']if a.old_driver else[]),unit,a.out/'runtime.o','-o',a.out/'input'],'compile-driver')
    if a.old_driver:run([a.out/'input','desktop'],'old-driver-functional-red',42)
    else:
        for scenario in ['desktop','legacy','unarmed','dma-fault']:run([a.out/'input',scenario],scenario)
    assert all(sha(p)==h for p,h in pins.items()),'inputs changed'
    print('actual compositor task-input host cases passed; no physical GPU result')
if __name__=='__main__':main()
