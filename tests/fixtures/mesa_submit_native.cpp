/* Compile the actual native submit method. IO/memory/ring execution is fake;
 * original BO permissions, ranges, complete validation and result flow remain. */
#include <IOKit/IOReturn.h>
#include <stdint.h>
#include <string.h>
#include <new>
#include <atomic>
#include @KERNEL_HEADER@
struct SweetSurface { unsigned gpuState;uintptr_t kernelAddress(){return 0;} };
struct gpu_buffer {uint32_t handle,flags;uint64_t address,size;SweetSurface *surface;};
struct gpu_queue {uint32_t id,completed;};
static unsigned jobs;static bool fail_timeout;
static int copyin(uint64_t p,void*d,size_t n){memcpy(d,(const void*)(uintptr_t)p,n);return 0;}
static void memoryBarrier(){std::atomic_thread_fence(std::memory_order_seq_cst);}
static void flush_dcache64(uintptr_t,unsigned,int){}
bool sweet_gpu_runtime_submit(const uint64_t*,const uint32_t*,uint32_t n,uint32_t*f){++jobs;if(!n||fail_timeout)return false;*f=jobs;return true;}
void sweet_gpu_runtime_stop(){}
#define IONew(type,n) new(std::nothrow) type[n]
#define IODelete(p,type,n) delete[] p
class GauguinGPUUserClient {
public:
    gpu_buffer bos[32]={};unsigned count=0;gpu_queue q={1,0};uint32_t fNativeFence=0;
    gpu_queue *queue(uint32_t id){return id==1?&q:nullptr;}
    gpu_buffer *find(uint32_t id){for(unsigned i=0;i<count;i++)if(bos[i].handle==id)return &bos[i];return nullptr;}
    IOReturn submit(struct ggr_submit*);
};
@NATIVE_SUBMIT_FUNCTION@
static GauguinGPUUserClient client;
extern "C" void native_reset(){client=GauguinGPUUserClient();jobs=0;fail_timeout=false;}
extern "C" void native_add(unsigned handle,unsigned long long size,unsigned flags){auto*b=client.find(handle);if(b){b->flags=flags;b->size=size;return;}if(client.count>=32)__builtin_trap();client.bos[client.count++]={handle,flags,0x40000000ULL+handle*0x100000ULL,size,nullptr};}
extern "C" unsigned native_submit(struct ggr_submit*s){return client.submit(s);}
extern "C" unsigned native_jobs(){return jobs;}
extern "C" unsigned native_wait(unsigned queue,unsigned fence){return queue==1&&fence&&fence<=client.q.completed?kIOReturnSuccess:kIOReturnBadArgument;}
extern "C" void native_timeout(int b){fail_timeout=b!=0;}
