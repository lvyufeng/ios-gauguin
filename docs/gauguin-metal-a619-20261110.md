# A619 Metal core and AIR compiler implementation

The current branch now implements A619 selection in the pinned HakiOS Metal
core and links the actual AIR-to-NIR-to-IR3 compiler. This is software-qualified
preparation for the first Metal-core device probe. No device was booted or
userdata modified during this work; the phone remains at the post-0219 TWRP
baseline. Full Metal UI, high refresh, all safe RAM and daily use remain open.

## Changes

`graphics/hakios-metal/` holds manifests, one twelve-file upstream patch and a
device-profile overlay. The default A635 profile remains available; native
gauguin builds explicitly select `HAKIOS_METAL_TARGET_A619`.

- The compiler and encoder select the actual `0x06010900` device, one SP/CCU,
  2048 fibers per SP, 64 instruction groups of preload and 32-by-32 tile
  alignment. Static register values and CCU layout follow the A619 Mesa row.
  A separate private-memory allocation site now uses the same core/fiber facts.
- GET_PARAM and GEM_SUBMIT both use pipe `0x10`. Actual A619 open refuses a
  missing/different chip ID and requires the queried 512 KiB GMEM size. The
  provider remains `HakiosGPU`; it already matches the local kernel.
- LPAC register copies are excluded on gen1, including when a diagnostic
  option requests them. Indirect draws emit the gen1 wait-for-idle / wait-for-me
  ordering. Unsupported hardware bicubic filtering is refused explicitly.
  The current renderer exposes no depth-bounds state; the gen1 depth-bounds
  quirk is recorded for any later addition of that feature.
- Shader-cache identity includes the selected chip. Native build identity also
  includes source, headers and linked compiler archives.
- Production IOKit transport rejects a successful struct call with the wrong
  returned size, and rejects/unmaps an undersized CPU mapping.

The profile is compared with the actual linked Mesa device table, not a test
copy of the new constants. That check caught an initially incorrect A619 UBWC
swizzle: its row inherits **6**, not 7. The final profile and fake parameter
responses use the corrected inherited value. Compression and GMEM execution
have not been device-qualified by this change.

## Executed qualification

DSH executed immutable local stages. Codex wrote and reviewed the source.
Private evidence lives inside
`research/tmp/gauguin-metal221-worktree-20261110/research/tmp/`:

| Evidence | Result |
| --- | --- |
| `dsh-metal-0222-air-compiler/compiler-stage-v4/result.json` | Exit 0, unchanged inputs. Verifies 13 host and 13 iOS archives built from fresh Mesa 25.0.7 with the pinned AIR frontend. |
| AIR compiler smoke | Actual A619 compilation of the authors' `fill_id`, `tri_color_vs` and `tri_color_fs` bitcode. Device FD619, one SP core. No GPU execution. |
| Canonical source preparation | Exit 0. `prepare-hakios-air.py` reproduces all 10,992 files of the source actually used for those archives. Canonical source-pin-map SHA-256 `450d30f53291d6c8b5593306fc18a35e4f53d002900b6ae23d2ce02860f7b063`. |
| `dsh-metal-0221-a619-profile/qualification-stage-v5/result.json` | Exit 0, unchanged inputs. **663** production-core/Mesa/compiler/encoder checks under ASAN/UBSAN for the core and fixture; the linked Mesa archives are release builds. |
| A619 core checks | Real shader compilation/linkage; actual query/submit pipe fields; private-memory extent; 64-group preload and long-program workaround; absence of LPAC writes even when forced; sampler refusal; indirect-draw ordering. Fake GPU completion is not hardware or rasterization proof. |
| Production IOKit fixture | Identical fixture against original source fails functionally on a short successful reply. Candidate passes **12** size, mapping and lifetime checks. Uses IOKit stubs, not a real device. |
| Upstream compatibility | **261** unchanged A635 tests passed. After the A619-specific CCU assertion fix, a fresh default-profile translation unit confirms the original A635 chip/layout. Unaffected tests were retained rather than repeated. |

The native `native-v4/result.json` records twelve arm64 iOS object files linked
with the thirteen iOS compiler archives, an iOS16 deployment target, ad-hoc
signature verification and the public core entry points. The available SDK is
iPhoneOS 26.5, so compile/link success does not prove the phone's iOS16 runtime
ABI or framework behavior.

Artifact: `libGauguinMetalCore.dylib`, **8,369,632 bytes**, SHA-256
`8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1`.
It contains the AIR compiler, unlike the earlier MESA-disabled 0220 archive.
It does not contain the Metal device plug-in or CoreAnimation integration.

## Preserved failures and scope

All original stage results remain intact. AIR v1 rejected an unnecessary OSMesa
configuration; v2 built the archives then failed its Ninja-indent fixture; v3
needed an explicit macOS SDK; v4 uses those same verified archives successfully.
Core v1 retained an upstream two-CCU literal assertion and had two fixture
compile issues. V2's guard caught a stale prepared-receipt path. V3 caught the
incorrect swizzle and a stale native-result path, although native linking had
completed. V4 passed native linking, then correctly refused a compute fixture
missing its required constant buffer. V5 adds that fixture binding and retains
the unchanged native, transport and upstream-regression evidence. These are
separate results, not rewritten passes.

No MTLDevice was discovered, Metal application run, texture sampled or frame
presented on the phone during this work. The 0219 image/kernel, installed UI210
bridge and Mesa library remain intact; UI216 is still uninstalled.

## Next device boundary

Build a root diagnostic using this exact native core and its own shader inputs.
Require clear, compute, triangle, texture and blend results with exact pixel
readback and completed fences. The existing kernel admits one owner; the root
probe must finish and release it before the compositor can claim it. Current
compositor admission requires at least six completed root fences. Do not race a
second ordinary client or relax the kernel's ownership/BO checks.

Prepare any required userland installation as a fresh bounded delta against
the actual post-0219 root header and full log prefixes. Complete the new full
backup, filesystem and old-block/readback checks, then obtain the required
individual destructive-write approval. Follow with one authorized temporary
boot and automatic capture. Only after real rendering passes should the Metal
plug-in, exact 20H392 shader libraries and full CA/presentation path be connected.
