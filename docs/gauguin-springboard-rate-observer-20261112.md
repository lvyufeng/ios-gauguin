# SpringBoard animation-rate observer, offline candidate

The 0301 kernel/HID trace remains pinned and its one-shot phone approval is
pending. This separate candidate does not alter the 0301 plan or image. No
partition write or new boot occurred here.

## What the HakiOS success case actually observes

HakiOS's [SpringBoard hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1783-L1852)
reads each animation's `preferredFrameRateRange` at `CALayer
addAnimation:forKey:` and records display-link requests. Its source reports
animations with no rate request advancing at 24 fps despite about 0.3 ms of
GPU work. Its `anim_max=1` copies animations and requests 80–120 fps for a
120 Hz Redmi. The same file records SpringBoard's main run-loop wake and
around-CA-commit times with observer order 2,000,000. HakiOS delivers that
dylib through its [userland build/injection path](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/build.sh#L14).
Those rates and injection mechanics are source-specific; Gauguin iOS 16.7
still needs its own measurement.

HakiOS's [phone measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/main/docs/reference/metal-measurements.md#under-real-fingers-5-november)
also show why a driver refresh number alone does not explain touch lag. On
redwood, a missed touch-controller interrupt left a finger lift waiting
88–169 ms; fixing the [Goodix/FocalTech report polling path](https://github.com/oosexgang/hakios-xnu-kernel/blob/main/drivers/input/hakios.goodix.c)
reduced it to 5–6 ms. Its own 120 Hz panel still did not deliver 120 distinct
frames per second across gestures: [the changelog](https://github.com/oosexgang/hakios-xnu-kernel/blob/main/CHANGELOG.md#2026-11-05-234)
reports 109.6 at the default screen, with remaining long SpringBoard turns
and GPU work. These are redwood results, not Gauguin measurements. Our next
0301 trace must distinguish touch report/HID queue delay from C4 producer,
submission and presentation delay. Only if that trace leaves SpringBoard's
rate requests or turns as a plausible cause should the separate observer
trial be run. The HakiOS [CA heartbeat issue](https://github.com/oosexgang/hakios-xnu-kernel/issues/40)
describes a reported 120 Hz app-rate fix on renoir; it does not establish a
60 Hz lag fix or a Gauguin result.

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
incomplete rollback is reported explicitly. The restore core now reparses
the current HFSX catalog and rehashes all three restored files before it
returns success; a failed final filesystem check also triggers reverse
rollback to the postboot candidate preimages.

`tests/test_sb_rate_restore_model.py` applied the candidate six ranges only
to an in-memory overlay of the real root's read-only recovery bytes. It
injected an unrelated catalog-record change, prepared the dynamic restoration,
faulted each of six writes in turn, verified reverse rollback, detected a
simulated rollback failure, rejected a final HFSX check and rolled that back,
and restored all three files in the strict HFSX parser. Review SHA-256 is
`e40663520a4abf0c91025b1709a7ff4eb01b95a9d1a933c68b211b2b009612c6`.
No actual phone block write or boot occurred.

There is still no bounded trial executor, misc recovery marker, selected boot
image, postboot log collection or separate exact-scope user authorization.
These are required before any phone installation. Actual SpringBoard loading,
hook ABI and visible cadence remain unverified.

## 2026-11-12 source correction: current dyld policy blocks the observer

HakiOS's [AMFI stand-in](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/bsd/kern/kern_minimac.c#L59)
answers dyld policy request 0x5a with an allow mask of 0xff; its
[injection source](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject.c#L1)
says launchd's `DYLD_INSERT_LIBRARIES` works because of that answer.
Gauguin's actual 0301 `sweet_amfi.c` instead registers its opt-in `AMFI`
policy for `sweet_dyld_probe=1` and returns mask 2 **only for an exact
backboardd executable**. The SpringBoard process gets `ENOPOLICY`. Therefore
the existing slot plus launch plist delta is **not a working observer trial
with the pinned 0301 image**. Preparing its phone executor before fixing this
policy would have been misleading.

Patch `xnu/patches/0226-gauguin-springboard-dyld-rate-observer.patch` SHA-256
`4dbca60cf2194256abb32da2d12e0adce20d5f7049ad8cef38d9495acc0af6e9`
adds a *separate* default-off `sweet_sb_rate_probe=1` gate. It grants only
the same dyld PATH mask 2 to a UID 501 SpringBoard process whose executable
vnode matches `/System/Library/CoreServices/SpringBoard.app/SpringBoard` on
the root mount, is root-owned and not group/world writable, and is not
writable by that mobile caller. The prior backboardd gate, its boot token,
log prefix and result are retained. This is narrower than HakiOS's global
0xff permission. The new gate does not attest the launchd job's environment
value; the separate root-delta preimages and rollback must still do that.

The patch replays exactly onto the pinned 0301 `sweet_amfi.c`, changing only
that file. A copied production policy plus unchanged XNU MAC dispatcher
passed **47 ASAN/UBSAN host cases**, including the old backboardd cases and
SpringBoard disabled, correct UID/vnode, wrong UID/vnode/mount/permissions,
and policy failures. Actual ARM64 kernel single-file compilation passed
against the 0301 build's generated headers. Host receipt SHA-256
`361d76255426eaa85335373fbfe7870647913b3b9d2ba1d80ef28f19b3a2ad30`;
native receipt SHA-256
`beaa3d5bf7b2e04f63952c21467e0cfc52023ac85fe6a41d9f00f1a9c862d4f1`.
No full kernel build or image exists for this patch, and no phone execution
or SpringBoard dyld result has been observed. A future boot command can fit
the new token by removing the redundant `metal_fps=timeline` summary token
from 0301's 601-byte command: the proposed command is 604 bytes and retains
`touch_lat=1`, `sweettrace=2` and `sweetfb_hz=60`. This is a length check,
not a reviewed image or an authorization to boot it. Run the pinned 0301
causal trace first and use its result to decide whether to build this
separate observer image.

## 2026-11-12 follow-up: full offline kernel and image

An independent APFS clone of the pinned 0301 source was audited bytewise:
only `bsd/kern/sweet_amfi.c` differs, exactly as patch 0226 replays. The
source-state record still checks after the build. The admitted build batch
was **3,000,000,000 bytes** at 496,309,448,704 bytes accounted; a larger
3,800,000,000-byte simultaneous build-plus-trial batch was refused, so the
trial remains separate. `SKIP_TESTS=1` full local `make install` exited zero
after the focused 47-case host and native TU tests. Build manifest SHA-256 is
`e56269f3aa6e1f99b33a4acfa83e19365e471a3531e9a60864b4ab657b241183`.
The 17,348,416-byte kernel SHA-256 is
`e5a840b948858c91ddff76d8f941757e04d9cd6752b5041ac5b410c7bbe7b935`;
banner identity is `xnu-d1a9a6247e7f4664b6dff6ac512413b1`.

`tools/package-sb-rate-observer.py` produced an offline 20,037,632-byte
image SHA-256
`a11b7b7424af91803295d3cb1338e6084b69c9af7ff97ab28d7c500f2b9ea804`.
Its 604-byte boot command retains `sweettrace=2`, `touch_lat=1` and
`sweetfb_hz=60`, removes the redundant `metal_fps=timeline` summary token,
and adds `sweet_sb_rate_probe=1`. It is a **new** image, separate from the
pending 0301 image and authorization. Package receipt SHA-256 is
`3e463d62ea57b452d3db2fd180519dcab191f6589151183eb720e8daf5e2ea14`.

The first independent review rejected a too-strong assumption that firmware
physical addresses would remain identical. The added kernel policy caused a
16 KiB kernel VM layout shift and a 16,640-byte payload shift. The five
firmware assets therefore also move **16 KiB** in high DRAM. The revised
review checks the exact new ADT physical addresses, segment ordering,
non-overlap, bounds, unchanged firmware contents and zero padding; the ADT
otherwise differs only in those addresses and its PAS payload-tail offsets.
Each kernel asset consumer reads its address from the ADT and validates the
range/hash, but this structural check does **not** prove runtime acceptance.
The wrapper, shim and DTB remain byte-identical. Independent review SHA-256
is `700c47db0a1ed330cde75dff75a8107dd0c58e65c0e9fe164a089cbf94abeb9b`.

The duplicated 457,569,543-byte build driver log was retired with a private
cleanup manifest. The retained 457,562,293-byte build log was compressed to
38,743,244 bytes, verified with `zstd -t`, with its preimage and compressed
hashes in another cleanup manifest. Source, staged build inputs, kernel,
manifest and image remain. After cleanup, a fresh 1 GiB trial storage
reserve was admitted at 498,798,858,240 accounted bytes. **No phone boot,
partition write, SpringBoard load or visible frame-rate result occurred.**
The 0301 causal trial remains the next phone experiment; its pending consent
cannot be used for this observer image.

The first build estimate missed that duplicated driver log outside the build
root, so its peak batch exceeded the admitted 3 GB estimate, while remaining
below the 500 GB cap. The duplicate was removed immediately after verifying
the build; future batch estimates must include both log destinations.

## 2026-11-12 follow-up: SpringBoard log interpretation

`tools/analyze-sb-rate-log.py` parses the observer's exact `SWEET SB RATE`
animation/display-link requests, `SWEET SB TURN` main-loop timestamps,
activation marker and dropped-row count. An optional complete UI254 kernel log
selects the same four-second `mach_absolute_time` window **within one boot**.
The output keeps raw requested ranges separate from wake-to-observer and
observer-bracket intervals. It flags invalid/missing observer ordering and
does not treat requested rate, run-loop spacing, or a 60 Hz software clock as
panel frames. The observer's CA ordering on 20H392 remains unverified.

The synthetic parser check passes window filtering, zero-maximum animation
requests, 60 fps display-link requests, 20 ms wake gaps, a missing observer
timestamp, dropped rows and malformed rows. Parsing the existing 120,324-byte
SpringBoard log produced `observer_seen=false` and zero rate/turn records:
that older boot had no SpringBoard hook, so zero records are **missing
evidence**, not evidence that no animations ran. A future trial must collect
only the new log tail and confirm the activation marker before interpreting
the request counts. No new phone write or boot occurred for this analyzer.

## 2026-11-12 follow-up: installation core modeled

`tools/sb-rate-slot-install-io.py` now has the separate exact-range install
core. It has no device entry point or approval creator. Before a write it
requires one-shot approval bound to the six-range plan, an unmounted Gauguin
recovery partition, the exact current root header, old HFSX paths/CNIDs/
extents/file hashes, original catalog field positions, and byte-for-byte
preimages for all three data extents and three catalog leaves. The catalog
candidate must change only each target file's eight-byte logical length.
Fixture approval cannot reach an IO object that is not explicitly a model.
The core checks every write's readback, reparses the installed HFSX files,
and reverses touched ranges on failure; incomplete rollback is reported.

`tests/test_sb_rate_install_model.py` used a writable **in-memory overlay**
over read-only current phone blocks. It verified three installed HFSX files,
failures at each of writes 1 through 6 with full reverse rollback, a failed
rollback report, and fixture refusal against non-model IO. Private receipt
SHA-256 is
`d634100c53604b0b04bcce85b3bf4f2bd17a68b0e68f86d500d98183e4adb2d6`.
There was no actual phone write or boot. A full one-shot executor, boot/misc
handling, postboot log capture and separate exact-scope user approval still
remain before this observer can be tried on the device. The pinned 0301
causal diagnostic is still first.

## 2026-11-12 follow-up: separately gated one-shot trial, offline only

`tools/prepare-sb-rate-trial.py` pins the independently reviewed 0304 image,
six-range HFSX delta, current root backup, misc preimage, observer helper,
restore code and log analyzers. It admits a fresh 1 GiB storage reserve before
writing private `trial-plan.json` and `ready.json`. This preparation reads
only local files; it is **not** a phone trial or a user approval.

`tools/run-sb-rate-trial.py` first requires an individual user reply bound to
the exact trial plan, install plan and image hashes. Without that reply it
stops before ADB, fastboot or an execution claim. Its bounded sequence is:
read-only recovery capture; install the three observer file replacements
across six readback-verified userdata ranges (1,380,352 bytes); write the
13-byte misc recovery marker; make one temporary image boot; collect the
same-boot kernel, root and SpringBoard logs; dynamically restore the three
original root files; and reparse those files plus the unchanged 29-file
owned-root set. A failed restore may be retried once only after verified
reverse rollback; the maximum modeled userdata write budget is 6,901,760
bytes. At most one `fastboot reboot recovery` fallback is allowed. An
unsuccessful install, unreadable device state, incomplete rollback or changed
preimage stops progression rather than permitting another boot.

The private gate test supplies fake `adb` and `fastboot` commands and confirms
that absent approval executes neither and creates no trial directory. The
result labels preserve distinctions among a SpringBoard log whose tail cannot
be proven, a missing activation marker, an active observer without samples,
and measured SpringBoard *requests and CPU turns*. None means physical panel
FPS or smooth touch has been achieved. The distinct 0301 causal trace remains
the next phone diagnostic, and its consent cannot authorize this trial.
