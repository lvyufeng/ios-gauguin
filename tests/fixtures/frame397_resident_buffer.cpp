#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>

#include "gauguin_gpu_runtime.h"

constexpr uint64_t PAGE_SIZE = 16384, PAGE_MASK = PAGE_SIZE-1;
constexpr uint64_t address = GGR_VA_START + PAGE_SIZE;

struct IOMemoryDescriptor {
    unsigned retainCount = 1;
    virtual ~IOMemoryDescriptor() = default;
    unsigned getRetainCount() const { return retainCount; }
};
struct IOBufferMemoryDescriptor : IOMemoryDescriptor {
    std::array<uint8_t, PAGE_SIZE> bytes;
    void *getBytesNoCopy() { return bytes.data(); }
};
#define OSDynamicCast(type, object) dynamic_cast<type *>(object)
struct SweetSurface;

// These members are extracted from the patched driver with the methods.
#include "Frame397Buffers.inc"

static bool gMapUnrelated, gapi_frozen, gapi_valid, capture, runtimeBusy;
static uint64_t gPendingCache397Hits, gPendingCache397CaptureHits;
static unsigned runtimeQueries, barriers, reuseRecords;
static struct { uint64_t hits, misses; } gCache335;
static struct { uint64_t token; } gapi_pending;
static struct { unsigned stages[8], cursor; } receipt;

static void cache335_count(uint64_t *counter) { if(!gapi_frozen) ++*counter; }
static void memoryBarrier() { ++barriers; }
static uint32_t current_proc() { return 57; }
static uint32_t proc_pid(uint32_t process) { return process; }
static constexpr unsigned GUT_BO_REUSE335 = 33;
static void sweet_ui_trace_record(unsigned kind, uint64_t token, uint32_t pid, unsigned success,
    uint64_t length, uint32_t handle, uint32_t flags)
{
    assert(kind==GUT_BO_REUSE335 && token==89 && pid==57 && success==1);
    assert(length==PAGE_SIZE && handle && flags==GGR_BO_WC);
    ++reuseRecords;
}
static void gbo333_record(unsigned stage, uint64_t, uint32_t, uint32_t) { receipt.stages[receipt.cursor++]=stage; }
static bool sweet_frame344_clock() { return capture; }
bool sweet_gpu_runtime_pending_metadata(uint32_t fence) { ++runtimeQueries; return runtimeBusy && fence==41; }
namespace io342 {
static void phase(uint32_t selector, unsigned at) {
    assert(selector==0x42 && (at==3 || at==5 || at==11));
    receipt.stages[receipt.cursor++]=100+at;
}
}

struct GauguinGPUUserClient {
    gpu_buffer *fBuffers;
    uint64_t fCachedBytes=PAGE_SIZE;
    uint32_t fCachedCount=1, fNextHandle=12, fAllocationStage=0;
    bool fCacheEnabled=true, fClosed=false, fCompositor=true, fAsync=true;
    gpu_queue *fPendingQueue;
    uint32_t fPendingCount=1, fPendingNativeFence=41, fPendingQueueFence=7;
    gpu_buffer *fPending[GGR_MAX_BUFFERS]{};
    void cacheState335() {}
    gpu_buffer *takeCached335(uint64_t,uint32_t,bool pending=false);
    bool pendingOwner397() const;
    bool disjointPending397(const gpu_buffer &) const;
    void publishCached397(gpu_buffer *,uint64_t,ggr_new &,bool);
    bool reusePending397(ggr_new &);
};

#include "Frame397Methods.inc"

struct Case {
    IOBufferMemoryDescriptor resident, inFlight;
    std::array<gpu_buffer,GGR_MAX_CLIENT_BUFFERS> buffers{};
    gpu_queue queue{3,7,6};
    GauguinGPUUserClient client{buffers.data(),PAGE_SIZE,1,12,0,true,false,true,true,&queue};
    ggr_new request{};
    Case() {
        resident.bytes.fill(0xa5);
        inFlight.bytes.fill(0x39);
        buffers[0]={&resident,nullptr,address,PAGE_SIZE,address,PAGE_SIZE,0,GGR_BO_WC,true,false,false,true};
        buffers[1]={&inFlight,nullptr,address+PAGE_SIZE,PAGE_SIZE,address+PAGE_SIZE,PAGE_SIZE,7,GGR_BO_WC,true,true,false,false};
        client.fPending[0]=&buffers[1];
        request.size=PAGE_SIZE-1;
        request.flags=GGR_BO_WC;
        gMapUnrelated=gapi_valid=capture=runtimeBusy=true;
        gapi_pending.token=89;
        gapi_frozen=false;
        gPendingCache397Hits=gPendingCache397CaptureHits=0;
        gCache335={};
        runtimeQueries=barriers=reuseRecords=0;
        receipt={};
    }
    void reject() {
        const auto count=client.fCachedCount;
        const auto next=client.fNextHandle;
        const auto before=request.handle;
        assert(!client.reusePending397(request));
        assert(pendingStateUnchanged() && buffers[0].cached && client.fCachedCount==count && client.fNextHandle==next);
        assert(request.handle==before && !receipt.cursor && !barriers && !gCache335.hits && !gCache335.misses);
        assert(resident.bytes.front()==0xa5 && resident.bytes.back()==0xa5);
    }
    bool pendingStateUnchanged() const {
        return !gPendingCache397Hits && !gPendingCache397CaptureHits && !reuseRecords && inFlight.bytes.front()==0x39;
    }
};

