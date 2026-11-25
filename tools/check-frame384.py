#!/usr/bin/env python3
"""Verify the private staging change against the 0383 trace and kernel source."""

from importlib import import_module
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import frame384_stage as analysis

scope = import_module('prepare-frame384')
flip = import_module('run-frame382-trial')

STUBS = r"""
#include <cassert>
#include <cstdint>
#include <cstring>
using std::memcpy;
enum { F382_FRONT, F382_FIRST, F382_SECOND };
enum { F382_WAIT, F382_TOUCHED, F382_CONFIRMED, F382_UNCERTAIN };
constexpr unsigned F382_MAX_FLIPS = 1024, F375_INFO_QUEUE = 4;
struct f375_copy {
    uint64_t target, copied;
    uint32_t swap, scan, owner;
};
struct Surface {};
struct OSObject {};
struct IOInterruptEventSource {
    unsigned posts;
    void interruptOccurred(void *, void *, int) { ++posts; }
};
static uint32_t get32(const uint8_t *r, unsigned i) {
    uint32_t value;
    memcpy(&value,r+i,4);
    return value;
}
static bool active, ending, locked;
static uint64_t tick = 1;
static unsigned issueResult, latchResult, requests, latches;
static unsigned nextFront, nextBack;
static uint64_t mach_absolute_time() { return tick; }
static void absolutetime_to_nanoseconds(uint64_t ns, uint64_t *out) { *out = ns; }
static void IOLockLock(void *) { assert(!locked); locked = true; }
static void IOLockUnlock(void *) { assert(locked); locked = false; }
static bool IOLockTryLock(void *l) { if (locked) return false; IOLockLock(l); return true; }
static bool sweet_frame382_active() { return active; }
static bool sweet_frame382_ending() { return ending; }
static uintptr_t sweet_frame382_buffer(unsigned slot) {
    assert(locked && (slot == 1 || slot == 2));
    return slot * 0x10000000;
}
static unsigned sweet_frame382_issue(unsigned front, unsigned back, uint32_t *scan) {
    assert(locked && front != back && front == nextFront && back == nextBack);
    ++requests;
    *scan = 99;
    return issueResult;
}
static unsigned sweet_frame382_latch(unsigned back, uint32_t scan) {
    assert(locked && back == nextBack && scan == 99);
    ++latches;
    return latchResult;
}
static void IOLog(const char *, ...) {}
"""

DRIVER = r"""
struct sweet_fb_frame {
    struct { bool observed; } ready;
    uint8_t record[0x108];
    Surface *surfaces[4];
    bool owner;
    uint64_t generation, retryEpoch;
    uint32_t frameInfoOwner;
};

class AppleCLCD : public OSObject {
public:
    sweet_fb_flip382 fFlip382 = {};
    sweet_fb_frame fHeldReady = {};
    uint64_t fHeldRetryEpoch = 1, fStage384PauseUntil = 0, fHeldConsumed = 0;
    unsigned fFrameInfo375Head = 0, fFrameInfo375Size = 0, takes = 0, presents = 0;
    f375_copy fFrameInfo375Pending[F375_INFO_QUEUE] = {};
    IOInterruptEventSource *fStage384Event = nullptr;
    void *fLock = nullptr;
    bool fHeldActive = false, fCalibrating = false, fPowerOff = false, fHeldStopped = false;
    bool blankReady = true;
    bool blankEnabledLocked() const { return blankReady && !fHeldStopped && !fPowerOff; }
    void flip382Poll(uint32_t);
    void flip382AdvanceLocked(uint32_t);
    uintptr_t flip382Begin(const sweet_fb_frame *, uint64_t, uint64_t, bool, bool *);
    void flip382Finish(const sweet_fb_frame *, uint64_t, uint64_t);
    bool stage384EnabledLocked() const;
    bool stage384CanTakeLocked() const;
    void signalStage384Locked();
    static void stage384Fired(OSObject *, IOInterruptEventSource *, int);
    bool takeHeldFrameLocked(sweet_fb_frame *frame, sweet_fb_frame *candidate) {
        assert(locked && candidate == &fHeldReady);
        *frame = *candidate;
        *candidate = {};
        fHeldActive = true;
        ++fHeldConsumed;
        ++takes;
        return true;
    }
    void presentTimed(uint8_t *record, sweet_fb_frame *frame, uint64_t attempt, uint64_t scan, bool early) {
        assert(!locked && record == frame->record && scan == UINT64_MAX && early && fHeldActive);
        bool blocked = false;
        assert(flip382Begin(frame,attempt,scan,early,&blocked) && !blocked);
        flip382Finish(frame,attempt,++tick);
        fHeldActive = false;
        ++presents;
    }
};
"""

