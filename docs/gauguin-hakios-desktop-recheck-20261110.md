# HakiOS recheck after the 0238 task-surface trial

Reviewed again against GitHub on 2026-11-10. Current main is still
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438`; this is a deeper integration review
of the same revision, not a newly released fix. Nine fresh connector fetches,
708,049 bytes, match their Git blob identities. Local evidence is retained in
`research/tmp/hakios-recheck-20261110-v3/source-proof.json`. Two initially guessed
source paths returned 404; the correct files are under `xnu/files/iokit/Kernel`.
This review performs no phone write or reboot.

The implementation direction remains gauguin's proven A619 kernel/hardware
baseline with the complete HakiOS iOS 16 Metal integration adapted above it.
The significant planning correction is to make the next milestone a real
backboardd desktop, with shared resources and presentation covered together.
Additional standalone GPU features are justified only by a concrete blocker.

## Gaps confirmed against current code

### The diagnostic frontend cannot yet serve the desktop

HakiOS publishes `MetalPluginName` and `MetalPluginClassName` on its accelerator
when `metal=1`; the window server can discover and instantiate its device.
See [MiniIOMobileFramebuffer.cpp:2014](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L2014)
and [the measured runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L18).

Our installed `GauguinMetalProfile.m` admits only the named root probe,
`GAUGUIN_METAL_MODE=offscreen226` and the checked 20H392 ABI. Kernel 0238 does
not publish the Metal plugin. Its compositor import gate still refuses generic
read-only caller surfaces. These are deliberate diagnostic boundaries that
must be changed for a compositor profile. Passing root tests will not change
them automatically. Earlier interactive EAGL tests do not prove Metal desktop use.

### No-copy buffers are a separate omitted image path

HakiOS's [newBufferWithBytesNoCopy implementation and comment](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L2612)
identify QuartzCore's `copy_image_to_texture` as a caller: it stages a decoded
image for an immediate blit. The authors report refusing this call previously
left those textures without their intended contents. Their direct Metal path
copies the initial bytes and preserves the deallocator, explicitly documenting
that subsequent CPU/GPU writes are not shared.

Our `0001-gauguin-offscreen-diagnostic.patch` replaces that implementation with
an unconditional named refusal. This restriction remains in the installed
frontend. The five IOSurface sampler cases exercise another API and do not
qualify this call. The five synthetic CA scenes do not cover every image upload
path used by SpringBoard and image services either.

Desktop integration must inventory actual calls to both no-copy buffer and
no-copy texture APIs, their layouts and deallocators. Provide the required
backing/lifetime semantics and pixel checks. A bounded decoded-image upload
workaround must be explicit about copying; do not advertise it as general
bidirectional no-copy sharing. Do not infer that this caused an earlier EAGL
icon failure: the Metal frontend was not serving that desktop.

### Presentation is more than rendering to an IOSurface

HakiOS keeps surface references from swap submission, waits for GPU completion
on a presenter thread, bounds the pending queue and presents on a frame beat.
It advertises `HakiosWaitsForGPU`. See
[its queue ownership](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L358).

Our `AppleCLCD::swap()` retains a raw record of surface IDs; its timer later
looks up the surfaces in `present()`. Object retention and surface-table
membership have separate lifetimes. CPU copy currently serializes with GPU
activity and the boot caps copies at `sweetfb_hz=30`. The notification timer is
60 Hz. This cannot establish high-refresh operation or low input latency.
Shared render targets, held surface identity, fence/completion, replacement,
client exit and pending-frame retirement belong in the same integration work.

The reference still copies/scales on the CPU. We should measure and improve
this stage rather than assume a direct hardware scanout path already exists.
Use gauguin's display resources and observed counters; HakiOS's SM7325 register
addresses and panel timings are not portable constants.

### The fast demonstration includes a specific performance profile

The [author's measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md)
report roughly 100–104 fps page swipes and 89–91 fps Settings scrolling at
1125x2436. Their reduced 750x1624 rendering profile reports 118–120 fps Settings
scrolling; it is scaled to the panel. The runs use deferred command recording,
six copy workers, a frozen wallpaper, persistent shader caches and synthetic
gestures. Real-finger dragging is reported at 75–80 fps with remaining main
thread stalls. These are author measurements on an A642L, not A619 predictions
or steady 120 fps for all UI operations.

`metal_defer=1` already exists in our imported frontend, but the current boot
does not enable it. Its value must be measured after the desktop uses Metal.
Dynamic wallpapers, full-resolution rendering and animation completion should
have separate measurements from a frozen-wallpaper/lower-resolution profile.
The [runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L18)
and [reference options](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal.md#boot-arguments)
document these conditions. Current gauguin 0238 logs already prove 8/8 CPUs
initialized; enabling eight cores is not a newly missing fix. Clock/performance
levels still require measurement rather than copying another board's settings.

The reference also corrects Goodix report polling and traces touch, commit,
GPU fences and presentation. Gauguin uses Novatek with its own 8 ms poll path.
We need the same end-to-end timing evidence, not the Goodix-specific register fix.

## What has been resolved since the earlier review

Actual 0235 qualified native FP16 pixels and the current system's original LPH
shader route for five real CA scene pixel arrays. Actual 0237/0238 preserve those
pixel results. Replacing shaders with another system's library is not the next
action. Unexercised desktop variants and capabilities remain to be inventoried.

0238 also advances direct immutable task input: R8, RG8, BGRA8 and RGBA16F GPU
readbacks all match, 16,384 pixels total. The last case draws after the caller's
original VA is unmapped. A subsequent IOSurface CPU-view/full-allocation guard
fails; RGBA32F and final teardown are not reached. The original failed suite
receipt is preserved. Actual XNU's same-task static mapping fast path supports
the next kernel-only `kIOMapUnique` candidate. DSH has now run the extracted
policies with real host unmap/address reuse: the old view reads reused memory,
the candidate preserves all five modeled layouts (151 checks), and existing
transport/Surface regressions pass. This is a typed host VM model; a native
0239 kernel and unchanged-probe phone trial remain unperformed.

## Revised execution milestones

1. Finish the existing 0239 mapping candidate against the unchanged installed
   0237 probe: all five inputs, permissions, full allocation guards and ownership
   release. This closes the observed lifetime fault without another userdata
   installation or a new test-feature series.
2. Complete the [shared CA output test](gauguin-shared-ca-output-plan-20261110.md)
   and implement the bounded display ownership/completion handoff. Prepare a
   separate backboardd frontend/admission/registration profile with the necessary
   decoded-image upload paths. Keep root probe and compositor GPU ownership
   coordinated and the finite recovery window for initial device tests.
3. Run a real desktop workload: lock/unlock, populated icons, widgets, App Library,
   Settings, return home and repeated transitions. Record actual Metal device,
   process/selector/format/pipeline refusals, native jobs, memory, completion and
   presentation. Investigate named failures; do not replace this milestone with
   more offscreen feature counts or silently skipped draws.
4. Trace touch-to-panel latency and frame intervals. Measure deferred recording,
   copy workers, cache warmth, wallpaper and render scale as controlled changes
   on the real desktop. Target sustained usable 60 Hz first, then qualify actual
   90/120 Hz panel mode, timing and long-session behavior.

Every new userdata proposal still needs its fresh backup, exact delta review
and individual write consent. Existing 0237 approval is consumed. Kernel-only
temporary boots against that unchanged installation need no new userdata write.
Full phone RAM/storage/peripherals/power/daily-use acceptance remains open.
