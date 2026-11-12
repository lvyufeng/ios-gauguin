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

## 2026-11-12 follow-up: bounded existing-file slot, still offline

An additional read-only pass found the existing
`/usr/local/lib/gauguin/libGauguinEAGL.dylib` at CNID 607529, one contiguous
138-block data extent (565,248 allocated bytes), logical length 563,200 and
SHA-256 `aafa07f85e6e2ae86d525ebcd1f5661a0fee561009521b28584b15da1e83eab9`.
The current C4 backboardd job has no explicit dylib insertion, its launch
cache has no reference to that library, and the C4 kernel source suppresses
the automatic EAGL insertion. The old EAGL admission dylib can still load it
in other modes; temporarily reusing this slot is suitable only for a
separately approved, bounded trial with complete rollback.

Separate `tools/build-sb-rate-slot.py` and
`tools/prepare-sb-rate-slot-launch.py` keep the original pinned build and
launch tools unchanged. The slot variant is an ad-hoc signed iOS 16 ARM64
dylib, 87,232 bytes, SHA-256
`d7e07dae4886e8adf47a19e130b9e4546f51b621f5b4b24b85201e94311e3638`.
Its install name and both SpringBoard launch variants point to the existing
EAGL path. `tools/capture-sb-rate-slot.py` read and pinned the current full
allocations and catalog leaves for that file, SpringBoard's standalone job,
and launchd's cache. Three catalogs occupy distinct blocks. The standalone
job is 2,457 bytes and cache 795,924 bytes after the transform, each within
its existing allocation. The transform still changes only the SpringBoard
entry among 531 cached jobs.

`tools/prepare-sb-rate-slot.py` produced a six-range data/catalog delta:
**1,380,352 bytes for installation**, with 2,760,704 userdata bytes for a
normal install plus restoration. It changes only the three files' logical
length fields in their catalog leaves; no HFSX extent, allocation bitmap,
volume header or GPT change is planned. Install plan SHA-256 is
`574ecae90d57ce5af826975d7ad68bf54a2c0485e303d131068ac565b2e216e8`.
`tools/review-sb-rate-slot.py` overlaid those exact six candidate ranges on
read-only recovery reads and let the actual HFSX parser resolve all three
candidate files. Review SHA-256 is
`d1b608d31a8c357ba48efae91a1295204ffa719f1c5617a7dbc7b106d20a1856`.
Both old and slot-variant artifact input pins still rehash exactly.

This was still **not** a device-qualified trial when the six-range delta was
prepared. The current phone remained in TWRP and no write or boot occurred.
SpringBoard's dyld/AMFI acceptance and the iOS 16.7 hook ABI remain unknown.
First use the pending 0301 trace to locate the lag; only if a SpringBoard
request/turn gap remains plausible should this slot candidate become a
separate reviewed phone trial. Replacing the EAGL file, even temporarily,
would disable its old use during that trial and requires verified restoration.

## 2026-11-12 follow-up: dynamic restoration model

`tools/build-sb-rate-restore.py` resolves the three files again from a
postboot HFSX catalog **through read-only IO**, verifies their CNIDs, modes,
unchanged data extents, candidate logical sizes and file hashes, then locates
their current catalog fields. It makes three data restoration images and up
to three catalog images. Multiple target fields found in one relocated leaf
are grouped into one write. Each catalog target starts from that leaf's
postboot bytes and changes only the target logical-length fields, preserving
unrelated changes made during the boot.

`tools/sb-rate-slot-restore-io.py` is an exact-range restore core without a
device entry point or approval creator. It requires a fresh one-shot approval
bound to the base plan, an unmounted Gauguin recovery device, full-range
preimages, bounded disjoint ranges, and hash-checked local restoration
images. Fixture approvals are accepted only by an object marked as a model.
It readbacks every write and reverses touched ranges after a failure; an
incomplete rollback is reported explicitly.

`tests/test_sb_rate_restore_model.py` applied the candidate six ranges only
to an in-memory overlay of the real root's read-only recovery bytes. It
injected an unrelated catalog-record change, prepared the dynamic restoration,
faulted each of six writes in turn, verified reverse rollback, detected a
simulated rollback failure, and restored all three files in the strict HFSX
parser. Review SHA-256 is
`2a00b96de1ffb15cee190c6c956a069990f4d39448530f4aff9a51deec37c8a7`.
No actual phone block write or boot occurred.

There is still no bounded trial executor, misc recovery marker, selected boot
image, postboot log collection or separate exact-scope user authorization.
These are required before any phone installation. Actual SpringBoard loading,
hook ABI and visible cadence remain unverified.
