// Compile the actual production transport; only the host IO/close endpoints
// are replaced, so no device/service is opened by this fixture.
#define IOConnectCallStructMethod fakeIo341
#define IOServiceClose fakeClose341
#include "iokit_transport.cpp"
#undef IOConnectCallStructMethod
#undef IOServiceClose
#include <chrono>
#include <thread>
#include <cstdlib>

namespace gauguin341 {
thread_local SubmitData* activeSubmit=nullptr;
thread_local Workspace* activeWorkspace=nullptr;
thread_local uint64_t activeJobSequence=0;
thread_local DrawData* activeDraw=nullptr;
thread_local FineSubmitData* activeGpu=nullptr;
}
static unsigned calls341=0,closes341=0;
static kern_return_t answer341=KERN_SUCCESS;
static bool short341=false;
#define CHECK(x) do {if (!(x)) {std::fprintf(stderr,"IO341 %d %s\n",__LINE__,#x);std::abort();}} while(0)
extern "C" kern_return_t fakeIo341(mach_port_t,uint32_t,const void*,size_t n,void*,size_t* out) {
    calls341++;std::this_thread::sleep_for(std::chrono::milliseconds(2));*out=short341?n-1:n;return answer341;
}
extern "C" kern_return_t fakeClose341(io_connect_t) {closes341++;return KERN_SUCCESS;}
int main() {
    using namespace hakios::metal;
    {
        KernelGpu gpu(0);MsmGemSubmit input{};gauguin341::FineSubmitData good;
        gauguin341::activeGpu=&good;CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==0);
        CHECK(calls341==1 && good.ioCalls==1 && good.cpu.calls==1 && good.cpu.ok==1 && good.cpu.queries==2);
        CHECK(good.cpu.flags==0 && good.ioNs>1000000 && good.cpu.offLower>500000);
        CHECK(gpu.call(kGemNew,&input,sizeof(input))==0);
        CHECK(calls341==2 && good.cpu.queries==2 && good.ioCalls==1);
        answer341=kIOReturnNoMemory;gauguin341::FineSubmitData failed;gauguin341::activeGpu=&failed;
        CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==ENOMEM);
        CHECK(calls341==3 && failed.ioCalls==1 && failed.cpu.ok==1 && failed.cpu.flags==0);
        answer341=KERN_SUCCESS;short341=true;gauguin341::FineSubmitData shortData;gauguin341::activeGpu=&shortData;
        CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==EPROTO);
        CHECK(calls341==4 && shortData.ioCalls==1 && shortData.cpu.ok==1);
        gauguin341::activeGpu=nullptr;
        CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==EPROTO && calls341==5);
    }
    CHECK(closes341==1);std::puts("PASS341 iokit-wrapper");return 0;
}
