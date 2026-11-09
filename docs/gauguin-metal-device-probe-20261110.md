# A619 Metal-core device probe: physical 0223 result

The finite 0223 probe has now passed on the actual A619: eight jobs, eight
completed native fences and **28,928 exact output words**. The kernel then
records the compositor acquiring the GPU after a clean eight-fence root release.
The desktop continues through the existing GLES bridge. MTLDevice discovery,
Metal CoreAnimation, IOSurface import, high refresh and daily use remain open.

## Executed physical result

The user explicitly approved plan `41cb87fe...` and touched-run rollback.
DSH applied all **77 runs / 9,957,376 bytes**, rechecking every old range before
the first write and verifying every new range afterward. The header run was
last. There were 77 write attempts and no rollback. All seventeen actual
installed files matched their expected content, length, UID, GID and mode.

The first trial stopped before any recovery IO or boot: one host preflight
resolved a relative kernel-proof path under the 0223 worktree instead of the
qualified 0219 worktree. Its original failure remains intact. A fresh v2 changes
only that reference root, passes all positive host preflight gates up to an
intentional IO sentinel, and performs the first real temporary boot. Fastboot
reported Sending OKAY (0.456 s), Booting OKAY (0.134 s).

| Actual A619 test | Checked output |
| --- | --- |
| Two complementary RGBA8 clears | 4,096 pixels each |
| AIR/NIR/IR3 compute | 256 exact words, runtime seed 920,434,345 |
| Triangle | All 4,096 pixels, including background and 2,016 covered pixels |
| Two updated checkerboard textures | 4,096 pixels each; changed source data between draws |
| Additive RGBA8 blend | 4,096 pixels |
| Premultiplied RGBA16Float blend | 4,096 exact packed half-float results |

All eight stdout hashes match independent CPU expectations. Queue 1 fences
1–8 complete. The raw kernel log independently records the first eight completed
submissions and three compositor opens with `root_fence=8`, after those
completions. Effective active/inactive hard limits are both 128 MiB. These
results cover 64×64, linear, uncompressed, single-sample **sysmem** rendering;
they do not cover BGRA/sRGB, imported IOSurfaces, GMEM, UBWC, MSAA or a full
CoreAnimation scene. The logged command-buffer durations are not a desktop FPS
measurement.

Strict image/banner identity passes without a reconstructed log. The complete
observer/capture interval is 746.946455 seconds and the phone returns to TWRP
automatically. The 600-second service has 598 verified renewals and 93 completed
native submissions; the first sixteen are individually sampled, and later
successes are aggregate evidence. A backboardd crash, two BO failures and one
cleanup failure occur after the explicit planned service stop. This remains a
finite diagnostic, with no long-session or recovery qualification.

`trial-stage-v2` and `dispatch-stage-v2` both exit 0 with unchanged inputs.
`physical-review223.json` has no errors and qualifies only the offscreen core.
All fourteen static files and complete old log prefixes are preserved. New full
stdout/stderr/backboardd sizes are **71,036 / 10,411 / 1,350,137 bytes**. The actual
post-223 volume header SHA-256 is
`11f3ff237da06b9767069fc6a14721d8310ce50e4f24655bcaf6d5d8005c781e`.
Any new root proposal must bind this current state and obtain a fresh full backup
and individual destructive-write approval. The consumed 0223 consent is not
approval for a Metal plug-in installation.

The qualified 0219 IOSurface/touch patches and their existing tests have also
been integrated with the Metal source. DSH replays all 198 patches from pristine
XNU and confirms **all 5,330 materialized entries match the actual qualified
0219 source**, SHA-256
`fd75fc6d3960240dd02a4c038f5ec935b4e2b5b18b97f8d401345d6f2afce242`.
No new kernel was built; the physical image still carries its recorded original
0219 build identity. Existing native/host evidence is retained without rerunning
unchanged tests. The synthetic swipe remains off by default and physical touch
has priority.

## Probe contract

`userland/metal/device_probe.cpp` requires root, the sole `--metal223` argument,
an explicit A619 target, a build tag and the exact linked core hash. It verifies
the effective active/inactive 128 MiB hard limits and a measured 90-second delay
before opening the kernel GPU. The actual GPU, chip and GMEM queries must match
619 / 0x06010900 / 512 KiB / base 0x100000.

One GPU connection covers eight separately completed command buffers:

1. Two complementary, runtime-seeded RGBA8 clears.
2. Compute of 256 exact words with a bound constant buffer.
3. A triangle whose independently calculated coverage has no diagonal edge
   through a pixel centre.
4. Two textured checkerboard draws, with changed source contents between them.
5. Additive RGBA8 blending.
6. Premultiplied-alpha RGBA16Float blending with exact half-float expectations.

All rendering uses uncompressed linear sysmem and one sample. CPU prepare/fini,
completed queue/fence identity and full readback comparison are required. Test
expectations are computed without GPU output. Target poisoning makes an absent
write observable. The successful path compares 28,928 output words in total.
Failure exits without unwinding potentially in-flight buffers; kernel client
teardown remains responsible for their ownership and quarantine.

