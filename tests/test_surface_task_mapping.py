#!/usr/bin/env python3
"""Run production task-map policy and XNU's static fast path with real VM reuse.

The VM fallback is a typed host model using shared file mappings, not XNU VM.
The two decision bodies are extracted unchanged from the selected source tree.
"""
from pathlib import Path
import hashlib
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE = Path(os.environ['XNU_SOURCE'])

UNIT = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
using task_t = uintptr_t;
using mach_vm_address_t = uintptr_t;
using mach_vm_size_t = size_t;
constexpr int kIOReturnSuccess=0;
@OPTIONS@
static uintptr_t get_task_map(task_t t){return t;}
static unsigned checks, liveMaps;
static void check(bool good){++checks;assert(good);}
struct IOMemoryMap {
    uintptr_t fAddress=0, fAddressTask=0, fAddressMap=0;
    unsigned fOptions=0;
    void *allocation=nullptr;size_t length=0;
    IOMemoryMap(){++liveMaps;}
    uintptr_t getVirtualAddress(){return fAddress;}
    void release(){if(allocation)check(munmap(allocation,length)==0);--liveMaps;delete this;}
};
struct Memory {
    task_t _task=42;
    unsigned _rangesCount=1;
    int fd=-1;
    size_t fileOffset=0,length=0;
    uintptr_t original=0;
    bool failMap=false;
    int doMap(IOMemoryMap *mapping,unsigned options){
        size_t offset=0,length=this->length;
        uintptr_t range0Addr=original;size_t range0Len=length;
        @STATIC_FAST_PATH@
        const size_t page=static_cast<size_t>(getpagesize());
        const size_t bias=fileOffset%page;
        const size_t bytes=(bias+length+page-1)&~(page-1);
        int protection=PROT_READ|((options&kIOMapReadOnly)?0:PROT_WRITE);
        void *p=mmap(nullptr,bytes,protection,MAP_SHARED,fd,static_cast<off_t>(fileOffset-bias));
        check(p!=MAP_FAILED);
        mapping->allocation=p;mapping->length=bytes;mapping->fAddress=reinterpret_cast<uintptr_t>(p)+bias;
        return kIOReturnSuccess;
    }
    IOMemoryMap *createMappingInTask(task_t task,uint64_t address,unsigned options){
        check(!address);
        if(failMap)return nullptr;
        auto *m=new IOMemoryMap;
        m->fAddressTask=task;m->fAddressMap=get_task_map(task);m->fOptions=options;
        check(doMap(m,options)==0);return m;
    }
};
struct SweetSurface {
    Memory *memory=nullptr;unsigned mapCache=0;bool readOnly=false;
    IOMemoryMap *mapPixelsInTask(task_t);
};
@SURFACE_METHOD@
int main(int argc,char **argv){
    check(argc==2);const bool expectIndependent=std::strcmp(argv[1],"independent")==0;
    const size_t biases[]={64,4032,16448,0,8192};
    const size_t sizes[]={8205,12301,20493,36877,69645};
    for(unsigned i=0;i<5;++i){
        const size_t page=static_cast<size_t>(getpagesize());
        size_t total=(biases[i]+sizes[i]+page-1)&~(page-1);
        char path[]="/tmp/surface-task-map-XXXXXX";int fd=mkstemp(path);
        check(fd>=0);check(unlink(path)==0);check(ftruncate(fd,static_cast<off_t>(total))==0);
        auto *original=static_cast<uint8_t *>(mmap(nullptr,total,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0));
        check(original!=MAP_FAILED);
        for(size_t j=0;j<total;++j)original[j]=static_cast<uint8_t>(j*29+i*17+154);
        std::vector<uint8_t> snapshot(original+biases[i],original+biases[i]+sizes[i]);
        check(mprotect(original,total,PROT_READ)==0);
        Memory memory;memory.fd=fd;memory.fileOffset=biases[i];memory.length=sizes[i];
        memory.original=reinterpret_cast<uintptr_t>(original)+biases[i];
        SweetSurface s;s.memory=&memory;s.readOnly=true;s.mapCache=kIOMapWriteCombineCache;
        auto *view=s.mapPixelsInTask(42);check(view!=nullptr);
        check((view->fOptions&kIOMapReadOnly)!=0);
        check((view->fOptions&kIOMapCacheMask)==kIOMapWriteCombineCache);
        check(!std::memcmp(reinterpret_cast<void *>(view->getVirtualAddress()),snapshot.data(),sizes[i]));
        // The independent descriptor/kernel view survives address reuse in both policies.
        auto *retained=memory.createMappingInTask(84,0,kIOMapAnywhere|kIOMapReadOnly);
        check(retained&&retained->getVirtualAddress()!=memory.original);
        check(munmap(original,total)==0);
        void *reuse=mmap(original,total,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON|MAP_FIXED,-1,0);
        check(reuse==original);std::memset(reuse,0xcd,total);
        check(mprotect(reuse,total,PROT_READ)==0);
        const bool same=std::memcmp(reinterpret_cast<void *>(view->getVirtualAddress()),snapshot.data(),sizes[i])==0;
        std::printf("task-map case=%u original-reused=1 independent=%u source-preserved=%u\n",i,(view->fOptions&kIOMapStatic)==0,same);
        std::fflush(stdout);
        check(same==expectIndependent);
        check(((view->fOptions&kIOMapStatic)==0)==expectIndependent);
        check((view->getVirtualAddress()!=memory.original)==expectIndependent);
        check(!std::memcmp(reinterpret_cast<void *>(retained->getVirtualAddress()),snapshot.data(),sizes[i]));
        view->release();retained->release();check(liveMaps==0);
        check(munmap(reuse,total)==0);check(close(fd)==0);
    }
    Memory memory;memory.failMap=true;SweetSurface s;s.memory=&memory;s.readOnly=true;
    check(s.mapPixelsInTask(42)==nullptr);check(liveMaps==0);
    s.memory=nullptr;check(s.mapPixelsInTask(42)==nullptr);
    // Mutable same-task policy remains the pre-existing static view.
    memory.failMap=false;memory.original=0x12340000;memory.length=4096;
    s.memory=&memory;s.readOnly=false;s.mapCache=kIOMapWriteCombineCache;
    auto *mutableView=s.mapPixelsInTask(42);check(mutableView!=nullptr);
    check(mutableView->fAddress==memory.original);
    check(mutableView->fOptions==(kIOMapAnywhere|kIOMapStatic|kIOMapWriteCombineCache));
    mutableView->release();check(liveMaps==0);
    std::printf("task-map PASS checks=%u independent=%u all-five-layouts-real-VM-reuse=1\n",checks,expectIndependent);
}
'''


def main():
    paths = [Path(__file__), TREE/'iokit/Kernel/arm/SweetSurface.cpp',
             TREE/'iokit/Kernel/IOMemoryDescriptor.cpp', TREE/'iokit/IOKit/IOMapTypes.h']
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    source = paths[1].read_text()
    start = source.index('IOMemoryMap *\nSweetSurface::mapPixelsInTask(')
    method = source[start:source.index('\n}\n', start)+3]
    source = paths[2].read_text()
    start = source.index('\t// mapping source == dest?')
    fast = source[start:source.index('\n\tif (!_memRef)', start)]
    options = paths[3].read_text()
    names = ['Anywhere', 'ReadOnly', 'Unique', 'Static', 'GuardedMask', 'CacheMask', 'CacheShift']
    constants = []
    for name in names:
        match = re.search(r'kIOMap'+name+r'\s*=\s*(0x[0-9a-fA-F]+|[0-9]+)\s*,', options)
        assert match, name
        constants.append('constexpr unsigned kIOMap'+name+'='+match[1]+';')
    match = re.search(r'kIOWriteCombineCache\s*=\s*(0x[0-9a-fA-F]+|[0-9]+)\s*,', options)
    assert match
    constants.append('constexpr unsigned kIOMapWriteCombineCache='+match[1]+' << kIOMapCacheShift;')
    unit = UNIT.replace('@OPTIONS@', '\n'.join(constants)).replace('@STATIC_FAST_PATH@', fast).replace('@SURFACE_METHOD@', method)
    with tempfile.TemporaryDirectory(prefix='surface-task-map-') as temp:
        p = Path(temp); (p/'map.cpp').write_text(unit)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
        subprocess.run(['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(p/'map.cpp'), '-o', str(p/'map')], check=True, env=env)
        mode = os.environ.get('TASK_MAP_EXPECT', 'independent')
        subprocess.run([str(p/'map'), mode], check=True, env=env, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
