# A619 GMU memory and HFI contract

These CPU-only modules prepare the fixed legacy A619 memory image and implement
bounded HFI shared-RAM queues. They are not connected to a boot hook. They do
not configure an SMMU, release CM3 reset, execute firmware, handle an IRQ or
prove GPU acceleration. Hardware0120 qualified the configured200MHz clock path
and branch ON observations; actual firmware/HFI protocol is still unqualified.

## Native reference

All semantics below use LineageOS/android_kernel_xiaomi_gauguin commit
`19b63c8192b1c9b7c4d931d7d3be92024bc2d778`:

- [kgsl_gmu.c](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/kgsl_gmu.c): legacy VMA, cache-finalization and kernel allocation order.
- [kgsl_hfi.c](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/kgsl_hfi.c): four legacy queues, packet size fields, v2 padding and barriers.
- [kgsl_hfi.h](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/kgsl_hfi.h): binary layout and protocol fields.
- [io-pgtable-arm.c](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/iommu/io-pgtable-arm.c): AArch64 S1 NC/outer-shareable permissions and MAIR/TCR encoding.

## Allocation and translation

One already-reserved1MiB owner arena below4GiB supplies both modules. Its first
16KiB stays untouched for PAS metadata. The CPU uses16KiB pages; SMMU page tables
use4KiB granules. CPU reservations are16KiB aligned, firmware-visible lengths
are4KiB aligned. Runtime must verify that the whole arena remains excluded from
general allocation and has the existing single unmanaged NC CPU mapping.

| Purpose | Owner offset | CPU reservation | GMU IOVA | GMU bytes | Unprivileged access |
| --- | ---: | ---: | ---: | ---: | --- |
| Eight S1 tables | 0x4000 | 0x8000 | none | none | none |
| Instruction cache | 0x10000 | 0x3c000 | 0x4000 | 0x3c000 | no |
| Data cache | 0x4c000 | 0x3c000 | 0x44000 | 0x3c000 | no |
| Dummy | 0x88000 | 0x4000 | 0x60000000 | 0x1000 | no |
| HFI | 0x8c000 | 0x8000 | 0x60001000 | 0x5000 | yes |
| Crash dump | 0x94000 | 0x4000 | 0x60006000 | 0x4000 | yes |
| Log | 0x98000 | 0x4000 | 0x6000a000 | 0x1000 | no |

The kernel context maps exactly131 data pages with RW/NC/AF/outer-shareable/nG
attributes, matching native IOMMU_PRIV choices. Native does not specify NOEXEC
for these allocations. No metadata/table/gap/padding page is mapped. HFI/dump
unprivileged permissions are in the kernel context; the separate GMU user
context has empty roots. IAS32..39 and native OAS32/36/40/42/44/48 are encodable,
but this does not establish hardware support. Runtime must derive capabilities
from SMMU IDRs and program the native CBAR/ASID/TLB/TTBCR2 controls separately.
DT stream IDs4/5 must not be assumed to mean context banks4/5.

## HFI ownership and publication

The header is216 bytes; queues start at224 bytes and each contain1024 DWORDs.
Legacy queue IDs are0/4/5/1, priorities10/10/40/20, with the fourth disabled.
The native header still reports four active queues. The wire size is8 bits;
this transport accepts1..255 DWORD packets. It explicitly supports qualified
major1/2; family and zero version words in an asset do not select a protocol.

Bind one private channel once against the freshly emitted table before HFI is
started. A CAS serializes host ownership. Only queue0 can send; queues1/2 can
receive. Table/header/index checks precede queue access. Reserve one DWORD to
avoid full==empty. V2 indices and packet spans align to4 DWORDs, with native
0xfafafafa transmit padding. V1 indices advance by the unpadded wire size.

Owner-provided callbacks must guard each access before and after, implement
little-endian NC word reads/writes and full memory barriers. Payload is ordered
before index publication; the host-owned index is rechecked, stored, ordered
and read back. Receive output is copied only after successful index publication.
IO/corrupt state permanently quarantines the channel: an index may already be
visible, so there is no retry/rollback. EMPTY/FULL/CAPACITY do not mutate queues
or outputs. The peer must obey the native single-producer/single-consumer
publication protocol; this is not protection against arbitrary firmware writes.

The board adapter must retain its lease across send completion and the actual
HOST2GMU doorbell. No ACK interpretation, interrupt delivery or firmware version
qualification is supplied here. Callers must use private ordinary packet and
output buffers, without aliases of shared RAM or controller mappings.

## Next hardware integration

Before the next integrated boot, implement narrow controller ownership without
aliasing the retained GPUCC mapping, CM3 reset/IRQ containment, actual SMMU
stream/context/capability qualification, page-table publication and native
PDC/RSC setup. Stage the pinned32768-byte legacy firmware asset into AHB ITCM
only after those predicates, then follow the native reset/boot/version/HFI
handshake in the same bounded initialization. Preserve the0120 clock receipt
and existing watchdog margin. Stop on unknown ownership/state; do not insert
copy-only or mapping-only device reboots. ZAP authentication remains at its
native later GPU AWARE/GX/SMMU/SQE/CP_INIT point.
