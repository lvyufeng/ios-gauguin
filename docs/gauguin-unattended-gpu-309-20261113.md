# 0309 candidate: display progress during GPU waits and unattended animation

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

Full kernel build, image packaging and exact unattended trial plan remain
pending. The completed 0301 approval does not authorize another partition
write. Original backups, rollback snapshots, source308 and W301/W302 pins
remain retained.
