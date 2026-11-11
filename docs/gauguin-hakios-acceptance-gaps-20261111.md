# HakiOS follow-up: what the next phone run must establish

## Current recheck during the 0288 physical trial

Fresh GitHub connector reads on 2026-11-11 CST resolve upstream main to
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438` and the K90 workspace main to
`8968d47adf8331edbf84acc39a61f260ad7cd760`. The latest K90 release remains
`v0.1.2`, published 2026-11-10. Private file/blob identities and source URLs
are recorded in research/tmp/dsh-router-execute-0288/hakios-recheck290-sources.json.

| Requirement | Public success evidence | Gauguin's verified gap |
| --- | --- | --- |
| System Metal desktop | Redwood's window server draws through Metal; K90 reports accelerated home/apps | The completed 0288 trial now shows the root pixel tests, clean owner handoff and backboardd opening the Adreno Metal device. Final counters report 24 submissions/completions, but no displayed desktop is accepted: the user reports logs or inability to enter it. |
| Correct icons, widgets and effects | Redwood reports correct system drawing; K90 still lists large-widget black backgrounds and briefly transparent icons | Earlier GLES trials have missing icons/widgets and color artifacts. A successful offscreen shader or a successful GPU submission does not prove provider images, complete composition or visible scanout. |
| Throughput and touch latency | Redwood separately measures drag, release animation, main-thread stalls and copy/scan timing | The current GPU transport synchronously waits under its GPU lock. Submission/completion/resource lifetimes and display copying must be correlated before safely adding overlap. Real finger-to-first-frame latency remains unmeasured. |
| High refresh | Redwood panel is 120 Hz, with benchmark conditions explicitly documented | Correct sustained 60 Hz composition and real input response are unqualified. The software cadence is not physical panel timing; 90/120 Hz remains a separate measured board/display task. |
| Persistence and long sessions | K90 release reports cross-reboot shader-cache reuse, load-based GPU/DDR votes and eight hours without thermal throttling | Current 0250 is a diagnostic kernel with a 600-second GPU service window and automatic return. It is not an indefinitely running phone baseline. Mobile caches, cold/warm/reboot behavior and thermals need physical acceptance. |
| Daily phone functions | Redwood reports Wi-Fi, camera and audio, but no charging completion, Bluetooth or cellular registration; K90 lists other unfinished peripherals | Full safe RAM, real storage capacity/data integrity, power/charging and all required peripherals remain part of the original unfinished objective. Their successful desktop does not establish a fully usable daily phone. |

The source [Redwood measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md)
report 100–104 fps swipes and 89–91 fps Settings scrolling at 1125x2436 rendered
onto a 1080x2400 panel, with the documented bench settings including frozen
wallpaper. Settings at 118–120 uses 750x1624 and synthetic gestures. Real finger
drag is reported at 75–80 fps, and the author explicitly distinguishes interface
counters from independent physical-panel measurements. These are author-reported
results, not predictions for Gauguin's Adreno 619.

The [K90 release](https://github.com/iola1999/hackios-redmi-k90-annibale/releases/tag/v0.1.2)
reports Adreno 830 frequency/DDR management and persistent caches. Its frame
timings use their own conditions; a proportion of frames below 10 ms is not a
proof that every frame meets a 120 Hz 8.33 ms budget. The current
[K90 status](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/8968d47adf8331edbf84acc39a61f260ad7cd760/README.md)
still lists sound, Bluetooth audio, web video, camera and cellular unfinished.
[Redwood's status](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/devices/redwood.md)
has a different peripheral coverage. Do not combine their best individual
features into an imaginary single fully supported device.

The immediate order remains: diagnose this real desktop startup; establish
correct complete images and repeatable app/lock transitions; measure real
touch/CA/GPU/copy/scanout latency and sustained correct 60 Hz; then improve
overlap/cache/clocks and qualify physical 90/120 Hz. Keep the complete memory,
storage, peripheral and long-session objective intact. No new partition scheme,
GPU clock table or another SoC's display registers follow from this review.

After the automatic return, the current concrete gap is presentation: the held
frame queue accepted and consumed zero frames while rejecting 200 before the
planned GPU stop. Four buffer-allocation refusals occur after that stop and do
not establish the cause of the first missing frame. One later native submission
record is interleaved with an unrelated IOKit message; the strict trace gates
remain failed. Preserve that failure and qualify no frame rate or correct
desktop from the raw successful-operation counters. The next diagnostic should
identify which owner/mask/surface-retention guard rejects the presentation,
while preserving the lifetime checks. This is more immediate than changing
GPU frequency or assuming another shader defect.

## Earlier acceptance notes

Rechecked HakiOS main at `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`,
its [official changelog](https://hackios-web.vercel.app/en/changelog) and
[measurement notes](https://hackios-web.vercel.app/en/docs/reference/metal-measurements).
No newer graphics revision appeared on main. The previous review already
identified synchronous GPU submission and global lock contention. This
follow-up turns the remaining omissions into observable acceptance criteria.

1. **First response and steady animation need separate measurements.**
   HakiOS attributes some 100–300 ms real-finger stalls to SpringBoard's
   main thread before the CA commit, despite a fast Metal path. It also
   separates drag and post-release animation: roughly 75–80 fps during
   drag, with many 8.3 ms frames after release. Our 0255 measures report
   read/HID, kernel submission and copying; it cannot locate work before
   CA commit. Record touch down, movement and lift; time to the first
   visible update; then frame intervals during drag and coast separately.
   If the initial gap remains, correlate SpringBoard run-loop turns and CA
   commits with the existing kernel trace on the same timebase. The
   submit interval alone does not choose between CA, GPU and display work.
2. **Keep incorrect composition separate from tearing.** For red clock,
   missing icons/widgets and App Library corruption, compare a completed
   composed frame with the physical screen on the same gesture. If the
   completed frame is wrong, inspect requested shader variants, texture
   uploads and layout/format/alpha. If only the moving screen is wrong,
   inspect presentation ownership and scanout. A screenshot of live
   memory can itself show bands; use a completed frame and measured
   board-specific vblank/scan timing or external observation. HakiOS's
   measurement also notes red status-bar artifacts from a different
   display class; the color alone cannot identify a shader defect.
3. **Require a full-effects control.** The reference's full render size
   reports 100–104 fps for swipes and 89–91 in Settings on an Adreno 642L,
   with its documented bench configuration. Settings at 118–120 uses
   750x1624, a frozen wallpaper and synthetic gestures. Wallpaper changes
   substantially alter the home transition while doing little for swipes
   in some runs. Use intact effects and actual fingers as the primary
   gauguin control. If a correct desktop remains slow, vary render size
   or wallpaper one at a time as a diagnostic; compare first response
   and frame-time distributions per gesture, including cache state,
   clocks, and the physical refresh mode. Do not adopt a changed virtual
   screen class as a visual fix.

0250 remains the first whole-desktop correctness trial. 0255 is now a
complete offline diagnostic image, not a measured improvement. Use it
after correct composition and real backboardd jobs have been confirmed.
Then establish sustained correct 60 Hz and low input delay, before physical
90/120 Hz with the gauguin panel's measured timing. No write, boot, device
query or new build was performed during this review; exact 0240 consent and
the paired 0239 prerequisite are unchanged.

The [HakiOS device status](https://hackios-web.vercel.app/en/docs/devices/redwood)
still lists no cellular registration, Bluetooth or charging support in its
kernel. Its [FAQ](https://hackios-web.vercel.app/en/faq) does not claim Apple
ID, App Store or general Metal app compatibility. Desktop acceleration and
daily phone qualification remain separate milestones.
