#!/usr/bin/env python3
"""Execute production RO wrap, maps, lock traps and GPU-import rejection."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TREE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source207-codex'))
SURFACE = TREE / 'iokit/Kernel/arm/SweetSurface.cpp'
HEADER = TREE / 'iokit/Kernel/arm/SweetSurface.h'
GPU = TREE / 'iokit/Kernel/arm/GauguinGPU.cpp'
FIXTURE = ROOT / 'tests/fixtures/surface_wrap_host.cpp'


def change(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new, 1)


EXTRA = r'''
static unsigned seedCalls,seedBumps,gpuAdds;
static bool failSeed;
static SweetSurface *sweet_surface_held(int *,void *,uint32_t id){
    if(!table||table->id!=id)return nullptr;
    table->retain();return table;
}
static SweetSurface *sweet_surface_copy(uint32_t id){return sweet_surface_held(nullptr,nullptr,id);}
static IOReturn sweet_surface_seed_out(SweetSurface *,void *,bool bump){
    ++seedCalls;seedBumps+=bump;return failSeed?kIOReturnVMError:kIOReturnSuccess;
}
struct gpu_buffer {IOMemoryDescriptor *memory=nullptr;SweetSurface *surface=nullptr;uint32_t handle=0;};
struct GauguinGPUUserClient {
    gpu_buffer fBuffers[GGR_MAX_CLIENT_BUFFERS];
    IOReturn surface(struct ggr_surface *);
    IOReturn add(IOMemoryDescriptor *m,SweetSurface *s,uint64_t n,uint32_t flags,uint32_t *handle){
        assert(m==s->memory&&n==s->allocSize&&!flags);++gpuAdds;*handle=77;return 0;
    }
};
'''

CASES = r'''
    // Protection failure alone permits ONE fresh read-only descriptor.
    readOnlyInput=true;check(run(good)==0);
    check(table->readOnly&&table->memoryPrepared&&table->memory->direction==kIODirectionOut);
    check(allocated==2&&prepared==2&&completed==0&&activeDescriptors==2);
    check(descriptorCount==2&&descriptorFlags[0]==(kIODirectionInOut|kIOMemoryThreadSafe));
    check(descriptorFlags[1]==(kIODirectionOut|kIOMemoryThreadSafe));
    check(sweet_surface_wired==16384&&!std::memcmp(original,pixels,sizeof(pixels)));
    check(table->kernelAddress()==0x12340000&&lastCache==kIOMapReadOnly);
    auto *taskMap=table->mapPixelsInTask(42);
    check(taskMap&&lastTask==42&&lastCache==(kIOMapAnywhere|kIOMapReadOnly));
    taskMap->release();taskMap=table->mapPixelsInTask(84);
    check(taskMap&&lastTask==84&&lastCache==(kIOMapAnywhere|kIOMapReadOnly));taskMap->release();
    void *id=reinterpret_cast<void *>(uintptr_t(table->id));
    void *ro=reinterpret_cast<void *>(uintptr_t(kIOSurfaceLockReadOnly));
    check(client.trapLock(id,nullptr,nullptr,nullptr,nullptr,nullptr)==kIOReturnNotWritable);
    check(client.trapUnlock(id,nullptr,nullptr,nullptr,nullptr,nullptr)==kIOReturnNotWritable);
    check(!seedCalls&&!seedBumps);
    check(client.trapLock(id,ro,nullptr,nullptr,nullptr,nullptr)==0);
    check(client.trapUnlock(id,ro,nullptr,nullptr,nullptr,nullptr)==0);
    check(seedCalls==2&&!seedBumps);
    failSeed=true;check(client.trapLock(id,ro,nullptr,nullptr,nullptr,nullptr)==kIOReturnVMError);
    failSeed=false;check(client.trapLock(reinterpret_cast<void *>(999),ro,nullptr,nullptr,nullptr,nullptr)==kIOReturnNotFound);
    clear();

    readOnlyInput=failReadOnlyDescriptor=true;
    check(run(good)==kIOReturnNoMemory);check(allocated==2&&prepared==1&&!published&&!completed);clear();
    readOnlyInput=failReadOnlyPrepare=true;
    check(run(good)==kIOReturnVMError);check(allocated==2&&prepared==2&&!published&&!completed);clear();
    for(IOReturn error:{kIOReturnNoMemory,kIOReturnVMError,kIOReturnNotWritable,kIOReturnBadArgument}){
        injectedPrepareError=error;check(run(good)==error);
        check(allocated==1&&prepared==1&&!published&&!completed);clear();
    }
    readOnlyInput=failPublish=true;
    check(run(good)==kIOReturnNoResources);check(prepared==2&&completed==1&&!returned);clear();
    readOnlyInput=failReturn=true;
    check(run(good)==kIOReturnVMError);check(prepared==2&&completed==1&&returned==1);clear();
    readOnlyInput=true;edge=good;edge.address+=16380;
    check(run(edge)==0);check(table->readOnly&&sweet_surface_wired==32768);clear();
    readOnlyInput=true;sweet_surface_wired=SWEET_SURFACE_WIRED_MAX;
    check(run(good)==kIOReturnNoMemory);check(!allocated&&sweet_surface_wired==SWEET_SURFACE_WIRED_MAX);
    sweet_surface_wired=0;clear();

    // Unchanged writable aliases, write locks and seed semantics.
    check(run(good)==0&&!table->readOnly&&allocated==1&&prepared==1);
    taskMap=table->mapPixelsInTask(84);
    check(taskMap&&lastCache==kIOMapAnywhere&&lastTask==84);taskMap->release();
    id=reinterpret_cast<void *>(uintptr_t(table->id));
    check(client.trapLock(id,nullptr,nullptr,nullptr,nullptr,nullptr)==0);
    check(client.trapUnlock(id,nullptr,nullptr,nullptr,nullptr,nullptr)==0);
    check(seedCalls==2&&seedBumps==1);clear();

    // Execute the real GPU gate. RO must reject even a buffer descriptor;
    // generic task memory remains ineligible for either access direction.
    GauguinGPUUserClient gpu;
    for(unsigned kind=0;kind<3;kind++){
        auto *s=sweet_surface_alloc();
        s->memory=kind==2?new IOMemoryDescriptor:new IOBufferMemoryDescriptor;
        check(s->memory->prepare()==0);s->memoryPrepared=true;
        s->width=s->height=32;s->bytesPerRow=128;s->bytesPerElement=4;
        s->allocSize=16384;s->pixelFormat=0x42475241;s->readOnly=kind!=0;
        check(sweet_surface_publish(s));s->release();
        struct ggr_surface request={};request.surface=table->id;
        check(gpu.surface(&request)==(kind==0?kIOReturnSuccess:kIOReturnUnsupported));
        check(gpuAdds==(kind==0?1u:0u));clear();
    }
'''


def main():
    runtime_header = TREE / 'bsd/dev/gauguin_gpu_runtime.h'
    paths = [Path(__file__), SURFACE, HEADER, GPU, FIXTURE, runtime_header]
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    source, gpu = SURFACE.read_text(), GPU.read_text()

    def extract(text, signature):
        start = text.index(signature)
        return text[start:text.index('\n}\n', start) + 3]

    signatures = ['void\nSweetSurface::free()', 'uintptr_t\nSweetSurface::kernelAddress()',
                  'IOMemoryMap *\nSweetSurface::mapPixelsInTask(',
                  'IOReturn\nIOSurfaceRootUserClient::wrapImage(',
                  'IOReturn\nIOSurfaceRootUserClient::trapLock(',
                  'IOReturn\nIOSurfaceRootUserClient::trapUnlock(']
    methods = '\n'.join(extract(source, n) for n in signatures)
    methods += extract(gpu, 'IOReturn GauguinGPUUserClient::surface(')
    text = FIXTURE.read_text()
    text = change(text, '#include <algorithm>', '#include <algorithm>\n#include <initializer_list>\n#include "gauguin_gpu_runtime.h"\n#ifndef GGR_MAX_CLIENT_BUFFERS\n#define GGR_MAX_CLIENT_BUFFERS GGR_MAX_BUFFERS\n#endif')
    text = change(text, 'using task_t = uintptr_t;', 'using task_t = uintptr_t;\nusing IOMemoryMap = struct Mapping;')
    text = change(text, '''constexpr IOReturn kIOReturnSuccess = 0, kIOReturnBadArgument = 1,
    kIOReturnNoMemory = 2, kIOReturnVMError = 3, kIOReturnNoResources = 4;''', '''constexpr IOReturn kIOReturnSuccess=0,KERN_PROTECTION_FAILURE=2,
    kIOReturnBadArgument=static_cast<int>(0xe00002c2u),kIOReturnNoMemory=static_cast<int>(0xe00002bdu),
    kIOReturnVMError=static_cast<int>(0xe00002c8u),kIOReturnNoResources=static_cast<int>(0xe00002beu),
    kIOReturnNotWritable=static_cast<int>(0xe00002cfu),kIOReturnNotFound=static_cast<int>(0xe00002f0u),
    kIOReturnUnsupported=static_cast<int>(0xe00002c7u);''')
    text = change(text, 'static bool failSurface,', '''constexpr unsigned kIODirectionOut=2,kIOMapReadOnly=0x1000,kIOMapAnywhere=0x2000,kIOSurfaceLockReadOnly=1;
static bool readOnlyInput,failReadOnlyDescriptor,failReadOnlyPrepare;
static IOReturn injectedPrepareError;
static unsigned descriptorFlags[4],descriptorCount;
static task_t lastTask;
static bool failSurface,''')
    text = change(text, 'virtual void free() {}', 'virtual bool init(){return true;}\n    virtual void free() {}')
    text = change(text, 'unsigned pins = 0;', 'unsigned pins = 0,direction=kIODirectionInOut;')
    text = change(text, 'assert(options == (kIODirectionInOut | kIOMemoryThreadSafe) && task == 42);', '''assert(task==42&&descriptorCount<4);
        assert(options==(kIODirectionInOut|kIOMemoryThreadSafe)||options==(kIODirectionOut|kIOMemoryThreadSafe));
        descriptorFlags[descriptorCount++]=options;
        if((options&3)==kIODirectionOut){assert(activeDescriptors==1);if(failReadOnlyDescriptor)return nullptr;}''')
    text = change(text, 'm->address = a; m->length = n; return m;', 'm->address = a; m->length = n;m->direction=options&3;return m;')
    text = change(text, 'IOReturn prepare() { ++prepared; if (failPrepare) return kIOReturnVMError; ++pins; return 0; }', '''IOReturn prepare(){
        ++prepared;if(injectedPrepareError)return injectedPrepareError;
        if(readOnlyInput&&direction==kIODirectionInOut)return KERN_PROTECTION_FAILURE;
        if(failPrepare||(direction==kIODirectionOut&&failReadOnlyPrepare))return kIOReturnVMError;
        ++pins;return 0;
    }''')
    text = change(text, 'Mapping *map(unsigned);', 'Mapping *map(unsigned);\n    Mapping *createMappingInTask(task_t,uint64_t,unsigned);')
    marker = 'struct SweetSurface : OSObject {'
    text = change(text, marker, '''Mapping *IOMemoryDescriptor::createMappingInTask(task_t task,uint64_t address,unsigned options){
    assert((task==42||task==84)&&!address);lastTask=task;lastCache=options;++mapCalls;
    return failMap?nullptr:new Mapping;
}
''' + marker)
    text = change(text, 'bool memoryPrepared = false;', 'bool memoryPrepared=false,readOnly=false;\n    uint32_t gpuState=0,planeCount=0,offset=0;')
    init = re.search(r'bool init\(\) APPLE_KEXT_OVERRIDE\s*(\{[^}]+\})', HEADER.read_text())
    assert init
    text = change(text, 'SweetSurface() { ++activeSurfaces; }', 'bool init() override '+init[1]+'\n    SweetSurface(){++activeSurfaces;assert(init());}')
    text = change(text, 'uintptr_t kernelAddress();', 'uintptr_t kernelAddress();\n    Mapping *mapPixelsInTask(task_t);')
    text = change(text, 'task_t fTask = 42;', '''task_t fTask=42;int *fLock=nullptr;void *fRefs=nullptr;
    IOReturn trapLock(void *,void *,void *,void *,void *,void *);
    IOReturn trapUnlock(void *,void *,void *,void *,void *,void *);''')
    text = change(text, '@METHODS@', EXTRA + methods)
    text = change(text, 'failMap = false; check(!mapLocked);', '''failMap=false;check(!mapLocked);
        readOnlyInput=failReadOnlyDescriptor=failReadOnlyPrepare=failSeed=false;
        injectedPrepareError=0;descriptorCount=seedCalls=seedBumps=gpuAdds=0;''')
    text = change(text, '    // Buffer allocation and physical surfaces also use the new common free().', CASES + '\n    // Buffer allocation and physical surfaces also use the new common free().')
    with tempfile.TemporaryDirectory(prefix='surface-ro-wrap-') as directory:
        directory = Path(directory)
        unit = directory / 'readonly.cpp'
        unit.write_text(text)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run(['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I'+str(runtime_header.parent), str(unit), '-o', str(directory/'readonly')],
                       env=env, check=True)
        subprocess.run([str(directory/'readonly')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
