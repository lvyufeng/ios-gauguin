#include "gauguin_page_flip.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>

struct IOLock { bool available = true; };
static bool IOLockTryLock(IOLock *lock) { return lock->available; }
static void IOLockUnlock(IOLock *) {}
static constexpr uint64_t NSEC_PER_MSEC = 1'000'000;
static uint64_t now;
static uint64_t mach_absolute_time() { return now; }
static void absolutetime_to_nanoseconds(uint64_t ticks, uint64_t *ns) { *ns = ticks; }
static void IOLog(const char *, ...) {}

struct f375_copy { uint32_t owner, scan; };
struct sweet_fb_flip382 {
    enum { Idle, Copying, Ready, Pending, Quarantined, GPUProbe };
    unsigned stage, front, next, copies;
    uint32_t scan;
    uint64_t attempt, issueTick, stageEpoch;
    f375_copy receipt;
    bool closed;
};

struct AppleCLCD {
    IOLock lock;
    IOLock *fLock = &lock;
    sweet_fb_flip382 fFlip382{};
    bool fPowerOff = false, fHeldStopped = false, fHeldActive = false, fCalibrating = false;
    uint64_t fHeldRetryEpoch = 1, fHeldConsumed = 0;
    static constexpr unsigned F375_INFO_QUEUE = 4;
    f375_copy fFrameInfo375Pending[F375_INFO_QUEUE]{};
    unsigned fFrameInfo375Head = 0, fFrameInfo375Size = 0;
    void signalStage384Locked() {}
    bool flip382EndingLocked() const;
    unsigned flip382Poll(uint32_t scan);
    void flip382AdvanceLocked(uint32_t scan, bool fromStaging = false);
};

static bool ending;
static unsigned issue_status, latch_status, issue_calls, requests, latch_calls, requested;

bool sweet_frame382_ending() { return ending; }
#ifdef SUSTAINED417
unsigned sweet_frame382_copy_limit() { return F382_MAX_FLIPS; }
#endif

unsigned sweet_frame382_issue(unsigned front, unsigned next, uint32_t *scan)
{
    assert(front != next);
    ++issue_calls;
    if (issue_status == F382_TOUCHED) {
        ++requests;
        requested = next;
        *scan = 42;
    }
    return issue_status;
}

unsigned sweet_frame382_latch(unsigned, uint32_t)
{
    ++latch_calls;
    return latch_status;
}

#include "display_drain416.inc"

static void reset()
{
    ending = false;
    now = 1;
    issue_status = F382_TOUCHED;
    latch_status = F382_CONFIRMED;
    issue_calls = requests = latch_calls = requested = 0;
}

static void verify_original(AppleCLCD &fb)
{
    assert(!fb.fFlip382.closed && fb.fFlip382.stage == sweet_fb_flip382::Pending);
    assert(fb.flip382Poll(43) == F382_DRAIN_DONE);
    assert(fb.fFlip382.closed && fb.fFlip382.front == F382_FRONT);
    assert(fb.flip382Poll(44) == F382_DRAIN_DONE);
    assert(requests == 1 && requested == F382_FRONT);
}

int main()
{
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382 = {sweet_fb_flip382::Ready, F382_FIRST, F382_SECOND, F382_MAX_FLIPS,
                       42, 77, 0, 1, {1, 42}, false};
        fb.flip382AdvanceLocked(42, true);
        assert(issue_calls == 0 && fb.flip382EndingLocked());
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT);
        verify_original(fb);
        assert(fb.fFrameInfo375Size == 0);
    }
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382 = {sweet_fb_flip382::Pending, F382_FIRST, F382_SECOND, 5,
                       41, 12, now, 0, {}, false};
        ending = true;
        latch_status = F382_WAIT;
        assert(fb.flip382Poll(41) == F382_DRAIN_WAIT && issue_calls == 0);
        latch_status = F382_CONFIRMED;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT && issue_calls == 0);
        assert(fb.fFlip382.front == F382_SECOND);
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT);
        verify_original(fb);
    }
    for (unsigned held : {sweet_fb_flip382::Copying, sweet_fb_flip382::GPUProbe}) {
        reset();
        AppleCLCD fb;
        fb.fFlip382.front = F382_FIRST;
        fb.fFlip382.stage = held;
        ending = true;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT && issue_calls == 0);
        fb.fFlip382.stage = sweet_fb_flip382::Idle;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT);
        verify_original(fb);
    }
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382.front = F382_FIRST;
        ending = true;
        fb.fHeldActive = true;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT && issue_calls == 0);
        fb.fHeldActive = false;
        fb.lock.available = false;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT && issue_calls == 0);
        fb.lock.available = true;
        issue_status = F382_WAIT;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT && requests == 0);
        issue_status = F382_TOUCHED;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT);
        verify_original(fb);
    }
    reset();
    {
        AppleCLCD fb;
        ending = true;
        assert(fb.flip382Poll(42) == F382_DRAIN_DONE && issue_calls == 0);
    }
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382.front = F382_FIRST;
        ending = true;
        issue_status = F382_UNCERTAIN;
        assert(fb.flip382Poll(42) == F382_DRAIN_QUARANTINED);
        assert(fb.flip382Poll(43) == F382_DRAIN_QUARANTINED && issue_calls == 1);
    }
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382.front = F382_FIRST;
        ending = true;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT);
        now += 46 * NSEC_PER_MSEC;
        assert(fb.flip382Poll(47) == F382_DRAIN_QUARANTINED && latch_calls == 0);
        assert(fb.flip382Poll(48) == F382_DRAIN_QUARANTINED && requests == 1);
    }
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382.front = F382_FIRST;
        fb.fPowerOff = true;
        ending = true;
        assert(fb.flip382Poll(42) == F382_DRAIN_QUARANTINED && issue_calls == 0);
    }
    reset();
    {
        AppleCLCD fb;
        fb.fFlip382.stage = sweet_fb_flip382::Ready;
        fb.fFlip382.next = F382_FIRST;
        assert(fb.flip382Poll(42) == F382_DRAIN_WAIT);
        assert(fb.flip382Poll(43) == F382_DRAIN_WAIT && fb.fFlip382.front == F382_FIRST);
        assert(requests == 1 && requested == F382_FIRST && !fb.fFlip382.closed);
    }
    std::puts("10");
}
