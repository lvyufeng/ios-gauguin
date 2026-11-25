#include "Recording340.hpp"
#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <functional>
#include <map>

namespace gauguin340 {
thread_local SubmitData* activeSubmit=nullptr;
thread_local Workspace* activeWorkspace=nullptr;
thread_local uint64_t activeJobSequence=0;
thread_local DrawData* activeDraw=nullptr;
thread_local FineSubmitData* activeGpu=nullptr;
}
using namespace hakios::metal;
#define CHECK(x) do {if(!(x)){std::fprintf(stderr,"BENCH340 line%d %s\n",__LINE__,#x);std::abort();}}while(0)

struct RecordingTransport340 final:Transport {
    std::map<uint32_t,std::vector<unsigned char>> memory;
    std::vector<MsmSubmitBo> last;
    uint32_t next=0,fence=0;unsigned made=0,closed=0,mapped=0,unmapped=0,submitted=0;
    bool reject=false;std::function<void()> reenter;
    int call(uint32_t request,void* data,size_t size) override {
        if(request==kGemNew){CHECK(size==sizeof(MsmGemNew));auto& n=*static_cast<MsmGemNew*>(data);n.handle=++next;memory.emplace(n.handle,std::vector<unsigned char>(n.size));made++;return 0;}
        if(request==kGemInfo){CHECK(size==sizeof(MsmGemInfo));auto& n=*static_cast<MsmGemInfo*>(data);CHECK(memory.count(n.handle));n.value=0x100000000ull+uint64_t(n.handle)*0x10000;return 0;}
        if(request==kGemClose){CHECK(size==sizeof(DrmGemClose));CHECK(memory.erase(static_cast<DrmGemClose*>(data)->handle)==1);closed++;return 0;}
        CHECK(request==kGemSubmit && size==sizeof(MsmGemSubmit));auto& n=*static_cast<MsmGemSubmit*>(data);
        CHECK(n.nr_cmds==1);const auto* c=reinterpret_cast<const MsmSubmitCmd*>(uintptr_t(n.cmds));CHECK(c->submit_idx==0 && c->type==kSubmitCmdBuf);
        const auto* b=reinterpret_cast<const MsmSubmitBo*>(uintptr_t(n.bos));submitted++;
        if(reenter){auto keep=std::vector<MsmSubmitBo>(b,b+n.nr_bos);auto fn=std::move(reenter);fn();CHECK(std::memcmp(b,keep.data(),keep.size()*sizeof(MsmSubmitBo))==0);}
        last.assign(b,b+n.nr_bos);n.fence=++fence;return reject?EIO:0;
    }
    void* map(uint32_t handle,uint64_t size) override {auto& m=memory.at(handle);CHECK(m.size()>=size);mapped++;return m.data();}
    void unmap(uint32_t handle,void* at) override {CHECK(memory.at(handle).data()==at);unmapped++;}
    int64_t nowNs() override {return int64_t(gauguin338::nowNs());}
};

std::vector<MsmSubmitBo> reference(const Bo& command,const std::vector<BoUse>& uses) {
    std::vector<MsmSubmitBo> out{{kSubmitBoRead,command.handle(),command.gpuAddress()}};
    for(const auto& u:uses){if(u.bo==&command)continue;bool seen=false;
        for(auto& b:out)if(b.handle==u.bo->handle()){b.flags|=u.write?kSubmitBoWrite:kSubmitBoRead;seen=true;}
        if(!seen)out.push_back({u.write?kSubmitBoWrite:kSubmitBoRead,u.bo->handle(),u.bo->gpuAddress()});}
    return out;
}
uint64_t checksum(const std::vector<MsmSubmitBo>& values) {
    uint64_t h=1469598103934665603ull;
    for(const auto& v:values)for(uint64_t n:{uint64_t(v.flags),uint64_t(v.handle),v.presumed}){h^=n;h*=1099511628211ull;}
    return h;
}
uint64_t quantile(std::vector<uint64_t> values,unsigned percent) {std::sort(values.begin(),values.end());return values[(values.size()*percent+99)/100-1];}

