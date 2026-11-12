# One-shot display-notification and touch-path diagnostic

**Prepared, not authorized or run.** The user reports the prior 60 Hz
candidate is still very laggy and touch does not follow the finger. The
completed candidate's framebuffer counter advanced by at most four new
presents in a regular 600-beat interval, and by at most three in intervals
with physical contact-mask changes. Those are software counters, not optical
FPS. See [the previous trial result](gauguin-60hz-candidate-trial-results-20261112.md).

## Diagnostic image

Patch `xnu/patches/0223-gauguin-display-notify-hid-trace.patch` (SHA-256
`0e60fb55d51e0a0586a24c8a24e4605461ef9f91bf6ada91cd82437c5a2d4bea`)
adds bounded notification registration/send-result counters and changed HID
frame/dispatch-duration counters. It explicitly initializes the framebuffer
client's port, callbacks and counters to zero. The patch leaves the 60 Hz
clock, GPU command submission, held-frame ownership and display copy path
unchanged. It does not itself repair a missing userland registration or prove
that a successful async send was consumed by the client.

The new staged source differs from the already booted 0299 source in only
`SweetFramebuffer.cpp` and `SweetHID.cpp`. Both changed units passed native
ARM64 compilation using the 0299 build recipe. Full local kernel `make install`
passed with `SKIP_TESTS=1` after the focused checks; the isolated checkout
still lacks the older source202 fixture cache for the full host suite. The
kernel SHA-256 is
`e0f5a016b831b3eb545f3c2812c58d072374068d56146ed585ec93a1522207fe`,
build identity `xnu-b644ce2e1b9943dba3aead8c5b65989d`.

The 20,021,248-byte offline image SHA-256 is
`9d4bbee3cb0c0653bb157b6b989c47c9f82382a0ab16f91bc5aea8c742575d49`.
Its image wrapper, shim, DTB, ADT, firmware bytes/addresses and kernel virtual
segment ranges match the 0299 image. The kernel file segment grows 88 bytes;
firmware payload offsets move by 96 bytes. The 600-byte boot command replaces
`metal_fps` with `metal_fps=timeline` and omits `sweetpasmem=0` to remain
within the payload's line limit. The staged PAS/BCM sources initialize a
missing `sweetpasmem` to zero before testing it. This command keeps the
600-second GPU service and `sweetfb_hz=60`. Independent offline image review
SHA-256 is `1dc8b23f2e77ffe9c044f84b0ebb763c10e352ea938fa3f8a1b4ce6b57e19369`.
This image has not been booted.

## Current phone and exact proposed write scope

The phone is in TWRP with userdata unmounted and no block holders. A fresh
read-only capture rechecked 29 files and five directories, the current root
header SHA-256
`2c9814834dbf66065e479f77b04f7139d5da723d6bf44a26e2ea051669fdd752`,
and the original desktop executable (428,400 bytes, SHA-256
`0a1b55bb20a29661de40099e58e45ec695ffb0bf78e132a9d10985450e868550`).
The preserved 16 GiB iOS root backup rehashed as
`a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608`.

The proposed one shot repeats the already tested C4 frontend install and
dynamic restore around one temporary boot of the exact diagnostic image:

1. Recheck all 72 pinned inputs before opening a one-shot claim; then check
   phone identity, root header, full preimages, misc and live HFSX catalog
   location before any write.
2. Write 105 existing desktop data blocks at root block **3,817,791**
   (430,080 bytes), then one existing catalog block **44,123** (4,096 bytes).
   Only the length at catalog offset **2010** changes 428,400 → 428,720.
   Sync/read back each run; a partial write or failed readback rolls touched
   runs back in reverse order.
3. Write/read back the 13-byte `boot-recovery` marker to misc offset zero,
   then `fastboot boot` the exact image once, with no boot retry. The observer
   allows 780 seconds for return to TWRP and requires the image's exact kernel
   banner. If reaching recovery for rollback fails, at most one bounded
   `fastboot reboot recovery` fallback is in scope.
4. Capture current-only kernel and desktop logs, correlate notification
   registration/send counters, changed HID frames, Metal timeline, SwapEnd,
   held-frame retirement and display copy. Re-read the **postboot** HFSX
   catalog leaf. Restore the original 430,080 data bytes and only the current
   leaf's eight-byte logical length, sync/read back and repeat the 29-file
   capture. A restore failure reports an incomplete trial and uses the tested
   reverse-order rollback.

Normal explicit writes total **868,352 bytes to userdata** and **13 bytes to
misc**. One failed restoration plus rollback can raise bounded userdata
writes to **1,302,528 bytes**. No new file, allocation, partition table,
bootloader, recovery, modem or persist write is planned. The 1 GiB trial
storage reservation was admitted: 492,519,837,696 accounted bytes plus
1,073,741,824 planned bytes is below the 500,000,000,000-byte cap.

The install plan SHA-256 is
`7f53afce0661307ae6d084b88f69484c193f035df78c70094f607377069ada39`;
whole trial plan SHA-256
`9b9470515f404751030ebc5f07c5e80ff75d572ea372f8ec0f4ad5c23cb52491`.
The 72-pin ready receipt SHA-256 is
`7553bbd0a074f06fa9409419902eb86d7e2a974eae24f8c8d35ec805f5b4b750`;
independent read-only review SHA-256
`2661a579a859950894f7d48866311f5273a5ca49b2836e4e8ce1ed40a0dde1d1`.
The actual-range writer model passed 24 fault and rollback controls. The
executor refuses to create an execution claim or access device IO without a
new user reply bound to both plan hashes and the image hash. No approval or
execution claim exists. All previous one-shot authorizations are consumed.

During the 600-second service, repeated Home ↔ App Library swipes and opening
and closing Settings would give the trace a meaningful touch workload. An
original-cadence screen video would help estimate visible frames. The logs
can narrow the pipeline break without video, but they cannot certify
physical 60 fps or touch-to-photon latency on their own.
