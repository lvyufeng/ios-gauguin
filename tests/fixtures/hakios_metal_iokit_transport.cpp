// SPDX-License-Identifier: MIT
// Executes production iokit_transport.cpp against bounded IOKit stubs.
#include <IOKit/IOKitLib.h>
#include <mach/mach.h>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "hakios-metal/gpu.hpp"

extern "C" const mach_port_t kIOMainPortDefault = MACH_PORT_NULL;

static size_t replyBytes = 24;
static mach_vm_size_t mappedBytes = 65536;
static mach_vm_address_t mappedAddress = 0x100000;
static kern_return_t methodResult = KERN_SUCCESS, mapResult = KERN_SUCCESS;
static unsigned unmaps, closes, releases;
static bool servicePresent = true;
static unsigned checks;
#define VERIFY(c,m) do { ++checks; if (!(c)) { std::fprintf(stderr,"FAIL %s\n",m); return 2; } } while (0)

extern "C" CFMutableDictionaryRef IOServiceMatching(const char* name) {
    if (std::strcmp(name,"HakiosGPU")) std::abort();
    return reinterpret_cast<CFMutableDictionaryRef>(uintptr_t(1));
}
extern "C" io_service_t IOServiceGetMatchingService(mach_port_t,CFDictionaryRef) { return servicePresent ? 7 : 0; }
extern "C" kern_return_t IOServiceOpen(io_service_t,mach_port_t,uint32_t,io_connect_t* c) { *c=9; return KERN_SUCCESS; }
extern "C" kern_return_t IOObjectRelease(io_object_t) { ++releases; return KERN_SUCCESS; }
extern "C" kern_return_t IOServiceClose(io_connect_t) { ++closes; return KERN_SUCCESS; }
extern "C" kern_return_t IOConnectCallStructMethod(mach_port_t,uint32_t,const void*,size_t,void*,size_t* bytes) {
    *bytes=replyBytes; return methodResult;
}
extern "C" kern_return_t IOConnectMapMemory64(io_connect_t,uint32_t,task_port_t,mach_vm_address_t* address,mach_vm_size_t* bytes,IOOptionBits) {
    *address=mappedAddress; *bytes=mappedBytes; return mapResult;
}
extern "C" kern_return_t IOConnectUnmapMemory64(io_connect_t,uint32_t,task_port_t,mach_vm_address_t) { ++unmaps; return KERN_SUCCESS; }

int main() {
    using namespace hakios::metal;
    std::string why;
    auto t=openKernelGpu(&why); VERIFY(t!=nullptr,"matching provider");
    MsmParam p{};
    VERIFY(t->call(kGetParam,&p,sizeof(p))==0,"complete reply");
    replyBytes=sizeof(p)-1;
    VERIFY(t->call(kGetParam,&p,sizeof(p))==EPROTO,"short reply rejected");
    replyBytes=sizeof(p)+1;
    VERIFY(t->call(kGetParam,&p,sizeof(p))==EPROTO,"oversized reply rejected");
    methodResult=kIOReturnNoMemory;
    VERIFY(t->call(kGetParam,&p,sizeof(p))==ENOMEM,"kernel error preserved");
    methodResult=KERN_SUCCESS;
    VERIFY(t->map(4,65536)==reinterpret_cast<void*>(mappedAddress),"complete mapping");
    mappedBytes=32768;
    VERIFY(t->map(4,65536)==nullptr && unmaps==1,"short mapping unmapped and rejected");
    mappedBytes=131072;
    VERIFY(t->map(4,65536)==reinterpret_cast<void*>(mappedAddress),"page-rounded mapping accepted");
    mappedAddress=0;
    VERIFY(t->map(4,65536)==nullptr && unmaps==1,"zero address rejected");
    mapResult=kIOReturnNoMemory;
    VERIFY(t->map(4,65536)==nullptr,"map error preserved");
    t.reset(); VERIFY(closes==1 && releases==1,"connection lifetime");
    servicePresent=false;
    VERIFY(openKernelGpu(&why)==nullptr && !why.empty(),"missing provider refused");
    std::printf("%u production IOKit transport checks\n",checks);
}
