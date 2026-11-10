# HakiOS recheck after the 0238 task-surface trial

## Follow-up after actual 0239, before the 0240 installation

Re-fetched GitHub main and nine files on 2026-11-10 in response to the user's
renewed request. Main is still `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`;
all nine fresh files, 696,126 bytes, match their pinned Git blobs. The receipt is
`research/tmp/hakios-recheck-20261110-v4/source-proof.json`. This pass also reads
the materialized source of the actual 0239 kernel, rather than treating the
original framebuffer instrumentation as its final implementation.

The earlier admission, decoded-image upload and presentation findings remain
open. They were identified, but they have not yet been integrated into a real
Metal desktop. Actual 0239 qualifies root-client immutable inputs; it does not
open the compositor's corresponding import gate. Corrected 0240 is a reviewed
shared-output candidate awaiting its own write consent, not a phone result.

Four additional integration details deserve explicit acceptance criteria:

1. **Animation request rate is independent of GPU speed.** HakiOS records Metal
   animations arriving every 41.7 ms (24 fps) while the GPU is busy only 0.3 ms.
   Its `inject_sb.c` copies animations and sets `preferredFrameRateRange` when
   `anim_max=1`. That integration is not present in our tracked UI code. See
   [the actual hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1941).
   Log requested and delivered animation rates on the real Metal desktop;
   choose ranges supported by gauguin's measured display mode. Do not force
   HakiOS's 80..120 range while qualifying a 60 Hz path, or diagnose every
   slow animation as a GPU execution problem. This is not evidence that our
   earlier EAGL desktop has that specific 24 fps fault.
2. **Holding display buffers too long can stall the next frame.** HakiOS keeps
   each submitted surface alive through consumption, then drops its use as
   soon as its pixels reach panel memory. Keeping it until the following frame
   left CoreAnimation without a reusable surface; the source records a median
   swap interval of 9.6 ms instead of 8.3 ms. See
   [presenter retirement](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L1394).
   Our future queue must verify timely retirement as well as retention:
   normal completion, replacement, timeout and client exit must each release
   exactly the right surface-table use and object reference. A framebuffer
   timer looking up a raw ID later does not provide that handoff.
3. **A root shader cache is not a ready compositor cache.** Our installed
   profile restricts its cache to a root-owned 0700 directory and clears the
   seed environment. Its successful compilation results do not establish that
   backboardd can use a persistent cache. Give the compositor its own usable
   cache and compare a cold boot, warm run and warm reboot. The paired deferred
   command recording, wallpaper and rendering-scale controls must be measured
   separately after admission. HakiOS's
   [runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L18)
   supplies these as a group; adding its boot arguments does not implement
   the missing hooks in our kernel or user space.
4. **The current copy timer includes its work in the next interval.** Actual
   0239's `SweetFramebuffer.cpp` fixes `SWEET_FB_VSYNC_US` at 16,667 and maps
   every `sweetfb_hz >= 60` to one copy per tick. Its callback calls `present()`
   before the final relative `setTimeoutUS(16667)`. From this source order,
   copy and GPU-lock wait time can lengthen the next interval; this is a source
   inference, not a measured phone frame-time distribution. Merely setting
   `sweetfb_hz=120` neither selects a 120 Hz timer nor establishes panel timing.
   The revised presenter needs a measured cadence that accounts for work,
   completion and late frames; physical scan timing remains a separate check.

The immediate desktop milestone therefore needs all of the following together:

| Connection | Present gauguin boundary | Required desktop evidence |
| --- | --- | --- |
| Discovery and client admission | No Metal plugin publication; the frontend admits only the root probe and reports no GPU family | backboardd discovers the intended device, passes its actual framework capability checks and submits native GPU jobs; coordinate the existing exclusive GPU owner |
| Images from applications and image services | Root task inputs pass; compositor task import remains denied, and no-copy buffer creation is explicitly refused | Exercise real decoded-image upload and caller-backed surfaces, their bounds, later updates and deallocator/lifetime behavior; verify icons and widgets rather than infer them from five synthetic CA scenes |
| Shared output and presentation | 0240 has not run; latest framebuffer still uses raw pending IDs, serialized CPU access and a 30 Hz copy cap | Correct shared target pixels, GPU completion before consumption, bounded queue, prompt retirement, repeatable lock/unlock and app transitions |
| Scheduling and latency | No equivalent complete desktop trace or animation-rate adjustment | Touch/HID, SpringBoard commit, CPU recording, submit, GPU fence, copy and panel timing on one trace; frame intervals and input latency, not only average submit duration |

HakiOS's no-copy buffer workaround copies the initial decoded image and
retains its deallocator; its own comment explicitly says later writes are not
shared. It is useful evidence for an immediate-upload caller, not a general
aliasing implementation. Our real-desktop candidate must distinguish those
contracts and keep unsupported work visible. Disabling strict errors or
silently skipping missing draws would not qualify populated icons or widgets.

The performance and daily-use limits also matter. The reference runs use an
A642L at 550 MHz and iOS 16.5 user space; gauguin has an A619 and build 20H392.
HakiOS reports about 100–104 fps full-resolution page swipes and 89–91 fps
Settings scrolling. Its 118–120 fps Settings result uses reduced 750x1624
rendering, a frozen wallpaper and synthetic input; real-finger dragging is
reported at 75–80 fps. These are the
[author's conditions and measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md),
not an A619 forecast. The reference
[device status](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/devices/redwood.md)
still lists no charging under its kernel, no Bluetooth, and cellular without
registration. Its successful UI is not a completed daily-use phone.

Execution remains: finish the bounded 0240 shared-output check, then prioritize
one integrated backboardd Metal candidate with image upload and display
handoff. Qualify populated UI and sustained usable 60 Hz, measure the controlled
performance options, and only then qualify the physical 90/120 Hz mode. Do not
insert more standalone GPU feature suites unless a named desktop failure
requires one. This review changes no driver, installs nothing, and makes no
device request; it does not consume or replace the pending 0240 write consent.

The following sections preserve the earlier review made after 0238.

Subsequent actual 0239 now passes the input-lifetime contract; see its
[physical acceptance report](gauguin-readonly-task-input-20261110.md). The
review below preserves the evidence and priorities established after 0238.

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
