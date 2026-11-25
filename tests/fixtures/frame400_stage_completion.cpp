// Exercise the exact framebuffer workloop and pending-latch state machine.
#include <cassert>
#include <cstdint>

struct OSObject {};
struct IOInterruptEventSource {};
void IOLockLock(int*) {}
void IOLockUnlock(int*) {}
void IOLog(const char*, ...) {}
constexpr uint32_t F382_FRONT = 0, F382_FIRST = 1, F382_SECOND = 2;
constexpr unsigned F382_WAIT = 0, F382_TOUCHED = 1, F382_CONFIRMED = 2, F382_UNCERTAIN = 3;
constexpr unsigned F375_INFO_QUEUE = 4;
uint64_t now = 1;
uint64_t mach_absolute_time() { return now; }
void absolutetime_to_nanoseconds(uint64_t ticks, uint64_t* ns) { *ns = ticks; }

unsigned issues = 0, latches = 0;
unsigned issue_code = F382_TOUCHED, latch_code = F382_WAIT;
bool positioned = true, ending = false;
struct scan351_position {uint32_t frame;};
bool sweet_frame351_position(scan351_position* position) {
    position->frame = 9;
    return positioned;
}
bool sweet_frame382_ending() { return ending; }
unsigned sweet_frame382_issue(unsigned front, unsigned next, uint32_t* scan) {
    assert(front != next);
    ++issues;
    *scan = 9;
    return issue_code;
}
unsigned sweet_frame382_latch(unsigned next, uint32_t frame) {
    assert(next == F382_SECOND && frame == 9);
    ++latches;
    return latch_code;
}

struct sweet_fb_frame {uint8_t* record; uint64_t generation;};
struct sweet_fb_flip382 {
    enum {Idle,Copying,Ready,Pending,Quarantined} stage = Idle;
    struct Receipt {unsigned owner,scan;} receipt = {};
    unsigned next = F382_SECOND, front = F382_FIRST, scan = 0;
    uint64_t stageEpoch = 1, attempt = 77, issueTick = 0;
    bool closed = false;
};
struct AppleCLCD : OSObject {
    static void stage384Fired(OSObject*,IOInterruptEventSource*,int);
    void flip382AdvanceLocked(uint32_t, bool = false);
    int lock = 0;
    int* fLock = &lock;
    IOInterruptEventSource event;
    IOInterruptEventSource* fStage384Event = &event;
    unsigned programState = sweet_fb_flip382::Ready, fHeldConsumed = 77;
    sweet_fb_frame fHeldReady = {nullptr,2};
    sweet_fb_flip382 fFlip382;
    bool fPowerOff = false, fHeldStopped = false, fHeldActive = false, fCalibrating = false;
    unsigned fHeldRetryEpoch = 1, fFrameInfo375Head = 0, fFrameInfo375Size = 0, signaled = 0;
    sweet_fb_flip382::Receipt fFrameInfo375Pending[F375_INFO_QUEUE] = {};
    bool stage384CanTakeLocked() { return true; }
    bool takeHeldFrameLocked(sweet_fb_frame* out,sweet_fb_frame* frame) { *out = *frame; return true; }
    void presentTimed(uint8_t*,sweet_fb_frame*,uint64_t,uint64_t,bool) { fFlip382.stage = static_cast<decltype(fFlip382.stage)>(programState); }
    void signalStage384Locked() { ++signaled; }
};

#include "Stage400Methods.inc"

int main() {
    using Flip = sweet_fb_flip382;
    AppleCLCD first;
    first.fFlip382.receipt = {1,0};
    AppleCLCD::stage384Fired(&first,&first.event,0);
    assert(issues==1 && first.fFlip382.stage==Flip::Pending && first.fFlip382.front==F382_FIRST);
    first.flip382AdvanceLocked(9);
    assert(issues==1 && latches==1 && first.fFlip382.stage==Flip::Pending);
    latch_code = F382_CONFIRMED;
    first.flip382AdvanceLocked(10);
    assert(issues==1 && latches==2 && first.fFlip382.stage==Flip::Idle && first.fFlip382.front==F382_SECOND);
    assert(first.fFrameInfo375Size==1 && first.fFrameInfo375Pending[0].scan==10);

    AppleCLCD late;
    issue_code = F382_WAIT;
    AppleCLCD::stage384Fired(&late,&late.event,0);
    assert(issues==2 && late.fFlip382.stage==Flip::Ready && late.fFlip382.front==F382_FIRST);
    issue_code = F382_TOUCHED;
    late.flip382AdvanceLocked(9);
    assert(issues==3 && late.fFlip382.stage==Flip::Pending);
    now += 45000001;
    late.flip382AdvanceLocked(12);
    assert(issues==3 && latches==2 && late.fFlip382.stage==Flip::Quarantined && late.fFlip382.front==F382_FIRST);

    AppleCLCD stale;
    stale.fFlip382.stageEpoch = 2;
    AppleCLCD::stage384Fired(&stale,&stale.event,0);
    assert(issues==3 && stale.fFlip382.stage==Flip::Idle && stale.signaled==1);

    AppleCLCD wrong;
    wrong.fFlip382.attempt = 91;
    AppleCLCD::stage384Fired(&wrong,&wrong.event,0);
    assert(issues==3 && wrong.fFlip382.stage==Flip::Ready);

    AppleCLCD no_position;
    positioned = false;
    AppleCLCD::stage384Fired(&no_position,&no_position.event,0);
    assert(issues==3 && no_position.fFlip382.stage==Flip::Ready);

    AppleCLCD restore;
    positioned = true;
    ending = true;
    AppleCLCD::stage384Fired(&restore,&restore.event,0);
    assert(issues==3 && restore.fFlip382.stage==Flip::Ready && restore.fFlip382.attempt==77);
    restore.flip382AdvanceLocked(10);
    assert(issues==4 && restore.fFlip382.stage==Flip::Pending && restore.fFlip382.attempt==0);
}
