#include "program342-methods.inc"

namespace {
struct AllocTransport342 : Transport {
    unsigned mode,calls=0,maps=0,unmaps=0,closes=0;uint32_t events[8]{};unsigned used=0;
    uint8_t memory[16384]{};
    explicit AllocTransport342(unsigned m):mode(m){}
    int call(uint32_t request,void* data,size_t)override {
        ++calls;CHECK(used<8);events[used++]=request;
        if(request==kGemNew){if(mode==1)return ENOMEM;static_cast<MsmGemNew*>(data)->handle=17;return 0;}
        if(request==kGemInfo){if(mode==2)return EINVAL;static_cast<MsmGemInfo*>(data)->value=0x20000;return 0;}
        CHECK(request==kGemClose);CHECK(static_cast<DrmGemClose*>(data)->handle==17);++closes;return 0;
    }
    void* map(uint32_t handle,uint64_t bytes)override {CHECK(handle==17&&bytes==16384);++maps;return mode==3?nullptr:memory;}
    void unmap(uint32_t handle,void* pointer)override {CHECK(handle==17&&pointer==memory);++unmaps;}
    int64_t nowNs()override {return 1000000;}
};
void allocationCase342(unsigned mode){
    auto transport=std::make_unique<AllocTransport342>(mode);auto* t=transport.get();Gpu gpu(std::move(transport));
    gauguin342::DrawData data;int error=0;
    {ProgramScope342 scope(data);gauguin342::ProgramAllocationScope program(&data.program.newBo);auto bo=gpu.newBo(4096,0,&error);
        CHECK(bool(bo)==(mode==0));
        if(bo){CHECK(!error&&bo->handle()==17&&bo->size()==16384);bo.reset();}
    }
    const auto& n=data.program.newBo;CHECK(n.calls==1&&n.ok==(mode?0u:1u)&&n.failed==(mode?1u:0u));
    CHECK(!n.flags&&!n.maximum.flags&&n.maxJob==101&&n.maxTid);
    CHECK(n.maximum.last>=n.maximum.first);
    uint64_t total=n.queryWall;
    for(unsigned i=0;i<6;i++){CHECK(n.wall[i]==n.maximum.end[i]-n.maximum.begin[i]);total+=n.wall[i];}
    CHECK(total==n.maximum.last-n.maximum.first);
    CHECK(t->events[0]==kGemNew&&t->closes==(mode==1?0u:1u));
    CHECK(t->maps==(mode<2?unsigned(mode==0):unsigned(mode==3))&&t->unmaps==unsigned(mode==0));
    if(mode==0){CHECK(n.maximum.mask==31&&n.queries==6&&n.maxHandle==17&&n.maxBytes==16384);CHECK(t->calls==3);}
    if(mode==1){CHECK(error==ENOMEM&&n.maximum.mask==3&&n.queries==3&&t->calls==1);}
    if(mode==2){CHECK(error==EINVAL&&n.maximum.mask==39&&n.queries==5&&t->calls==3);}
    if(mode==3){CHECK(error==ENOMEM&&n.maximum.mask==47&&n.queries==6&&t->calls==3);}
}
}
int main(int argc,char** argv){CHECK(argc==2);allocationCase342(unsigned(std::strtoul(argv[1],nullptr,10)));std::puts("PASS342 actual newBo stages, identity and exact failure cleanup");}
