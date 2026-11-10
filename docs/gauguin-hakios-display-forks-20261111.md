# HakiOS device ports and Gauguin display acceptance

HakiOS main still resolves to `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`.
The new evidence in this review comes from the Mayfly port and the Renoir
report. The main project's [Redwood measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md)
remain the Adreno 642L Metal reference. Its headline page-swipe numbers include
the post-release animation, and the authors report 75–80 fps while dragging.

## Scanout buffer ownership

The Xiaomi 12S Mayfly port reports a 120 Hz command-mode panel, Adreno 730
Mesa GLES rendering and hardware page flips. It identifies the active display
pipe from the original framebuffer address, writes a frame to a second buffer,
requests a source-address update, and observes the control path's flush bit.
One five-second log window shows 589 frames and 589 acknowledged flips. Other
windows are slower, and these driver records contain no independent optical
measurement. [Device findings](https://github.com/cotunjr/hakios-mayfly/blob/de73cdbe5dba410ed198456c6737bf383f900eaa/docs/FINDINGS.md#display),
[phone log](https://github.com/cotunjr/hakios-mayfly/blob/de73cdbe5dba410ed198456c6737bf383f900eaa/logs/flip1.log#L12292),
[framebuffer implementation](https://github.com/cotunjr/hakios-xnu-kernel/blob/9d3c291a9f9f4082d9571f9b2984d0026778a36b/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L224).

Gauguin's held-frame path retains the input surfaces through the software
copy. The materialized 0260 `SweetFramebuffer.cpp` still uses a 16,667 µs
timer and the inherited framebuffer, and emits its vsync notification from
the timer callback. The scan probe measures inherited cadence separately.
A complete frame and a completed CPU copy each leave the display engine's
buffer identity and latch time unknown. This distinction matters for the
reported App Library corruption. Check a stable, completed composition
against physical screen output under the same gesture.

Mayfly's command-mode tear signal, spare framebuffer reservation and SM8450
pipe/control offsets are specific to that port. Gauguin's J17 panel is
video-mode with vertical-front-porch refresh switching. After the existing
clock and scan preflight, identify its active pipe/control path, validate a
second display-visible buffer and cache visibility, then prove that the
intended new address latched. Keep both allocations held across ambiguous
completion. Mayfly's copy path ignores the wait result before it can pick
the other buffer on an initial timeout, so Gauguin needs an explicit
timeout and no-reuse rule before qualifying flips.
[Mayfly timeout caller](https://github.com/cotunjr/hakios-xnu-kernel/blob/9d3c291a9f9f4082d9571f9b2984d0026778a36b/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L1598),
[Gauguin panel](gauguin-physical-display-profile-20261111.md),
[XNU scan probe](gauguin-inherited-scan-timing-20261111.md).

## High refresh must reach the app

On a Renoir fork, the reporter measured a 90 Hz panel while apps received
`UIScreen.maximumFramesPerSecond = 60`. Fingerprinting frames during scroll
showed about 50 distinct frames per second initially and up to 84 after
advertising 90 Hz through the Core Animation heartbeat. That observation
is for iOS build 20F66 and the reporter's hardware. The separate open PR #42
has host tests and no device reproduction. Mayfly also has a per-app path
for `CADisableMinimumFrameDurationOnPhone`; Apple documents the app opt-in
for high refresh. [Renoir measurements](https://github.com/oosexgang/hakios-xnu-kernel/issues/40),
[PR #42](https://github.com/oosexgang/hakios-xnu-kernel/pull/42),
[Mayfly app policy](https://github.com/cotunjr/hakios-xnu-kernel/blob/9d3c291a9f9f4082d9571f9b2984d0026778a36b/userland/src/inject_fps.c#L1),
[Apple app requirements](https://developer.apple.com/documentation/quartzcore/optimizing-iphone-and-ipad-apps-to-support-promotion-displays).

For 20H392, start with read-only observations of the effective CA heartbeat,
the app's reported maximum and actual display-link intervals. Compare
distinct presented frames during a real swipe and Settings scroll against
the hardware scan cadence. Record repeat frames, missed deadlines and
first visible response. A test app with the documented opt-in provides a
control before changing any policy for stock apps. Tie any eventual
advertised maximum to a qualified physical mode. Recovery measured about
60.24 Hz. The 0250 image targets software 60 Hz and has not completed a
desktop trial. [Recovery vblank](gauguin-recovery-vblank-20261111.md),
[0250 profile](gauguin-desktop-boot-profile-20261111.md).

## Next acceptance

Keep the existing paired storage and desktop trials. Qualify backboardd's
real GPU jobs, then check complete lock screen, icons/widgets, Settings
and App Library frames with normal effects. During real gestures, correlate
the existing 0255 kernel trace with SpringBoard/CA commits and physical
presentation. Use the result to choose the first correctness or latency
fix. After a correct 60 Hz baseline, qualify page flips, panel mode, app
cadence and distinct presented frames at 90/120 Hz. Mayfly also reports
working Wi-Fi, Bluetooth audio and speakers, with charging, cellular and
other peripherals still open. [Mayfly status](https://github.com/cotunjr/hakios-mayfly/tree/de73cdbe5dba410ed198456c6737bf383f900eaa#what-works).

This review compared public source and logs against existing local code and
build records. Four Mayfly source/log files match the GitHub blob IDs at
device commit `de73cdbe5dba410ed198456c6737bf383f900eaa` and common fork
commit `9d3c291a9f9f4082d9571f9b2984d0026778a36b`. The flip rate and the
heartbeat behavior have not been reproduced on Gauguin. No new build,
phone command or persistent write was performed.
