#include <cassert>
#include <cstdint>
#include <cstdio>
#include "gauguin_probe358.h"
#include "gauguin_ready354.h"

struct IOLock { bool held; };
static IOLock gpuLock{};
static IOLock *gLock = &gpuLock;
static bool IOLockTryLock(IOLock *lock) {
    if (lock->held) return false;
    lock->held = true;
    return true;
}
static void IOLockUnlock(IOLock *lock) { assert(lock->held); lock->held=false; }

struct SweetSurface { uint32_t state; };
struct GauguinGPUUserClient {
    uint64_t ticket;
    uint32_t version, fence;
    bool pendingDisplayIs(uint64_t t, uint32_t v) const {
        return fence && ticket==t && version==v;
    }
};
static GauguinGPUUserClient owner{0x100000002,4,191};
static GauguinGPUUserClient *gOwner = &owner;
#define OSDynamicCast(type, object) (object)
static SweetSurface target{5};
static uint32_t GauguinGPUSurfaceState(const SweetSurface *surface) { return surface->state; }
static struct {uint64_t ticket; uint32_t version, fence;} gCompletedDisplayWrite{};
static bool gpuComplete;
static unsigned polls;

static bool completePendingOwnerLocked(bool wait, bool reap) {
    assert(gpuLock.held && !wait && !reap);
    ++polls;
    if (!gpuComplete) return false;
    gCompletedDisplayWrite={owner.ticket,owner.version,owner.fence};
    target.state=owner.version;
    owner.fence=0;
    return true;
}

#include "frame358-gpu-probe.inc"

int main()
{
    assert(!scan358_probe_line(1727) && scan358_probe_line(1728));
    assert(scan358_probe_line(3044) && !scan358_probe_line(3045));
    scan358_probe_slot inbox{};
    assert(scan358_offer(&inbox,0xffffffff,owner.ticket));
    assert(!scan358_offer(&inbox,0xffffffff,owner.ticket+1));
    const auto displaced = scan358_take(&inbox);
    assert(displaced.frame==0xffffffff && displaced.ticket==owner.ticket);
    assert(!scan358_offer(&inbox,0xffffffff,owner.ticket));
    assert(scan358_offer(&inbox,0,owner.ticket));
    assert(!scan358_offer(&inbox,0xfffffffe,owner.ticket));
    assert(scan358_offer(&inbox,1,owner.ticket));
    const auto request = scan358_take(&inbox);
    assert(request.frame==1 && !scan358_take(&inbox).ticket);
    scan351_slot blank{};
    const scan351_position early{0,1,1727,4878}, at{0,1,1880,4878}, next{0,2,2480,4878};
    const scan351_position routeCut{0,1,1880,4313}, late{0,1,3045,4878};
    assert(!scan358_still_timely(&request,&early,&blank));
    assert(scan358_still_timely(&request,&at,&blank));
    assert(!scan358_still_timely(&request,&next,&blank));
    assert(!scan358_still_timely(&request,&routeCut,&blank));
    assert(!scan358_still_timely(&request,&late,&blank));
    scan351_take(&blank,&at);
    assert(!scan358_still_timely(&request,&at,&blank));
    for (unsigned i=2; inbox.sent<SCAN358_PROBE_LIMIT; ++i)
        assert(scan358_offer(&inbox,i,owner.ticket));
    assert(!scan358_offer(&inbox,2000,owner.ticket));

    uint32_t result=0;
    gpuLock.held=true;
    assert(!GauguinGPUSurfaceReadyFence(&target,owner.ticket,4,&result));
    assert(result==SCAN358_PROBE_LOCK_BUSY && polls==0 && gpuLock.held);
    gpuLock.held=false;
    assert(!GauguinGPUSurfaceReadyFence(&target,owner.ticket+1,4,&result));
    assert(result==SCAN358_PROBE_STALE && polls==0 && !gpuLock.held);
    assert(!GauguinGPUSurfaceReadyFence(&target,owner.ticket,8,&result));
    assert(result==SCAN358_PROBE_STALE && polls==0);
    assert(!GauguinGPUSurfaceReadyFence(&target,owner.ticket,4,&result));
    assert(result==SCAN358_PROBE_PENDING && polls==1);
    gpuComplete=true;
    assert(GauguinGPUSurfaceReadyFence(&target,owner.ticket,4,&result)==191);
    assert(result==SCAN358_PROBE_PUBLISHED && polls==2 && target.state==4);
    assert(!GauguinGPUSurfaceReadyFence(&target,owner.ticket,4,&result));
    assert(result==SCAN358_PROBE_STALE && polls==2);
    assert(GauguinGPUSurfaceReadyFence(&target,owner.ticket,4,nullptr)==191 && !gpuLock.held);
    puts("bounded workloop probe, wrap, stale, trylock, pending and exact publication passed");
}
