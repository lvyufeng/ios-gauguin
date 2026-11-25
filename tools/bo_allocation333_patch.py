"""CPU-only allocation phase records. No device I/O; reversible source transform."""
GPU='iokit/Kernel/arm/GauguinGPU.cpp'
HEADER='bsd/dev/gauguin_ui_trace.h'

HELPER='''/* BO333: bounded UI trace only. Existing producer supplies the CPU clock;
 * no new allocation, locks, waits, GPU calls or MMIO. All calls below hold
 * the original request and GPU locks. Never publish raw kernel pointers. */
static void gbo333_record(uint32_t phase,uint64_t a,uint64_t b,uint64_t c)
{
    if(!gapi_pending.token||gapi_frozen||!gapi_valid||
       gapi_pending.index>=GAPI_COUNT||gapi_selectors[gapi_pending.index]!=0x42)return;
    sweet_ui_trace_record(GUT_BO_ALLOC333,gapi_pending.token,
        (uint32_t)proc_pid(current_proc()),phase,a,b,c);
}
/* END BO333 helper */

'''

def transform(name,source):
    original=source;edits=[]
    def edit(old,new):
        nonlocal source
        assert source.count(old)==1,(name,old)
        source=source.replace(old,new);edits.append((old,new))
    if name==HEADER:
        edit('    GUT_HID_QUEUE_STATE=31 /*','    GUT_BO_ALLOC333=32, /* CPU allocation phases; API token and numeric metadata */\n    GUT_HID_QUEUE_STATE=31 /*')
    else:
        assert name==GPU
        edit('#include <kern/task.h>\n','#include <kern/task.h>\n#include <kern/thread.h> /* BO333 numeric current-thread ID */\n')
        edit('static void gapi_end(uint64_t token,IOReturn result)\n',HELPER+'static void gapi_end(uint64_t token,IOReturn result)\n')
        edit('    fAllocationStage=0; /* runtime/client gate, before request validation */',
             '    fAllocationStage=0; /* runtime/client gate, before request validation */\n'
             '    if(selector==0x42)gbo333_record(1,r.make.size,r.make.flags,thread_tid(current_thread()));')
        edit('        auto m=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,',
             '        gbo333_record(2,n,0,0);\n        auto m=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,')
        edit('        if(!m){result=kIOReturnNoMemory;break;}\n        bzero(m->getBytesNoCopy(),(size_t)n);memoryBarrier();',
             '        gbo333_record(3,m!=nullptr,0,0);\n'
             '        if(!m){result=kIOReturnNoMemory;break;}\n'
             '        bzero(m->getBytesNoCopy(),(size_t)n);memoryBarrier();\n        gbo333_record(4,0,0,0);')
        edit('    memoryBarrier();fAllocationStage=9;\n    if(!sweet_gpu_runtime_sync())',
             '    gbo333_record(5,mappingSize,slot->handle,flags);\n'
             '    memoryBarrier();fAllocationStage=9;\n    if(!sweet_gpu_runtime_sync())')
        edit('out:\n    if(selector==0x42&&result!=kIOReturnSuccess&&fAllocationFailures<8){',
             'out:\n    if(selector==0x42)gbo333_record(6,(uint32_t)result,r.make.handle,fAllocationStage);\n'
             '    if(selector==0x42&&result!=kIOReturnSuccess&&fAllocationFailures<8){')
    undone=source
    for old,new in reversed(edits):
        assert undone.count(new)==1
        undone=undone.replace(new,old)
    assert undone==original
    return source,edits
