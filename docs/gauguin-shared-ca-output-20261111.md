# Physical shared CoreAnimation output, 0240

The Gauguin trial passes the bounded shared-output test and its retained
FP16, original CoreAnimation and readonly task-texture regressions. The phone
automatically returns to TWRP after 746 seconds. This qualifies the tested
offscreen path; desktop Metal rendering and physical high refresh remain open.

## Installation and execution

The actual reply to `call_04e6536b94c24018ad8ce89fdb2523e1` authorizes both
the 794,624-byte userdata delta and the 13-byte misc recovery marker, one
temporary boot and failed-write/readback rollback. A fresh readonly check
rehashes the full 16 GiB backup and matches all 194 old blocks in 33 runs,
the original misc block and the paired image. The delta is installed with
33 successful writes and readbacks, volume header last. No rollback is needed.
The misc marker is separately written and its complete 4 KiB block read back.

The temporary image retains the physically qualified 0239 kernel, SHA256
`7357a0abf1894969d1b67b2000fcf2e1e928adb2583bf02bb9850cfea6b99956`.
The installed 0240 probe is SHA256
`26d09095687544b44af83232fd850c8d8c0d2149a7c17b87b7a0500b697bca3b`.
The observer matches the actual kernel banner. The 22-file postcapture retains
19 static files and the complete old prefixes of all three captured logs.
No new kernel build or CI run is used.

| DSH stage | Dispatcher | Exit | Elapsed |
| --- | ---: | ---: | ---: |
| Fresh preflight | 1219 | 0 | 9.382 s |
| Apply and readback | 1488 | 0 | 8.354 s |
| Installed-file check, temporary boot and postcapture | 1854 | 0 | 777.294 s |

Independent review rehashes the stage profiles, inputs and logs, then reruns
the strict parsers against this trial's appended logs and native kernel log.
The input sets contain 9, 3,215 and 46 pins respectively. The outer DSH launch
receipts alone are not used as completion evidence.

## Pixel and native evidence

The five scenes are opaque color, image, alpha, mask and updated image.
Each renders directly into the owned shared IOSurface. After ordered GPU
completion, the original IOSurface CPU view and the original core BO CPU view
are read independently. All 40,960 view-pixels, comprising 163,840 channels,
match their CPU oracles with zero maximum error in this run. The two views
are identical; row padding, allocation tail and teardown checks pass.
There are no target readback blits in this shared-output test.

The original FP16 prelude, original five CoreAnimation scenes and five readonly
task-input formats pass. Five deliberate write requests to readonly inputs
are rejected. Owner release/reacquisition and the finite 600-second GPU
service checks pass. The total of 36 native jobs correlates with 26 explicit
command buffers and 10 framework jobs. The native ring trace individually
records the first 16 jobs; aggregate service records, raw pixels, ordered
markers and teardown supply the later-job evidence. Their exact later IB
sequence is not claimed.

Private evidence is in the 0240 worktree's
`research/tmp/dsh-shared-0240-ca-output/physical-review240.json` and MAIN's
`research/tmp/dsh-shared-execute-0275/review275-v1.json`.

## Next acceptance

This run uses the existing desktop path. It measures neither touch latency
nor desktop frame rate, and does not establish general application Metal.
The next desktop candidate is [0250](gauguin-desktop-boot-profile-20261111.md).
A fresh post-0240 root snapshot, regenerated launch/cache files and a reviewed
installation delta are now prepared. Its individual write authorization is
still required.
Its real-phone acceptance must cover backboardd discovery and native jobs,
populated icons/widgets, effects, repeated transitions and shared presentation,
followed by measured input-to-panel latency and sustained correct 60 Hz.
Physical 90/120 Hz and the full daily-phone objective remain unfinished.

The full snapshot SHA256 is
`2b9796b0dfbfb47d6c5158c946b7beaae4e18871f7cdec804795cd64408a7663`.
The readonly scanner hashes all 16 GiB on the phone. Reconstruction verifies
all 16,384 chunks and the complete digest, transferring 282 MiB of differing
chunks into an independent local clone. The first reconstruction stops before
transferring changed chunks because its 256 MiB budget is too small. A new stage preserves that
failure, reuses the complete scan with an unchanged device header, verifies
fresh transferred chunks and the full digest, and retains a 2.5 GiB host
reserve. DSH 5953 completes the snapshot and launch regeneration successfully.

The desktop proposal adds five files, changes three launch/cache files and
creates four directories, including mobile-owned private caches. Its delta
contains 528 blocks, 2,162,688 bytes in 44 runs, plan SHA256
`1d220805cc5b9e77698e63b09675939579fed8d31091f4171dc6dccc4063fda6`.
DSH 6482 passes local staging, scoped reconstruction and readonly HFS fsck;
DSH 7173 passes 102 writer failure/rollback checks and an independent complete
image diff plus all current old device ranges. DSH 7678 verifies that the
actual application and boot-readback gates reject missing consent. The misc
marker is cleared by recovery, so the next trial also needs separate approval
to arm its 13 bytes. These preparation stages write no desktop delta or misc
marker to the phone and do not boot the next image.
