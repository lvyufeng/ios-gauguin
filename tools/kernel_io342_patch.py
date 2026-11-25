"""Reversible clocks/counters only, over the exact337 GPU driver source."""
from core_prof339_patch import matching


def patch(raw):
    edits=[]
    def change(old,new):
        nonlocal raw
        assert raw.count(old)==1,(old,raw.count(old));raw=raw.replace(old,new);edits.append((old,new))
    def once(s,a,b):
        assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
    def method(marker,transform):
        start=raw.index(marker);end=matching(raw,raw.index('{',start),'{','}')+1
        old=raw[start:end];change(old,transform(old))
    change('extern "C" boolean_t pmap_valid_page(ppnum_t);',
        'extern "C" boolean_t pmap_valid_page(ppnum_t);\n#include "Kernel342.hpp"\nextern "C" void sweet_log_append(const char*,int);')
    change('    gapi_dumped=true;char line[256];uint64_t queued,held;',
        '    gapi_dumped=true;io342::dump(record,sweet_log_append);char line[256];uint64_t queued,held;')
    def wait(s):
        at=s.index('{')+1;s=s[:at]+'\n    auto* wait342=io342::current();const uint64_t begin342=wait342?io342::wall():0;'+s[at:]
        return s[:-1]+'    if(wait342)wait342->waited(begin342);\n}'
    method('static void gpuWaitUnlocked(void)',wait)
    locks='    uint64_t queued=mach_absolute_time();IOLockLock(gRequests);IOLockLock(gLock);'
    def newlocks(selector):return f'''    uint64_t queued=mach_absolute_time();
    io342::Scope trace342(fCompositor,{selector},queued);
    IOLockLock(gRequests);trace342.phase(1);IOLockLock(gLock);trace342.phase(2);trace342.activate();'''
    def external(s):
        s=once(s,locks,newlocks('selector'))
        s=once(s,'    if(selector==0x42)gbo333_record(1,',
            '    if(selector==0x42)trace342.allocation(r.make.handle,r.make.size);\n    if(selector==0x43)trace342.allocation(r.info.handle,0);\n    if(selector==0x46)trace342.tag(r.submit.queueid,r.submit.fence,0,0,r.submit.nr_bos,r.submit.nr_cmds);\n    if(selector==0x42)gbo333_record(1,')
        s=once(s,'        fAllocationStage=1; /* request flags/shape */','        io342::phase(0x42,3);\n        fAllocationStage=1; /* request flags/shape */')
        s=once(s,'            bzero(m->getBytesNoCopy(),','            io342::phase(0x42,5);\n            bzero(m->getBytesNoCopy(),')
        s=once(s,'            b->handle=fNextHandle++;','            io342::phase(0x42,11);\n            b->handle=fNextHandle++;')
        s=once(s,'        auto m=IOBufferMemoryDescriptor::inTaskWithOptions(',
            '        io342::phase(0x42,4);\n        auto m=IOBufferMemoryDescriptor::inTaskWithOptions(')
        s=once(s,'\n        bzero(m->getBytesNoCopy(),','\n        io342::phase(0x42,5);\n        bzero(m->getBytesNoCopy(),')
        s=once(s,'    case 0x43: {','    case 0x43: {\n        io342::phase(0x43,3);')
        s=once(s,'out:\n','out:\n    trace342.phase(11);\n    if(selector==0x42)trace342.allocation(r.make.handle,r.make.size);\n    if(selector==0x46)trace342.fence(r.submit.queueid,r.submit.fence);\n')
        return once(s,'    gapi_end(profile,result);IOLockUnlock(gLock);',
            '    gapi_end(profile,result);trace342.finish((uint32_t)result);IOLockUnlock(gLock);')
    method('IOReturn GauguinGPUUserClient::externalMethod(',external)
    def mapping(s):
        s=once(s,locks,newlocks('0x100')+'\n    trace342.allocation(type,0);')
        s=once(s,'    const bool fast=', '    trace342.phase(3);\n    const bool fast=')
        s=once(s,'    bool waited=false;', '    trace342.phase(4);\n    bool waited=false;')
        s=once(s,'    if(b&&!(b->surface', '    trace342.phase(5);\n    if(b&&!(b->surface')
        s=once(s,'    if(profile&&!gapi_frozen)', '    trace342.phase(11);\n    trace342.allocation(type,b?b->size:0);\n    if(profile&&!gapi_frozen)')
        return once(s,'    gapi_end(profile,r);IOLockUnlock(gLock);',
            '    gapi_end(profile,r);trace342.finish((uint32_t)r);IOLockUnlock(gLock);')
    method('IOReturn GauguinGPUUserClient::clientMemoryForType(',mapping)
    def submit(s):
        s=once(s,'    gpu_queue *q=queue(r->queueid);','    io342::phase(0x46,3);\n    gpu_queue *q=queue(r->queueid);')
        s=once(s,'    if(copyin(r->bos,','    io342::phase(0x46,4);\n    if(copyin(r->bos,')
        s=once(s,'        uint64_t addresses[GGR_MAX_COMMANDS];uint32_t words[GGR_MAX_COMMANDS];',
            '        uint64_t addresses[GGR_MAX_COMMANDS];uint32_t words[GGR_MAX_COMMANDS];\n        io342::phase(0x46,5);')
        s=once(s,'        for(uint32_t i=0;i<r->nr_cmds;i++) {','        io342::phase(0x46,6);\n        for(uint32_t i=0;i<r->nr_cmds;i++) {')
        s=once(s,'            addresses[i]=','            if(i==0)if(auto* p=io342::current())p->tag(r->queueid,r->fence,b->handle,cmds[i].size,r->nr_bos,r->nr_cmds);\n            addresses[i]=')
        s=once(s,'        /* Validate ALL requests','        io342::phase(0x46,7);\n        /* Validate ALL requests')
        s=once(s,'        /* Escrow every descriptor','        io342::phase(0x46,8);\n        /* Escrow every descriptor')
        a='''        for(uint32_t i=0;i<r->nr_bos;i++) {
            gpu_buffer *b=find(bos[i].handle);
            if(b->surface) {
                b->surface->gpuState=1;'''
        s=once(s,a,'        io342::phase(0x46,9);\n'+a)
        s=once(s,'        memoryBarrier();uint32_t fence=0;','        io342::phase(0x46,10);\n        memoryBarrier();uint32_t fence=0;')
        s=once(s,'        if(ok&&(!fence||fence<=fNativeFence))','        io342::phase(0x46,11);\n        if(ok&&(!fence||fence<=fNativeFence))')
        return once(s,'out:\n','out:\n    io342::phase(0x46,11);\n')
    method('IOReturn GauguinGPUUserClient::submit(',submit)
    def add(s):
        at=s.index('{')+1;s=s[:at]+'\n    io342::phase(0x42,6);'+s[at:]
        s=once(s,'    fAllocationStage=6;','    io342::phase(0x42,7);\n    fAllocationStage=6;')
        s=once(s,'    fAllocationStage=7;','    io342::phase(0x42,8);\n    fAllocationStage=7;')
        s=once(s,'    fAllocationStage=8;','    io342::phase(0x42,9);\n    fAllocationStage=8;')
        s=once(s,'    memoryBarrier();fAllocationStage=9;','    io342::phase(0x42,10);\n    memoryBarrier();fAllocationStage=9;')
        return once(s,'    *handle=slot->handle;', '    io342::phase(0x42,11);\n    *handle=slot->handle;')
    method('IOReturn GauguinGPUUserClient::add(',add)
    return raw,edits


def reverse(original,candidate,edits):
    for old,new in reversed(edits):
        assert candidate.count(new)==1;candidate=candidate.replace(new,old)
    assert candidate==original
