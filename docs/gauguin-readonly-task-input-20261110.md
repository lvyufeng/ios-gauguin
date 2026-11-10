# Qualified A619 read-only task input lifetime

Trial 0239 physically qualifies the bounded root-only IOSurface sampler input
contract. It does not qualify general Metal device discovery, the desktop,
presentation, high refresh or daily phone use.

The installed probe remained byte-identical across 0237, 0238 and 0239:
`d1f08acbb2dbc71265023fd151fd7e224cc82b4e76fd524dcc79e32e7840a47f`,
build `58a59434c686b6c5cdf17060`. The frontend, core, own sampler library and
launch configuration also remained unchanged. Trials 0238 and 0239 changed
only temporary kernel boot images, with zero new userdata writes.

## What the experiment established

| Input | Bytes per pixel | Allocation bytes | Original virtual offset | Original VA released before draw |
| --- | ---: | ---: | ---: | --- |
| R8 | 1 | 8,205 | 64 | No |
| RG8 | 2 | 12,301 | 4,032 | No |
| BGRA8 | 4 | 20,493 | 16,448 | No |
| RGBA16F | 8 | 36,877 | 0 | Yes |
| RGBA32F | 16 | 69,645 | 8,192 | Yes |

All five 64x64 GPU sampler readbacks, 20,480 pixels and 81,920 channels,
independently match the CPU oracle. Source allocation hashes, including row
padding and the partial allocation tail, match before and after drawing.
The first three retained original allocations also pass their full guards.
Both early-release cases drop the caller's reference and unmap its original
address before the first GPU draw.

Read-only GPU flags, refusal of a GPU-client CPU alias, refusal of CPU WRITE
preparation, and rejection of valid submissions listing the source as WRITE
all pass. Five deliberate WRITE refusals add no successful native job. All
21 positive native jobs complete: 11 FP16/poison/readback jobs, five real CA
jobs and five task sampler jobs. Native logging samples the first 16; later
five successes use raw pixels, completion receipts and aggregate counters.
No exact later IB sequence is claimed.

The original native FP16 prelude still matches all 4,096 pixels; the five
real CARenderer scenes still match all 20,480 pixels. Final resource release,
GPU owner reacquisition and a healthy finite 600-second service pass, with
598 verified renewals. The phone automatically returns to TWRP after
746.564538 seconds. This is a finite diagnostic run, not a sustained desktop
or power-management acceptance test.

## Driver changes and causal evidence

Patch 0207 admits prepared, generic, immutable task memory to the root GPU
client, preserves byte offsets and scatter mappings, enforces read-only GPU
permissions, and retains the descriptor and Surface through DMA ownership.
The compositor admission boundary remains closed for these generic inputs.

0237 passed the first three formats but rejected the first draw after the
RGBA16F caller VA was unmapped. Patch 0208 establishes the retained read-only
kernel alias while that original VA still exists. With 0238, the same RGBA16F
GPU draw/readback passes, but the subsequent CPU source-view comparison fails.

XNU's `IOGeneralMemoryDescriptor::doMap()` has a same-origin-task optimization:
without `kIOMapUnique`, it can return the original caller address as a static
mapping. That address is exactly the one the probe unmaps. Patch 0209 gives
read-only `SweetSurface::mapPixelsInTask()` an independent mapping, preserving
its read-only protection and cache flags. Mutable mappings retain their prior
policy. Real host VM unmap/address-reuse controls reproduce the old stale view
and preserve all five modeled layouts with the candidate. Native disassembly
confirms the conditional `0x04001000` Unique/read-only flags. The unchanged
probe then passes the full lifetime/permission suite on 0239.

## Build and evidence

The actual tested kernel was built locally by DSH from pristine XNU
`1b191cb58250d0705d8a51287127505aa4bc0789`, strict replay of all 201 patches,
and fresh objects. Its source revision is
`8cb296db422b120d34f61f147bf5bd60c856c664`; source-tree SHA-256 is
`60fd1db57a9c38e5bfa0fbfc153356ca3c722d2b456f9379f3eff6fecc10474f`.
Only `SweetSurface.cpp` differs from actual 0238. Kernel SHA-256 is
`a450339883f8d21bcbb991aac34e8ce37cafa3ac2cb2b32e31b3910e1aa5ac88`;
image SHA-256 is
`7357a0abf1894969d1b67b2000fcf2e1e928adb2583bf02bb9850cfea6b99956`.
Header warnings remain; generic provenance, symbols, archive/install identity
and 64-bit cache-flush checks pass.

Private evidence lives under
`research/tmp/gauguin-unique239-worktree-20261110/research/tmp/dsh-unique-0239-task-map/`.
The original trial dispatcher 71658 exits 0 with all 62 input pins unchanged.
`acceptance239-v1.json` rechecks 101 pins, the actual raw sampler arrays, source
hashes, prefix preservation and native/service correlation. Its SHA-256 is
`068006a8331ce053f236c9f6e3df0dcbdc0297d186ae254420fc0673c429af00`.
Original failed 0237/0238 evidence is retained.

The next milestone is shared CA output, then real compositor registration,
decoded-image uploads, display ownership/completion and measured interaction;
see the [desktop integration review](gauguin-hakios-desktop-recheck-20261110.md).
