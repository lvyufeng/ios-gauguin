# Held-frame rejection diagnostic

The 0288 physical trial completed GPU jobs (24/24), created the Adreno619 Metal
device and linked the system CoreAnimation pipelines, yet accepted zero held
display frames and rejected 200 before the planned stop. The user saw logs and
could not reach the desktop. Which admission guard failed is not yet known.

Patch 0216 preserves those guards and all existing hold/drop paths. It adds
first-eight rejection records and periodic reason totals under the existing
framebuffer lock. Reason 1 means null owner, 2 unsupported layer-mask bits,
3–6 failure to hold a surface in layer 0–3, and 7 unregistered client. Records
include owner presence/membership, client count, mask and four surface IDs;
they contain no object addresses. Failed input still releases partial holds
and preserves the prior pending frame.

The host harness extracts and executes the production methods. Tests cover
each reason, partial-hold unwind, unchanged input/pending references, invalid
IDs, saturated users and concurrent retry output bounds, alongside existing
close/replacement/active-frame tests. ARM64 compilation checks use the pinned
native kernel recipe. These checks do not certify a desktop or physical FPS.

The intended next device trial changes only the temporary kernel image and a
13-byte recovery marker. The installed router, bootstrap, frontend, Mesa and
userdata root remain as captured after 0288. Individual marker/boot approval
is required after the complete image and read-only preflight are reviewed.

## 0291 build and read-only device results

The critical code is committed and pushed as
`b34deaeed8b84253c42f9435cd64dd5427be7c9a` on
`codex/gauguin-present-reject-20261111`. DSH executed the tests and native
build. The full local build, with fresh objects and retained dependency
clones, completed with provenance and symbol qualification in 188.055 s.
No GitHub Actions run was used for this build.

The 208-patch source contains 5,332 files, SHA-256
`69c8e8bc3da239da5ed59c08cc7db52fcb8a09ac23a4778234baff7494bae7ae`.
Compared with the qualified 0250 source, only SweetFramebuffer.cpp changes.
The kernel SHA-256 is
`0aad55999f5ae95178f06e0da313217a876f93c987a002105be05d75279e5e40`.
The 20,021,248-byte temporary boot image SHA-256 is
`746f3741d2b88efec3707426da1e386e7a74fe2363d7790f9c8ddf105b9171d7`.
The 607-byte boot command, 6 GiB managed-memory description, firmware data,
shim, DTB and boot-image geometry match the 0250 baseline.

Read-only recovery capture matched all 27 files, including the complete old
logs, and four directory ownership/mode tuples against the post-0288 capture.
The actual installed router and both target binaries pass compatibility
checks. The current misc preimage is backed up. No device write or reboot
has been performed in this preparation.

The concrete plan SHA-256 is
`ab70b41bff4a8149202d69c7058e8e5b27ebd109cb242a83bf97b33efab6317f`.
Its scope is one 13-byte misc recovery marker and one temporary 0291 boot.
Marker write/readback failure may restore only those 13 bytes. There is no
explicit userdata write. Actual artifact gates and 14 negative controls
passed, and real invocation with absent consent stops before output or
recovery IO. Positive authorization controls exist only in memory as clearly
identified host models; no approval receipt has been created.

This is an instrumented kernel ready for a separately authorized test. It
has not yet been booted. It does not fix or qualify desktop rendering,
physical FPS, high refresh rate, or daily use. The strict 0288 GPU trace
remains failed because of its interleaved record; no old log was normalized.

## Capture and interpretation

The 0291 marker and one temporary boot have now been individually approved and
started. The outer launcher checks the sealed inputs plus the actual ring-log
decoder and records a separate process group. A helper timeout is not treated
as completion while any process in that group remains alive.

The strict held-frame parser verifies branch-consistent first-eight details,
monotonic classifications, complete per-snapshot totals and the existing frame
ownership accounting. It binds each reason histogram to its preceding HOLD
snapshot, so a service-stop message interleaved between the two logging calls
does not change that snapshot's phase. LF/CRLF are the only accepted record
boundaries. Interleaved or incomplete diagnostic records are rejected.

Seven parser tests and the unchanged actual 0288 trace replay pass. That older
trace still reports zero accepted frames and 200/211 rejected frames before/
after planned stop, with no known cause; it still fails the strict GPU execution
gate on its interleaved submission record. The capture-first postprocessor has
also passed an actual 27-file capture replay, including zero log growth, and
refuses to collect a still-running trial as a completed result. Current 0291
physical rejection causes remain pending until the phone returns and its new
logs are captured.

## Actual 0291 result

The approved single temporary boot automatically returned to TWRP after 746 s.
The wrapper found no remaining process-group children. The complete capture
preserved 24 static files, four directory tuples and all three old log prefixes.
The exact new kernel identity and strict full GPU trace pass: all 14 submissions
completed, with eight root pixel-test stages and six later compositor jobs.
There are no GPU buffer failure records or backboardd crashes in this trace.
The separate older 0288 trace remains failed on its interleaved submission.

All eight detailed rejection records show a registered owner, two clients and
`0x80000007`; all 15 classified rejections at the last pre-stop snapshot are
mask rejections. No held frame was accepted or consumed. The guard rejects
bit31 before trying surface retention. This identifies an admission bug without
establishing any desktop pixels or frame rate.

The immutable [HakiOS framebuffer implementation](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp)
keeps the raw request and handles four surface layers without rejecting its
high bit. An independent [iOS 16.7 instruction analysis](https://github.com/shenli99/ios-mh2lm/blob/d6448669b3b433a069c0bd9eae010c31360cb13d/docs/FRAMEBUFFER-USERLAND-ABI.md)
identifies bit31 as a background-color update and explains how clearing layers
can produce `0x80000007`. Its cache identity has not been bound to our exact
phone cache, so this is corroborating protocol evidence. It also identifies
separate background/disable, partial-layer-state and SwapWait semantics that
must not be claimed implemented by a mask-admission fix.

The next candidate will allow this one identified metadata bit alongside four
layer bits, keep unknown bits 4–30 rejected, preserve the raw record and all
surface ownership checks, and test the actual observed input against the old
and new methods. It needs its own build, image review and subsequent trial
consent; the 0291 consent has been consumed.
