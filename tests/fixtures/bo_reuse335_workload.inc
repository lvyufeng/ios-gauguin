int main(){
    hardware_ready=true;CHECK(GauguinGPUStart());
    gMetalBootstrapMode=true;gMetalBootstrap.ready=true;gReleasedRootFence=6;
    pilot_mode=pilot_job=true;mock_task=(void *)2;cache335_host_async=true;
    auto client=new GauguinGPUUserClient;
    CHECK(client->initWithTask(mock_task,nullptr,0,nullptr)&&client->start(IOService::getPlatform()));
    const unsigned initial=allocations-frees,allocated=allocations,synchronized=sync_calls;
    for(unsigned i=0;i<512;i++){
        const uint64_t bytes=16384ull<<(i%3);const uint32_t flags=(i&1)?GGR_BO_READONLY:GGR_BO_WC;
        auto handle=new_bo(client,bytes,flags);CHECK(address(client,handle)>=GGR_VA_START);
        auto memory=mapped(client,handle);
        bool zero=true;for(uint64_t j=0;j<bytes;j++)zero=zero&&memory->bytes[j]==0;
        CHECK(zero&&memory->size==bytes);memset(memory->bytes,int(i%255+1),(size_t)bytes);
        memory->release();ggr_close close={handle,0};CHECK(request(client,0x09,&close)==0);
        printf("OBS iteration=%u handle=%u bytes=%llu flags=%u zero=%u\n",i,handle,(unsigned long long)bytes,flags,zero);
    }
    CHECK(client->clientClose()==0&&!gOwner);client->release();
    CHECK(allocations-frees==initial&&mock_task_refs==0);
    printf("COUNTS backing=%u sync=%u\n",allocations-allocated,sync_calls-synchronized);
}
