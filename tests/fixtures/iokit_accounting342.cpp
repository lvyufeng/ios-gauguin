// Compile the actual production transport; only the host IO/close endpoints
// are replaced, so no device/service is opened by this fixture.
#define IOConnectCallStructMethod fakeIo342
#define IOServiceClose fakeClose342
#include "iokit_transport.cpp"
#undef IOConnectCallStructMethod
#undef IOServiceClose
#include <chrono>
#include <thread>
#include <cstdlib>

namespace gauguin342 {
thread_local SubmitData* activeSubmit=nullptr;
thread_local Workspace* activeWorkspace=nullptr;
thread_local uint64_t activeJobSequence=0;
thread_local DrawData* activeDraw=nullptr;
thread_local FineSubmitData* activeGpu=nullptr;
}
static unsigned calls342=0,closes342=0;
static kern_return_t answer342=KERN_SUCCESS;
static bool short342=false;
#define CHECK(x) do {if (!(x)) {std::fprintf(stderr,"IO342 %d %s\n",__LINE__,#x);std::abort();}} while(0)
extern "C" kern_return_t fakeIo342(mach_port_t,uint32_t,const void*,size_t n,void*,size_t* out) {
    calls342++;std::this_thread::sleep_for(std::chrono::milliseconds(2));*out=short342?n-1:n;return answer342;
}
extern "C" kern_return_t fakeClose342(io_connect_t) {closes342++;return KERN_SUCCESS;}
int main() {
    using namespace hakios::metal;
    {
        KernelGpu gpu(0);MsmGemSubmit input{};gauguin342::FineSubmitData good;
        gauguin342::activeGpu=&good;CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==0);
        CHECK(calls342==1 && good.ioCalls==1 && good.cpu.calls==1 && good.cpu.ok==1 && good.cpu.queries==2);
        CHECK(good.cpu.flags==0 && good.ioNs>1000000 && good.cpu.offLower>500000);
        CHECK(gpu.call(kGemNew,&input,sizeof(input))==0);
        CHECK(calls342==2 && good.cpu.queries==2 && good.ioCalls==1);
        answer342=kIOReturnNoMemory;gauguin342::FineSubmitData failed;gauguin342::activeGpu=&failed;
        CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==ENOMEM);
        CHECK(calls342==3 && failed.ioCalls==1 && failed.cpu.ok==1 && failed.cpu.flags==0);
        answer342=KERN_SUCCESS;short342=true;gauguin342::FineSubmitData shortData;gauguin342::activeGpu=&shortData;
        CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==EPROTO);
        CHECK(calls342==4 && shortData.ioCalls==1 && shortData.cpu.ok==1);
        gauguin342::activeGpu=nullptr;
        CHECK(gpu.call(kGemSubmit,&input,sizeof(input))==EPROTO && calls342==5);
    }
    CHECK(closes342==1);std::puts("PASS342 iokit-wrapper");return 0;
}
