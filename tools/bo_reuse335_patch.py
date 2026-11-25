"""Bounded completed-owned-BO reuse; apply only over the verified 0333 kernel."""
GPU = 'iokit/Kernel/arm/GauguinGPU.cpp'
HEADER = 'bsd/dev/gauguin_ui_trace.h'

GLOBALS = '''/* BC335: per-connection completed-owned-BO cache. All mutations hold the
 * original request/GPU locks. Exported descriptor aliases exclude retention.
 * Cached handles are zero; fBytes includes their still-resident mappings. */
static constexpr uint32_t kCache335Slots=32;
static constexpr uint64_t kCache335Bytes=16ull<<20;
static constexpr uint64_t kCache335MaxBo=1ull<<20;
static struct {
    uint64_t hits,misses,stores,evicts,aliases,bytes;
    uint32_t slots,connections;
    bool invalid;
} gCache335;
static void cache335_count(uint64_t *value)
{if(!gapi_frozen){if(*value==UINT64_MAX)gCache335.invalid=true;else ++*value;}}

'''

METHODS = '''void GauguinGPUUserClient::cacheState335(void)
{
    if(!gapi_frozen&&fCacheEnabled){gCache335.slots=fCachedCount;gCache335.bytes=fCachedBytes;}
}
gpu_buffer *GauguinGPUUserClient::takeCached335(uint64_t bytes,uint32_t flags)
{
    if(!fCacheEnabled||fClosed||!fNextHandle)return nullptr;
    for(uint32_t i=0;i<GGR_MAX_CLIENT_BUFFERS;i++) {
        gpu_buffer *b=fBuffers+i;
        if(!b->cached||!b->memory||b->surface||b->handle||b->pending||b->closePending||
           !b->installed||b->size!=bytes||b->flags!=flags)continue;
        if(b->memory->getRetainCount()!=1)continue;
        if(!OSDynamicCast(IOBufferMemoryDescriptor,b->memory))continue;
        b->cached=false;--fCachedCount;fCachedBytes-=b->mappingSize;
        cache335_count(&gCache335.hits);cacheState335();return b;
    }
    cache335_count(&gCache335.misses);return nullptr;
}
bool GauguinGPUUserClient::retire335(gpu_buffer *b)
{
    if(!b->memory)return true;
    if(b->pending||!sweet_gpu_runtime_ready())return false;
    auto *memory=OSDynamicCast(IOBufferMemoryDescriptor,b->memory);
    const bool eligible=fCacheEnabled&&!fClosed&&!b->cached&&!b->surface&&memory&&b->installed&&
        b->size>=PAGE_SIZE&&b->size<=kCache335MaxBo&&b->size==b->mappingSize&&
        b->address==b->mappingAddress&&!(b->flags&~(GGR_BO_READONLY|GGR_BO_WC));
    if(eligible&&memory->getRetainCount()!=1)cache335_count(&gCache335.aliases);
    if(eligible&&memory->getRetainCount()==1&&fCachedCount<kCache335Slots&&
       b->mappingSize<=kCache335Bytes-fCachedBytes) {
        b->handle=0;b->closePending=false;b->cached=true;
        ++fCachedCount;fCachedBytes+=b->mappingSize;
        cache335_count(&gCache335.stores);cacheState335();return true;
    }
    return drop(b);
}
bool GauguinGPUUserClient::trimCached335(uint64_t bytes,bool all)
{
    for(uint32_t i=0;i<GGR_MAX_CLIENT_BUFFERS;i++) {
        bool empty=false;
        if(!all) {
            for(uint32_t j=0;j<GGR_MAX_CLIENT_BUFFERS;j++)if(!fBuffers[j].memory){empty=true;break;}
            if(empty&&bytes<=GGR_MAX_CLIENT_BYTES-fBytes)return true;
        }
        if(fBuffers[i].cached&&!drop(fBuffers+i))return false;
    }
    return true;
}

'''


