#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "gauguin_ready353.h"
#include "gauguin_ready357.h"
#include "gauguin_calibration357.h"
#include "gauguin_frame344.h"

struct SweetSurface {
    uint32_t id, state;
    unsigned display_holds;
};
struct IOMobileFramebufferUserClient {};
struct IOLock { bool held; };
struct EventSource {
    unsigned notices = 0;
    void interruptOccurred(void *, void *, int) { ++notices; }
};
struct Clients {
    unsigned getNextIndexOfObject(IOMobileFramebufferUserClient *, int) { return 0; }
};

static IOLock ready_lock;
static IOLock *gReadyLock = &ready_lock;
static EventSource event_source;
static EventSource *gReadySource = &event_source;
static uint64_t gReadyTicket;
static uint32_t gReadyVersion;
static bool gReadyRetainsIssued = true;
static struct scan357_writer gReadyWriters[SCAN357_WRITERS];
static unsigned promotions, releases;
static bool scan_window = true;
static void IOLockLock(IOLock *lock) { assert(!lock->held); lock->held = true; }
static void IOLockUnlock(IOLock *lock) { assert(lock->held); lock->held = false; }
static void sweet_surface_drop(SweetSurface *s) {
    if (s) {
        assert(!ready_lock.held && s->display_holds);
        --s->display_holds;
        ++releases;
    }
}
static uint32_t GauguinGPUSurfaceState(SweetSurface *s) { assert(s); return s->state; }
extern "C" void sweet_frame344_record(uint32_t kind, uint64_t, uint32_t,
    uint64_t, uint64_t, uint64_t) { if (kind==F354_PROMOTE) ++promotions; }
extern "C" bool sweet_frame351_window() { return scan_window; }
extern "C" bool sweet_frame351_position(scan351_position *out) {
    *out = {1000,20,2480,4878};
    return scan_window;
}
extern "C" uint64_t sweet_fb352_waiting_ticket() { return gReadyTicket; }

#include "frame357-records.inc"

class AppleCLCD {
public:
    bool fReadyAcrossFrames = true, fPhasePresent = true, fHoldPresent = true;
    bool fHeldStopped = false, fDirty = false, fPowerOff = false, fHeldActive = false;
    bool fReadyRequested = true, fCalibrating = false;
    EventSource *fReadyEvent = &event_source;
    IOLock local{}, *fLock = &local;
    Clients clients{}, *fClients = &clients;
    uint64_t fHeldLastTaken = 0, fReadyGeneration = 0, fHeldRetryEpoch = 1;
    uint64_t fHeldReplaced = 0, fHeldRetired = 0, fHeldCanceled = 0, fHeldConsumed = 0;
    uint64_t fHeldRetryCanceled = 0, fHeldRetrySuperseded = 0, fHeldRetryExhausted = 0, fHeldRequeued = 0;
    sweet_fb_frame fHeldPending{}, fHeldIssued[SCAN357_WRITERS]{}, fHeldReady{};
    bool blankEnabledLocked() const;
    bool waitingForReadyLocked() const;
    uint64_t pendingTicketLocked() const;
    sweet_fb_frame *boundFrameLocked(unsigned, uint64_t);
    void replacePendingLocked(sweet_fb_retired *);
    uint64_t watchPendingReadyLocked();
    void clearReadyTicketLocked();
    bool collectIssuedLocked(bool, sweet_fb_retired *);
    void cancelHeldFramesLocked(sweet_fb_retired *, sweet_fb_retired *, sweet_fb_retired *,
        IOMobileFramebufferUserClient *);
    bool takeHeldFrameLocked(sweet_fb_frame *, sweet_fb_frame * = nullptr);
    void invalidateHeldRetryLocked();
    void finishHeldFrame(sweet_fb_frame *, bool, bool);
};

#include "frame357-projection.inc"

static IOMobileFramebufferUserClient client, other_client;

static uint64_t swap(AppleCLCD &fb, uint64_t generation, SweetSurface *surface,
    uint32_t version=4, IOMobileFramebufferUserClient *owner=&client)
{
    sweet_fb_retired old{};
    if (fb.fHeldPending.owner) fb.replacePendingLocked(&old);
    auto &wait = fb.fHeldPending;
    wait.generation = generation;
    wait.owner = owner;
    wait.retryEpoch = fb.fHeldRetryEpoch;
    wait.surfaces[0] = surface;
    wait.surfaceVersion = version;
    const uint32_t mask = 1;
    memcpy(wait.record+0x104, &mask, sizeof(mask));
    fb.fDirty = true;
    if (surface) ++surface->display_holds;
    sweet_fb_retired_release(&old);
    return fb.watchPendingReadyLocked();
}

static bool drain(AppleCLCD &fb)
{
    sweet_fb_retired retired[SCAN357_WRITERS]{};
    bool marked = fb.collectIssuedLocked(false, retired);
    for (auto &entry: retired) sweet_fb_retired_release(&entry);
    return marked;
}

