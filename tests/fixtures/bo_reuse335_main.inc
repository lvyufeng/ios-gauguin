// The peer exposes observations and boundary injection only; cache, request,
// submit, completion, quota and ownership decisions are the real kernel code.
struct BC335Host {
    static uint32_t slots(GauguinGPUUserClient *c){return c->fCachedCount;}
    static uint64_t bytes(GauguinGPUUserClient *c){return c->fCachedBytes;}
    static uint64_t resident(GauguinGPUUserClient *c){return c->fBytes;}
    static gpu_buffer *live(GauguinGPUUserClient *c,uint32_t h){return c->find(h);}
    static void next(GauguinGPUUserClient *c,uint32_t value){c->fNextHandle=value;}
    static bool enabled(GauguinGPUUserClient *c){return c->fCacheEnabled;}
    static IOReturn finish(GauguinGPUUserClient *c){
        IOLockLock(gRequests);IOLockLock(gLock);
        IOReturn r=c->finishPending(false,true);
        IOLockUnlock(gLock);IOLockUnlock(gRequests);return r;
    }
    static bool trim(GauguinGPUUserClient *c){
        IOLockLock(gRequests);IOLockLock(gLock);bool r=c->trimCached335(0,true);
        IOLockUnlock(gLock);IOLockUnlock(gRequests);return r;
    }
};
static void close_bo(GauguinGPUUserClient *c,uint32_t handle){
    ggr_close close={handle,0};CHECK(request(c,0x09,&close)==0);
    ggr_info old={handle,1,0,0,0};CHECK(request(c,0x43,&old)==kIOReturnBadArgument);
}
static unsigned persistent;
static GauguinGPUUserClient *start_cache(){
    hardware_ready=true;CHECK(GauguinGPUStart());
    // Typed board/caller inputs: bootstrap completed and the opted-in window
    // server is the one permitted owner. start() still checks these inputs.
    gMetalBootstrapMode=true;gMetalBootstrap.ready=true;gReleasedRootFence=6;
    pilot_mode=pilot_job=true;mock_task=(void *)2;cache335_host_async=true;
    auto c=new GauguinGPUUserClient;
    CHECK(c->initWithTask(mock_task,nullptr,0,nullptr));
    CHECK(c->start(IOService::getPlatform())&&BC335Host::enabled(c));
    persistent=allocations-frees;return c;
}
static void finish_cache(GauguinGPUUserClient *c){
    CHECK(c->clientClose()==0&&!gOwner);c->release();
    CHECK(allocations-frees==persistent&&mock_task_refs==0);
}
static void submit_pending(GauguinGPUUserClient *c,uint32_t data,uint32_t commands){
    auto m=mapped(c,commands);uint64_t target=address(c,data),source=address(c,commands);
    uint32_t words[]={0x703d8003u,uint32_t(target),uint32_t(target>>32),0x12345678};
    memcpy(m->bytes,words,sizeof(words));m->release();
    ggr_submit_bo bos[]={{3,data,target},{1,commands,source}};
    ggr_submit_cmd command={1,1,0,sizeof(words),0,0,0};
    struct ggr_submit request_{};request_.flags=0x10;request_.nr_bos=2;request_.nr_cmds=1;
    request_.bos=(uintptr_t)bos;request_.cmds=(uintptr_t)&command;request_.fence_fd=-1;
    CHECK(request(c,0x46,&request_)==0&&request_.fence==1);
}
int main(int argc,char **argv){
    CHECK(argc==2);std::string mode=argv[1];auto c=start_cache();
    if(mode=="basic"){
        uint32_t first=new_bo(c,20001,GGR_BO_WC);uint64_t va=address(c,first);
        auto m=mapped(c,first);CHECK(m->size==32768);memset(m->bytes,0xa7,32768);
        auto raw=m;m->release();uint64_t descriptor=*pte(va);
        unsigned allocated=allocations,synchronized=sync_calls;
        close_bo(c,first);CHECK(BC335Host::slots(c)==1&&BC335Host::bytes(c)==32768);
        CHECK(BC335Host::resident(c)==32768&&sync_calls==synchronized);
        uint32_t second=new_bo(c,20002,GGR_BO_WC);CHECK(second>first&&address(c,second)==va);
        CHECK(allocations==allocated&&sync_calls==synchronized&&*pte(va)==descriptor);
        m=mapped(c,second);CHECK(m==raw);
        for(unsigned i=0;i<32768;i++)CHECK(m->bytes[i]==0);
        m->release();CHECK(BC335Host::slots(c)==0);close_bo(c,second);
        CHECK(gCache335.hits==1&&gCache335.stores==2);
    }else if(mode=="flags"){
        uint32_t first=new_bo(c,16384,GGR_BO_WC);auto va=address(c,first);close_bo(c,first);
        auto count=allocations;uint32_t ro=new_bo(c,16384,GGR_BO_WC|GGR_BO_READONLY);
        CHECK(allocations==count+1&&address(c,ro)!=va&&(*pte(address(c,ro))&0x80));
        uint32_t plain=new_bo(c,16384,0);CHECK(address(c,plain)!=va);
        uint32_t same=new_bo(c,16384,GGR_BO_WC);CHECK(address(c,same)==va&&gCache335.hits==1);
        close_bo(c,ro);close_bo(c,plain);close_bo(c,same);
    }else if(mode=="aliases"){
        uint32_t first=new_bo(c,16384);auto m=mapped(c,first);
        memset(m->bytes,0x6b,16384);auto before=allocations;close_bo(c,first);
        CHECK(BC335Host::slots(c)==0&&m->refs==1&&m->prepared==0&&gCache335.aliases==1);
        uint32_t second=new_bo(c,16384);CHECK(allocations==before+1);
        auto fresh=mapped(c,second);CHECK(fresh!=m);
        for(unsigned i=0;i<16384;i++)CHECK(m->bytes[i]==0x6b&&fresh->bytes[i]==0);
        fresh->release();m->release();close_bo(c,second);
    }else if(mode=="pending"||mode=="fault"){
        uint32_t data=new_bo(c,16384),commands=new_bo(c,16384,GGR_BO_READONLY);
        uint64_t va=address(c,data);host_poll_result=GGR_PENDING;
        submit_pending(c,data,commands);auto owner=BC335Host::live(c,data);
        CHECK(owner&&owner->pending);unsigned synchronized=sync_calls,allocated=allocations;
        close_bo(c,data);CHECK(owner->memory&&owner->pending&&owner->closePending&&!owner->cached);
        CHECK(BC335Host::slots(c)==0&&BC335Host::finish(c)==kIOReturnNotReady);
        CHECK(owner->memory&&owner->pending&&BC335Host::slots(c)==0);
        if(mode=="fault"){
            host_poll_result=GGR_IO;CHECK(BC335Host::finish(c)==kIOReturnNotReady);
            CHECK(owner->memory&&owner->pending&&!owner->cached&&!hardware_ready);
            CHECK(BC335Host::slots(c)==0&&sync_calls==synchronized&&allocations==allocated);
            ggr_new refused={16384,0,0};CHECK(request(c,0x42,&refused)==kIOReturnNotReady);
            std::puts("PASS fault: DMA owner retained, no cache reuse after completion failure");return 0;
        }
        host_poll_result=GGR_OK;CHECK(BC335Host::finish(c)==0);
        CHECK(!owner->pending&&owner->cached&&BC335Host::slots(c)==1);
        auto again=new_bo(c,16384);CHECK(again>commands&&address(c,again)==va);
        CHECK(sync_calls==synchronized&&allocations==allocated);
        close_bo(c,again);close_bo(c,commands);
    }else if(mode=="concurrent"){
        std::vector<std::thread> workers;
        for(unsigned thread=0;thread<8;thread++)workers.emplace_back([&,thread]{
            for(unsigned i=0;i<200;i++){
                auto h=new_bo(c,(i&1)?16384:262144,(thread&1)?GGR_BO_WC:GGR_BO_READONLY);
                auto m=mapped(c,h);
                for(unsigned j=0;j<m->size;j++)CHECK(m->bytes[j]==0);
                memset(m->bytes,0xa5,(size_t)m->size);m->release();close_bo(c,h);
            }
        });
        for(auto &worker:workers)worker.join();
        CHECK(gCache335.hits>1000&&BC335Host::slots(c)<=32&&BC335Host::bytes(c)<=16777216);
    }else if(mode=="caps"){
        std::vector<uint32_t> handles;
        for(unsigned i=0;i<40;i++)handles.push_back(new_bo(c,1u<<19));
        for(uint32_t h:handles)close_bo(c,h);
        CHECK(BC335Host::slots(c)==32&&BC335Host::bytes(c)==16777216);
        CHECK(BC335Host::resident(c)==16777216&&allocations-frees==persistent+32);
    }else if(mode=="quota"){
        std::vector<uint32_t> cached;
        for(unsigned i=0;i<16;i++)cached.push_back(new_bo(c,1u<<20));
        for(uint32_t h:cached)close_bo(c,h);
        CHECK(BC335Host::bytes(c)==16777216);
        std::vector<uint32_t> large;
        for(unsigned i=0;i<4;i++)large.push_back(new_bo(c,GGR_MAX_BO_BYTES));
        CHECK(BC335Host::slots(c)==0&&gCache335.evicts==16);
        CHECK(BC335Host::resident(c)==GGR_MAX_CLIENT_BYTES);
        ggr_new refused={16384,0,0};CHECK(request(c,0x42,&refused)==kIOReturnNoResources);
        for(uint32_t h:large)close_bo(c,h);
        CHECK(BC335Host::slots(c)==0);
    }else if(mode=="pressure"||mode=="oom"){
        auto h=new_bo(c,16384);close_bo(c,h);CHECK(BC335Host::slots(c)==1);
        fail_allocations=mode=="pressure"?1:2;
        ggr_new request_={32768,0,0};auto result=request(c,0x42,&request_);
        CHECK(BC335Host::slots(c)==0&&gCache335.evicts==1&&fail_allocations==0);
        if(mode=="pressure"){CHECK(result==0&&request_.handle);close_bo(c,request_.handle);}
        else CHECK(result==kIOReturnNoMemory&&request_.handle==0);
    }else if(mode=="wrap"){
        auto h=new_bo(c,16384);close_bo(c,h);BC335Host::next(c,UINT32_MAX);
        auto last=new_bo(c,16384);CHECK(last==UINT32_MAX);close_bo(c,last);
        ggr_new refused={16384,0,0};CHECK(request(c,0x42,&refused)==kIOReturnNoResources&&refused.handle==0);
    }else if(mode=="evict-fault"){
        auto h=new_bo(c,16384);close_bo(c,h);unsigned before=frees;
        fail_sync=true;CHECK(!BC335Host::trim(c));
        CHECK(!hardware_ready&&BC335Host::slots(c)==1&&BC335Host::bytes(c)==16384&&frees==before);
        std::puts("PASS evict-fault: failed synchronization retains descriptor and cache owner");return 0;
    }else if(mode=="surface"){
        auto surface=new SweetSurface;surface->id=7;surface->width=surface->height=64;
        surface->bytesPerRow=256;surface->bytesPerElement=4;surface->planeCount=0;
        surface->pixelFormat=0x42475241;surface->allocSize=16384;
        surface->memory=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,0,16384,16384);
        surface_table[7]=surface;
        ggr_surface request_={7,0,0,0,0,0,0,0,0};CHECK(request(c,0x7e,&request_)==0);
        close_bo(c,request_.handle);CHECK(BC335Host::slots(c)==0&&gCache335.stores==0);
        surface_table.erase(7);surface->release();
    }else assert(false);
    finish_cache(c);
    printf("PASS %s: %u checks; actual full IOUserClient, typed board/allocator inputs\n",mode.c_str(),checks.load());
}
