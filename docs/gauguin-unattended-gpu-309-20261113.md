# 0309 candidate: display progress during GPU waits and unattended animation

**2026-11-14: this one-shot trial is complete and the original frontend is
restored.** The script ran while the display was off; see the
[recorded result](gauguin-unattended-gpu-309-results-20261114.md).
The preparation and approved scope below are historical, not permission to
repeat the boot.

The user is away from the phone and asked work to continue. The completed
0301 trial measured no contact, so repeating an idle physical-touch trial
would not exercise the lag. This candidate supplies a bounded automatic
workload and addresses a concrete remaining serialization in the async path.
It is not a measured 60 Hz result. No 0309 phone boot or partition write has
occurred; its exact image and destructive trial scope must be finalized first.

## GPU wait contract

Patch0230 follows HakiOS's
[200 microsecond waits outside its GPU lock](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L195).
Gauguin's default path is still synchronous. With the existing
`sweetgpuasync=1` compositor opt-in, the bridge issues one native fence and
keeps every referenced descriptor, IOSurface and SMMU mapping until completion.
Waiting for that fence now releases the GPU lock between guarded polls, so a
framebuffer reader can poll and finish it. A separate request mutex keeps
client close, handle reuse, queue removal, new submissions and heartbeat
serialized throughout the wait. Lock orders are request → GPU → surface and
framebuffer → GPU → surface; the display never takes the request mutex.

After relocking, the waiter checks whether display already finished its
escrow before reading pending pointers. All board calls still run under the
GPU lock with the same live-owner, route, EOP and timeout checks. A timeout
does not cancel DMA or release pages. Faulted memory and the owning client
remain retained. The runtime's original two-second pending deadline remains,
with an additional 10,000-iteration bound. This is deliberately narrower than
HakiOS's broader concurrent request model; upload/map APIs still serialize.

API profiling now excludes unlocked wait intervals from `held_ns` and emits
them as `wait_ns`. A stop while the request is unlocked freezes only its
actual held prefix. End-to-end API trace spans continue to include the wait.
The 0301 mean 10.93 ms submit-lock cost is a baseline observation, not a
predicted improvement from this change; full guard and CPU copy costs remain.

## Unattended workload

Patch0231 adds `sweetnvt=0 swp=2`. At +180 seconds it emits one bottom-to-top
stroke, waits six seconds after release, then emits six alternating left/right
pairs at y=1200, with two seconds between releases and the next stroke.
There are exactly 13 strokes and 442 reports. Every stroke has a 1.5-second
window; any failed HID call or invalid clock stops the sequence and attempts
one release. There is no retry or indefinite input loop. `swp=1` retains the
existing single unlock stroke, and physical input still uses `sweetnvt=1`.

Generated reports use the same HID frame entry and queue instrumentation,
but carry explicit `GUT_SYNTHETIC` markers with stroke, step and coordinates.
The trace parser checks those markers and labels the capture's input origin.
`sweettrace=2` selects the first horizontal stroke after the unlock attempt.
HID return success does not establish that SpringBoard unlocked or animated;
accepted queue records, C4 submissions and framebuffer presentations must
demonstrate that the workload actually ran. Synthetic input cannot qualify
Novatek sampling, physical finger latency or panel refresh.

## Offline validation

Source309 is an admitted APFS clone of retained source308. The 350,000,000-byte
batch passed the 500 GB cap at 499,080,052,736 bytes accounted. Its 5,336-file
comparison found exactly three changed production files: GauguinGPU.cpp,
sweet_touch.c and gauguin_ui_trace.h. Both patches apply with exact replay;
source-state receipt SHA-256:
`1b351ab0f1540688cc3fcf3c5b2e80d73fa737f1dd323feee7750c38a5202bff`.

The actual wait/completion methods and profiling helpers passed ASAN/UBSAN
cases for display completion during the unlocked interval, stop/freeze during
that interval, caller timeout, bounded noncompletion, alias failure and
deferred close. Actual submit tests and the full IOKit typed-seam scenarios
passed. The actual automatic callbacks passed 6,671 checks, including every
possible HID failure point; the original single-swipe callbacks passed 2,910
checks. Trace/core/board tests and timeline parsing passed with synthetic
origin and malformed-marker cases. Initial standalone ARM64 translation-unit
compiles passed for both changed implementation files. These are CPU and
compile checks, not a hardware performance result.

## Linked kernel and image review

