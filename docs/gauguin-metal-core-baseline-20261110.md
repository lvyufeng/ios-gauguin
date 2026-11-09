# Pinned HakiOS Metal core baseline

This follows the [renewed graphics review](gauguin-upstream-graphics-review-20261110.md)
and [transport audit](gauguin-metal-transport-audit-20261110.md). It establishes
a reproducible upstream software baseline before A619 adaptation. It does not
establish Metal availability or correct rendering on gauguin.

## Source and executed checks

The complete `hakios-metal/` directory at HakiOS
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438` was obtained through the GitHub
connector: 227 files, 5,716,039 bytes. Each file's exact size and Git blob hash
matches the pinned repository tree. Upstream source, fixtures, license and
notices remain in the private research cache. No Apple files are involved.

Private evidence is in `research/tmp/dsh-metal-0220-core-baseline/`.
`source-receipts-v1.json` SHA-256:
`9e4c3d158061efafff76c7e3e7000f2d0c84f8656f6ece17e244938046342897`.

DSH executed each immutable stage once. Original v1 failed and remains intact:

- macOS's `chipKnown` helper is unused outside the iPhone path; `-Werror` turns
  that diagnostic into a compile failure.
- The included `compiler.mk` defines `IOS_CXX` before the main Makefile's
  Darwin default, selecting an absent `xnu-clang++` wrapper. The SDK itself is
  present. This is a command-selection issue in this checkout layout.

Fresh v2 uses a separate byte-identical source directory and output paths. On
the host only, `-Wno-error=unused-function` keeps the warning visible and leaves
other warnings fatal. For iOS it explicitly supplies Xcode clang with
`-target arm64-apple-ios16.0`; native warnings remain fatal. The available SDK
is iPhoneOS 26.5, so this is an iOS16 deployment-target compile, not proof of
linking or running against the phone's iOS16 frameworks.

V2 stage completed with both inner exits zero and all 233 input pins unchanged:

- Complete host/fake-GPU suite under AddressSanitizer and UndefinedBehaviorSanitizer:
  **261 tests, zero failed checks**.
- Native core archive: **12 ARM64 Mach-O object files**, each checked for the
  expected CPU and object type. Archive 1,024,144 bytes, SHA-256
  `aa8fd4be795fd5fb3a3fc3b309415e6907dadaa11672fb0d88efdcc8621be6d4`.

Shader fixtures were held as the pinned inputs instead of being regenerated
because of download timestamps. They target the upstream chip, not A619.
`MESA` was disabled: `compileAir` refuses unsupported compilation by design.
Neither the AIR frontend nor the Metal plug-in/CA integration was linked.
There were zero device commands in this stage.

## Concrete A619 differences

The already-used Mesa 25.0.7 source contains the actual `GPUId(619)` row in
`src/freedreno/common/freedreno_devices.py`. It inherits `a6xx_base` and
`a6xx_gen1`, while the upstream Metal constants select `a6xx_gen4`.

| Consumed state or capability | Pinned HakiOS core | A619 reference |
| --- | --- | --- |
| Chip target | `0x06030500` | Observed board `0x06010900` |
| Query and submit pipe | `1` | Existing kernel requires `0x10` in both |
| SP / CCU count | 2 / 2 | 1 / 1 |
| Fibers per SP | 4096 | 2048 |
| Instruction-cache preload cap | 127 groups | 64 groups |
| LPAC | enabled | absent in gen1 |
| Register-file size | gen4: 64 vec4 | gen1: 96 vec4 |
| Tile alignment | 32 by 16 | 32 by 32 |
| Static magic registers | gen4 values | Several different gen1 values |
| Shader features | gen4 scalar/packing capabilities | Compiler must use the actual gen1 profile |
| Draw/depth quirks | gen4 profile | gen1 indirect-draw and depth-bounds quirks |

This is an adaptation checklist, not an exhaustive compatibility proof.
For example, the Metal encoder consumes `kInstrCacheSize` in both compute and
render paths, and the tile planner consumes `kTileAlignH`. Changing only
`kChipId` would leave both wrong. A635 fixture binaries also cannot serve as
A619 shader qualification. Existing `HakiosGPU` service matching already
agrees; no provider rename is needed.

## Next implementation boundary

Keep the working firmware, power, SMMU and admitted A619 backend. Introduce an
explicit device profile covering every consumed compiler/encoder capability,
with incompatible generations refused. Adapt both transport pipe fields,
validate returned request sizes and map extents, and preserve BO ownership,
deadline and fence checks. Start with uncompressed linear sysmem; qualify GMEM
and compression separately.

Obtain HakiOS's matching AIR-to-NIR frontend and build it against a separate
Mesa tree, without mutating the installed GLES compiler. Compile shaders for
the actual A619 target. Then require device clear/triangle/texture/blend,
readback and fence/lifetime checks before wiring Metal discovery, the plug-in,
20H392 shader libraries and complete CoreAnimation presentation. The existing
finite single-owner admission remains a separate runtime limitation.

The separate 0219 automatic-swipe trial only seeks desktop/create-path
coverage. It does not qualify this Metal core or physical high refresh.
