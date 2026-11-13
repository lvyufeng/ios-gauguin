# 0310 candidate: observe display-on before the unattended workload

0309 completed all generated input with the requested display state off:
68 HID queue enqueues, zero command buffers or presentations in the selected
window. Its first stroke was about 69.8 seconds after the last startup Metal
buffer. The phone returned to TWRP and its original frontend was restored;
see the [0309 result](gauguin-unattended-gpu-309-results-20261114.md).

HakiOS's [actual benchmark](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/rc.jobs.bench)
begins with an unlock step before its repeated gestures. Its
[SpringBoard button handling](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L831)
also documents delayed release processing during wake producing false long
presses. The local change uses Gauguin's existing HID button service and
observes the display request; it does not assume a swipe wakes the UI or
port HakiOS's OS-specific SpringBoard hook without qualification.

## Change

Patch0232 adds a cached, atomic requested-power state in the framebuffer:
unknown until selector 12 is called, then on or off. Its timestamped log is
emitted outside the framebuffer lock. This is a software request, not proof
that the physical panel latched pixels.

Only `sweetnvt=0 swp=3` enables the new gate. At the script's existing start
time it refuses unknown state. If off, it queues one power-button press and
release in the **same callback**, then polls the cache at 50 ms intervals
for at most five seconds / 100 polls. It never holds a key across a timer or
repeats the button pair. After observing on, it waits one second and requires
on again before starting the same 13 strokes / 442 reports. A later off or
unknown state stops the workload and attempts a touch release. An already-on
display follows the settle/gate path without a power button event. The
existing `swp=1` and `swp=2` behaviors remain available.

This establishes an observable prerequisite. It does not prove SpringBoard
unlocked, consumed the gestures, rendered the desktop or achieved 60 Hz.
Another trial must require the wake-confirmation record, on state during
the workload, HID queue acceptance and actual repeated frame production.
The async GPU code is the exact one measured in 0309; the GPU-read refusal /
held-frame retirement issue remains separate.

## Offline verification and storage

The actual scripted callbacks passed 6,886 ASAN/UBSAN host checks, including
already-on, off-to-on, failed wake, unknown state, power loss during settle
or a stroke, delayed callbacks and nonadvancing-clock bounds. The original
one-stroke callback passed 2,910 checks. Both modified ARM64 translation
units compiled successfully. Exact source replay found only sweet_touch.c
and SweetFramebuffer.cpp changed from retained source309. Patch SHA-256:
`5233eede4dbd66f006ac02c093925d4448b5d32ed7db9a51ec2d21d1e3d0643e`.

Before the clone/build/capture batch, 330,161,915 bytes of obsolete generated
data were retired with checks against 178 distinct protected trial pins.
Source308 was reconstructed exactly from source309 plus reverse patches
before retirement; duplicate static files from completed0301 captures were
matched byte-for-byte to retained0309 captures. Original partition backups,
current rollback data, all raw trial logs, capture metadata and all ready
pins remain. Cleanup manifest SHA-256:
`18957425ef297aa5b32e395d1a263a177f29bbbe56a55fb493d17b44e587c26e`.
The full 780,000,000-byte batch, including a future 512 MiB capture reserve,
was admitted at 499,168,301,056 bytes accounted.

Kernel link, image review and the exact next one-shot plan are being prepared.
No 0310 phone write or boot has occurred. The 0309 approval is consumed.
