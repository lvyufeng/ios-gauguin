#!/usr/bin/env python3
"""Run real readiness dispatcher, cleanup and ownership against typed IOKit seams."""
from pathlib import Path
import argparse,os,re,subprocess

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--old-driver',action='store_true');a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];a.out.mkdir(parents=True,exist_ok=False)
    gpu=a.source/'iokit/Kernel/arm/GauguinGPU.cpp';d=a.source/'bsd/dev'
    strip=lambda p:re.sub(r'^#include .*\n','',p.read_text(),flags=re.M)
    fixture=(repo/'tests/fixtures/gpu-user/iokit_host.cpp').read_text()
    fixture=fixture[:fixture.index('int main(int argc,char **argv)')]
    fixture=fixture.replace('@SURFACE_HEADER@',strip(gpu.parent/'SweetSurface.h'))
    surface=(gpu.parent/'SweetSurface.cpp').read_text()
    match=re.findall(r'uintptr_t\nSweetSurface::kernelAddress\(\)\n\{[\s\S]*?\n\}',surface);assert len(match)==1
    fixture=fixture.replace('@SURFACE_KERNEL_ADDRESS@',match[0])
    wire='#include \"'+str(repo/'graphics/hakios-metal-ca/bootstrap/gauguin_metal_bootstrap.h')+'\"\n'
    seam='''\nstatic bool bootstrap_host_mode;\n[[maybe_unused]] static bool PE_parse_boot_argn(const char *name,void *value,int bytes){
if(strcmp(name,"gmt")||bytes!=4)return false;*(uint32_t *)value=bootstrap_host_mode?2:0;return bootstrap_host_mode;\n}\n'''
    fixture=fixture.replace('@SOURCE@',wire+seam+strip(gpu))
    fixture=fixture.replace('__asm__ volatile("dsb sy" ::: "memory")','__atomic_thread_fence(__ATOMIC_SEQ_CST)')
    fixture+=(repo/'tests/fixtures/gpu-user/bootstrap_main.inc').read_text();unit=a.out/'bootstrap.cpp';unit.write_text(fixture)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    common=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(d)]
    def run(args,name,expect=0):
        with(a.out/(name+'.log')).open('x')as f:rc=subprocess.run(list(map(str,args)),env=env,stdout=f,stderr=subprocess.STDOUT).returncode
        assert rc==expect,(name,rc,expect)
    run(['xcrun','clang','-std=c11',*common,'-c',d/'gauguin_gpu_runtime.c','-o',a.out/'core.o'],'compile-core')
    run(['xcrun','clang++','-std=c++17',*common,'-DGAUGUIN_GPU_PILOT_HOST=1',*(['-DGAUGUIN_BOOTSTRAP_OLD_DRIVER=1']if a.old_driver else[]),unit,a.out/'core.o','-o',a.out/'bootstrap'],'compile-driver')
    if a.old_driver:run([a.out/'bootstrap','good'],'old-driver-functional-red',42)
    else:
        for name in ['good','duplicate','after-arm','fault']:run([a.out/'bootstrap',name],name)
    print('actual readiness driver host cases passed; no physical GPU claim')

if __name__=='__main__':main()
