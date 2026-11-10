# Native FP16 and the image-owned CoreAnimation shader path

The actual 20H392 QuartzCore code offers a route to its existing LPH shaders
through `supportsNativeHardwareFP16`. This gives a concrete alternative to
adapting a later system's incompatible shader library. Physical CA rendering
with this route is still unqualified.

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

These links explain a specific precision-selection failure mode. The upcoming
physical test must establish that the new route actually works through all five
real CA scenes, with correct pixels and continuous native draw receipts.

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

The evidence proves software preparation and the Mac oracle workload. It does
not prove that the A619 completed this workload or that CA/UI rendering works.
Those claims require a new approved physical trial, fresh captured artifacts,
native fences, pixel rows and the original strict CA/service qualification.

Private artifacts are under
`research/tmp/gauguin-precision235-worktree-20261110/research/tmp/dsh-precision-0235-flow/`.
Apple framework bytes and their disassembly stay outside Git. The previous
[precision comparison](gauguin-ca-precision-contract-20261110.md) remains relevant
to any future later-library adapter. Broad Metal publication, MPS/application
compatibility, presentation speed, high refresh and daily-phone acceptance remain
open requirements.
