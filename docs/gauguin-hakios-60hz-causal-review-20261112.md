# HakiOS success case against Gauguin's laggy 0300 boot

I rechecked the public HakiOS repositories on 2026-11-12. [Redwood main](https://github.com/oosexgang/hakios-xnu-kernel/tree/63fc2b4633bac3af8e57dadab9f5a8d4cb940438)
is still at 63fc2b4. The [Redmi K90 main](https://github.com/iola1999/hackios-redmi-k90-annibale/tree/3c25d9601e62b04a127889673e45f763635739cf)
has newer documentation commits, while its latest published device release is
[v0.1.2 from 10 November](https://github.com/iola1999/hackios-redmi-k90-annibale/releases/tag/v0.1.2).
The reference measurements are author-reported, with the authors' specified
devices and workloads. Gauguin is an Adreno 619/iOS 16.7 port; Redwood is an
Adreno 642L/iOS 16.5 port and K90 uses Adreno 830/iOS 26.6.2.

## Where HakiOS actually gained frame rate

| Stage | Published source/result | Gauguin 0300 observation and decision |
| --- | --- | --- |
| Touch polling | Redwood's Goodix/FocalTech loop reads every poll while a finger is down. It reduced missed lift reports from 88–169 ms to about 5–6 ms. [Loop](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/input/hakios.goodix.c#L1516), [measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md#under-real-fingers-5-november) | Novatek already read and accepted 63,920 packets; at least 512 changed kernel HID frames formed. The reference's missed-interrupt fix does not match this measured path. Next count queue enqueues/drops and userland processing. |
| CA frame clock and animation request | Redwood's framebuffer publishes TimingElements, ColorElements and IOMFBDisplayRefresh. Its source explicitly says that absent IOMFBDisplayRefresh, CA chooses a fixed 60 Hz built-in mode. A separate SpringBoard hook raised animations that requested no rate and ran at 24 fps despite only 0.3 ms of GPU work. [Frame clock](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L470), [animation hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1941) | Our framebuffer lacks those properties and had zero notification registrations. The reference also says CA need not request driver refresh notifications, so that zero is not a proven cause. Adding an explicit 60 Hz metadata dictionary alone is unlikely to explain or repair 33 retired frames over the service window. Measure CA's effective clock and requested animation ranges before changing policy. |
| GPU submission and lifetime | Redwood returns an **issued** fence, tracks it on buffers/surfaces and waits in a bounded presenter. Deferred recording and async GPU completion are separate. [Submit](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.adreno.c#L3461), [presenter](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L1250), [runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L66) | Gauguin currently waits for completion inside each native submit and holds a global GPU lock across display reads. It completed 51/51 submissions, but this serialization limits overlap. Removing the wait or lock without issued/completed state and resource retention would be wrong. First locate the long frame-production gaps. |
| Copy and scan | Redwood uses a bounded surface queue, multiple CPU copy workers and a scan-aware presenter. Its full-resolution real-finger drag was 75–80 fps, while whole swipe/settle windows were about 100–104 fps under a frozen wallpaper and deferred recording. [Measurements and setup](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md) | Gauguin's latest sampled copy prefix had 29 full copies; individual copies in the previous candidate were 2–4 ms, but only 33 held frames retired in 0300. Copy optimization cannot manufacture missing frames. Physical scanout and distinct visible FPS remain unmeasured. |
| Later K90 pipeline work | v0.1.2 reports a fix for a Metal copy-before-render race, partial dirty-region redraw, 3.29–6.65 ms driver work and many motion frames under 10 ms. [Release](https://github.com/iola1999/hackios-redmi-k90-annibale/releases/tag/v0.1.2) | These are K90/iOS 26 numbers and corrections. They support checking producer completion and dirty-region ownership, not copying Adreno 830 clock or display registers to Gauguin. |

Redwood's authors explicitly report that neither its Metal, Metal-on-Vulkan
nor OpenGL ES run reached a sustained 120 fps. Its 75–80 fps real-finger drag
is separate from the faster post-release animation. The metrics are from its
software trace, not an independent optical measurement of each panel frame.
The K90 release likewise reports its own conditions. These successful cases
show which stages to verify, not a transferable frame-rate guarantee.

## Consequence for the current patch

An opt-in 60 Hz timing/color/refresh property patch was assembled in a
separate temporary worktree and its changed ARM64 translation unit compiled.
The full build was stopped during SDK staging after this reference review.
No new image was produced or booted; the source is not a qualified fix. The
successful reference explicitly says CA already falls back to 60 Hz without
the refresh property, which weakens that patch as an explanation for Gauguin's
sparse output. The unqualified candidate worktree and 882,772 KiB of generated
source/build scratch were retired; the private cleanup receipt is
research/tmp/gpu-notify-hid-20261112/cleanup-mode301.json (SHA-256
e4fe96807d5db4bcedb91382404216f2f491c6c1653d726be896306240aafb65).
The completed 0300 trial and all backups remain. The missing property remains
a correctness difference to revisit if effective CA mode logging contradicts
the reference.

The next measurement should use one clock domain across Novatek report,
HID event enqueue/drop, SpringBoard event/animation request, CA command-buffer
creation and commit, issued/completed GPU work, SwapEnd, held-frame retirement,
copy and panel observation. Use the same real swipes and Settings interactions
for a paired 60 Hz comparison. Gauguin's current
[0300 result](gauguin-notify-hid-trial-results-20261112.md) has kernel touch
events and a sparse output counter, but no userland touch receipt or CA
requested-rate trace. That is the first missing causal link. A future
functional change should be selected from that trace; a new phone write or
boot needs a fresh exact plan and separate authorization.
