# A619 Metal-core device probe: software readiness

The finite 0223 root probe now compiles and is signed for arm64 iOS 16. Its
imports resolve against the actual installed 20H392 cache and the qualified
A619 core. It has **not been installed or run on the phone**. No MTLDevice,
CoreAnimation integration or correct device pixels have been demonstrated by
this milestone.

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

## Next physical boundary

Prepare a local COW root adding the probe/core and changing only the existing
root diagnostic job and its matching launchd cache entry. Keep the label,
128 MiB device policy, installed GLES/Mesa/bridge, compositor admission and
logs. The Metal probe does not print an old GLES PASS or change the admission
criterion. Eight completed root fences followed by a verified owner close must
allow the existing compositor path to acquire the single GPU owner.

Pair it with the qualified 0219 kernel, physical touch enabled and the finite
synthetic swipe disabled. Preserve the 600-second diagnostic service and all
firmware, memory and safety controls. Complete minimal-delta reconstruction,
local filesystem checks, writer-model tests, real-device old-block comparison
and independent review before requesting the required individual userdata
write approval. No new delta, temporary image, application or approval exists
at this milestone. The fresh backup alone is not installation authorization.

After one approved temporary trial, require the exact build prefix, eight
native completed fences, eight readback passes and clean kernel handoff.
Only then proceed to a real Metal device plug-in, image-specific 20H392 CA
shader variants and presentation. Full memory, high refresh, peripherals and
daily-use qualification remain separate work.
