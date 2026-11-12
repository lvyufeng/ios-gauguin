/* Actual GauguinGPUUserClient::submit body is inserted at the marker. Typed
 * CPU-only seams verify that every BO is escrowed before a possible doorbell. */
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <new>
#include "gauguin_gpu_runtime.h"

using IOReturn=int;
constexpr IOReturn kIOReturnSuccess=0;
constexpr IOReturn kIOReturnBadArgument=1;
constexpr IOReturn kIOReturnNoMemory=2;
constexpr IOReturn kIOReturnVMError=3;
constexpr IOReturn kIOReturnTimeout=4;
constexpr IOReturn kIOReturnNotReady=5;
#define GUT_SUBMIT_BEGIN 12
#define GUT_SUBMIT_END 13
#define GUT_SURFACE 14
#define IONew(T,n) new T[n]
#define IODelete(p,T,n) delete[] p
#define CHECK(x) do {++cases;assert(x);} while(0)

static unsigned cases,issues,syncs,stops,flushes,escrow_before_issue;
static bool issue_success=true,sync_success=true;
static IOReturn settle_result=kIOReturnNotReady;
static uint32_t native_fence=9;
static uint64_t dummy_pid=57;
static struct {uint64_t token=1;} gapi_pending;
static void memoryBarrier(void) {}
static void *current_proc(void) {return &dummy_pid;}
static int proc_pid(void *) {return 57;}
static int copyin(uint64_t address,void *dest,size_t bytes)
{std::memcpy(dest,reinterpret_cast<const void *>(address),bytes);return 0;}
static void flush_dcache64(uintptr_t,unsigned,int) {++flushes;}
static void sweet_ui_trace_record(int,uint64_t,uint32_t,uint32_t,uint32_t,uint64_t,uint64_t) {}
extern "C" void sweet_gpu_runtime_stop(void) {++stops;}

struct SweetSurface {
    uint32_t id=7,gpuState=0;
    char pixels[64]{};
    uintptr_t kernelAddress(void) {return reinterpret_cast<uintptr_t>(pixels);}
};
struct gpu_buffer {
    void *memory=nullptr;
    SweetSurface *surface=nullptr;
    uint64_t address=GGR_VA_START+65536,size=64;
    uint32_t handle=5,flags=0;
    bool pending=false,closePending=false;
};
struct gpu_queue {uint32_t id=0,issued=0,completed=0;};
class GauguinGPUUserClient {
public:
    gpu_buffer buffer{};
    gpu_queue defaultQueue{};
    gpu_buffer *fPending[GGR_MAX_BUFFERS]{};
    gpu_queue *fPendingQueue=nullptr;
    uint32_t fPendingCount=0,fPendingNativeFence=0,fPendingQueueFence=0,fNativeFence=0;
    bool fAsync=false;
    gpu_buffer *find(uint32_t handle)
    {return buffer.memory&&handle==buffer.handle?&buffer:nullptr;}
    gpu_queue *queue(uint32_t id) {return id==0?&defaultQueue:nullptr;}
    IOReturn finishPending(bool,bool) {return settle_result;}
    IOReturn submit(struct ggr_submit *r);
};
static GauguinGPUUserClient *active;

extern "C" enum ggr_error sweet_gpu_runtime_issue(const uint64_t *,const uint32_t *,uint32_t,uint32_t *fence)
{
    ++issues;
    CHECK(active&&active->fPendingCount==1&&active->fPending[0]==&active->buffer);
    CHECK(active->buffer.pending&&active->buffer.surface->gpuState==1);
    ++escrow_before_issue;
    if(!issue_success)return GGR_IO;
    *fence=native_fence;return GGR_OK;
}
extern "C" bool sweet_gpu_runtime_submit(const uint64_t *,const uint32_t *,uint32_t,uint32_t *fence)
{
    ++syncs;CHECK(active&&active->buffer.surface->gpuState==1);
    if(!sync_success)return false;
    *fence=native_fence;return true;
}

/* INSERT_REAL_SUBMIT_METHOD */

static void reset(void)
{
    issues=syncs=stops=flushes=escrow_before_issue=0;
    issue_success=sync_success=true;settle_result=kIOReturnNotReady;native_fence=9;
}
static struct ggr_submit request(struct ggr_submit_bo *bo,struct ggr_submit_cmd *cmd)
{
    struct ggr_submit r={};r.flags=0x10;r.nr_bos=1;r.nr_cmds=1;
    r.bos=reinterpret_cast<uint64_t>(bo);r.cmds=reinterpret_cast<uint64_t>(cmd);
    r.fence_fd=-1;return r;
}

int main(void)
{
    struct ggr_submit_bo bo={1,5,0};
    struct ggr_submit_cmd cmd={};cmd.type=1;cmd.submit_idx=0;cmd.size=16;

    reset();GauguinGPUUserClient async;SweetSurface surface;
    active=&async;async.fAsync=true;async.buffer.memory=&surface;
    async.buffer.surface=&surface;
    auto r=request(&bo,&cmd);
    CHECK(async.submit(&r)==kIOReturnSuccess);
    CHECK(issues==1&&syncs==0&&escrow_before_issue==1&&r.fence==1);
    CHECK(async.defaultQueue.issued==1&&async.defaultQueue.completed==0);
    CHECK(async.fPendingNativeFence==9&&async.fPendingQueueFence==1);
    CHECK(async.buffer.pending&&surface.gpuState==1&&flushes==1&&!stops);
    auto second=request(&bo,&cmd);
    CHECK(async.submit(&second)==kIOReturnNotReady&&issues==1);

    reset();GauguinGPUUserClient fault;SweetSurface s2;
    active=&fault;fault.fAsync=true;fault.buffer.memory=&s2;fault.buffer.surface=&s2;
    issue_success=false;r=request(&bo,&cmd);
    CHECK(fault.submit(&r)==kIOReturnTimeout&&r.fence==0);
    CHECK(fault.fPendingCount==1&&fault.buffer.pending&&s2.gpuState==2);
    CHECK(stops==1&&escrow_before_issue==1&&fault.defaultQueue.issued==0);

    reset();GauguinGPUUserClient synchronous;SweetSurface s3;
    active=&synchronous;synchronous.buffer.memory=&s3;synchronous.buffer.surface=&s3;
    r=request(&bo,&cmd);
    CHECK(synchronous.submit(&r)==kIOReturnSuccess&&r.fence==1);
    CHECK(syncs==1&&issues==0&&flushes==2&&s3.gpuState==0);
    CHECK(synchronous.defaultQueue.issued==synchronous.defaultQueue.completed);

    reset();GauguinGPUUserClient bad;SweetSurface s4;
    active=&bad;bad.fAsync=true;bad.buffer.memory=&s4;bad.buffer.surface=&s4;
    bo.flags=0;r=request(&bo,&cmd);
    CHECK(bad.submit(&r)==kIOReturnBadArgument);
    CHECK(issues==0&&bad.fPendingCount==0&&s4.gpuState==0);

    std::printf("PASS: %u real async-submit escrow/fence/failure/sync assertions; CPU-only\n",cases);
    return 0;
}
