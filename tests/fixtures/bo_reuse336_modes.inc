    if(mode=="policy-single"||mode=="policy-wave"||mode=="policy-alias"||mode=="policy-fault"){
        // Warm 32 different, completed classes, then introduce a hot new class.
        for(unsigned i=1;i<=32;i++)close_bo(c,new_bo(c,i*16384,GGR_BO_WC));
        CHECK(BC335Host::slots(c)==32&&BC335Host::bytes(c)==8650752);
        if(mode=="policy-single"||mode=="policy-wave"){
            unsigned start_alloc=allocations,start_sync=sync_calls;
            unsigned width=mode=="policy-wave"?8:1,waves=512/width,index=0;
            for(unsigned wave=0;wave<waves;wave++){
                std::vector<uint32_t> handles;
                for(unsigned j=0;j<width;j++){
                    auto h=new_bo(c,1048576,GGR_BO_WC);auto m=mapped(c,h);
                    CHECK(m->size==1048576&&address(c,h)>=GGR_VA_START);
                    for(unsigned k=0;k<m->size;k++)CHECK(m->bytes[k]==0);
                    memset(m->bytes,0x5a,(size_t)m->size);m->release();
                    std::printf("OBS %u %u 1048576 %u zero=1\n",index++,h,GGR_BO_WC);
                    handles.push_back(h);
                }
                for(auto h:handles){
                    unsigned sync_before=sync_calls;close_bo(c,h);
                    CHECK(sync_calls-sync_before<=1); // never flush many cached mappings
                }
                CHECK(BC335Host::slots(c)==32&&BC335Host::bytes(c)<=16777216);
            }
            unsigned expected=BC336_POLICY?width:512;
            CHECK(allocations-start_alloc==expected&&sync_calls-start_sync==expected*2);
            CHECK(gCache335.hits==(BC336_POLICY?512-width:0));
            CHECK(gCache335.evicts==(BC336_POLICY?width:0));
            std::printf("HOT backing=%u sync=%u hits=%llu\n",allocations-start_alloc,
                sync_calls-start_sync,(unsigned long long)gCache335.hits);
        }else if(mode=="policy-alias"){
            auto h=new_bo(c,1048576,GGR_BO_WC);auto alias=mapped(c,h);
            memset(alias->bytes,0xc7,1048576);auto evicted=gCache335.evicts;
            close_bo(c,h);CHECK(gCache335.aliases==1&&gCache335.evicts==evicted);
            CHECK(BC335Host::slots(c)==32&&BC335Host::bytes(c)==8650752);
            auto fresh=new_bo(c,1048576,GGR_BO_WC);auto m=mapped(c,fresh);CHECK(m!=alias);
            for(unsigned k=0;k<1048576;k++)CHECK(alias->bytes[k]==0xc7&&m->bytes[k]==0);
            alias->release();m->release();close_bo(c,fresh);
        }else{
            auto h=new_bo(c,1048576,GGR_BO_WC);unsigned freed=frees;
            fail_sync=true;ggr_close close={h,0};
            CHECK(request(c,0x09,&close)==kIOReturnNotReady&&!hardware_ready);
            CHECK(frees==freed&&BC335Host::slots(c)==32&&gCache335.evicts==0);
            auto active=BC335Host::live(c,h);CHECK(active&&active->memory&&!active->cached);
            ggr_new refused={16384,0,0};CHECK(request(c,0x42,&refused)==kIOReturnNotReady);
            std::puts("PASS policy-fault: original DMA owners retained after one failed removal");
            return 0; // Deliberate fault escrow; no unsafe teardown.
        }
    }else if(mode=="policy-bytes"){
        std::vector<uint32_t> handles;
        for(unsigned i=0;i<32;i++)handles.push_back(new_bo(c,524288,GGR_BO_WC));
        for(auto h:handles)close_bo(c,h);
        CHECK(BC335Host::slots(c)==32&&BC335Host::bytes(c)==16777216);
        // One old 512KiB mapping cannot admit a 1MiB class. Preserve release-new
        // instead of introducing two removals or flushing the whole cache.
        auto large=new_bo(c,1048576,GGR_BO_WC);unsigned synced=sync_calls;
        close_bo(c,large);CHECK(sync_calls==synced+1&&gCache335.evicts==0);
        CHECK(BC335Host::slots(c)==32&&BC335Host::bytes(c)==16777216);
        auto small=new_bo(c,65536,GGR_BO_WC);synced=sync_calls;close_bo(c,small);
        CHECK(sync_calls==synced+1&&gCache335.evicts==(BC336_POLICY?1:0));
        CHECK(BC335Host::bytes(c)==(BC336_POLICY?16318464:16777216));
        unsigned before=allocations;auto next=new_bo(c,65536,GGR_BO_WC);
        CHECK(allocations==before+(BC336_POLICY?0:1));close_bo(c,next);
    }else
