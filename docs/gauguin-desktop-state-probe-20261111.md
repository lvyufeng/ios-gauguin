# Gauguin desktop registration and layout probe

The physical 0239 observer has one kernel start, a successful launch-cache
delivery, and exec records for SpringBoard, backboardd, containermanagerd,
lsd, chronod, pkd and iconservicesagent. The provider exec records establish
that those executables ran in that boot. The capture has no application
inventory, icon-model counts, artwork or widget-provider result at unlock.

The read-only 20H392 backup has one saved SpringBoard page with five entries
and three Dock entries. Page entries include strings and dictionaries. The
saved layout describes the file in the backup. Its slots can differ from
SpringBoard's live state, and a dictionary can represent different layout
objects. The probe counts these as opaque slots.

## Probe

`userland/desktop_state_probe.m` runs as mobile (real and effective UID 501)
on iOS build 20H392. Each process takes one snapshot and has an eight-second
alarm. The operator supplies first-unlock or settled timing outside the
probe. The output includes absolute Mach ticks and the timebase so the sample
can be aligned to the same boot's 0255 trace.

- `--filesystem` reports `/private/var` filesystem type, mount writability
  and whether it shares the root mount. It reads `IconState.plist` as a
  bounded regular file and reports page, Dock, string and opaque slot counts.
- `--registration` queries `LSApplicationWorkspace` in a separate process.
  It reports the returned app count, unreadable proxies and two stock-app
  presence bits for Settings and Safari. No app or device identifiers are
  printed. The probe checks the three exact Objective-C method encodings
  against the runtime before calling them. An empty list is distinct from
  unavailable data. A query can wake LaunchServices and warm its state, so
  capture the untouched first-unlock scene and the filesystem snapshot first.

The modes add no writes, GPU work, app launches or provider commands to the
probe. Read-only status describes its own operations. CoreServices can do
work in another process to answer registration queries. Results still need
the matching visual, icon-service or widget-provider logs. A present bundle
and saved slot each leave the corresponding image and live widget unknown.

## Build and evidence

Build using the existing iPhone SDK from the repository root. Replace the
output path if that name is already in use.

```sh
xcrun --sdk iphoneos clang -target arm64-apple-ios16.0 -O2 \
  -Wall -Wextra -Werror -fobjc-arc -framework Foundation \
  userland/desktop_state_probe.m -o /tmp/gauguin-desktop-state
codesign --force --sign - /tmp/gauguin-desktop-state
codesign --verify --strict /tmp/gauguin-desktop-state
```

DSH read the exact 20H392 cache. `LSApplicationWorkspace` and
`LSApplicationProxy` are in CoreServices UUID
`8d42103dbd59308d9d2c2082b39738e7`. `defaultWorkspace`, `allApplications`
and `applicationIdentifier` each have encoding `@16@0:8`.

DSH built and strictly verified the 88,080-byte signed iOS ARM64 executable.
All 49 imports resolve against the same 20H392 cache. ASan/UBSan host controls
cover populated/empty/malformed layouts, the slot limit, runtime encoding
acceptance, non-regular file refusal and signal exit status 124. The native
binary SHA256 is `e6467221b67fffd5b267421dfb00da17a5cae7c4e26c68f97410e79d5ac8113f`.
The inputs and receipts were independently rehashed. Private artifacts are
under `research/tmp/dsh-desktop-state-0269`.

Physical qualification needs an approved desktop test package and a measured
mobile launch. The existing paired 0239/0240 trial precedes the 0250 desktop
package. This candidate is available for that later package. Compare a
filesystem-only first-unlock sample with a registration sample taken after
the visual baseline, then repeat after a normal reboot. If registration and
layout look healthy while pixels are missing, capture source artwork and
widget-provider results before tracing the matching compositor draw. Keep
first response, steady animation and physical scanout in the same boot record.
