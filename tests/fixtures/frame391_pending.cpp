#include <cassert>
#include <cstdint>
#include <cstring>

#include "gauguin_ready357.h"

struct IOLock {};
static IOLock publication;
static IOLock *gReadyLock = &publication;
static bool gReadyRetainsIssued = true;
static IOLock *gReadySource = &publication;
static uint64_t gPreviousTicket;
static uint32_t gPreviousVersion;
static scan357_writer gReadyWriters[SCAN357_WRITERS];
static unsigned claims;
static void IOLockLock(IOLock *) {}
static void IOLockUnlock(IOLock *) {}
static bool sweet_frame351_window() { return true; }
enum { F357_BOUND, F353_READY, F354_PROMOTE };
static void sweet_frame344_record(unsigned kind, uint64_t, uint32_t flags, uint64_t, uint64_t, uint64_t) {
    if (kind == F357_BOUND) {
        assert(flags == 1);
        ++claims;
    }
}
struct IOMobileFramebufferUserClient {};
struct Surface { uint32_t id, state; };
static uint32_t GauguinGPUSurfaceState(const Surface *surface) { return surface->state; }
struct scan351_position { uint32_t frame; };
static bool sweet_frame351_position(scan351_position *pos) { pos->frame = 41; return true; }
struct sweet_fb_frame {
    IOMobileFramebufferUserClient *owner = nullptr;
    Surface *surfaces[1] = {};
    uint64_t generation = 0;
    uint32_t surfaceVersion = 0;
    uint8_t record[0x108] = {};
    struct { bool valid; uint64_t frame; } ready = {};
};
struct sweet_fb_retired { uint64_t generation = 0; };
static void sweet_fb_frame_move(sweet_fb_frame *target, sweet_fb_frame *source) {
    assert(!target->owner && source->owner);
    *target = *source;
    *source = {};
}
static void sweet_fb_frame_retire(sweet_fb_retired *target, sweet_fb_frame *source) {
    assert(!target->generation && source->owner);
    target->generation = source->generation;
    *source = {};
}
static uint32_t get32(const uint8_t *record, unsigned offset) {
    uint32_t value;
    std::memcpy(&value,record+offset,sizeof value);
    return value;
}
static uint64_t scan352_ticket(uint64_t generation, uint32_t surface) {
    return generation << 32 | surface;
}

struct AppleCLCD {
    void replacePendingLocked(const sweet_fb_frame &, sweet_fb_retired *, sweet_fb_retired *);
    sweet_fb_frame *boundFrameLocked(unsigned, uint64_t);
    bool collectIssuedLocked(bool, sweet_fb_retired *);
    void cancelHeldFramesLocked(sweet_fb_retired *, sweet_fb_retired *, sweet_fb_retired *,
                                IOMobileFramebufferUserClient *);
    bool stage384EnabledLocked() const { return stage; }
    bool blankEnabledLocked() const { return fDirty; }
    void signalStage384Locked() { ++stageSignals; }
    void clearReadyTicketLocked() {}
    uint64_t pendingTicketLocked() const;
    sweet_fb_frame fHeldPending, fHeldPrevious, fHeldIssued[SCAN357_WRITERS], fHeldReady;
    uint64_t fHeldLastTaken = 0;
    bool stage = true, fReadyAcrossFrames = true, fReadyEvent = true, fDirty = false, fHoldPresent = true;
    unsigned fHeldReplaced = 0, fHeldRetired = 0, fHeldCanceled = 0, stageSignals = 0;
};

#include "Frame391Methods.inc"

struct Fixture {
    Fixture() {
        gPreviousTicket = gPreviousVersion = claims = 0;
        for (auto &writer : gReadyWriters) writer = {};
    }
    AppleCLCD fb;
    IOMobileFramebufferUserClient owner, other;
    Surface a{11,4}, b{12,8}, c{13,12};
    sweet_fb_retired waiting, ready, retired[SCAN391_RETIRE_SLOTS];

    void accept(uint64_t generation, Surface &surface, IOMobileFramebufferUserClient *client = nullptr) {
        sweet_fb_frame next;
        next.generation = generation;
        next.owner = client ? client : &owner;
        next.surfaces[0] = &surface;
        next.surfaceVersion = surface.state;
        uint32_t one = 1;
        std::memcpy(next.record+0x104,&one,sizeof one);
        waiting = {};
        retired[SCAN357_WRITERS] = {};
        fb.replacePendingLocked(next,&waiting,&retired[SCAN357_WRITERS]);
        sweet_fb_frame_move(&fb.fHeldPending,&next);
        fb.fDirty = true;
    }
};

int main()
{
    {
        Fixture f;
        f.accept(1,f.a);
        f.accept(2,f.b);
        assert(f.fb.fHeldPrevious.generation==1 && sweet_fb391_previous_surface()==f.a.id);
        assert(sweet_fb391_claim_previous(f.a.id,8)==0);
        const auto ticket = sweet_fb391_claim_previous(f.a.id,4);
        assert(ticket==scan352_ticket(1,11) && claims==1 && !sweet_fb391_claim_previous(f.a.id,4));
        assert(!scan357_signal(gReadyWriters,ticket,8,70));
        assert(scan357_signal(gReadyWriters,ticket,4,70));
        assert(f.fb.collectIssuedLocked(false,f.retired));
        assert(f.fb.fHeldReady.generation==1 && !sweet_fb391_previous_surface() && f.fb.stageSignals==1);
    }
    {
        Fixture f;
        f.accept(1,f.a);
        f.accept(2,f.a);
        assert(f.waiting.generation==1 && !sweet_fb391_previous_surface());
        f.accept(3,f.b,&f.other);
        assert(f.waiting.generation==2 && !sweet_fb391_previous_surface());
    }
    {
        Fixture f;
        f.accept(1,f.a);
        f.accept(2,f.b);
        f.accept(3,f.c);
        assert(f.retired[SCAN357_WRITERS].generation==1 && !sweet_fb391_claim_previous(f.a.id,4));
        const auto ticket = sweet_fb391_claim_previous(f.b.id,8);
        assert(ticket && scan357_signal(gReadyWriters,ticket,8,71));
        f.fb.fHeldLastTaken = 3;
        f.retired[0] = {};
        assert(!f.fb.collectIssuedLocked(false,f.retired) && f.retired[0].generation==2);
    }
    {
        Fixture f;
        f.accept(1,f.a);
        f.accept(2,f.b);
        const auto ticket = sweet_fb391_claim_previous(f.a.id,4);
        f.accept(3,f.c);
        assert(f.fb.fHeldIssued[scan357_find(gReadyWriters,ticket)].generation==1);
        assert(scan357_signal(gReadyWriters,ticket,4,72));
        assert(f.fb.collectIssuedLocked(false,f.retired));
        assert(f.fb.fHeldReady.generation==1 && f.fb.fHeldPrevious.generation==2);
        f.waiting = {};
        f.fb.cancelHeldFramesLocked(&f.waiting,&f.ready,f.retired,&f.owner);
        assert(f.waiting.generation==3 && f.ready.generation==1 && f.retired[SCAN357_WRITERS].generation==2);
        assert(!f.fb.fDirty && !sweet_fb391_previous_surface());
    }
}