TESTS = r"""
int main() {
    IOInterruptEventSource event{}, detached{};
    Surface surface{};
    AppleCLCD fb;
    fb.fStage384Event = &event;
    fb.fHeldReady.owner = true;
    fb.fHeldReady.generation = 10;
    fb.fHeldReady.retryEpoch = 1;
    fb.fHeldReady.frameInfoOwner = 5;
    fb.fHeldReady.surfaces[0] = &surface;
    fb.fHeldReady.record[0x104] = 1;
    fb.fHeldReady.record[0] = 1;
    auto frame = fb.fHeldReady;
    assert(!fb.stage384CanTakeLocked());
    active = true;
    assert(!fb.stage384CanTakeLocked());  // EOP without visibility
    fb.fHeldReady.ready.observed = frame.ready.observed = true;
    fb.fCalibrating = true;
    fb.signalStage384Locked();
    assert(!event.posts);
    fb.fCalibrating = false;
    fb.fStage384PauseUntil = 100;
    assert(!fb.stage384CanTakeLocked());
    tick = 100;
    assert(fb.stage384CanTakeLocked());
    fb.signalStage384Locked();
    assert(event.posts == 1);
    AppleCLCD::stage384Fired(&fb, &detached, 1);
    assert(!fb.takes);
    AppleCLCD::stage384Fired(&fb, &event, 1);
    assert(fb.takes == 1 && fb.presents == 1 && fb.fFlip382.copies == 1 &&
           fb.fFlip382.stage == sweet_fb_flip382::Ready && fb.fFlip382.next == F382_FIRST);
    fb.fHeldReady = frame;
    nextFront = F382_FRONT;
    nextBack = F382_FIRST;
    issueResult = F382_WAIT;
    fb.flip382Poll(99);
    assert(requests == 1 && !fb.stage384CanTakeLocked());
    issueResult = F382_TOUCHED;
    fb.flip382Poll(99);
    assert(requests == 2 && fb.fFlip382.stage == sweet_fb_flip382::Pending);
    bool blocked = false;
    assert(!fb.flip382Begin(&frame,2,UINT64_MAX,true,&blocked) && blocked);
    latchResult = F382_WAIT;
    fb.flip382Poll(99);
    assert(latches == 1 && fb.fFlip382.front == F382_FRONT && !fb.stage384CanTakeLocked());
    latchResult = F382_CONFIRMED;
    fb.flip382Poll(100);
    assert(latches == 2 && fb.fFlip382.front == F382_FIRST && fb.fFrameInfo375Size == 1 &&
           fb.fFrameInfo375Pending[0].scan == 100 && fb.stage384CanTakeLocked() && event.posts == 2);

    // The old front becomes writable when the next scan confirms.
    blocked = false;
    assert(fb.flip382Begin(&frame,2,UINT64_MAX,true,&blocked) == 0x20000000 && !blocked);
    fb.flip382Poll(100);
    assert(requests == 2);
    fb.flip382Finish(&frame,2,0); // failed to acquire the exact lease, no flip
    assert(fb.fFlip382.stage == sweet_fb_flip382::Idle);
    assert(fb.flip382Begin(&frame,3,UINT64_MAX,true,&blocked));
    ++fb.fHeldRetryEpoch; // close during copy
    fb.flip382Finish(&frame,3,++tick);
    assert(fb.fFlip382.stage == sweet_fb_flip382::Idle && requests == 2);
    frame.retryEpoch = fb.fHeldRetryEpoch;
    assert(fb.flip382Begin(&frame,4,UINT64_MAX,true,&blocked));
    fb.flip382Finish(&frame,4,++tick);
    ++fb.fHeldRetryEpoch; // close after staging, before MMIO
    fb.flip382Poll(100);
    assert(fb.fFlip382.stage == sweet_fb_flip382::Idle && requests == 2);
    frame.retryEpoch = fb.fHeldRetryEpoch;
    assert(fb.flip382Begin(&frame,5,UINT64_MAX,true,&blocked));
    fb.flip382Finish(&frame,5,++tick);
    nextFront = F382_FIRST;
    nextBack = F382_SECOND;
    fb.flip382Poll(100);
    assert(requests == 3 && fb.fFlip382.stage == sweet_fb_flip382::Pending);
    tick += 45000001;
    fb.flip382Poll(101);
    assert(latches == 2 && fb.fFlip382.stage == sweet_fb_flip382::Quarantined &&
           fb.fFlip382.front == F382_FIRST && fb.fFlip382.next == F382_SECOND);
    assert(!fb.stage384CanTakeLocked());
    fb.flip382Poll(102);
    assert(requests == 3 && latches == 2);

    AppleCLCD cleanup;
    cleanup.fStage384Event = &event;
    cleanup.fFlip382.front = F382_FIRST;
    cleanup.fFlip382.copies = F382_MAX_FLIPS;
    cleanup.fHeldReady = frame;
    blocked = false;
    assert(!cleanup.flip382Begin(&frame,1,UINT64_MAX,true,&blocked) && blocked);
    ending = true;
    nextBack = F382_FRONT;
    cleanup.flip382Poll(103);
    assert(requests == 4 && cleanup.fFlip382.stage == sweet_fb_flip382::Pending);
    cleanup.flip382Poll(104);
    assert(latches == 3 && cleanup.fFlip382.closed && cleanup.fFlip382.front == F382_FRONT);
}
"""


