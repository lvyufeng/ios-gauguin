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

## Linked and reviewed image

Code is pushed as `ea09a96`. The two changed implementations passed native
ARM64 compilation. The local link used the same verified 0301 object list,
replacing the five implementations changed since that baseline (three
unchanged GPU objects from 0309 plus the two new 0310 objects) and a new
version object. The original-object check again matched its original kernel
except `LC_UUID`; all protected inputs retained hashes and mtimes. This is
an incremental native link, not a clean CI build. The previous CI attempt
failed before compilation because no hosted macOS runner acquired the job.

Kernel identity: `xnu-local310-e8a65610fda2474a98e0eada9d12a2f8`.
Kernel size: 17,365,456 bytes; SHA-256:
`47f86a5371c8b48b425f910a81c7c432da4e515848d4995b294f3a3b53ce6cf7`.
Link manifest SHA-256:
`58995bc792fc31b7cb8d920d52b393b19b5a5d09248a1ceb38ea4ff107a424a2`.
The retained version template still has its old date; this unique identity
distinguishes the candidate.

The temporary boot image is 20,054,016 bytes, SHA-256
`0a7726d90f5588a8f0c9d405066761d1c335030b9dc4df068660083adc339067`.
Separate review checked all embedded kernel segment bytes against Mach-O,
the entry point, managed RAM and low-PAS request. The Android wrapper,
shim, DTB, firmware addresses/contents/padding and full ADT match 0309.
The 606-byte command changes only `swp=2` to `swp=3`; it retains
`sweetgpuasync=1`, the 60 Hz software clock and the 600-second service.
Review SHA-256:
`bd60cc861c6c39a0037e1ecfd6dfcf32f0b5fe1dfc59b964c6e3bd0e8342da08`.

## Exact next trial awaiting confirmation

The baseline is the independently verified 0309 restored 29-file capture.
A new read-only HFSX check matched the current file identity, data extent,
catalog logical-size location and misc preimage. Root header SHA-256 is
`7cfe30f1b55eb7ed941250226751b60b3b165625f6bab90697e90fa4f5f91055`.
The actual writer passed all 24 model controls again with the new preimages.
The executor also rejects missing approval before device IO. Its wake-log
validator passed two valid cases and rejected 12 invalid cases, including
missing/repeated button events, off-state input and reordered strokes.

With a new exact-scope reply, the one-shot executor will rehash its inputs
and repeat the live 29-file/preimage checks, install/read back 434,176 bytes
in the existing userdata extent/catalog, write/read back the 13-byte misc
recovery marker and temporarily boot this exact image once. The script may
send **at most one power-button press/release pair** if the display is off,
must observe on, then emits the 13 strokes. It needs no person beside the phone.

The observer is bounded to 780 seconds. After log collection, the executor
restores/read backs the original frontend's 434,176 bytes. Normal userdata
writes total 868,352 bytes; the tested failure/rollback ceiling remains
2,170,880 bytes. At most one `fastboot reboot recovery` is allowed if needed
for rollback. There is no boot retry. A 536,870,912-byte capture reserve passed
at 499,368,902,656 bytes accounted, covering the same 394,007,680-byte bounded
capture maximum as 0309.

Plan SHA-256:
`b4813fc023f981b56408cb908982209c9d37c12942da69b3a48afb90ca47e41e`;
install plan SHA-256:
`1d14000e1515dc6cf778cc8ae94269ff3c2de4b0f157380a0bed7c9fef5acbd3`.
All 93 execution inputs, including the retained 16 GiB backup, were rehashed.
Ready receipt SHA-256:
`431efde8befffb4577c4378d68e2a154e7ed31e5bfb2b6affb022e6b0dca813f`.
Validation requires display-on confirmation before the first stroke, no off
request during the workload, HID queue acceptance, repeated C4 command buffers,
presentations and completed GPU-protected surface reads. It reports observed
frame gaps without claiming physical refresh or an unlocked desktop from those
counters alone.

No 0310 phone write or boot has occurred. The 0309 approval is consumed;
AGENTS.md requires confirmation for this new destructive trial.
