# Gauguin GMU SMMU initialization

The cold SMMU transaction and native board adapter consume the
[memory/HFI image contract](gauguin-gmu-memory-hfi.md). No boot hook calls the
adapter yet. Native compilation and host execution with hardware seams do not
establish physical register access, firmware boot or GPU acceleration.

The primary reference is
[arm-smmu.c](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/iommu/arm-smmu.c)
and its
[register definitions](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/iommu/arm-smmu-regs.h),
plus the captured gauguin DT's GPU SMMU aperture and attach-impl-defs values.
The GPU SMMU is at03d40000, distinct from the APPS SMMU at15000000.

## Board ownership

The future single GMU coordinator passes its actual same-boot CPU-stage claim.
The stage owner verifies the immutable CLAIMED record, all64 unmanaged NC pages,
and the metadata hash/zero tail again. The adapter sets an eight-second CPU
deadline and initially requires13 nominal watchdog seconds, then repeats
three-second margins around accesses. There is no pet, disable, re-arm, retry
or rollback. The clock owner supplies current fixed-profile checks using its
retained private mappings independently of its old transaction deadline.

The GIC helper reuses the PE mapping and checks the NS ISENABLER view only:

| Resource | DT SPI | INTID | Byte offset/mask |
| --- | --- | --- | --- |
| SMMU global | 229,231 | 261,263 | 0x120 / 0xa0 |
| GMU HFI/error | 304,305 | 336,337 | 0x128 / 0x30000 |
| SMMU context | 364..371 | 396..403 | 0x130 / 0xff000 |

Zero bits do not prove secure IRQ ownership. No handler is installed or GIC
state changed. GX PWR_ON must remain zero and CM3_SYSRESET must already read1.
An inherited running CM3 is rejected. The board maps exactly03d7c000+4000 for
reset and03d40000+10000 for SMMU, validating unmanaged Device attributes,
virtual range bounds and every16KiB endpoint. Mappings remain retained on all
outcomes; no pointer is exported. A broad GMU map would alias GPUCC and is
never created.

The low NC mapping starts AFTER the protected first16KiB metadata page. A64KiB
ordinary scratch buffer holds expected table/HFI images. Only named CPU data
reservations and table bytes are zeroed/copied, in bounded4KiB chunks with
fresh guards and actual NC readback comparisons. The metadata page, gaps and
tail after0x9c000 are untouched. Scratch is freed; the low owner remains held.

## SMMU sequence

The fixed envelope requires a64KiB SMMUv2-style aperture with4KiB register pages,
AArch644KiB S1 support, architected ATOS, at most128 stream groups and eight
context banks. EXIDS and other geometries are rejected. IAS is min(ID2.UBS
width,39); S1 output width uses ID2.IAS, the native ipa_size. ID2.OAS is a
separate downstream capability. All context SCTLR.M and stalled-fault bits
must initially be zero; this is cold initialization with no active handover.

Resolve exact GMU streams4/5 through SMR/S2CR or indexing; reject duplicate or
masked matches. Reuse exclusively referenced S1 banks or allocate unused banks,
preserving shared disabled banks. Use native ASID=bank+1. Recheck captured
controls/routes after preparing memory and before global writes. Halt the
Qualcomm micro-MMU and poll idle, retaining the halt request through all12
native DT implementation values, context programming and ATOS. Clear/sync
global faults/TLBs; enable native reporting/VMIDPNE/PTM/non-shareable controls
and fault unmatched streams. Fence GMU streams with S2CR FAULT during setup.

Use atomic64-bit TTBR writes, CBA2R1, CBAR0x1f300, native TCR/MAIR,
non-stall SCTLR0xc01067 and ACTLR0x70000000, then invalidate/sync each ASID.
Actual ATOS must translate all131 kernel data pages correctly; six holes and
three empty-user-root addresses must report translation faults. External
aborts and all-ones PAR are rejected. These140 operations verify translations,
not independent cache-attribute measurements. Publish exact GMU routes only
afterwards, recheck unrelated controls/routes, and clear the local halt request.
Failure quarantines the transaction and its watchdog authorization; software
timeouts cannot cancel a fabric access that never returns.

## Following integration

Next implement the pinned32768-byte legacy asset contract, narrow TCM and GMU
AO/PDC/RSC owners, native ucode/power/boot/version setup, reset release and
fresh firmware result, then A619-specific GX/OOB/HFI ordering and request/ACK
exchange. Select protocol using qualified runtime evidence. Integrate these in
one bounded initialization before a new temporary boot; no mapping-only reboot
is needed. GPU commands, ZAP at its native point, Metal/rendering and high
refresh remain required work toward the unchanged daily-use objective.
