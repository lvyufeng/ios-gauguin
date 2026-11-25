#include "Recording340.hpp"
#include <atomic>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <thread>

static std::atomic<bool> failAllocation340{false};
void* operator new(std::size_t n) {
    if (failAllocation340.exchange(false)) throw std::bad_alloc();
    if (void* p=std::malloc(n?n:1)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void* operator new[](std::size_t n) {return ::operator new(n);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}

namespace gauguin340 {
thread_local SubmitData* activeSubmit=nullptr;
thread_local Workspace* activeWorkspace=nullptr;
thread_local uint64_t activeJobSequence=0;
thread_local DrawData* activeDraw=nullptr;
thread_local FineSubmitData* activeGpu=nullptr;
}
using namespace gauguin340;
#define CHECK(x) do {if (!(x)) {std::fprintf(stderr,"CHECK340 line%d: %s\n",__LINE__,#x);std::abort();}} while(0)

std::vector<MsmSubmitBo> reference(const std::vector<MsmSubmitBo>& input) {
    std::vector<MsmSubmitBo> out{input[0]};
    for (size_t i=1;i<input.size();i++) {
        bool seen=false;
        for (auto& b:out) if (b.handle==input[i].handle) {b.flags|=input[i].flags;seen=true;}
        if (!seen) out.push_back(input[i]);
    }
    return out;
}
void equal(const std::vector<MsmSubmitBo>& a,const std::vector<MsmSubmitBo>& b) {
    CHECK(a.size()==b.size());CHECK(std::memcmp(a.data(),b.data(),a.size()*sizeof(MsmSubmitBo))==0);
}
void lists(bool collide,bool oversize) {
    Workspace w;WorkspaceScope scope(w,7);ReuseCounts counts;
    std::vector<MsmSubmitBo> values{{1,0,0x1234}};
    uint32_t seed=12345;const unsigned unique=oversize?1500:257;
    for (unsigned i=0;i<6000;i++) {
        seed=1664525u*seed+1013904223u;uint32_t key=(seed%unique)*(collide?2048u:1u);
        values.push_back({1u+unsigned(i%2),key,uint64_t(i)+0x10000});
    }
    auto expected=reference(values);
    for (unsigned round=0;round<2;round++) {
        SubmitLease lease(&counts);lease.seed(values[0],1024);
        for (size_t i=1;i<values.size();i++) lease.add(values[i]);
        equal(lease.get(),expected);CHECK(lease.get()[0].handle==0 && lease.get()[0].presumed==0x1234);
        CHECK(lease.mode()==(oversize?2u:1u));
    }
    CHECK(!w.submitting && w.bos.empty());CHECK(w.bos.capacity()<=boCapacity);
    CHECK(counts.values[0]==2 && !counts.flags);
    if (oversize) CHECK(counts.values[3]==2 && w.bos.capacity()==0);
    else CHECK(counts.values[2]==1);
}

void reentry() {
    Workspace w;WorkspaceScope scope(w,1);
    {
        SubmitLease outer;outer.seed({1,7,700},64);outer.add({2,8,800});auto expected=outer.get();
        {SubmitLease inner;CHECK(inner.mode()==0);inner.seed({1,99,9900},8);inner.add({2,7,7777});}
        equal(outer.get(),expected);CHECK(w.submitting);
        DrawLease d;CHECK(d.borrowed());d.get().vs.sharedBytes=123;
        {DrawLease nested;CHECK(!nested.borrowed());nested.get().vs.sharedBytes=456;}
        CHECK(d.get().vs.sharedBytes==123 && w.drawing);
    }
    CHECK(!w.drawing && !w.submitting && w.draw.vs.sharedBytes==0);
}

void drawReset(bool exception) {
    Workspace w;ReuseCounts counts;std::weak_ptr<const void> weak;
    for (unsigned round=0;round<2;round++) {
        try {
            WorkspaceScope scope(w,round+1);DrawLease lease(&counts);auto& d=lease.get();
            CHECK(d.vs.buffers.empty() && d.fs.textures.empty() && d.members.empty());
            CHECK(d.vs.sharedBytes==0 && d.fs.nullMask==0);
            d.vs.buffers.resize(16);d.vs.textures.resize(8);d.fs.samplers.resize(16);
            d.vs.sharedBytes=123;d.fs.nullMask=456;
            auto owner=std::make_shared<unsigned>(99);weak=owner;d.members.push_back(owner);owner.reset();
            if (exception) throw std::runtime_error("intentional draw unwind");
        } catch (const std::runtime_error&) {CHECK(exception);}
        CHECK(weak.expired() && !w.drawing && activeWorkspace==nullptr && activeJobSequence==0);
    }
    CHECK(counts.values[0]==2 && counts.values[2]==4 && counts.values[3]==0);
}

void failures() {
    Workspace w;WorkspaceScope scope(w,55);
    {SubmitLease lease;failAllocation340=true;lease.seed({1,1,100},1024);CHECK(lease.reserveFailures==1);lease.add({2,2,200});CHECK(lease.get().size()==2);}
    try {DrawLease lease;failAllocation340=true;lease.get().vs.buffers.resize(16);CHECK(false);} catch (const std::bad_alloc&) {}
    CHECK(!w.submitting && !w.drawing && w.draw.vs.buffers.empty());
    ReuseCounts counts;
    {DrawLease lease(&counts);lease.get().vs.buffers.resize(bindingCapacity+1);lease.get().members.resize(bindingCapacity+1);}
    CHECK(counts.values[3]==2 && w.draw.vs.buffers.capacity()==0 && w.draw.members.capacity()==0);
    Workspace inner;
    try {WorkspaceScope nested(inner,66);throw std::runtime_error("workspace unwind");} catch (const std::runtime_error&) {}
    CHECK(activeWorkspace==&w && activeJobSequence==55);
}

uint64_t clock340=100;
uint64_t fakeClock340() {return clock340;}
void phases() {
    Workspace w;WorkspaceScope scope(w,17);Times<8> t;
    {TimeProbe<8> p(&t,fakeClock340);for (unsigned i=1;i<8;i++){clock340+=10;p.phase(i);}clock340+=10;p.complete();}
    CHECK(t.calls==1 && t.ok==1 && t.failed==0 && t.flags==0 && t.worst==80 && t.worstJob==17);
    for (auto n:t.ns) CHECK(n==10);
    FineSubmitData g;clock340=200;
    {IoProbe p(&g,fakeClock340);clock340=240;}
    CHECK(g.ioCalls==1 && g.ioBegin==200 && g.ioEnd==240 && g.ioNs==40 && !g.flags);
    {IoProbe p(&g,fakeClock340);clock340++;} CHECK(g.flags&fineIo);
}

void threads() {
    std::atomic<unsigned> ready{0};std::atomic<bool> go{false};
    auto run=[&](uint32_t id) {Workspace w;WorkspaceScope scope(w,id);ready++;while(!go.load()) std::this_thread::yield();
        SubmitLease lease;lease.seed({1,id,id*1000ull},16);lease.add({2,id+1,777});CHECK(activeWorkspace==&w && activeJobSequence==id && lease.get()[0].handle==id);};
    std::thread a(run,100),b(run,200);while(ready.load()!=2) std::this_thread::yield();go=true;a.join();b.join();
    CHECK(activeWorkspace==nullptr && activeJobSequence==0);
}

int main(int argc,char** argv) {
    CHECK(argc==2);const std::string name=argv[1];
    if(name=="ordered") lists(false,false);
    else if(name=="collisions") lists(true,false);
    else if(name=="oversize") lists(false,true);
    else if(name=="reentry") reentry();
    else if(name=="draw-reset") drawReset(false);
    else if(name=="draw-unwind") drawReset(true);
    else if(name=="allocation") failures();
    else if(name=="phases") phases();
    else if(name=="threads") threads();
    else CHECK(false);
    std::printf("PASS340 %s\n",name.c_str());return 0;
}
