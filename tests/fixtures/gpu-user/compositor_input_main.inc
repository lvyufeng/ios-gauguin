/* Real client/bootstrap/import/submit methods; hardware and IOKit are seams. MIT. */
static void qualify_root(bool arm)
{
    auto root=new GauguinGPUUserClient;
    CHECK(root->initWithTask(kernel_task,nullptr,0,nullptr)&&root->start(IOService::getPlatform()));
    uint32_t data=new_bo(root,16384),commands=new_bo(root,16384,GGR_BO_READONLY);
    auto data_m=mapped(root,data),command_m=mapped(root,commands);
    uint64_t data_va=address(root,data),command_va=address(root,commands);
    const uint32_t words[]={0x703d8003u,(uint32_t)data_va,0,0x11223344};
    memcpy(command_m->getBytesNoCopy(),words,sizeof(words));
    ggr_submit_bo bos[]={{3,data,data_va},{1,commands,command_va}};
    ggr_submit_cmd cmd={1,1,0,sizeof(words),0,0,0};
    struct ggr_submit submit={};submit.flags=0x10;submit.nr_bos=2;submit.nr_cmds=1;
    submit.bos=(uintptr_t)bos;submit.cmds=(uintptr_t)&cmd;submit.fence_fd=-1;
    for(unsigned n=1;n<=8;n++){
        submit.fence=0;CHECK(request(root,0x46,&submit)==0&&submit.fence==n);
        CHECK(*gpu_word(data_va)==0x11223344);
    }
    if(arm){ggr_bootstrap ready={1,8,0,0,0};CHECK(request(root,GGR_BOOTSTRAP_SELECTOR,&ready)==0);}
    CHECK(!gMetalBootstrap.ready);
    data_m->release();command_m->release();CHECK(root->clientClose()==0&&!gOwner);
    CHECK(gMetalBootstrap.ready==arm&&gReleasedRootFence==8);root->release();
}
static SweetSurface *task_image(uint32_t id,uint32_t bytes,uint32_t bias,
                               uint32_t bpe,uint32_t pitch)
{
    auto image=new SweetSurface;CHECK(image->init());image->id=id;
    image->memory=TaskPixels::make(bytes,bias);image->memoryPrepared=image->readOnly=true;
    image->allocSize=bytes;image->offset=7;image->width=image->height=64;
    image->bytesPerElement=bpe;image->bytesPerRow=pitch;image->pixelFormat=0x42475241;
    surface_table[id]=image;return image;
}
int main(int argc,char **argv)
{
    CHECK(argc==2);const bool legacy=!strcmp(argv[1],"legacy");
    const bool unarmed=!strcmp(argv[1],"unarmed"),fault=!strcmp(argv[1],"dma-fault");
    pilot_mode=pilot_job=true;bootstrap_host_mode=!legacy;
    hardware_ready=true;CHECK(GauguinGPUStart());qualify_root(!legacy&&!unarmed);
    task_t mobile=(void *)2;mock_task=mobile;
    auto denied=new GauguinGPUUserClient;pilot_job=false;
    CHECK(!denied->initWithTask(mobile,nullptr,0,nullptr));denied->release();pilot_job=true;
    denied=new GauguinGPUUserClient;CHECK(!denied->initWithTask((void *)3,nullptr,0,nullptr));denied->release();
    auto c=new GauguinGPUUserClient;CHECK(c->initWithTask(mobile,nullptr,0,nullptr));
    CHECK(c->start(IOService::getPlatform())==!unarmed);
    if(unarmed){c->release();CHECK(!mock_task_refs);printf("PASS unarmed: %u checks; no compositor owner\n",checks);return 0;}
    if(legacy){
        auto image=task_image(100,20493,64,4,320);auto pixels=static_cast<TaskPixels *>(image->memory);
        ggr_surface input={};input.surface=image->id;unsigned maps=map_calls;
        CHECK(request(c,0x7e,&input)==kIOReturnUnsupported&&!input.handle);
        CHECK(pixels->prepared==1&&map_calls==maps);
        surface_table.erase(image->id);image->release();CHECK(c->clientClose()==0&&!gOwner);
        c->release();CHECK(!mock_task_refs);printf("PASS legacy: %u checks; generic task input still denied\n",checks);return 0;
    }
    uint32_t data=new_bo(c,16384),commands=new_bo(c,16384,GGR_BO_READONLY);
    auto data_m=mapped(c,data),command_m=mapped(c,commands);
    uint64_t data_va=address(c,data),command_va=address(c,commands);
    const uint32_t words[]={0x703d8003u,(uint32_t)data_va,0,0x55667788};
    memcpy(command_m->getBytesNoCopy(),words,sizeof(words));
    uint32_t id=200,layouts=0;
    for(uint32_t bpe:{1u,2u,4u,8u,16u})for(uint32_t bias:{0u,64u,4032u,4096u,16320u,16448u}){
        uint32_t pitch=64*bpe+64,bytes=pitch*64+13;
        auto image=task_image(id++,bytes,bias,bpe,pitch);
        auto pixels=static_cast<TaskPixels *>(image->memory);unsigned maps=map_calls;
        ggr_surface input={};input.surface=image->id;input.handle=UINT32_MAX;
        auto rc=request(c,0x7e,&input);
#ifdef GAUGUIN_DESKTOP_INPUT_OLD_DRIVER
        if(rc!=kIOReturnSuccess){CHECK(rc==kIOReturnUnsupported);printf("OLD driver refuses compositor task description rc=%d\n",rc);return 42;}
#endif
        CHECK(rc==0&&!input.handle&&pixels->prepared==1&&map_calls==maps);
        rc=request(c,0x7e,&input);
#ifdef GAUGUIN_DESKTOP_INPUT_OLD_DRIVER
        if(rc!=kIOReturnSuccess){printf("OLD driver refuses actual compositor task input rc=%d\n",rc);return 42;}
#endif
        CHECK(rc==0&&input.handle&&pixels->prepared==2&&map_calls==maps+1);
        CHECK(input.offset==7&&input.size==bytes&&input.rowBytes==pitch&&input.width==64&&input.height==64);
        uint32_t handle=input.handle;uint64_t va=address(c,handle),start=va&~UINT64_C(4095);
        uint64_t span=(bytes+(va&4095)+4095)&~UINT64_C(4095);
        CHECK((va&4095)==(bias&4095));
        for(uint64_t at=0;at<span;at+=4096)CHECK((*pte(start+at)&0x83)==0x83);
        CHECK(*gpu_word(va)==*(uint32_t *)(pixels->backing->bytes+bias));
        input.handle=0;CHECK(request(c,0x7e,&input)==0&&input.handle==handle&&pixels->prepared==2);
        IOOptionBits options=99;IOMemoryDescriptor *alias=nullptr;
        CHECK(c->clientMemoryForType(handle,&options,&alias)==kIOReturnBadArgument&&!alias&&options==99);
        mock_task=(void *)3;input.handle=0;CHECK(request(c,0x7e,&input)==kIOReturnNotPrivileged);
        CHECK(c->clientMemoryForType(handle,&options,&alias)==kIOReturnNotPrivileged&&!alias&&options==99);
        mock_task=mobile;ggr_cpu_prep prep={};prep.handle=handle;prep.op=2;prep.timeout={1,0};
        CHECK(request(c,0x44,&prep)==kIOReturnBadArgument);prep.op=1;CHECK(request(c,0x44,&prep)==0);
        ggr_submit_bo bos[]={{3,data,data_va},{1,commands,command_va},{3,handle,va}};
        ggr_submit_cmd cmd={1,1,0,sizeof(words),0,0,0};
        struct ggr_submit submit={};submit.flags=0x10;submit.nr_bos=3;submit.nr_cmds=1;
        submit.bos=(uintptr_t)bos;submit.cmds=(uintptr_t)&cmd;submit.fence_fd=-1;
        unsigned submitted=submit_calls;CHECK(request(c,0x46,&submit)==kIOReturnBadArgument&&submit_calls==submitted);
        // Drop the originating task VA/table ownership before the first DMA.
        pixels->originalVAValid=false;surface_table.erase(image->id);image->release();
        bos[2].flags=1;fail_submit=fault;rc=request(c,0x46,&submit);
        CHECK(submit_calls==submitted+1&&map_calls==maps+1&&live_maps==1&&pixels->prepared==2);
        CHECK(*gpu_word(va)==*(uint32_t *)(pixels->backing->bytes+bias));
        if(fault){
            CHECK(rc==kIOReturnTimeout&&!hardware_ready&&image->gpuState==2);
            CHECK(!GauguinGPUSurfaceBegin(image));unsigned freed=frees;
            data_m->release();command_m->release();CHECK(c->clientClose()==0&&gOwner==c);
            CHECK(frees==freed&&pixels->prepared==2&&live_maps==1&&(*pte(start)&0x83)==0x83);
            printf("PASS dma-fault: %u checks; compositor DMA-visible memory retained\n",checks);return 0;
        }
        CHECK(rc==0&&submit.fence&&image->gpuState==0&&*gpu_word(data_va)==0x55667788);
        unsigned freed=frees;ggr_close close={handle,0};CHECK(request(c,9,&close)==0&&frees==freed+1&&!live_maps);
        for(uint64_t at=0;at<span;at+=4096)CHECK(!*pte(start+at));
        ++layouts;
    }
    for(unsigned bad=0;bad<12;bad++){
        auto image=task_image(id++,20493,bad==0?16:64,4,320);
        auto pixels=static_cast<TaskPixels *>(image->memory);
        if(bad==1)image->readOnly=false;
        if(bad==2){image->memoryPrepared=false;pixels->prepared=0;}
        if(bad==3)image->bytesPerRow=255;
        if(bad==4)image->bytesPerElement=3;
        if(bad==5)image->offset=image->allocSize;
        if(bad==6)image->planeCount=2;
        if(bad==7)image->width=0;
        if(bad==8)image->allocSize=GGR_MAX_BO_BYTES+1;
        if(bad==9)pixels->shortSegment=true;
        if(bad==10)pixels->invalidPhysical=true;
        if(bad==11)pixels->badKernelMap=true;
        unsigned synced=sync_calls,submitted=submit_calls;ggr_surface input={};input.surface=image->id;
        CHECK(request(c,0x7e,&input)!=0&&!input.handle&&hardware_ready);
        CHECK(sync_calls==synced&&submit_calls==submitted&&pixels->prepared==(bad==2?0u:1u));
        surface_table.erase(image->id);image->release();CHECK(!live_maps);
    }
    data_m->release();command_m->release();CHECK(c->clientClose()==0&&!gOwner);c->release();
    CHECK(!mock_task_refs&&!live_maps&&!*pte(data_va)&&!*pte(command_va));
    printf("PASS desktop: %u checks; %u layouts, 12 malformed inputs, permissions/early-VA-release/cleanup; host seams only\n",checks,layouts);
    return 0;
}