int main() {
    auto transport=std::make_unique<RecordingTransport340>();auto* raw=transport.get();Gpu gpu(std::move(transport));
    {
        gauguin340::Workspace workspace;gauguin340::WorkspaceScope scope(workspace,1);
        int error=0;auto command=gpu.newBo(4096,kBoWriteCombined,&error);CHECK(command && !error);
        std::vector<std::unique_ptr<Bo>> buffers;
        for(unsigned i=0;i<512;i++){buffers.push_back(gpu.newBo(4096,kBoWriteCombined,&error));CHECK(buffers.back() && !error);}
        for(unsigned unique:{32u,128u,512u}) {
            const unsigned duplicate=unique==32?8:unique==128?16:32;
            std::vector<BoUse> uses{{command.get(),true}};
            for(unsigned i=0;i<unique*duplicate;i++)uses.push_back({buffers[(i*17)%unique].get(),bool((i/unique)&1)});
            const auto expected=reference(*command,uses);std::vector<uint64_t> wall,prep,io,comparisons,growth;
            auto once=[&](bool record){
                gauguin340::FineSubmitData fine;gauguin340::activeGpu=&fine;uint32_t fence=0;
                const auto begin=std::chrono::steady_clock::now();CHECK(gpu.submit(1,*command,0,1,uses,&fence)==0);
                const auto end=std::chrono::steady_clock::now();gauguin340::activeGpu=nullptr;
                CHECK(fence && raw->last.size()==expected.size() && std::memcmp(raw->last.data(),expected.data(),expected.size()*sizeof(MsmSubmitBo))==0);
                CHECK(raw->last[0].flags==kSubmitBoRead && fine.stages.calls==1 && fine.stages.ok==1 && !fine.stages.flags && fine.ioCalls==0);
                if(record){wall.push_back(uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count()));prep.push_back(fine.stages.ns[1]);io.push_back(fine.stages.ns[3]);comparisons.push_back(fine.comparisons);growth.push_back(fine.reuse.values[2]);}
            };
            for(unsigned i=0;i<8;i++)once(false);
            const auto before=raw->submitted;for(unsigned i=0;i<60;i++)once(true);CHECK(raw->submitted-before==60);
            std::printf("BENCH340 {\"enabled\":%d,\"unique\":%u,\"uses\":%zu,\"iterations\":60,\"wire_checksum\":%llu,\"wall_median_ns\":%llu,\"wall_p95_ns\":%llu,\"BO_prepare_median_ns\":%llu,\"transport_stub_median_ns\":%llu,\"comparisons\":%llu,\"capacity_growths_measured\":%llu}\n",
                GAUGUIN_REUSE340_ENABLED,unique,uses.size(),static_cast<unsigned long long>(checksum(expected)),static_cast<unsigned long long>(quantile(wall,50)),
                static_cast<unsigned long long>(quantile(wall,95)),static_cast<unsigned long long>(quantile(prep,50)),static_cast<unsigned long long>(quantile(io,50)),
                static_cast<unsigned long long>(comparisons.back()),static_cast<unsigned long long>(quantile(growth,100)));
            raw->reject=true;uint32_t fence=0xaabbccdd;const auto attempts=raw->submitted;CHECK(gpu.submit(1,*command,0,1,uses,&fence)==EIO && fence==0xaabbccdd && raw->submitted==attempts+1);raw->reject=false;
            CHECK(!workspace.submitting && workspace.bos.empty());
            raw->reenter=[&]{uint32_t nested=0;CHECK(gpu.submit(2,*command,0,1,uses,&nested)==0);};
            CHECK(gpu.submit(1,*command,0,1,uses,&fence)==0 && !workspace.submitting);
            CHECK(raw->last.size()==expected.size() && std::memcmp(raw->last.data(),expected.data(),expected.size()*sizeof(MsmSubmitBo))==0);
        }
    }
    CHECK(raw->made==raw->closed && raw->mapped==raw->unmapped && raw->memory.empty() && gpu.allocatedBytes()==0);
    std::printf("PASS340 actual-Gpu-submit-wire-order-flags-reentry-errors-and-closure\n");return 0;
}
