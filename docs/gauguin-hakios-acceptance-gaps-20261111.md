# HakiOS follow-up: what the next phone run must establish

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
