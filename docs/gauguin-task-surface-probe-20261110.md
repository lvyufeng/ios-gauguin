# Real immutable task IOSurface sampler qualification

The 0236 kernel passes the unchanged 0235 FP16 and five real CoreAnimation
offscreen scenes. That regression uses existing surfaces. The new task-backed
import requires its own physical test before compositor admission.

The optional task suite extends the existing finite root probe. It retains the
native FP16 prelude, original system shader specialization and five CA scenes,
then samples five genuine task-backed immutable IOSurfaces. The executable uses
the existing project-owned `hakiosDevice` and `hakiosTexture` getters after class
and return-type checks. Two core object definitions are generated from the exact
core8a `c_api.cpp`; the core binary and frontend bundle are unchanged. No Apple
object layout is projected. The executable carries the installed core rpath.

The cases use R8, RG8, BGRA8, RGBA16F and RGBA32F, padded rows, 64-byte-aligned
nonzero page offsets and partial final pages. Fresh task VM becomes read-only
before IOSurface creation. Each texture must retain the original surface and
must have no shadow copy. The exact source BO must have GPU read-only flags,
preserve its page bias and provide no GPU-client CPU alias. CPU WRITE preparation
and a valid NOP submission listing the source as WRITE must both return EINVAL.
The negative submission must not acquire a fence. An unexpected successful NOP
is waited before teardown; an uncertain fence retains its command memory and
queue until process exit.

For the last two formats, the caller releases its IOSurface reference and
unmaps its original task VA before drawing. The frontend texture still retains
the IOSurface, and the kernel retains prepared memory through DMA. This tests
that combined ownership chain, not a claim that the kernel is the sole owner.
All 20,480 output pixels are emitted as raw rows. The independent Python reader
reconstructs each channel and the entire source allocation hash, including row
padding and tail bytes. Native checks compare every source byte after the fence;
the first three cases also check exterior guards in the retained original VM.
Final queue/device release and owner reacquisition remain mandatory.

Software validation by DSH has completed:

- The real core `Gpu` request writer passes 25 transport, permission and failure
  lifetime scenarios under ASan and UBSan. Two uncertain-DMA cases intentionally
  retain command BOs until task exit; leak detection is disabled for those tests.
- The iOS ARM64 executable compiles and signs without compiler warnings. The
  initial artifact lacked the core rpath and was rejected during review; it is
  retained privately. A fresh build adds and verifies the actual LC_RPATH.
- Public Mac Metal samples the same owned shader over all five formats and
  padded input rows for four seeds: 81,920 raw pixels match. Forty corruptions of
  actual logs are rejected. This does not qualify phone IOSurface lifetime.
- Parser tests combine those actual Mac rows with explicitly synthetic
  permission records and reject 72 malformed envelopes. They are parser tests.
- All 717 native imports resolve against the actual iOS 20H392 cache and exact
  core artifact. The new probe has no weak imports. Unchanged core/frontend
  import inventories match the previous accepted audit. The initial audit's
  overbroad weak-import gate rejected already-resolved baseline imports; its
  failed result remains preserved.

The candidate has 16 explicit successful jobs plus five separate CA framework
jobs. The five negative WRITE requests must not become GPU jobs. Since kernel
logging samples only the first 16 successes, final physical review must retain
aggregate fence/service checks without claiming an exact later IB sequence.

No 0237 userdata delta has been installed or approved. A new current-device
capture, complete backup, scoped delta review and separate user consent are
required before installation. GPU execution, task-backed sampling, compositor
presentation, general Metal, high refresh and daily use remain unqualified by
this software work.

Private artifacts:
`research/tmp/gauguin-surface237-worktree-20261110/research/tmp/dsh-surface-0237-task-probe/`.
