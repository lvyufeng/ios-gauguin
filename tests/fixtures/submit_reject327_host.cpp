/* Actual GauguinGPUUserClient::submit body is inserted at the marker. Typed
 * CPU-only seams verify that every BO is escrowed before a possible doorbell. */
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <new>
#include <cstdarg>
#include <string>
#include <vector>
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
static unsigned alloc_calls,fail_alloc,live_alloc,copy_calls,fail_copy;
template<class T> T *model_new(unsigned n){++alloc_calls;if(fail_alloc==alloc_calls)return nullptr;T *p=new(std::nothrow)T[n];if(p)++live_alloc;return p;}
template<class T>void model_delete(T *p){if(p){assert(live_alloc);--live_alloc;delete[]p;}}
#define IONew(T,n) model_new<T>(n)
#define IODelete(p,T,n) model_delete(p)
static std::vector<std::string> log_lines;
static unsigned clock_reads;
static uint64_t mach_absolute_time(){++clock_reads;return UINT64_C(5000000000)+clock_reads;}
static void IOLog(const char *format,...){char line[1024];va_list a;va_start(a,format);int n=vsnprintf(line,sizeof(line),format,a);va_end(a);assert(n>0&&n<512);log_lines.emplace_back(line);}

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
{++copy_calls;if(copy_calls==fail_copy)return 1;std::memcpy(dest,reinterpret_cast<const void *>(address),bytes);return 0;}
static void flush_dcache64(uintptr_t,unsigned,int) {++flushes;}
static void sweet_ui_trace_record(int,uint64_t,uint32_t,uint32_t,uint32_t,uint64_t,uint64_t) {}
extern "C" void sweet_gpu_runtime_stop(void) {++stops;}

struct SweetSurface {
    uint32_t id=7,gpuState=0;
    char pixels[64]{};
    bool aliasReady=true;
    uintptr_t kernelAddress(void) {return aliasReady?reinterpret_cast<uintptr_t>(pixels):0;}
};
struct gpu_buffer {
    void *memory=nullptr;
    SweetSurface *surface=nullptr;
    uint64_t address=GGR_VA_START+65536,size=64;
    uint32_t handle=5,flags=0;
    bool pending=false,closePending=false;
};
struct gpu_queue {uint32_t id=0,issued=0,completed=0;};
/* INSERT_REAL_DIAGNOSTIC */
class GauguinGPUUserClient {
public:
    struct gsub_diag327 fSubmitDiag327{};
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
    assert(live_alloc==0);alloc_calls=fail_alloc=copy_calls=fail_copy=0;
    issue_success=sync_success=true;settle_result=kIOReturnNotReady;native_fence=9;
}
static struct ggr_submit request(struct ggr_submit_bo *bo,struct ggr_submit_cmd *cmd)
{
    struct ggr_submit r={};r.flags=0x10;r.nr_bos=1;r.nr_cmds=1;
    r.bos=reinterpret_cast<uint64_t>(bo);r.cmds=reinterpret_cast<uint64_t>(cmd);
    r.fence_fd=-1;return r;
}