The final PASS line is emitted after C++ object destruction and says only
`connection-teardown-requested=1`. IOServiceClose success and ownership transfer
must be established from the captured kernel records. Do not treat this line as
proof that the compositor acquired the GPU. The completed probe checks its
120-second elapsed-work budget; individual core GPU waits also have deadlines.
This is not a new kernel watchdog.

## Executed evidence

DSH executed the local build and read-only audits; Codex wrote the probe and
CPU oracle. Evidence is private under the isolated 0223 worktree's
`research/tmp/dsh-metal-0223-device-probe/`.

| Boundary | Result |
| --- | --- |
| CPU oracle | 20,491 ASAN/UBSAN checks: independent vertex-to-screen edge reference, exact coverage and deliberate corrupted RGBA8/half readbacks. Triangle coverage 2,016 pixels. No GPU rasterization. |
| First native attempt | Preserved failure: a helper incorrectly took a const Texture before calling replace. Oracle had passed. |
| Native build v2 | Exit 0, unchanged inputs; one const qualifier corrected. The unchanged oracle evidence is retained rather than rerun. |
| Signed executable | 115,728 bytes; build `57f7536766149f9b7aca9621`; SHA-256 `2e118d960a219890d3215bef81ab9ad3c71d2a68be62244d870900dae0e1e2d8`. |
| Linked core | Qualified 0221 AIR/NIR/IR3 library, 8,369,632 bytes; SHA-256 `8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1`. No Metal plug-in linked. |
| Actual OS import audit | `abi-stage-v1/result.json` exit 0, unchanged inputs. All 282 imports resolve through actual export/reexport tries in the current 20H392 cache or the exact core. Zero missing strong or unresolved weak imports. Reads 44 cache shards, with 2,710 images; does not prove runtime semantics. |
| Fresh root backup | Read-only 17,179,869,184-byte backup; SHA-256 `eb2a3096a3bff1884e10284455e1f2085aa1888c7efec5f7b9fc65dc748fca94`. Current fifteen files and before/after volume header match post-0219. No device writes or reboot. |

The native compiler uses iOS16 deployment with the available SDK26.5. The build
result deliberately retains its original ABI-review-pending state; the later,
separate cache audit supplies the resolved-import evidence without rewriting it.
The new offline upstream recheck also revalidates these result/input/log pins.

## Reproduction inputs

The prepared HakiOS source and its shader fixtures come from the exact 0221
receipt. Build with the same target and core used by that receipt:

```sh
xcrun --sdk iphoneos clang++ -target arm64-apple-ios16.0 \
  -isysroot "$(xcrun --sdk iphoneos --show-sdk-path)" \
  -std=c++17 -O2 -Wall -Wextra -Werror -DHAKIOS_METAL_TARGET_A619 \
  '-DGAUGUIN_METAL_PROBE_BUILD="REPLACE_WITH_PINNED_INPUT_BUILD_TAG"' \
  '-DGAUGUIN_METAL_CORE_SHA256="REPLACE_WITH_EXACT_CORE_SHA256"' \
  -I"$metal_probe_source/include" -I"$metal_probe_source/tests" \
  userland/metal/device_probe.cpp "$metal_probe_core" \
  -Wl,-rpath,/usr/local/lib/gauguin -o "$metal_probe_output"
codesign --force --sign - "$metal_probe_output"
codesign --verify --strict "$metal_probe_output"
```

`metal_probe_source`, `metal_probe_core` and `metal_probe_output` are explicit
local paths. The executed private `build223v2.py` records exact input hashes,
the generated tag, compiler arguments, SDK identities and verification outputs.
Its own shader fixtures are upstream test inputs, not downloaded Apple shaders.
The pixel oracle builds from `tests/fixtures/metal_probe_pixels.cpp` with
`-Iuserland/metal`, ASAN and UBSAN.

## Concrete physical proposal and preparation record

DSH has now prepared a local COW root, minimal delta and paired temporary image.
The proposal adds the probe/core and changes only ProgramArguments of the
existing root diagnostic job and its matching launchd cache entry. It preserves
the label, 128 MiB device policy, the other 530 jobs, installed GLES/Mesa/bridge,
compositor admission and complete existing logs. Both D22 and D221 device-policy
overrides remain keyed by `org.gauguin.gpu-probe`, with the inherited active soft
limit cancelled and active/inactive hard limits of 128 MiB.

The Metal probe does not print an old GLES PASS or change the admission
criterion. Eight completed root fences followed by a verified owner close must
allow the existing compositor path to acquire the single GPU owner.