static void cancel(AppleCLCD &fb, IOMobileFramebufferUserClient *owner = nullptr)
{
    sweet_fb_retired pending{}, ready{}, issued[SCAN357_WRITERS]{};
    fb.cancelHeldFramesLocked(&pending, &ready, issued, owner);
    fb.invalidateHeldRetryLocked();
    fb.watchPendingReadyLocked();
    sweet_fb_retired_release(&pending);
    sweet_fb_retired_release(&ready);
    for (auto &entry: issued) sweet_fb_retired_release(&entry);
}

int main()
{
    {
        AppleCLCD fb;
        SweetSurface a{10,4,0}, b{11,4,0}, c{12,4,0};
        auto first = swap(fb,1,&a);
        assert(first && !sweet_fb357_claim_writer(first,8));
        assert(sweet_fb357_claim_writer(first,4));
        auto next = swap(fb,2,&b);
        assert(a.display_holds==1 && b.display_holds==1 && !drain(fb));
        assert(!sweet_fb357_claim_writer(next,4));
        sweet_fb357_finish_writer(first,8,111);
        assert(!drain(fb));
        sweet_fb357_finish_writer(first,4,111);
        assert(sweet_fb357_claim_writer(next,4));
        const unsigned before = promotions;
        sweet_fb357_finish_writer(next,4,112);
        auto third = swap(fb,3,&c);
        assert(!sweet_fb357_claim_writer(third,4));
        assert(drain(fb) && promotions==before+2 && fb.fHeldReady.generation==2);
        assert(a.display_holds==0 && b.display_holds==1 && c.display_holds==1);
        assert(sweet_fb357_claim_writer(third,4));
        sweet_fb357_finish_writer(third,4,0);
        assert(!drain(fb) && c.display_holds==0 && fb.fHeldReady.generation==2);
        sweet_fb_frame active{};
        assert(fb.takeHeldFrameLocked(&active) && active.generation==2 && b.display_holds==1);
        b.state=8; /* A new writer invalidates a previously ready descriptor. */
        fb.finishHeldFrame(&active,true,true);
        assert(b.display_holds==0 && !fb.fHeldActive && !fb.fHeldReady.owner);
        cancel(fb);
    }
    {
        AppleCLCD fb;
        SweetSurface a{10,4,0}, b{11,4,0};
        auto first = swap(fb,4,&a);
        assert(sweet_fb357_claim_writer(first,4));
        auto next = swap(fb,5,&b,4,&other_client);
        cancel(fb,&client);
        assert(a.display_holds==0 && b.display_holds==1);
        sweet_fb357_finish_writer(first,4,113);
        assert(!drain(fb) && sweet_fb357_claim_writer(next,4));
        b.state=8;
        sweet_fb357_finish_writer(next,4,114);
        assert(!drain(fb) && b.display_holds==0);
        cancel(fb);
    }
    {
        AppleCLCD fb;
        SweetSurface a{10,4,0};
        auto first = swap(fb,6,&a);
        assert(sweet_fb357_claim_writer(first,4));
        assert(!swap(fb,7,nullptr));
        sweet_fb_frame empty{};
        assert(fb.takeHeldFrameLocked(&empty) && empty.generation==7 && !empty.surfaces[0]);
        sweet_fb357_finish_writer(first,4,115);
        assert(!drain(fb) && a.display_holds==0);
        fb.finishHeldFrame(&empty,false,false);
        assert(!fb.fHeldActive);
    }
    {
        AppleCLCD fb;
        SweetSurface a{10,4,0};
        auto first = swap(fb,8,&a);
        assert(sweet_fb357_claim_writer(first,4));
        sweet_fb357_finish_writer(first,4,116);
        assert(drain(fb));
        sweet_fb_frame active{};
        assert(fb.takeHeldFrameLocked(&active));
        fb.fHeldStopped=true;
        cancel(fb);
        assert(a.display_holds==1);
        fb.finishHeldFrame(&active,true,false);
        assert(a.display_holds==0 && !fb.fHeldActive && !fb.fHeldReady.owner);
    }
    assert(releases==7 && promotions==3 && !ready_lock.held);
    const scan351_position early{0,1,2751,4878}, open{0,1,4078,4878}, late{0,1,4079,4878};
    assert(!scan357_calibration_window(&early) && scan357_calibration_window(&open)
        && !scan357_calibration_window(&late));
    const uint32_t pixel=0xaabbccdd;
    assert(scan357_pixel(pixel,SCAN357_FIRST)==0xaa44ccdd &&
        scan357_pixel(pixel,SCAN357_SECOND)==0xaabb33dd && scan357_pixel(pixel,SCAN357_RESTORE)==pixel);
    puts("issued lifetimes, cancellation, completion ordering and calibration window passed");
}
