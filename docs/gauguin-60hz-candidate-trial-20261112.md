# One-boot 60 Hz latency candidate trial

**Historical pretrial plan; executed once and restored.** See
[the trial result](gauguin-60hz-candidate-trial-results-20261112.md) for the
actual one-shot outcome and the user's lag report. The user reports
that iOS reaches the screen but remains laggy and asked to establish smooth
60 Hz before high refresh. This trial keeps the C4 Metal frontend active for
one bounded diagnostic boot, changes only the native submit status-check
schedule in the kernel, and restores the original frontend afterward. It can
measure whether GPU lock wait improves. It cannot, by itself, certify physical
60 fps or a correct scanout latch.

## Exact candidate and current phone state

The phone is reachable in Gauguin TWRP. A fresh read-only HFSX capture
verified 29 files and five directories with userdata unmounted and no block
holders. Its root-header SHA-256 is
`8e81a422e334b7f484a17f9af7c6e85076319f41ac9a7dcca65b0301a45453fe`.
The original desktop executable is restored at 428,400 bytes, SHA-256
`0a1b55bb20a29661de40099e58e45ec695ffb0bf78e132a9d10985450e868550`.
The preserved full 16 GiB iOS root backup was rehashed as
`a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608`.

The one-boot image is 20,021,248 bytes, SHA-256
`63c085a7bcbaacd494cc94b965b1386ffa8770f4e77cd4e415e7bf9389636f73`.
Its kernel is SHA-256
`ff30b0829be9049645e96a3415441c172af1f3fe396c79314f1396bfa4b68241`
with build identity `xnu-355bac7a07774f6585bb66ee521f9ce7`. The image
uses the exact 605-byte 0298 boot command, including `sweetfb_hz=60`,
`sweetfb_stats=1`, `sweetnvt=1` and a 600-second GPU service. Its shim, DTB,
ADT, firmware addresses/bytes and outer boot geometry match 0298. Only the
kernel payload differs. The physical touch worker was observed polling in the
prior C4 boot; software clock callbacks do not prove a 60 Hz panel frame rate.

The C4 frontend executable is the already signed 428,720-byte artifact,
SHA-256 `560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5`.
It selects the private owned core at
`/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib`. The existing
installed private core is left unchanged. No allocation, file creation or
partition-table change is proposed.

## Proposed one-shot scope

1. Recheck the pinned 67 inputs, current 29-file capture, full backup, volume
   header, misc preimage, data extent and the live HFSX catalog location before
   any write. The prior trial's catalog block 44139 is stale. The current
   catalog leaf is block **44123**, with the file length field at byte **2010**.
2. Write 105 existing data blocks starting at root block **3,817,791**
   (430,080 bytes), then one existing catalog block **44,123** (4,096 bytes).
   Only its eight-byte logical length changes 428,400 → 428,720. Sync and
   read back each run. Any partial write or failed readback rolls touched runs
   back to their current preimages in reverse order.
3. Write and verify the 13-byte `boot-recovery` marker at misc offset zero.
   Temporarily `fastboot boot` the exact candidate image once, with no boot
   retry. The GPU service runs 600 seconds; the observer waits at most 780
   seconds for TWRP and requires the image's exact kernel banner. A preboot
   failure may use at most one `fastboot reboot recovery` to reach the phone
   for rollback, if explicitly approved.
4. Capture current-only kernel, stdout, stderr and backboardd evidence. Parse
   completed GPU submissions, full health-check counts, successful copied
   bytes, copy/guard histograms, software-beat skips and touch transitions.
   Re-read the **postboot** HFSX catalog; its location may have moved again.
   Restore the original 430,080 data bytes and the then-current catalog leaf,
   changing only the eight-byte logical length back to 428,400. Sync, read
   back, and repeat the 29-file capture. A restore failure uses the tested
   reverse-order rollback and reports an incomplete trial.

Normal explicit userdata writes total **868,352 bytes**, plus **13 bytes**
in misc. A restore failure and rollback can raise bounded userdata writes to
**1,302,528 bytes**. The plan has no GPT, bootloader, recovery, modem or
persist writes. It reserves 1 GiB: 488,925,081,600 accounted bytes plus
1,073,741,824 planned bytes is within the 500,000,000,000-byte cap.

For a useful 60 Hz observation, the user can repeat Home ↔ App Library swipes
for 30 seconds and open/close Settings during the service window. An original
speed video of the screen would allow distinct visible frame analysis. These
actions are separate from the write approval; the trial may still collect
kernel measurements if no interaction/video is available. No result is called
smooth 60 Hz without a sustained visible-frame measurement.

## Review and remaining limit

The fresh install plan SHA-256 is
`a6d1c2a4810d1f1d551ded7cdecdebbc47b73a27b71c02cf9ed3b5346708e3ed`;
the whole trial plan is
`dfaad8e4db036aead3e3d83e5aba91194b21c00dbc9ca1ec61ee9202581b5c81`.
The ready receipt SHA-256 is
`a6f8cabe22bd98b6dfecddb2682b26d27c131c7b208968aa67998f2bd462546f`.
The independent read-only review SHA-256 is
`ca4e6ad7f1538e17a6e62dfd040e8463b82e2e8fe38c4738b518aaa1a7b528d8`.
Its 24 in-memory writer controls include absent/wrong consent, stale data,
catalog or header, partial writes, failed readback and dynamic restoration
that preserves unrelated postboot catalog bytes. The executor required an
actual user reply bound to both plan hashes and the image hash. That approval
was granted for this one shot and is now consumed.

Private artifacts, exact images, candidate ranges, ready pins and runner are
under `research/tmp/gpu-poll-guard-20261112` inside the present-trace
worktree. The original 0298/C4 trials and their approvals are consumed. If
this boot shows lower guard counts but the UI remains slow, the next comparison
must isolate command-buffer/CA production latency and hardware scanout. The
current 60 Hz software timer and TWRP's measured 60.244 Hz vblank do not prove
the same physical scan during iOS.