| Proposal proof | Executed result |
| --- | --- |
| Minimal delta | **2,431 blocks / 9,957,376 bytes / 77 runs**, including necessary HFS metadata. Plan SHA-256 `41cb87fe654943f7dc96d30a088acdae2560ffe346b38579de64b3dcc3443c90`. |
| Final local root | SHA-256 `bf20ed3bf7a42f69aded451cafe8d9ebb5773d15e980097cfabf18eb6d0f9e2b`; full-volume independent comparison confirms exactly those 2,431 changed sectors. |
| Filesystem | Read-only local fsck exit 0; detach exit 0; final image hash unchanged. The log reports iOSRoot appears OK. |
| Writer | Same proven writer body, with only backup/image pins, plan key and error label changed. All **102** approval, stale-range, partial-write, readback, reporting-failure and rollback model assertions pass; fake IO only. |
| Current phone | Read-only RecoveryIO checks all **77** old ranges, 9,957,376 bytes, against the actual idle/unmounted userdata partition. Volume header matches before/after. Zero writes and reboots. |
| Independent review | Exact new namespace, all target contents/owners/modes, retained files/logs, job semantics, range bytes and full-volume change set pass. |

The paired image keeps the **qualified 0219 kernel** and restores physical
Novatek touch while removing `swp=1`. The 601-byte command stays in its fixed
608-byte field. Every payload byte outside that field is identical to 0219;
boot geometry, shim, DTB, firmware, 6 GiB bootstrap and 600-second service remain
the same. Image: 20,021,248 bytes, SHA-256
`346c74953fbc006a8f09d31104cdc23605f5474b618de53bcaa34afb0dd6378e`.

`proposal-stage-v1` packaged the image successfully, then failed before COW
creation because an audit guard expected missing-import counts instead of the
actual empty arrays. That original failure and its inputs remain intact.
Fresh v2 fixes that schema comparison, reuses the exact packaged image without
rerunning its step, and completes staging through independent review with
exit 0 and unchanged inputs. DSH handles 26037 and 91571 are terminal/reaped.
Private scripts, images, delta bytes, receipts and logs remain outside git.

At this preparation milestone the individual userdata-write question was still
pending. The later explicit approval, application and physical result are
recorded above. The guarded apply wrapper requires the plan-bound approval and
review input pins; the writer rechecks every old range before its first write.
Its failure path restores only runs touched by that application.

## Capture and acceptance tools prepared while approval is pending

`tools/metal_probe_log.py` validates all eight ordered probe jobs, effective
memory checkpoints, exact output counts/hashes, queue/fence receipts and build/
core/seed identity. It independently computes expected hashes for all 28,928
output words. The kernel must also show the first eight successful completions
and an authorized compositor open after the clean eight-fence root release.
A PASS line reporting teardown requested is insufficient for this validator.
Strict image/banner identity and the full finite-service validator remain
separate required checks in the post-trial controller.

DSH executed the C++ expectation fixture under ASAN/UBSAN and compared **32**
phase/seed hashes with Python. All **58** receipt/hash/handoff checks passed,
including rejection of stale builds, missing/duplicate/truncated records,
bad memory policy, changed pixels/counts, incomplete native fences, an old
six-fence release, unauthorized/early compositor opens and pre-stop client
faults. These tests use synthetic logs and CPU images. The first collector
erroneously expected at least 60 assertions, after the actual suite had passed
58; a separate read-only v2 review retains the successful compile/tests and
corrects the count interpretation without rerunning or rewriting that failure.

The private `read_files223.py` uses the actual HFS parser and a fixed seventeen-
file namespace, with an explicit 8,369,632-byte limit for the new core. It rejects
wrong recovery identity, mounted/held partitions, unsafe output names/paths,
short reads, oversize forks and a changing root header. The local model reads
both full-hash-verified immutable root images: the base has the original fifteen
files and two absent new files; the final has all seventeen, including the exact
signed core. **246** read/bounds/metadata/refusal assertions passed. Removing
the new core's explicit limit reproduces the old 1 MiB default refusal.
Root and mobile-owned retained files preserve their exact captured UID/GID;
the first fixture's incorrect all-root assumption failed and remains recorded.
Only that fixture expectation changes in its successful fresh v2.

Future before/after-boot capture profiles and the exact seventeen-file expected
manifest have been derived from the checked local final image. Private
`trial223.py`, `boot_pilot223.py` and `post223.py` are prepared. The pilot verifies
kernel inputs against the qualified **0219 worktree**, while preserving the
user's original main-worktree mkadt diff. The post controller captures every
file and complete prior log prefix before independent image, service and pixel
checks; failed identity is retained as failed, even if another component passes.
All four actual prepare/run/post/pilot entry points refused missing consent in
**19** guard/syntax checks with RecoveryIO replaced by a forbidden sentinel.
No device IO, trial claim, approval file, write or boot occurred in those tests.

These results qualify the CPU validation/capture tooling and its missing-consent
guards. They do not exercise the positive live boot/capture path. Private
evidence: `log-tools-v2/result.json`, `capture-model-v2/result.json` and
`startup-guards-v1/result.json`; all DSH workers are terminal. The exact root
delta, paired image and pending individual write question remain unchanged.

The first approved trial now supplies the required build prefix, native fences,
readback passes and clean kernel handoff. Next connect a real Metal device
plug-in, image-specific 20H392 CA shader variants and presentation, keeping one
GPU owner throughout the transition from the existing GLES worker. Actual OS
class metadata is recorded in the separate frontend ABI inventory. Full memory,
high refresh, peripherals and daily-use qualification remain separate work.
