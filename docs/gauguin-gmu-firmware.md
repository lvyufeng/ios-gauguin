# A619 firmware asset and bootstrap

The packer, native asset reader and bounded bootstrap engine are implemented.
The engine runs against host controller seams and the actual HFI ring code;
physical firmware execution is still unqualified. There is no new boot hook.
The next integration must bind it to the retained0122 board owner, not create
aliases of that owner's CSR, SMMU or low-memory mappings.

Primary sources are the fixed gauguin kernel commit
[19b63c8192b1c9b7c4d931d7d3be92024bc2d778](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/tree/19b63c8192b1c9b7c4d931d7d3be92024bc2d778),
particularly adreno_a6xx_gmu.c, a6xx_reg.h, adreno.h, adreno-gpulist.h and
kgsl_gmu/core/hfi headers and implementation. No generic A640 block-stream
firmware loader or generic OOB numbering is used for this A619 legacy target.

## Pinned data asset

`tools/mkpayload.py --gmu-firmware FILE` appends exactly32768 bytes with SHA256
`9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e`.
The ADT entry `/chosen/memory-map/A619GMUFirmware` is two little-endian64-bit
values: physical address and32768-byte length. Two16KiB pages are reserved
above earlier ramdisk/Novatek/MDT assets. All topOfKernelData reports and the
optional low-PAS pending tail include the new extent. The default path is
unchanged, and a size/hash mismatch leaves an existing CLI output intact.

The native asset reader revalidates boot_args, actual DRAM/top/kernel bounds,
descriptor alignment/length, contiguous direct-map endpoints and fresh native
SHA256. It returns a const data view only; no mapping, TCM access, allocation,
reset release, secure authentication or execution occurs. This asset remains
private and is not added to Git. Public tests use synthetic data and real
platform SHA256, with only the temporary host expected pin changed. Additional
local tests use the actual captured asset and unmodified production pin.

## Native bootstrap engine

Before hardware writes, verify the supplied pinned asset view and cold inherited
state. The plan must come from four entries of the already published immutable
same-boot CMDDB snapshot, in cx/mx/gfx/xo order. The new read-only exporter does
not recapture or map anything. Plan policy independently requires the exact
native resource addresses and legal tables; upper-envelope GX/MX selectors7/7
are a bounded bring-up policy, not measured voltage or a daily power policy.

The sequence follows the native cold path:

1. Hold CM3 reset while setting TCM retention, programming the five-word RSC
   and PDC sequences, native sleep/wake TCS1/3 commands and PDC enable/start.
2. Copy and compare all8192 words of the whole legacy asset through AHB. Check
   the actual five TCM metadata words, bind the freshly emitted legacy HFI
   table, mask host delivery and clear inherited status under reset.
3. Configure native TCM_BOOT=2, queue/log IOVAs, fence range0x80a008a0, CM3_CFG
   0x4052, compressed chip ID0x06019000 and cumulative native IFPC/SPTP/RPMh
   controls. Clear GBIF halt at03d0f114; A619 has GBIF despite being615_family.
4. Release reset once and require fresh0xbabeface firmware completion. Issue
   A619 boot-slumber OOB: HOST2GMU bit22, fresh GMU2HOST bit30, then clear ACK.
5. Start HFI, send the native INIT request with dump IOVA60006000/size4000/
   cold-state1, then query GMU1.11. Consume actual ring packets, require v1
   ACK type2 and an exact echoed request header. INIT rejects the native
   0xffffffff error sentinel; version status must be zero and report major1,
   minor>=11. Bounded known debug messages may be drained; errors/stale ACKs,
   corrupt queues, wrong echoes, timeouts or lost guards stop permanently.

The exact pinned legacy image plus native family rules select the legacy
transport; zero metadata alone is not proof. Actual firmware completion and
matching replies are required to qualify execution when this runs on hardware.
No DCVS/BW tables, TEST, normal HFI_ON, SQE/CP commands, ZAP or Metal readiness
are claimed by this bootstrap result. Those remain required later stages.

## Board adapter still required

| Engine window | Mapping base/bytes | Ownership |
| --- | --- | --- |
| CSR | 03d7c000 / 4000 | Reuse0122 reset owner |
| AO and RSC | 03d8c000 / 4000 | New narrow owner |
| PDC config | 0b294000 / 4000 | New narrow owner |
| PDC sequence | 0b490000 / 4000 | New narrow owner |
| TCM | 03d6c000 / c000 | New narrow owner; asset starts at+1000 |
| GBIF | 03d0c000 / 4000 | New narrow owner |
| HFI shared RAM | owner+8c000 / 8000 CPU reservation | Reuse0122 NC owner |

Callbacks must enforce fresh deadlines/WDT, same-boot clocks/CX/SMMU ownership,
phase-specific reset/GX predicates, fault checks and masked NS IRQ delivery.
Before GX power, also check the GPU core IRQ INTID332 (word10 bit12), beyond
0122's existing GMU/SMMU masks. The old reset1/GX-off guard cannot be reused
after an owned reset release or GX request. Capture uncertainty before a store
and quarantine on failure; no retry, rollback or watchdog pet. Software timeouts
cannot cancel hung fabric IO. Integrate and validate these callbacks and the
coordinator before building one coherent temporary-boot trial.
