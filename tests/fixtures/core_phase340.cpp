#include "inherited-prof340.inc"

namespace {
void workspace340(bool unwind) {
    Events events;auto* d=device(events);auto* q=queue(d);
    auto* a=hakios_metal_cb_new(q);auto* b=hakios_metal_cb_new(q);
    CHECK(a && b && a->deferrer==b->deferrer);
    gauguin340::Workspace* saved=nullptr;std::weak_ptr<const void> weak;Signal first,second;
    a->deferrer->post(a,[&]{
        CHECK(gauguin340::activeWorkspace && gauguin340::activeJobSequence);
        saved=gauguin340::activeWorkspace;
        gauguin340::DrawLease draw;draw.get().vs.buffers.resize(16);
        auto owner=std::make_shared<unsigned>(7);weak=owner;draw.get().members.push_back(owner);owner.reset();
        first.set();if(unwind) throw std::runtime_error("340 workspace unwind");
    });
    CHECK(first.wait());(void)hakios_metal_cb_status(a);
    CHECK(weak.expired());
    b->deferrer->post(b,[&]{
        CHECK(gauguin340::activeWorkspace==saved && !saved->drawing && !saved->submitting);
        CHECK(saved->draw.vs.buffers.empty() && saved->draw.vs.buffers.capacity()>=16 && saved->draw.members.empty());
        CHECK(gauguin340::activeSubmit==nullptr && gauguin340::activeDraw==nullptr && gauguin340::activeGpu==nullptr);
        {gauguin340::SubmitLease s;s.seed({1,77,7700},32);s.add({2,78,7800});CHECK(s.mode()==1);}
        CHECK(saved->bos.empty() && saved->bos.capacity()>=32);second.set();
    });
    CHECK(second.wait());(void)hakios_metal_cb_status(b);
    hakios_metal_cb_free(a);hakios_metal_cb_free(b);close(q,d,events);
    CHECK(events.destroyed.wait());
}
}
int main(int argc,char** argv) {
    CHECK(argc==2);const std::string name=argv[1];
    if(name=="workspace-owner") workspace340(false);
    else if(name=="workspace-unwind") workspace340(true);
    else return inherited340_dispatch(argc,argv);
    std::printf("PASS340 %s\n",name.c_str());return 0;
}
