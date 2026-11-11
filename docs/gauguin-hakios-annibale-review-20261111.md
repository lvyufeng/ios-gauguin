# HakiOS K90 findings for Gauguin desktop acceptance

The HakiOS main branch remains at `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`.
The K90 fork publishes separate records for visually similar failures and a
release validated on one test phone. It runs iOS 26.6.2 on Adreno 830. Gauguin
runs iOS 16 build 20H392 on Adreno 619. The K90 evidence informs what to measure
on Gauguin. Its code, firmware and measured frame rates are specific to K90.
[K90 v0.1.2 release](https://github.com/iola1999/hackios-redmi-k90-annibale/releases/tag/v0.1.2),
[device status at d76973c](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/plan/2026-10-23-tracking.md).

## Verify the application and widget state before sampling their pixels

K90 had a run where a missing launch cache left a sparse icon model, an empty
Dock and widgets waiting for their extensions. In a separate failure, an empty
RAM-backed `/private/var` on each boot forced LaunchServices to rebuild its
database. The first SpringBoard appeared before the data was ready. The same
missing icons occurred with GPU disabled, and repopulated after a SpringBoard
restart. A warmed data seed restored the first desktop. The reported causal
evidence is strongest for extension registration and the cold-data failure.
[Launch cache investigation](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/analysis/2026-10-28-ios26-icon-model-and-launchd-cache.md),
[cold-data investigation](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/analysis/2026-10-31-every-boot-is-first-boot.md).

DSH read the existing verified pre-0240 HFSX backup offline. It has 531 cached
daemon records and 421 `AppExtensions` records. The cache and system directory
contain jobs for `lsd`, `com.apple.iconservices.iconservicesagent`, `chronod`,
`pluginkit.pkd` and `containermanagerd`. `/var` points to `private/var`; the
catalog has 8,715 entries below it, including `IconState.plist` and 62 files
with `iconscache` in the path. The `SpringBoard.axbundle` and `UIKit.axbundle`
directories are present, so an accessibility-tree check is an option if the
runtime supports it. These are catalog and plist observations. Runtime mount
identity, loaded cache, registration, service health and artwork are open.
[HakiOS accessibility bundle report](https://github.com/oosexgang/hakios-xnu-kernel/pull/39).

At first unlock and again on the next equivalent boot, record the launch
cache status, application and icon model counts, widget provider responses,
and whether the requested icon/widget produces a valid source image. If the
model is empty, inspect LaunchServices, PluginKit, Chrono and data availability.
If it is populated and the image is empty, inspect `iconservicesagent` or the
widget provider, including exit/Jetsam and software or GPU rendering. The
0250 Metal profile admits only backboardd after root qualification. Its test
must establish the other processes' fallback behavior independently. A
backboardd submission receipt alone leaves their output unknown.
[Gauguin desktop admission](gauguin-metal-desktop-profile-20261111.md).

## Identify where a valid image first becomes invalid

K90's single-attachment framebuffer-fetch probe passed 198,916 pixel checks,
while large widgets still went black. The authors then recorded a full unlock
transition and found a particular draw that replaced valid samples in
attachment 0 with black. It used a different fragment from their initial AIR
capture. A fix for that exact draw is still open in the published record.
A separate K90 bug caused stale blocks during partial redraw when an internal
copy had not finished before the compositor rendered into the same texture.
Their tested repair waited for that copy and restored partial redraw. The
published status still reports large black widgets and other incomplete
features.
[Framebuffer-fetch probe](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/progress/2026-11-08-fbfetch-validation.md),
[first bad widget draw](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/progress/2026-11-08-widget-dense-transition.md),
[partial redraw and copy](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/progress/2026-11-09-thermal-and-pipeline-optimization.md).

For the Gauguin unlock and App Library transitions, capture a small region at
three boundaries in the same boot: source artwork, completed composition and
physical scanout. If the completed composition is the first bad image, trace
the actual draw with its source image, destination attachments, load/store and
blend state, shader identity and producer fence. Track prior-frame copies by
surface and fence when present. If only the panel is wrong, check the buffer
identity and scanout latch. The older GLES red clock and missing layers and the
K90 Metal bugs still have independent causes to establish.

## Include cold start, warm start and lock-screen idle

K90's release separately reports cross-boot shader-cache reuse, partial redraw
and load-based GPU clocks. Its pre-fix idle trace shows a small animated lock
screen region triggering full-frame work at 120 Hz. For Gauguin, include the
second boot, cold/warm app transitions, and locked/idle activity when assessing
the desktop. Record cache hits/rebuilds, service restarts, frame intervals,
observed frequency and temperature. Keep the 60 Hz full-effects and real-finger
baseline before assessing 90/120 Hz. K90's release records accelerated desktop
and persistent storage alongside unfinished audio, camera and cellular.
[K90 release results](https://github.com/iola1999/hackios-redmi-k90-annibale/releases/tag/v0.1.2),
[idle trace](https://github.com/iola1999/hackios-redmi-k90-annibale/blob/d76973c55b5c883fd6a038a8218c3d670bd9ec40/docs/progress/2026-11-09-thermal-and-pipeline-optimization.md).

## Handoff

Apply the application/provider checks and targeted frame capture to the paired
0239/0240 and later 0250 desktop trials as appropriate. The existing 0255
trace covers touch, kernel submission and copy; the application and render
observations above supply separate evidence. The 0261 scan trial has its own
pending authorization. This review consists of published source and results,
two local read-only catalog jobs, and independent receipt verification.
Gauguin's runtime cause, frame correctness and performance remain unverified.
