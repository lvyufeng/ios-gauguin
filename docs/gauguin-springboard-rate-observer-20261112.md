# SpringBoard animation-rate observer, offline candidate

The 0301 kernel/HID trace remains pinned and its one-shot phone approval is
pending. This separate candidate does not alter the 0301 plan or image. No
partition write or new boot occurred here.

## What the HakiOS success case actually observes

HakiOS's [SpringBoard hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1941)
reads each animation's `preferredFrameRateRange` at `CALayer
addAnimation:forKey:` and records display-link requests. Its source reports
animations with no rate request advancing at 24 fps despite about 0.3 ms of
GPU work. Its `anim_max=1` copies animations and requests 80–120 fps for a
120 Hz Redmi. The same file records SpringBoard's main run-loop wake and
around-CA-commit times with observer order 2,000,000. HakiOS delivers that
dylib through its [userland build/injection path](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/build.sh#L14).
Those rates and injection mechanics are source-specific; Gauguin iOS 16.7
still needs its own measurement.

`graphics/gauguin-sb-rate-trace/SBRateTrace.m` implements the read-only
observations for SpringBoard. Its wrappers call the original animation and
display-link methods once with the same arguments and return no changed
policy. They record absolute-clock microseconds into a 256-row bounded ring;
one background thread writes the records to standard error once per second
and reports drops. The same ring records main run-loop wake and the two
before-waiting observers around HakiOS's order. The probe only activates in a
process named SpringBoard with exact boot token `touch_lat=1`. The observer
order may differ on 20H392; the log must be compared with C4 command-buffer
timestamps before calling the interval a CA commit duration. Neither ring
rows nor C4 timestamps measure panel latch or visible FPS.

## Current-root and offline build evidence

The phone remains in TWRP. Read-only HFSX inspection rechecked root header
SHA-256 `6e272d2e11ae716993301df334c35eeb5498b0a77adbccd965f924e28a5e77e4`.
The standalone SpringBoard launch plist is 2,381 bytes, SHA-256
`e0aaf28a82db8c5c1c8df57968afffab4597c08172be8f6654fe552b59b9e0cf`.
It sends standard error to `/private/var/log/springboard.log`; that file
currently exists at 120,324 bytes. The cached launch entry has the same
program/user/log paths and two extra logging environment keys. Both lack an
existing `DYLD_INSERT_LIBRARIES` value. These are observations of current
root bytes, not proof that a new insertion would be accepted by dyld/AMFI.

`tools/build-sb-rate-trace.py` produced an ad-hoc signed ARM64 iOS 16 dylib,
87,232 bytes, SHA-256
`7ba69d08b9f717ef8d04378ba1a077587ae2f39d158c7b2d8ace35208986ff76`.
The native compile/link and strict code-sign verification exited zero. Its
Mach-O file type is `MH_DYLIB`, and its load commands contain Foundation,
QuartzCore, libobjc, libSystem and CoreFoundation at system paths. The iOS
16.7 runtime hook ABI and SpringBoard loading are unverified.

`tools/prepare-sb-rate-launch.py` produced *offline* standalone and cached
launch plist candidates. They add only the same
`DYLD_INSERT_LIBRARIES=/usr/local/lib/gauguin/libGauguinSBRateTrace.dylib`
value to SpringBoard. The new standalone plist is 2,464 bytes, SHA-256
`939288d1042b6b14477747f32b3e12ced205300c4fea700225ce01d718a868fb`,
within its existing 4,096-byte allocation. The new launch cache is 795,931
bytes, SHA-256
`9e8f7d573d8b2f896c4ea6d158259ca267a163359c81e549f7d8df42a52bf1c1`,
within its existing 798,720-byte allocation. An independent read-only
review confirmed all 530 other cached jobs and all other cache sections
are unchanged, removing the added value exactly restores both original
plists, and the binary/signature/input pins still match. Review SHA-256
`962840b03a2ec1ed4f3de3750bdd1d8b698c3350a63999cd99e965524e63e106`.

The new dylib has **no allocated root file** and no root-delta or rollback
plan. This is therefore not a deployable phone trial. It must not be installed
under the 0301 authorization, which covers only the C4 executable, misc
marker, one image boot and restoration. After the 0301 trace, use its queue/
producer timing evidence to decide whether to prepare a separate dylib
placement and SpringBoard launch experiment, with a separate exact write
scope and consent. A 60 fps animation policy should follow measured Gauguin
requests, not the Redmi's 80–120 fps value.