def transform(name, source):
    original = source
    edits = []
    def edit(old, new):
        nonlocal source
        assert source.count(old) == 1, (name, old)
        source = source.replace(old, new)
        edits.append((old, new))
    if name == HEADER:
        edit('    GUT_BO_ALLOC333=32,', '    GUT_BO_REUSE335=33, /* completed-owned mapping reused; API token */\n    GUT_BO_ALLOC333=32,')
    else:
        assert name == GPU
        edit('static void gapi_end(uint64_t token,IOReturn result)\n', GLOBALS + 'static void gapi_end(uint64_t token,IOReturn result)\n')
        edit('    gapi_dumped=true;char line[256];uint64_t queued,held;', '''    gapi_dumped=true;char line[256];uint64_t queued,held;
    snprintf(line,sizeof(line),"SWEET BC335: hits=%llu misses=%llu stores=%llu evicts=%llu aliases=%llu valid=%u",
        (unsigned long long)gCache335.hits,(unsigned long long)gCache335.misses,
        (unsigned long long)gCache335.stores,(unsigned long long)gCache335.evicts,
        (unsigned long long)gCache335.aliases,!gCache335.invalid&&gapi_valid?1u:0u);record(line);
    snprintf(line,sizeof(line),"SWEET BC335: slots=%u bytes=%llu connections=%u; completed prefix, zeroed owned only",
        gCache335.slots,(unsigned long long)gCache335.bytes,gCache335.connections);record(line);''')
        edit('    bool installed,pending,closePending;', '    bool installed,pending,closePending,cached;')
        edit('    uint64_t fBytes;', '    uint64_t fBytes,fCachedBytes;\n    uint32_t fCachedCount;\n    bool fCacheEnabled;')
        edit('    bool drop(gpu_buffer *);', '''    bool drop(gpu_buffer *);
    bool retire335(gpu_buffer *);
    gpu_buffer *takeCached335(uint64_t,uint32_t);
    bool trimCached335(uint64_t,bool);
    void cacheState335(void);''')
        edit('    fAsync=false;return true;', '    fCachedBytes=0;fCachedCount=0;fCacheEnabled=false;\n    fAsync=false;return true;')
        edit('        gOwner=this;\n', '''        gOwner=this;
        fCacheEnabled=fCompositor&&fAsync;
        if(fCacheEnabled){
            ++gCache335.connections;
            IOLog("SWEET BC335: enabled slots=32 bytes=16777216 max_bo=1048576 zero=1\\n");
        }
''')
        edit('flags,true,false,false};fBytes+=mappingSize;', 'flags,true,false,false,false};fBytes+=mappingSize;')
        edit('bool GauguinGPUUserClient::drop(gpu_buffer *b)\n', METHODS + 'bool GauguinGPUUserClient::drop(gpu_buffer *b)\n')
        edit('    releaseAddress(b->mappingAddress,b->mappingSize);fBytes-=b->mappingSize;', '''    if(b->cached){
        --fCachedCount;fCachedBytes-=b->mappingSize;
        cache335_count(&gCache335.evicts);cacheState335();
    }
    releaseAddress(b->mappingAddress,b->mappingSize);fBytes-=b->mappingSize;''')
        edit('fBuffers[i].closePending&&!drop(fBuffers+i)', 'fBuffers[i].closePending&&!retire335(fBuffers+i)')
        edit('} else result=drop(b)?kIOReturnSuccess:kIOReturnNotReady;', '} else result=retire335(b)?kIOReturnSuccess:kIOReturnNotReady;')
        edit('''        gbo333_record(2,n,0,0);
        auto m=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,''', '''        gbo333_record(2,n,0,0);
        if(gpu_buffer *b=takeCached335(n,r.make.flags)) {
            auto *m=OSDynamicCast(IOBufferMemoryDescriptor,b->memory);
            gbo333_record(3,1,0,0);
            bzero(m->getBytesNoCopy(),(size_t)n);memoryBarrier();
            gbo333_record(4,0,0,0);
            b->handle=fNextHandle++;r.make.handle=b->handle;fAllocationStage=0;
            gbo333_record(5,b->mappingSize,b->handle,b->flags);
            if(gapi_pending.token&&!gapi_frozen&&gapi_valid)
                sweet_ui_trace_record(GUT_BO_REUSE335,gapi_pending.token,
                    (uint32_t)proc_pid(current_proc()),1,n,b->handle,b->flags);
            result=kIOReturnSuccess;break;
        }
        if(fCacheEnabled&&!trimCached335(n,false)){
            gbo333_record(3,0,0,0);result=kIOReturnNotReady;break;
        }
        auto m=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,''')
        edit('''        gbo333_record(3,m!=nullptr,0,0);''', '''        // Under allocator pressure, release retained completed mappings and
        // retry the backing allocation once. Failure leaves the original code.
        if(!m&&fCacheEnabled&&fCachedCount) {
            if(!trimCached335(n,true)){
                gbo333_record(3,0,0,0);result=kIOReturnNotReady;break;
            }
            m=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,
                kIODirectionInOut|kIOMemoryKernelUserShared|kIOMapWriteCombineCache,(vm_size_t)n,PAGE_SIZE);
        }
        gbo333_record(3,m!=nullptr,0,0);''')
    undone = source
    for old, new in reversed(edits):
        assert undone.count(new) == 1
        undone = undone.replace(new, old)
    assert undone == original
    return source, edits
