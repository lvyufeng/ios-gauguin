# Renewed HakiOS / UniXNU review: desktop acceptance first

Rechecked the public sources on 2026-11-11 for the user's renewed request.
HakiOS main remains `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`; it offers no
new graphics revision beyond our earlier reviews. This review corrects work
priorities and sharpens acceptance criteria; it implements no driver change.
Do not describe an already known gap as a newly discovered fix.

## The reference is useful, but its success has boundaries

HakiOS reports full-resolution 1125x2436 swipes at about 100–104 fps and Settings
scrolling at 89–91 fps. Its 118–120 fps Settings run uses 750x1624 rendering,
frozen wallpaper and synthetic gestures. Real-finger drag rates are 75–80 fps.
These are the author's swap/driver measurements, not an independent optical
measurement of the panel. They are not an A619 performance forecast.
See [measurement conditions](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md).

HakiOS's own comparison finds native hakios-metal faster than its port of
metal2vulkan. It explicitly says its M2V result is not a measurement of UniXNU's
A740 driver or newer system. Its native driver is therefore a relevant A6xx
reference, while replacing our port with UniXNU is not a demonstrated shortcut
for this A619 board. See [backend differences and limitations](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal.md#known-gaps).

## What needs attention on gauguin

### A compiled Metal probe is not an accelerated desktop

The current physically qualified state is the 0239 kernel and installed 0237
root. The 0244–0250 desktop integration, including plugin publication, UID501
admission/cache, root-to-compositor ownership, task-backed input and held/phase
presentation, is a source/native candidate. The 0250 temporary image exists;
it has not run on the phone. Root offscreen successes cannot establish that
backboardd loads the plugin or that its visible frames use native GPU jobs.

HakiOS's frontend explicitly describes Metal.framework discovery through the
accelerator's `MetalPluginName` and `MetalPluginClassName`, which must match the
installed bundle. See [discovery contract](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L12).
Our [0250 build/profile report](gauguin-desktop-boot-profile-20261111.md) records
the candidate and repairs the earlier 638-byte command truncation. That repair
is complete in source/native assembly; it is not a new finding of this review.

Acceptance must join the entire same-boot chain: the root qualifier finishes
and releases ownership; backboardd discovers and opens the intended device;
its own submissions complete; completed shared output reaches presentation.
Record the process, selected class, submission/completion and frame identities.
Do not infer selection merely from a dylib having loaded.

### The reference's red/white image failures involved shader semantics

HakiOS documents that its previous fixed shader substitutions produced a red
wallpaper head, white status-band background and opaque widget. Its present
`hm_ca_nearest()` chooses substitutes by labels, and its docs still disclaim
equivalence to the matching library. It also documents an initially refused
decoded-image no-copy buffer upload that left textures uninitialized.
See [shader limitations](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal.md#known-gaps),
[variant selection](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L1520)
and [image upload](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L2610).

This resemblance is a diagnostic lead, not proof that gauguin's earlier EAGL
defects have the same cause. Our current candidate already removes nearest
and process-wide stand-ins in `0002-gauguin-exact-ca-functions.patch`, uses the
20H392-specific specialization path, and adds a bounded immediate image-upload
snapshot in patch 0006. Do not reintroduce substitutions to make a test pass.
Physical acceptance must cover actual requested variants/constants, bound
images, row strides, pixel formats/FP16, alpha and effects. Check whole frames:
populated icons/widgets, correct lock-screen clock, App Gallery, Settings,
return-home and repeated lock/unlock. Missing layers cannot count as speed.

### Our completion model still prevents overlap

The actual 0250 `GauguinGPU.cpp` calls the synchronous runtime under the global
lock, then increments the queue's completed counter. Display GPURead takes
that same lock through copying. This is still the [previously identified
serialization](gauguin-hakios-pipeline-review-20261111.md), not a newly fixed
performance issue. A 16.9 ms whole-submit average is neither GPU-only time nor
59 desktop frames per second: a frame can contain several submissions.

HakiOS associates issued fences with resources and waits later; see [buffer
and surface fence association](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L1063).
A safe change needs distinct issued/completed state, retained buffers and
mappings, per-output readiness, bounded queues, close/timeout handling and
fault quarantine. Removing a lock or returning early alone is insufficient.
Its separate deferred CPU encoding option is another mechanism.

### Input, animation requests and display scan are different clocks

The reference runner enables CPU frequency control, copy workers, deferred
encoding, animation-range changes and panel timing. Its measurement record
also shows a real-finger missed-report defect, long SpringBoard main-thread
turns and changes that did not help. Novatek on gauguin reads every poll, so
the other controller's IRQ fix is not established here. An 8 ms sleep also
does not prove an 8 ms total sampling interval.
See [runner settings](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L19)
and [real-finger measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md#under-real-fingers-5-november).

Correlate one real gesture across report-read/HID, CA commit, CPU encoding,
issued fence, actual completion, copy and panel latch. Include requested
animation cadence, actual CPU/GPU clocks and copy time. Eight enabled CPUs,
a software 60/120 Hz timer or one fast GPU request does not measure this chain.
Use the result to choose the optimization; do not copy SM7325 MMIO addresses
or force an unqualified 120 Hz value on SM7225.

## Fresh UniXNU lessons that complement HakiOS

Pinned UniXNU main `722379fdcfe0a4078ca59e38eb3c0d8f0ff4d4b7`, sheng
`b7ffb576b006c8e4345bc37a38748d58d315f430` and AdrenoMetal
`d84093bb04222e232e45fdab6578c0f5468535b2`.

Its [frame diagnostics](https://github.com/UniXNU/UniXNU/blob/722379fdcfe0a4078ca59e38eb3c0d8f0ff4d4b7/docs/porting/gpu-diagnostics.md)
separate allocation/lock time, encoding, completion, concurrent faults and
upstream display gaps. Hardware GPU durations require clock calibration to
align with CPU events. Log writer duration is measured too. Adopt that scope:
bounded correlated records and preserved fault evidence, rather than more
unrelated offscreen feature suites.

The [sheng GPU record](https://github.com/UniXNU/UniXNU-sheng/blob/b7ffb576b006c8e4345bc37a38748d58d315f430/porting.toml#L289)
records both host-only changes awaiting hardware qualification and physical
results. Its tested `metal-flow` variants have overlapping fps results and
one enabled run failed to reach the desktop without a known cause. This
supports controlled A/B acceptance, not a promise that a new queue strategy
will make our phone smooth.

Its [storage guide](https://github.com/UniXNU/UniXNU/blob/722379fdcfe0a4078ca59e38eb3c0d8f0ff4d4b7/docs/porting/ufs.md#findings-to-reuse)
also distinguishes capacity from DMA correctness, queueing and wait cost.
Gauguin already has a conditional 50-us-spin/200-us-sleep wait, with ordinary
I/O serialized and DMA ownership retained. The cited IODelay cost on sheng is
not a measured cost of gauguin's `delay(1)`. Keep storage/log waits in a UI
stall trace; do not attribute current lag to UFS without evidence.

AdrenoMetal additionally documents purgeable memory and retained-resource
rules, relevant to later multiple-app memory pressure. Its implementation and
A740/macOS-specific changes are not directly qualified on A619/iOS16. See
[runtime memory contracts](https://github.com/UniXNU/AdrenoMetal/blob/d84093bb04222e232e45fdab6578c0f5468535b2/README.md).

## Updated execution priority

1. Preserve pending 0240 and the qualified phone. Genuine consent is still
   required for its exact delta; install it and run its paired 0239 trial
   first. This source review does not provide consent or stale that proposal.
2. From a fresh post-0240 root capture, assemble/review the scoped desktop
   installation, regenerate launch/cache changes, and obtain the required
   individual write approval. Qualify the existing 0250 desktop as one system.
3. Establish correct whole-frame output and a real-finger latency trace on
   that desktop. Correct sustained 60 Hz is the first performance acceptance.
4. Prioritize asynchronous transport, CPU recording/copy, animation requests,
   clocks/cache or storage from the trace. Then qualify physical 90/120 Hz and
   longer thermal runs. New offscreen features need a named desktop blocker.
5. The full RAM/storage/peripheral/daily-phone goal remains active. The 0252
   handoff producer is useful completed memory work; additional RAM-consumer
   work does not substitute for the pending desktop acceptance and must not
   be presented as progress toward smooth animation.

HakiOS itself still lists unfinished charging, no Bluetooth and no cellular
registration. Its [device status](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/devices/redwood.md)
does not establish a daily-use phone; assess those milestones separately.

## Evidence and limits

Twelve freshly fetched files (750,889 bytes) match their Git blob identities.
Private source capture: `research/tmp/hakios-recheck-20261111-v7`.
`source-proof.json` SHA256:
`b2ed5e5d72e1716fa754cadd044522fb50525829d159804db391b93719d6a267`.
`local-audit.json` SHA256:
`7b019e9ba1b887cb83b7d59a76414512d3469c58a54949b248e9f3d29971b5a8`;
it pins six inspected local sources and confirms the pending 0240 delta, 0250
image and unrelated MAIN mkadt diff are unchanged.
The current 0250 GPU/surface/framebuffer/UFS sources and frontend patches were
read directly; the reports distinguish native candidates from installed state.
This turn performs source review only: no driver edit, compilation, hardware
test, device command, root write, reboot, CI run or push. DSH was not invoked
for a source-only review. Existing qualified receipts remain unchanged.