int main()
{
    { Case c;
      assert(c.client.reusePending397(c.request));
      assert(c.request.handle==12 && c.client.fNextHandle==13 && !c.buffers[0].cached && !c.client.fCachedBytes);
      assert(c.buffers[0].address==address && c.buffers[0].mappingSize==PAGE_SIZE && c.buffers[0].installed);
      assert(std::all_of(c.resident.bytes.begin(),c.resident.bytes.end(),[](uint8_t value){return value==0;}));
      assert(c.buffers[1].pending && c.inFlight.bytes.front()==0x39 && c.inFlight.bytes.back()==0x39);
      assert(c.queue.issued==7 && c.queue.completed==6 && c.client.fPendingNativeFence==41);
      assert(runtimeQueries==1 && barriers==1 && gCache335.hits==1 && !gCache335.misses);
      assert(gPendingCache397Hits==1 && gPendingCache397CaptureHits==1 && reuseRecords==1);
      const unsigned stages[]{103,2,3,105,4,111,5};
      assert(receipt.cursor==std::size(stages) && std::equal(std::begin(stages),std::end(stages),receipt.stages)); }
    { Case c; gMapUnrelated=false; c.reject(); }
    { Case c; c.client.fCompositor=false; c.reject(); }
    { Case c; c.client.fAsync=false; c.reject(); }
    { Case c; c.client.fClosed=true; c.reject(); }
    { Case c; c.client.fCacheEnabled=false; c.reject(); }
    { Case c; c.client.fPendingCount=0; c.reject(); }
    { Case c; c.client.fPendingCount=GGR_MAX_BUFFERS+1; c.reject(); }
    { Case c; c.queue.completed=7; c.reject(); }
    { Case c; c.client.fPendingNativeFence=42; c.reject(); }
    { Case c; runtimeBusy=false; c.reject(); }
    { Case c; c.client.fPending[0]=nullptr; c.reject(); }
    { Case c; c.client.fPending[0]=&c.buffers[0]; c.reject(); }
    { Case c; c.buffers[1].mappingAddress=address+1; c.reject(); }
    { Case c; c.buffers[1].memory=&c.resident; c.reject(); }
    { Case c; c.buffers[1].installed=false; c.reject(); }
    { Case c; c.buffers[0].mappingAddress=GGR_VA_END-1; c.reject(); }
    { Case c; c.buffers[0].closePending=true; c.reject(); }
    { Case c; c.resident.retainCount=2; c.reject(); }
    { Case c; c.request.flags=0; c.reject(); }
    { Case c; c.request.flags=0x40; c.reject(); }
    { Case c; c.request.size=PAGE_SIZE+1; c.reject(); }
    { Case c; c.request.handle=99; c.reject(); }
    { Case c; c.client.fNextHandle=0; c.reject(); }
    // A normal hit uses the same zero-and-publish path without claiming a pending hit.
    { Case c; c.client.fPendingCount=0;
      auto *buffer=c.client.takeCached335(PAGE_SIZE,GGR_BO_WC);
      assert(buffer==&c.buffers[0]);
      c.client.publishCached397(buffer,PAGE_SIZE,c.request,false);
      assert(c.resident.bytes.back()==0 && reuseRecords==1 && !gPendingCache397Hits && !runtimeQueries); }
    // A failed speculative lookup counts no miss. The deferred ordinary lookup does.
    { Case c; c.request.size=PAGE_SIZE+1; c.reject();
      assert(!c.client.takeCached335(2*PAGE_SIZE,GGR_BO_WC) && gCache335.misses==1); }
}