static unsigned run_matrix(void)
{
    unsigned scenarios=0;
    for(unsigned async=0;async<2;async++)for(unsigned kind=0;kind<41;kind++){
        reset();GauguinGPUUserClient client;SweetSurface surface;
        active=&client;client.fAsync=async;client.buffer.memory=&surface;client.buffer.surface=&surface;
        struct ggr_submit_bo bo[2]={{1,5,0},{1,5,0}};
        struct ggr_submit_cmd cmd[2]={{1,0,0,16,0,0,0},{1,0,0,16,0,0,0}};
        auto r=request(bo,cmd);unsigned expected_stage=10;
        switch(kind){
        case 0:break;
        case 1:r.flags=0x20;break;
        case 2:r.flags=0x11;break;
        case 3:r.fence=1;break;
        case 4:r.nr_bos=0;break;
        case 5:r.nr_bos=GGR_MAX_BUFFERS+1;break;
        case 6:r.nr_cmds=0;break;
        case 7:r.nr_cmds=GGR_MAX_COMMANDS+1;break;
        case 8:r.queueid=100;break;
        case 9:client.defaultQueue.issued=UINT32_MAX;break;
        case 10:r.in_syncobjs=1;break;
        case 11:r.out_syncobjs=1;break;
        case 12:r.nr_in_syncobjs=1;break;
        case 13:r.nr_out_syncobjs=1;break;
        case 14:r.syncobj_stride=1;break;
        case 15:r.pad=1;break;
        case 16:r.fence_fd=0;break;
        case 17:r.bos=0;break;
        case 18:r.cmds=0;break;
        case 19:r.bos=UINT64_MAX-7;break;
        case 20:fail_alloc=1;expected_stage=12;break;
        case 21:fail_alloc=2;expected_stage=12;break;
        case 22:fail_copy=1;expected_stage=13;break;
        case 23:fail_copy=2;expected_stage=13;break;
        case 24:bo[0].handle=99;expected_stage=14;break;
        case 25:bo[0].flags=0;expected_stage=14;break;
        case 26:bo[0].flags=4;expected_stage=14;break;
        case 27:bo[0].flags=3;client.buffer.flags=GGR_BO_READONLY;expected_stage=14;break;
        case 28:bo[0].presumed=client.buffer.address+65536;expected_stage=14;break;
        case 29:r.nr_bos=2;expected_stage=15;break;
        case 30:cmd[0].submit_idx=1;expected_stage=16;break;
        case 31:bo[0].flags=2;expected_stage=17;break;
        case 32:cmd[0].type=0;expected_stage=17;break;
        case 33:cmd[0].size=0;expected_stage=17;break;
        case 34:cmd[0].submit_offset=2;expected_stage=17;break;
        case 35:cmd[0].size=128;expected_stage=17;break;
        case 36:surface.aliasReady=false;expected_stage=18;break;
        case 37:issue_success=sync_success=false;expected_stage=19;break;
        case 38:native_fence=0;expected_stage=20;break;
        case 39:client.fNativeFence=9;expected_stage=20;break;
        case 40:client.fPendingCount=1;expected_stage=async?11:10;break;
        }
        auto before=r;IOReturn rc=client.submit(&r);
        CHECK(live_alloc==0);
        if(rc!=kIOReturnSuccess)CHECK(!memcmp(&before,&r,sizeof(r)));
#ifdef TEST_SUBMIT327
        if(rc!=kIOReturnSuccess)CHECK(client.fSubmitDiag327.stage==expected_stage);
#else
        (void)expected_stage;
#endif
        if(kind!=0&&kind!=40)CHECK(rc!=kIOReturnSuccess);
        if(kind==0)CHECK(rc==kIOReturnSuccess&&r.fence==1);
        std::printf("OBS %u %u rc=%d fence=%u issues=%u syncs=%u stops=%u flushes=%u allocs=%u copies=%u pending=%u owner=%u native=%u pending_fence=%u issued=%u completed=%u native_prior=%u gpu_state=%u\n",
            async,kind,rc,r.fence,issues,syncs,stops,flushes,alloc_calls,copy_calls,client.fPendingCount,
            client.fPendingQueue==&client.defaultQueue,client.fPendingNativeFence,client.fPendingQueueFence,
            client.defaultQueue.issued,client.defaultQueue.completed,client.fNativeFence,surface.gpuState);
        ++scenarios;
    }
    return scenarios;
}
int main(void)
{
    unsigned scenarios=run_matrix();
    reset();gsub_diag327_count=0;clock_reads=0;log_lines.clear();
    gsub_diag327 d={10,UINT32_MAX,0,0,0,0,0,0,0,0};
    struct ggr_submit r={};r.flags=1;r.nr_bos=1;r.nr_cmds=1;r.fence_fd=-1;
    for(unsigned i=0;i<4;i++)gsub_diag327_log(&d,&r,i==0?kIOReturnSuccess:kIOReturnBadArgument,i!=1,i!=2,7,0,0,0);
    CHECK(log_lines.size()==1&&clock_reads==1&&gsub_diag327_count==1);
    gsub_diag327_count=0;clock_reads=0;log_lines.clear();
    for(unsigned i=0;i<80;i++)gsub_diag327_log(&d,&r,kIOReturnBadArgument,true,true,7,0,0,0);
    CHECK(gsub_diag327_count==65&&log_lines.size()==65&&clock_reads==64);
    CHECK(log_lines.back()=="SWEET GPU SUBMIT327: limit=64 coverage=incomplete\n");
    for(const auto &line:log_lines)std::printf("FIXTURE %s",line.c_str());
    gsub_diag327_count=UINT32_MAX;gsub_diag327_log(&d,&r,kIOReturnBadArgument,true,true,7,0,0,0);
    CHECK(log_lines.size()==65&&clock_reads==64);
    gsub_diag327_count=0;
    d={UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX};
    std::memset(&r,0xff,sizeof(r));gsub_diag327_log(&d,&r,INT32_MIN,true,true,UINT64_MAX,UINT32_MAX,UINT32_MAX,UINT64_MAX);
    CHECK(log_lines.back().size()<512&&issues==0&&syncs==0&&stops==0&&flushes==0&&alloc_calls==0&&copy_calls==0);
    std::printf("PASS: %u scenarios, %u assertions; unchanged submit observations, all refusal stages, scope/rate/length bounds\n",scenarios,cases);
}
