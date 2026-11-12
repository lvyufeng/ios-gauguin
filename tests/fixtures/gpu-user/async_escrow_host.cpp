/* Minimal IOKit boundary for the actual GauguinGPUUserClient completion and
 * deferred-close method bodies inserted below. No device or GPU emulation. */
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>

#define GGR_MAX_CLIENT_BUFFERS 1024u
#define GGR_MAX_BUFFERS 256u
#define NSEC_PER_SEC 1000000000u
#define GUT_SURFACE 14
using IOReturn=int;
constexpr IOReturn kIOReturnSuccess=0;
constexpr IOReturn kIOReturnNotReady=1;
constexpr IOReturn kIOReturnTimeout=2;
enum ggr_error {GGR_OK,GGR_ARGUMENT,GGR_UNAVAILABLE,GGR_IO,GGR_TIMEOUT,GGR_PENDING};
struct ggr_timespec {int64_t seconds,nanoseconds;};

static unsigned cases,stops,drops,flushes,polls,waits,delays;
static uint64_t continuous_ns;
static bool runtime_ready;
static enum ggr_error poll_result=GGR_PENDING,wait_result=GGR_PENDING;
#define CHECK(x) do {++cases;assert(x);} while(0)
static void memoryBarrier(void) {}
static uint64_t mach_continuous_time(void) {return continuous_ns;}
static void absolutetime_to_nanoseconds(uint64_t value,uint64_t *out) {*out=value;}
static void IODelay(unsigned us) {++delays;continuous_ns+=(uint64_t)us*1000;}
static enum ggr_error sweet_gpu_runtime_poll(uint32_t) {++polls;return poll_result;}
static enum ggr_error sweet_gpu_runtime_wait(uint32_t) {++waits;return wait_result;}
static bool sweet_gpu_runtime_ready(void) {return runtime_ready;}
static void sweet_gpu_runtime_stop(void) {++stops;runtime_ready=false;}
static void flush_dcache64(uintptr_t,unsigned,int) {++flushes;}
static void sweet_ui_trace_record(int,uint64_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t) {}

struct SweetSurface {
    uint32_t id,gpuState;
    char pixels[16];
    bool aliasReady=true;
    uintptr_t kernelAddress(void) {return aliasReady?reinterpret_cast<uintptr_t>(pixels):0;}
};
struct gpu_buffer {
    void *memory;
    SweetSurface *surface;
    uint32_t flags;
    uint64_t size;
    bool pending,closePending;
};
struct gpu_queue {uint32_t id,issued,completed;};
class GauguinGPUUserClient {
public:
    gpu_buffer fBuffers[GGR_MAX_CLIENT_BUFFERS]{};
    gpu_buffer *fPending[GGR_MAX_BUFFERS]{};
    gpu_queue *fPendingQueue=nullptr;
    uint32_t fPendingCount=0,fPendingNativeFence=0,fPendingQueueFence=0,fNativeFence=0;
    bool drop(gpu_buffer *b) {
        if(b->pending||!runtime_ready)return false;
        ++drops;b->memory=nullptr;b->surface=nullptr;b->closePending=false;
        return true;
    }
    bool reapClosed(void);
    IOReturn finishPending(bool wait,bool reap,const ggr_timespec *deadline=nullptr);
};

/* INSERT_REAL_ESCROW_METHODS */

static void reset(void)
{
    stops=drops=flushes=polls=waits=delays=0;
    continuous_ns=0;runtime_ready=true;
    poll_result=wait_result=GGR_PENDING;
}
static void pending(GauguinGPUUserClient &client,gpu_queue &queue,SweetSurface &surface)
{
    queue={1,1,0};surface={7,1,{0}};
    auto &b=client.fBuffers[0];b.memory=&surface;b.surface=&surface;
    b.flags=3;b.size=sizeof(surface.pixels);b.pending=true;
    client.fPending[0]=&b;client.fPendingCount=1;
    client.fPendingNativeFence=9;client.fPendingQueueFence=1;
    client.fPendingQueue=&queue;
}

