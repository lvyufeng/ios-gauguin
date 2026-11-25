/* Actual IOUserClient dispatch/ownership; only hardware/IOKit transport modeled. MIT. */
int main(int argc,char **argv)
{
    const char *scenario=argc>1?argv[1]:"good";
#ifdef GAUGUIN_BOOTSTRAP_OLD_DRIVER
    const IOReturn shape_error=kIOReturnUnsupported;
#else
    const IOReturn shape_error=kIOReturnBadArgument;
#endif
    pilot_mode=true;bootstrap_host_mode=true;pilot_job=true;
    CHECK(!GauguinGPUStart());hardware_ready=true;CHECK(GauguinGPUStart());
    auto c=new GauguinGPUUserClient;
    CHECK(c->initWithTask(kernel_task,nullptr,0,nullptr)&&c->start(IOService::getPlatform()));
    ggr_bootstrap early={1,0,0,0,0};CHECK(request(c,GGR_BOOTSTRAP_SELECTOR,&early)!=0);
    uint32_t data=new_bo(c,16384),commands=new_bo(c,16384,GGR_BO_READONLY);
    auto data_m=mapped(c,data),command_m=mapped(c,commands);
    uint64_t data_va=address(c,data),command_va=address(c,commands);
    auto words=(uint32_t *)command_m->getBytesNoCopy();
    uint32_t cmdwords[]={0x703d8003u,(uint32_t)data_va,0,0x11223344};
    memcpy(words,cmdwords,sizeof(cmdwords));
    ggr_submit_bo bos[]={{3,data,data_va},{1,commands,command_va}};
    ggr_submit_cmd cmd={1,1,0,sizeof(cmdwords),0,0,0};
    struct ggr_submit s={};s.flags=0x10;s.nr_bos=2;s.nr_cmds=1;s.bos=(uintptr_t)bos;s.cmds=(uintptr_t)&cmd;s.fence_fd=-1;
    for(unsigned n=1;n<=8;n++) {
        s.fence=0;CHECK(request(c,0x46,&s)==0 && s.fence==n);
        CHECK(*gpu_word(data_va)==0x11223344);
    }
    ggr_bootstrap arm={1,8,0,0,0};
    for(int shape=1;shape<=4;shape++)CHECK(request(c,GGR_BOOTSTRAP_SELECTOR,&arm,shape)==shape_error);
    for(unsigned field=0;field<5;field++) {
        auto bad=arm;
        if(field==0)bad.version=2;if(field==1)bad.checks=7;if(field==2)bad.reserved=1;
        if(field==3)bad.fence=8;if(field==4)bad.epoch=1;
        CHECK(request(c,GGR_BOOTSTRAP_SELECTOR,&bad)!=0);
    }
    task_t mobile=(void *)2;
    auto denied=new GauguinGPUUserClient;mock_task=mobile;
    CHECK(denied->initWithTask(mobile,nullptr,0,nullptr)&&!denied->start(IOService::getPlatform()));
    denied->release();mock_task=kernel_task;
    auto rc=request(c,GGR_BOOTSTRAP_SELECTOR,&arm);
    if(rc!=0){fprintf(stderr,"bootstrap arm unsupported by original driver rc=%d\n",rc);return 42;}
    CHECK(arm.epoch==1 && arm.fence==8 && arm.checks==8);
    if(!strcmp(scenario,"duplicate")) {
        auto duplicate=ggr_bootstrap{1,8,0,0,0};CHECK(request(c,GGR_BOOTSTRAP_SELECTOR,&duplicate)!=0);
    }
    if(!strcmp(scenario,"after-arm"))CHECK(request(c,0x46,&s)==kIOReturnNotPrivileged);
    if(!strcmp(scenario,"fault"))hardware_ready=false;
    data_m->release();command_m->release();CHECK(c->clientClose()==0);
    mock_task=mobile;auto client=new GauguinGPUUserClient;
    CHECK(client->initWithTask(mobile,nullptr,0,nullptr));
    bool expected=!strcmp(scenario,"good");
    CHECK(client->start(IOService::getPlatform())==expected);
    if(expected) {
        ggr_bootstrap forbidden={1,8,0,0,0};
        CHECK(request(client,GGR_BOOTSTRAP_SELECTOR,&forbidden)==kIOReturnNotPrivileged);
        CHECK(client->clientClose()==0);client->release();mock_task=kernel_task;
        auto root=new GauguinGPUUserClient;
        CHECK(root->initWithTask(kernel_task,nullptr,0,nullptr)&&root->start(IOService::getPlatform()));
        mock_task=mobile;auto second=new GauguinGPUUserClient;
        CHECK(second->initWithTask(mobile,nullptr,0,nullptr)&&!second->start(IOService::getPlatform()));
        second->release();mock_task=kernel_task;
        CHECK(root->clientClose()==0);root->release();
        mock_task=mobile;second=new GauguinGPUUserClient;
        CHECK(second->initWithTask(mobile,nullptr,0,nullptr)&&!second->start(IOService::getPlatform()));
        second->release();
    } else client->release();
    if(strcmp(scenario,"fault"))c->release(); /* fault retains DMA-visible owner until reset */
    printf("PASS %s: %u actual bootstrap dispatcher/owner checks; modeled hardware\n",scenario,checks);
    return 0;
}
