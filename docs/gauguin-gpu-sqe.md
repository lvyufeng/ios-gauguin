# Pinned SQE asset and cold staging

Patch0149 prepares the A619 command processor's firmware without starting it.
The existing, default-off `sweetgpustart=1` pipeline selects the new cold SQE
entrypoint, then runs the retained MMU/OOB/core-access stage. All five older
firmware entrypoints keep SQE disabled and retain their hardware callback trace.
The immutable148 image remains the physical MMU/OOB/core-access baseline.

`tools/mkpayload.py --sqe-firmware` appends a separate `A630SQEFirmware` boot asset
after GMU. Its exact raw size is32304 bytes, reserved extent32768 bytes and SHA256
is `a0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b`.
The native four-byte header stays in the boot asset; its464 padding bytes are
zero. The descriptor records the raw size. Existing asset contents and segment
addresses survive; final top-of-kernel-data and PAS accounting include the asset.
Omitting this option preserves old payload bytes and metadata.

The new CPU view validates the complete reserved extent, boot RAM bounds,
contiguous direct-map endpoints, zero padding and raw SHA256. It requires valid,
pairwise disjoint NVT/MDT/GMU descriptors. It allocates and maps nothing, leaves
output unchanged on failure and grants no execution permission.

The board authenticates the view before any mapping. During `ggb_prepare`, while
the existing guards require CM3 reset and GX off, it uses the existing NC SQE
reservation. Following the pinned native `_load_firmware` convention, it skips
the four-byte header, copies32300 code bytes and zeros the remaining468 bytes.
The complete32768-byte destination is read back. Each4KiB chunk is bounded by
owner, clock, IRQ, fault, deadline and watchdog checks, with DSB completion.
The source view is revalidated at entry and after copying; the loaded flag is
published only after8192 issued and8192 compared words and final guards succeed.
Page tables are published afterward. No new allocation, alias or GPU leaf is
introduced. Failures keep partial counters and follow shared quarantine policy.

Validation covers all143 patches applied to pristine XNU, the actual raw pinned
asset and synthetic SHA/bounds/refusal cases,143 new cold-board cases, retained
board/coordinator tests, all68 host test files and three actual ARM64 translation
units. Frozen148 old-entrypoint fixtures produce identical107464820 callback
events on148 and149;32 SQE-absent payload combinations are byte/info identical.
These are source and host results. There is no149 complete kernel/image or
physical qualification yet, and no SQE execution, CP command, ZAP authentication,
GPU rendering or Metal claim.

The next stage must preserve native target policy and lifecycle ordering: GBIF
deassertion before MMU/OOB;64-bit/core/HWCG/protection setup; a powerup register
list filled from actual live register reads; scratch/RB/SQE programming and the
native CP_ME_INIT submission protocol. A619 lacks APRIV, so native spin submission
also appends CP_WHERE_AM_I to update the shadow RPTR. Native CP init precedes ZAP
loading; ZAP success and proper unsecured-mode transition remain required later.
Runtime preemption may initially stay disabled, as explicitly supported by the
native driver. Full preemption needs normal and secure records of0x190000 bytes
per ring plus additional buffers, beyond the current1MiB retained owner.
