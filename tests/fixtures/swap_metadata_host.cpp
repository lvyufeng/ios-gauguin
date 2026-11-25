    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(130,0x12345678);
        auto input=record(130,0x80000007u);
        if(!fb.swap(input.data(),&a)){
            closeCreator(s);empty();
            std::fputs("FAIL background update bit31 rejected a valid low-layer handoff\n",stderr);return 42;
        }
        check(users(130)==2&&fb.fHeldPending.surfaces[0]==s);
        check(std::memcmp(fb.fHeldPending.record,input.data(),input.size())==0);
        closeCreator(s);sweet_fb_frame frame={};check(take(fb,frame));view(frame,0x12345678);
        fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};
        SweetSurface *surfaces[4];for(unsigned i=0;i<4;i++)surfaces[i]=publish(130+i,0xff000000u+i);
        for(uint32_t background: {0u,0x80000000u})for(uint32_t bits=0;bits<16;bits++){
            auto input=record(130,background|bits);
            for(unsigned i=0;i<4;i++)word(input,0x54+4*i,130+i);
            auto original=input;check(fb.swap(input.data(),&a));check(input==original);
            check(std::memcmp(fb.fHeldPending.record,input.data(),input.size())==0);
            for(unsigned i=0;i<4;i++){
                check(fb.fHeldPending.surfaces[i]==((bits&(1u<<i))?surfaces[i]:nullptr));
                check(users(130+i)==1+unsigned(bool(bits&(1u<<i))));
            }
            sweet_fb_frame frame={};check(take(fb,frame));
            for(unsigned i=0;i<4;i++){
                if(bits&(1u<<i))view(frame,0xff000000u+i,i);
                else check(sweet_fb_present_surface(frame.record,frame.surfaces,i)==nullptr);
            }
            fb.finishHeldFrame(&frame);accounting(fb);
            for(unsigned i=0;i<4;i++)check(users(130+i)==1);
        }
        auto pending=record(130,0x80000001u);check(fb.swap(pending.data(),&a));
        for(uint32_t background: {0u,0x80000000u})for(unsigned bit=4;bit<31;bit++){
            auto bad=record(130,background|1u|(1u<<bit));auto original=bad;
            check(!fb.swap(bad.data(),&a)&&bad==original);
            check(users(130)==2&&surfaces[0]->refs==3&&fb.fHeldPending.surfaces[0]==surfaces[0]);
            check(std::memcmp(fb.fHeldPending.record,pending.data(),pending.size())==0);
        }
        check(fb.fHeldRejectReasons[2]==54);
        check(!fb.swap(record(130,0xffffffffu).data(),&a)&&fb.fHeldRejectReasons[2]==55);
        uint32_t reason=0;sweet_fb_frame scratch={};
        check(!sweet_fb_frame_prepare(&scratch,record(130,0x80000003u,134).data(),&a,&reason)&&reason==4);
        check(scratch.owner==nullptr&&users(130)==2&&surfaces[0]->refs==3);
        check(!fb.swap(pending.data(),&b)&&fb.fHeldRejectReasons[7]==1);
        check(!fb.swap(pending.data(),nullptr)&&fb.fHeldRejectReasons[7]==2);
        check(!sweet_fb_frame_prepare(&scratch,pending.data(),nullptr,&reason)&&reason==1);
        for(auto *surface:surfaces)closeCreator(surface);
        check(live==1&&users(130)==1);sweet_fb_frame frame={};check(take(fb,frame));
        view(frame,0xff000000u);fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