Commit `1229548` is pushed. Actions run
[43446429656](https://github.com/lvyufeng/ios-gauguin/actions/runs/43446429656)
was dispatched for its exact full SHA. It ended with run conclusion `failure`
and job conclusion `cancelled` before any step ran: GitHub reported that no
hosted runner acquired the job after repeated attempts, with macOS arm64
capacity notices. This provides no compiler or test result.
To continue, the existing native 0301 build was used for a verified local
incremental link. Re-linking its original object list reproduced every byte
of its unstripped kernel except the linker's 16-byte `LC_UUID`. Comparing
source309 against the build manifest found exactly four changed implementation
files and two headers. The four implementations were compiled for ARM64;
they replaced exactly four entries in the original object list. A separately
compiled version object supplies the new unique identity
`xnu-local309-5a3b61208fee4cba8f1f0e9e7c3da645` (the date in the retained
version template remains the original template date). The unchanged link
flags, libraries and remaining objects produced a complete kernel, with all
protected input hashes and mtimes unchanged. This is an incremental native
link, not a completed clean CI build.

The kernel is 17,365,208 bytes, SHA-256
`60e08633e856e8c2c72083c673f0c630b3bc7fb170772a98d6ccfe8971169f9e`.
Its link manifest SHA-256 is
`91cffbcd165ee397ceda2bda3f356a500526b69a569052210898bb07e964e527`.
The 20,054,016-byte temporary boot image SHA-256 is
`f0ce9885ccb059c099f49f9e1c433524d91f6d8e84e0b99603f5a67ef253f9e3`.
A separate checker verified the Android wrapper, shim and DTB against 0301,
and all ten embedded kernel segments directly against the Mach-O bytes
(there are no chained fixups). It checked firmware contents, zero padding,
managed RAM, entry point, ADT and pending low-PAS request. Firmware addresses
move by 32 KiB with the kernel growth; the ADT points to the checked new
locations. Review receipt SHA-256:
`32c4c3dae2196ebb50ddf154abfea96a417b0a65f8ed6f73c5db1b00c2e3ab89`.

The command is 606 bytes. It keeps the 60 Hz software clock and 600-second
service, selects `sweetnvt=0 swp=2 sweetgpuasync=1`, and removes
`sweettouchmode=0`, whose legacy consumer is bypassed by the script branch.
No phone boot or performance result exists for this image yet.

## Exact unattended phone trial awaiting confirmation

A fresh read-only 29-file capture and live HFSX inspection passed in TWRP.
Root header SHA-256 is
`490a694e52106fbc3b1333800d7d0735b879909255c0e249c28037b13294731d`.
The original desktop bytes, file identity, 105-block extent and catalog
logical-size location still match. Misc is the checked original zero preimage.
The actual range writer passed 24 model tests, including stale preimages,
partial writes, incorrect readback and rollback. No device writes occurred.

With a fresh exact-scope user reply, the prepared one-shot executor will:

1. Rehash its inputs and recheck the current TWRP files and partition preimages.
2. Write/read back the same 434,176-byte C4 frontend delta: 105 existing data
   blocks and one existing catalog leaf, changing only its logical-size field.
3. Write/read back the 13-byte misc recovery marker and temporarily boot the
   exact 0309 image once. Enable async GPU submission and run the 13-stroke
   workload automatically; no physical interaction is required.
4. Observe for at most 780 seconds, collect the current logs, then restore
   and read back 434,176 bytes for the original frontend. Normal userdata
   writes total 868,352 bytes. The existing tested failure/rollback bound is
   2,170,880 userdata bytes, with at most one `fastboot reboot recovery` if
   recovery is needed. There is no repeated boot.

Capture output has a calculated 394,007,680-byte maximum (four bounded full
captures, current log tails, kernel dump, rollback files and metadata), covered
by a 536,870,912-byte reserve under the 500 GB project cap. Each log capture
refuses files above 8 MiB; an oversized postboot log fails diagnostics and
takes the restoration path. The executor was tested to reject missing user
approval before any device IO. The exact trial plan SHA-256 is
`f6e051b80e6b3ca0293d4dd2f31c444af886ec3fb3e9171a7700bd57f7c8c624`;
install plan SHA-256 is
`b75e258b2a0faa23667fef6639b1ae59bacecda5ff7f3adfe68be1c2ba0e4333`.
All 87 execution inputs were rehashed, including the retained 16 GiB backup.
The immutable ready receipt SHA-256 is
`3a2fab8e9061ba2ddad8ee58e707b9caed5674638ea572c78c25090de43469b0`.

Validation requires the async opt-in, all 13 scripted strokes, explicitly
synthetic/loss-free HID queue evidence, repeated C4 frame production and
framebuffer presentations in the capture window, and completed native jobs.
It reports frame gaps and API held/wait times. It does not equate scripted
input, a software clock or successful copies with physical touch or panel
refresh. Original backups, rollback snapshots, source308/309 and active pins
remain retained. AGENTS.md requires confirmation before this new destructive
trial; the completed 0301 one-shot approval is not reused.