int main(void)
{
    reset();GauguinGPUUserClient client;gpu_queue queue{};SweetSurface surface{};
    pending(client,queue,surface);
    CHECK(client.finishPending(false,false)==kIOReturnNotReady);
    CHECK(client.fPendingCount==1&&client.fBuffers[0].pending&&surface.gpuState==1);
    CHECK(!drops&&!flushes&&!stops&&polls==1);
    poll_result=GGR_OK;
    CHECK(client.finishPending(false,false)==kIOReturnSuccess);
    CHECK(client.fPendingCount==0&&!client.fBuffers[0].pending);
    CHECK(queue.issued==queue.completed&&queue.completed==1&&client.fNativeFence==9);
    CHECK(surface.gpuState==0&&flushes==1&&!drops&&!stops);

    reset();GauguinGPUUserClient closed;gpu_queue q2{};SweetSurface s2{};
    pending(closed,q2,s2);closed.fBuffers[0].closePending=true;
    poll_result=GGR_OK;
    CHECK(closed.finishPending(false,true)==kIOReturnSuccess);
    CHECK(drops==1&&closed.fBuffers[0].memory==nullptr&&s2.gpuState==0);

    reset();GauguinGPUUserClient fault;gpu_queue q3{};SweetSurface s3{};
    pending(fault,q3,s3);poll_result=GGR_IO;
    CHECK(fault.finishPending(false,true)==kIOReturnNotReady);
    CHECK(stops==1&&fault.fPendingCount==1&&fault.fBuffers[0].pending);
    CHECK(fault.fBuffers[0].memory==&s3&&s3.gpuState==2&&!drops);

    reset();GauguinGPUUserClient expired;gpu_queue q4{};SweetSurface s4{};
    pending(expired,q4,s4);continuous_ns=1000000000;
    ggr_timespec deadline={1,0};
    CHECK(expired.finishPending(true,true,&deadline)==kIOReturnTimeout);
    CHECK(expired.fPendingCount==1&&expired.fBuffers[0].pending);
    CHECK(s4.gpuState==1&&!stops&&!drops&&polls==1);

    reset();GauguinGPUUserClient waited;gpu_queue q5{};SweetSurface s5{};
    pending(waited,q5,s5);wait_result=GGR_OK;
    CHECK(waited.finishPending(true,false)==kIOReturnSuccess);
    CHECK(waits==1&&s5.gpuState==0&&q5.completed==1);

    reset();GauguinGPUUserClient no_fence;gpu_queue q6{};SweetSurface s6{};
    pending(no_fence,q6,s6);no_fence.fPendingNativeFence=0;
    CHECK(no_fence.finishPending(true,true)==kIOReturnNotReady);
    CHECK(no_fence.fBuffers[0].pending&&s6.gpuState==1&&!stops&&!drops);

    reset();GauguinGPUUserClient aliases;gpu_queue q7{};SweetSurface s7{},s8{};
    pending(aliases,q7,s7);
    auto &second=aliases.fBuffers[1];second.memory=&s8;second.surface=&s8;
    second.flags=1;second.size=sizeof(s8.pixels);second.pending=true;
    s8.id=8;s8.gpuState=1;s8.aliasReady=false;
    aliases.fPending[1]=&second;aliases.fPendingCount=2;poll_result=GGR_OK;
    CHECK(aliases.finishPending(false,true)==kIOReturnNotReady);
    CHECK(stops==1&&flushes==0&&drops==0&&aliases.fPendingCount==2);
    CHECK(aliases.fBuffers[0].pending&&second.pending);
    CHECK(s7.gpuState==2&&s8.gpuState==2);

    std::printf("PASS: %u real escrow completion/timeout/fault/deferred-close assertions; CPU-only\n",cases);
    return 0;
}
