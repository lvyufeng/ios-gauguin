int main(void)
{
    hardware_ready=true;CHECK(GauguinGPUStart());
    auto c=new GauguinGPUUserClient;
    CHECK(c->initWithTask(kernel_task,nullptr,0,nullptr)&&c->start(IOService::getPlatform()));
    auto original_buffers=c->fBuffers;
    struct ggr_submit_bo bo={1,99,0};struct ggr_submit_cmd cmd={1,0,0,16,0,0,0};
    for(unsigned which=0;which<8;which++){
        c->fClosed=false;c->fBuffers=original_buffers;gOwner=c;hardware_ready=true;
        c->fPendingCount=0;c->fPendingNativeFence=0;c->fPendingQueue=nullptr;
        c->fCompositor=c->fAsync=true;c->fTask=(void *)2;mock_task=(void *)2;
        gMetalBootstrapMode=false;gMetalBootstrap={};
        struct ggr_submit r={};r.flags=0;r.nr_bos=r.nr_cmds=1;r.fence_fd=-1;
        r.bos=(uint64_t)&bo;r.cmds=(uint64_t)&cmd;
        unsigned stage=10;
        switch(which){
        case 0:break;
        case 1:c->fClosed=true;stage=1;break;
        case 2:gOwner=nullptr;stage=1;break;
        case 3:c->fBuffers=nullptr;stage=1;break;
        case 4:c->fPendingCount=1;stage=2;break;
        case 5:hardware_ready=false;stage=3;break;
        case 6:r.flags=0x10;stage=14;break;
        case 7:r.flags=0x10;c->fCompositor=c->fAsync=false;c->fTask=kernel_task;mock_task=kernel_task;
               gMetalBootstrapMode=true;gMetalBootstrap.armed=true;stage=4;break;
        }
        IOReturn rc=request(c,0x46,&r);CHECK(rc!=kIOReturnSuccess&&!lock_depth);
#ifdef TEST_SUBMIT327
        CHECK(c->fSubmitDiag327.stage==stage);
        CHECK(submit_logs.size()==(which<7?which+1:7));
#else
        (void)stage;CHECK(submit_logs.empty());
#endif
        printf("OBS gate=%u rc=%d fence=%u hw=%u pending=%u submit_calls=%u sync_calls=%u maps=%u\n",
               which,rc,r.fence,hardware_ready,c->fPendingCount,submit_calls,sync_calls,map_calls);
    }
#ifdef TEST_SUBMIT327
    CHECK(gsub_diag327_count==7);
    for(const auto &line:submit_logs)printf("FIXTURE %s",line.c_str());
#endif
    c->fClosed=false;c->fBuffers=original_buffers;gOwner=c;hardware_ready=true;
    c->fPendingCount=0;c->fCompositor=c->fAsync=false;c->fTask=kernel_task;mock_task=kernel_task;gMetalBootstrapMode=false;
    size_t before=submit_logs.size();ggr_param param={0x10,1,0,0,0};CHECK(request(c,0x40,&param)==0&&param.value==619&&submit_logs.size()==before);
    CHECK(c->clientClose()==0&&!gOwner);c->release();
    printf("PASS: actual externalMethod gates and output-preservation, %u assertions; CPU seams only\n",checks);
}
