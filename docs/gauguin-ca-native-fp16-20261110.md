# Native FP16 and the image-owned CoreAnimation shader path

The actual 20H392 QuartzCore code offers a route to its existing LPH shaders
through `supportsNativeHardwareFP16`. This gives a concrete alternative to
adapting a later system's incompatible shader library. Trial 0235 now qualifies
this route for five bounded real CoreAnimation offscreen scenes on A619.

Offline inspection of the exact cached framework established these links:

1. The context queries Apple1 at `0x1884886d4` and
   `supportsNativeHardwareFP16` at `0x1884889ec`. The actual parent method has
   encoding `B16@0:8`.
2. Either affirmative answer takes the branch that sets context flag bit 20.
3. The program-key constructor moves that flag to bit 4 of its halfword at
   offset 13. Its generic-key copier preserves this precision bit.
4. The specialization builder uses that bit and the color-precision bit to
   index the exact table: LPH/CPH, LPH/CPF, absent, LPF/CPF. Both LPH functions
   are present in the current image. Trial 0233 requested the missing LPF/CPF.

These links explain the precision-selection failure captured in trial 0233.
The physical result below confirms the new route through all five real CA
scenes, with correct pixels and correlated native submissions.

## Scoped implementation

`gauguin-ca-fp16` adds patch 0005 after the exact-identity profile. Its FP16
capability begins disabled. The paired root probe first runs a project-owned
shader workload over runtime-provided half buffers, vertex half arithmetic,
half varyings, fragment half arithmetic and an RGBA16F render target. Four
scissored draws cover the complete 64 by 64 image in one command buffer.

Every one of the 16,384 half channels is compared, and all raw rows are retained
for independent host review. Only after readback succeeds can the exact seeded
hash activate FP16 on this admitted device instance. The activation method and
the inherited SPI encoding are checked at runtime. Public GPU-family answers
remain zero. The current framework and its complete library remain unchanged.

The same device and queue then execute the original real CARenderer scenes.
There are 11 explicit probe jobs: one FP16 prelude and ten CA poison/readbacks;
the framework's actual CA jobs are counted separately. Four prelude render draws
are accounted separately from subsequent CA draws. Existing pixel tolerances,
hard memory limits, finite execution, original specialization/error trace and
sole-owner teardown remain in force. Legacy mode2 SETEXEC follows its retained
qualified GLES path before reaching this new test.

## Software evidence

- All five older source preparation profiles are byte-identical to 0234.
- Both native iOS artifacts compile, link and sign. The frontend retains one
  existing SDK deprecation warning; the paired probe has none.
- The actual A619 compiler emits half-register vertex multiplication and
  fragment `mad.f16` for these exact project shaders. The initial register-count
  assertion stopped the first native stage: its half-register count is zero in
  the merged register-file accounting, despite actual half instructions. The
  failed stage is retained. A separate stage captures the actual cached ISA.
- A real Mac GPU rendered all four seed permutations. Independent Python
  binary16 expressions compared 16,384 pixels / 65,536 channels. Seven corrupt
  versions of those actual raw logs were rejected.
- Fourteen reader tests pass, including incorrect or premature activation,
  missing/corrupt rows, unchanged old CA checks and separate prelude draw counts.

These software checks support the separate physical trial below. The Mac
oracle alone does not prove A619 execution or desktop rendering.

## Physical trial 0235

After individual consent for the exact 286-block delta, all 35 writes were read
back successfully; no rollback was needed. The installed 22-file set was checked
before one temporary boot of the unchanged qualified 0219 kernel. The phone
automatically returned to TWRP after 746 seconds; the observer completed in
747.089870 seconds with the matching kernel banner. All 19 retained static
files and the complete three historical log prefixes survived unchanged.

The actual A619 FP16 prelude passed independent comparisons of all 4,096 pixels
and 16,384 half channels. Only then did this device instance activate its native
FP16 capability. The original image-owned `fixed_frag_lph_cph` and
`fixed_vert_lph_spc` specializations succeeded in all six calls, with no missing
functions or substituted newer library. Public GPU families remained zero.

| Real CARenderer scene | Independently compared pixels | Maximum channel error |
| --- | ---: | ---: |
| Opaque color | 4,096 | 0 |
| Image texture | 4,096 | 0 |
| Alpha blending | 4,096 | 0 |
| Mask | 4,096 | 0 |
| Updated image | 4,096 | 0 |

All 81,920 CA output channels matched. The kernel recorded all 16 completed
submissions: one FP16 prelude, ten poison/readback jobs and five actual framework
jobs. Four FP16 draws were accounted separately from 14 accepted CA draws.
The finite 600-second GPU service completed 598 verified renewals. No competing
compositor owner, GPU fault cleanup, BO failure, compositor crash or post-stop
submission failure was accepted. Probe resource release also passed.

The original results are `physical-review235.json` and the independent
398-pin `acceptance235-v1.json` in the private directory below. This is an
offscreen CA result, not desktop acceleration, general Metal compatibility,
application admission, a frame-rate measurement or high-refresh support.

Next, qualify actual IOSurface-backed input/output and the compositor's display
handoff. The current kernel surface importer explicitly rejects read-only or
non-IOBuffer-backed surfaces; borrowed task memory requires its own mapping and
lifetime validation. The qualified root probe does not expose the device to
backboardd or other applications, and the 600-second service is still a finite
diagnostic window.

Private artifacts are under
`research/tmp/gauguin-precision235-worktree-20261110/research/tmp/dsh-precision-0235-flow/`.
Apple framework bytes and their disassembly stay outside Git. The previous
[precision comparison](gauguin-ca-precision-contract-20261110.md) remains relevant
to any future later-library adapter. Broad Metal publication, MPS/application
compatibility, presentation speed, high refresh and daily-phone acceptance remain
open requirements.