def kernel_fixture(source):
    state = source.split('struct sweet_fb_flip382 {', 1)[1].split('\nstruct sweet_fb_frame', 1)[0]
    worker = source.split('bool\nAppleCLCD::stage384EnabledLocked', 1)[1].split(
        '\nvoid\nAppleCLCD::presentTimed', 1)[0]
    target = 'static uint64_t\nrequestedPresentation375' + source.split(
        'static uint64_t\nrequestedPresentation375',1)[1].split('\nvoid\n',1)[0]
    contents = STUBS + 'struct sweet_fb_flip382 {' + state + DRIVER + target + \
        '\nbool\nAppleCLCD::stage384EnabledLocked' + worker + TESTS
    with TemporaryDirectory(prefix='gauguin-stage384-') as directory:
        path = Path(directory)/'verify.cpp'
        binary = path.with_suffix('')
        path.write_text(contents)
        subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined',str(path),'-o',str(binary)],check=True,timeout=45)
        subprocess.run([binary],check=True,timeout=15)


def check():
    scope.baseline()
    prior = scope.load(scope.P383/'native-kernel/build-manifest.json')
    native = scope.load(scope.BASE/'native-kernel/build-manifest.json')
    before, after = [Path(manifest['source']) for manifest in (prior,native)]
    for unit in ('bsd/dev/gauguin_ui_trace_board.c','iokit/Kernel/arm/GauguinGPU.cpp',
                 'bsd/dev/gauguin_copy356.h','bsd/dev/gauguin_frame380_phase.h'):
        assert scope.sha(before/unit) == scope.sha(after/unit)
    source = (after/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    old = (before/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    row_loop = lambda text: text.split('} else if (pairedCopy && fReadyAcrossFrames) {',1)[1].split(
        '} else if (pairedCopy)',1)[0]
    assert row_loop(source)==row_loop(old)
    present = source.split('AppleCLCD::present(const', 1)[1]
    invariants = ('SweetSurfaceGPURead gpuRead', '*stale = !scan354_has_version',
                  'if(!gpuRead.valid() || (stale && *stale))', 'const uintptr_t dst = (flipDst ?',
                  'if (flipDst && (!pairedCopy || layer != 0 || mask != 1))',
                  'scan356_copy_row(', 'if (ordered) __asm__ volatile("dsb sy"',
                  'if (flipDst && verifiedFullCopy) *verifiedFullCopy = frameCopyEnd')
    assert (positions := [present.index(item) for item in invariants]) == sorted(positions)
    assert '(!earlyStage || flipDst)' in source
    assert 'return 0; /* Empty layers retain the inherited path. */' in source
    kernel_fixture(source)
    lifetime = import_module('model-scanout-buffers').exercise()
    assert lifetime['requires_pending_flush_and_later_scan'] and \
        not lifetime['ambiguous_timeout_reuses_either_buffer']
    raw = (scope.REFERENCE/'kernel.log').read_text()
    rows, strokes, n, d = analysis.parse(raw)
    assert len(strokes)==13
    receipts = flip.latch_receipts(raw,rows)
    joined = analysis.verified_latches(rows,receipts['accepted_by_scan'])
    replay = analysis.replay(rows,joined,n,d)
    assert len(joined)==760 and replay['earlier_stage_candidates'] > 0
    return dict(state='0384-offline-stage-verified',patch_sha256=scope.sha(scope.PATCH),
        unchanged_GPU_and_DPU=True,exact_lease_before_copy=True,output_barrier_before_stage_publication=True,
        sanitizer_state_machine=True,original_latch_fixtures=import_module('check-frame382').check_fixtures(),
        lifetime=lifetime,reference_replay=replay,device_commands=0)


if __name__=='__main__':
    proof = check()
    scope.save(scope.HOST,proof)
    print(proof)
