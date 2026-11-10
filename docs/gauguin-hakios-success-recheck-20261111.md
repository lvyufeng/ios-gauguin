# HakiOS success-case recheck: what remains missing

Rechecked GitHub main for the user's renewed request on 2026-11-11 CST. It is
still 63fc2b4633bac3af8e57dadab9f5a8d4cb940438 (2026-11-06); there is no new
upstream graphics revision to import. Twelve freshly fetched files, 958,378
bytes, match their Git blob identities. This review separates new local
findings from previously identified work that still lacks phone acceptance.

## New concrete local startup blocker

The 0249 package's command is 638 UTF-8 bytes. Its validator checks a 1,023-byte
bound, but that is not the loader ABI: tools/mkpayload.py and shim/loader.c
both define a 608-byte command field, including the terminating NUL.
The current packer silently slices to 607 bytes. Applying that exact operation
to the actual package receipt ends the command at `sweetfb_hold=` and discards
`1 sweetfb_phase=1 sweetfb_hz=60`.

This contradicts the previous description of the profile as checked for boot.
The 0249 kernel and userland files remain independently built candidates;
the package is **not ready for boot-image assembly with this profile**.
No such image was built or booted. Preserve the old receipts instead of
editing qualified outputs in place.

Before assembling a successor: reject oversize and embedded-NUL commands,
supply a complete profile within the actual ABI, and check a round trip of
the exact payload field and terminating NUL. Preserve required board/GPU/UFS
and health settings. Do not simply enlarge the field: that moves the segment
table and changes the shim/boot-args contracts. A compact explicit desktop
policy is a possible source change, not a solution implemented by this review.

## Touch latency deserves separate acceptance, without copying the wrong fix

HakiOS documents a real-finger fault: its FocalTech reports could be missed
when polling only the interrupt level. Lifts arrived 88–169 ms after the last
move. Its revised loop reads every poll while a finger is down, even with the
line high, and reads at least every 16 ms while idle. Reported post-fix lifts
were about 5–6 ms. See [measurements](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md#under-real-fingers-5-november)
and [the actual polling loop](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/input/hakios.goodix.c#L1516).

Gauguin uses Novatek. The actual 0249 materialized nvt_poll unconditionally
reads the report on every cycle, then decodes and sends the HID snapshot,
then sleeps 8 ms. It does not gate those reads on IRQ state, so the reference's
specific missed-IRQ error is not established here. However, its period includes
SPI/read/decode/HID work and scheduling in addition to that sleep; 125 Hz is
not a measured sampling rate. SweetHID timestamps after processing, and the
existing aggregate counters do not measure physical-report-to-HID latency.

Acceptance needs first down, move intervals, last move to release, SPI duration,
HID dispatch and downstream commit timing during real finger drags, not just
synthetic swipes or successful unlocks. Start with measurement; do not blindly
halve the sleep or copy another controller's register configuration.

## The larger gap is still the complete desktop pipeline

| Reference requirement | Current gauguin evidence | Remaining acceptance |
| --- | --- | --- |
| System discovers and selects the Metal plugin | 0244–0249 desktop source/native package | Actual backboardd loading, device creation and native GPU submissions |
| Image upload, shader variants and effects | Candidate decoded-image upload and checked 20H392 shader assets | Populated icons/widgets, correct effects and repeatable transitions together |
| Mobile cache instead of root-probe state | 0249 fixes a confirmed root:root0755 pipeline-cache directory conflict | Real UID501 cold/warm/reboot behavior |
| GPU completion and presentation ownership | 0240 shared-output proposal pending; 0241/0242 held-frame/phase candidates | Same-boot producer/consumer completion, safe reuse and delivered frame intervals |
| CPU, GPU and display overlap | Current submission is synchronous; copy holds the same global GPU lock | Issued/completed fence split, retained buffers, per-output readiness, bounded queues and fault handling |
| Input and animation cadence | Successful Novatek unlock; no complete correlated trace | Real down/move/up timing, SpringBoard commits and requested versus delivered frame rate |
| CPU/DDR/copy/panel timing | Eight CPUs and software display target | Actual clocks/bandwidth, copy time, scan timing and sustained physical refresh |

The [earlier pipeline review](gauguin-hakios-pipeline-review-20261111.md)
explains the synchronous transport difference. HakiOS's
[submission returns an issued fence](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.adreno.c#L3465)
and [records it on buffers and surfaces](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L1063).
Our returned queue values denote completed work. Removing a lock or returning
early without the matching resource lifetimes would be incorrect.

HakiOS also records animations requested at 24 fps while GPU work took only
0.3 ms, and adds a SpringBoard animation-range hook. That is a separate clock
from software copying and panel scan. See [the hook and its rationale](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1941).
Measure our requested rate before choosing a range for the qualified mode.

## What the success numbers do and do not establish

The author's full-resolution A642L results are roughly 100–104 fps for swipes
and 89–91 for Settings. The 118–120 Settings result uses 750x1624 rendering,
a frozen wallpaper and synthetic gestures; real-finger drag results are
75–80 fps. A faster earlier run drew the picture incorrectly. CPU copy workers,
deferred recording, cache persistence and CPU frequency control are explicit
parts of its runner. See [conditions and results](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md)
and [runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh).
Those are author-reported measurements, not an A619 forecast or an independent
optical panel test. Its [device status](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/devices/redwood.md)
still lists charging unfinished, Bluetooth unavailable and cellular without
registration. UI acceleration and a daily-use phone are separate milestones.

## Next work

1. Correct the command ABI validation/profile before making any desktop image.
2. Preserve the pending 0240 proposal; genuine consent permits its installation
   and its exact paired 0239 physical trial first.
3. Qualify one complete real Metal desktop, including images, effects, shared
   output, clean owner handoff, mobile cache and repeated lock/app transitions.
4. Trace real touch -> HID -> CA commit -> encode -> issue -> complete -> copy
   -> panel. Use that trace to prioritize input, asynchronous transport,
   animation cadence, cache, clocks and copy work; qualify correct sustained
   60 Hz before physical 90/120 Hz.
5. Keep charging, radios, memory/storage and long-session thermals in the
   separate daily-phone acceptance. Avoid unrelated offscreen feature suites
   unless a concrete desktop failure requires them.

No driver, native binary or existing package receipt changed. No tests were
rerun as new GPU evidence. This is source review and an exact profile-truncation
reproduction, with no device command, root write, boot, CI run or push.
Private evidence: research/tmp/hakios-recheck-20261111-v6.
Source proof SHA256:
670ace3fb93c5c9fbdf6a69e6f9ae34a9cb424159d385f22468fe762cde37c00.
Local audit SHA256:
dbe2d276295c0cf31c3c941c64f4ff5f73b324caecd608b1fee3659a91fa1dc8.
