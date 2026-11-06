# A619 firmware asset and bootstrap

The packer, native asset reader, bounded bootstrap engine, physical callback
adapter and opt-in coordinator are implemented. Host controller seams exercise
the engine and actual HFI rings; physical firmware execution remains unqualified.
The adapter reuses the retained0122 board owner's CSR, SMMU and low-memory
mappings without exporting pointers or creating aliases.

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

## Physical adapter and opt-in coordinator

| Engine window | Mapping base/bytes | Ownership |
| --- | --- | --- |
| CSR | 03d7c000 / 4000 | Reuse0122 reset owner |
| AO and RSC | 03d8c000 / 4000 | New narrow owner |
| PDC config | 0b294000 / 4000 | New narrow owner |
| PDC sequence | 0b490000 / 4000 | New narrow owner |
| TCM | 03d6c000 / c000 | New narrow owner; asset starts at+1000 |
| GBIF | 03d0c000 / 4000 | New narrow owner |
| HFI shared RAM | owner+8c000 / 8000 CPU reservation | Reuse0122 NC owner |

The physical adapter remains inside the sole board-owner translation unit.
It invokes the cold SMMU transaction, retains its actual NC image and private
CSR/SMMU mappings, then maps only the five new apertures above. An additional
eight-second CPU deadline and initial13s WDT margin are fresh observations;
the hardware watchdog is never rearmed or petted. Per-access live guards keep
at least3s, check thread context, current fixed clocks/CX, masked NS IRQs and
owned SMMU global/CB fault, route, TTBR, TCR, MAIR and context controls. GPU core
INTID332 (word10 bit12) is checked before SMMU mapping and throughout bootstrap.

Reset-release and GX-request intent are latched before their single stores.
Before release, CM3 reset must remain1; after our release it must remain0.
GX power/branch transitions are allowed only after our own boot-slumber OOB
store. The old quiet clock helper keeps its stricter behavior for cold users.
Firmware copy writes only TCM[1000,9000), rechecks guards around each1KiB chunk,
and compares all8192 words. HFI uses the original NC reservation without a new
alias. Failure quarantines both owners and the shared lease before synchronous
logs; partial issued/compared counts are diagnostic evidence, not success.

`sweetgmufw=1` requires `sweetgmuclk=1`, `sweetcxpower=1` and the existing BCM/
PAS CPU-stage prerequisites, with PAS INIT/MEM disabled. Default0 calls no new
firmware APIs. The coordinator validates the exact same-boot ARC plan and
pinned asset before watchdog/RSC writes, then serializes BCM, ARC, CX, clocks,
SMMU and firmware bootstrap. A fresh native reader revalidates the asset again
before loading it. Success logs raw SMMU identity, TCM metadata, copy counts,
firmware result, INIT/version replies and reset/GX/IRQ observations, and awaits
the diagnostic watchdog reset. Failure consumes no poisoned receipt and never
retries. Host typed board models do not constitute physical firmware ACKs.
Software timeouts cannot cancel hung fabric IO. A full kernel/image and one
coherent temporary-boot trial still require qualification.

## First physical firmware-stage refusal and cached comparisons

The real0129 trial completed cold SMMU setup and reached all five firmware
apertures. It stopped with GMF_READBACK in RESET phase after5 stores and no
poll, TCM copy, reset release or OOB request. The raw context FSR words were
both0x400, with no named fault flag. No firmware result or HFI reply was obtained.
The full runtime verifier rejected this trial; cold SMMU stage evidence does
not establish firmware or GPU execution.

The frozen instruction order infers the fifth store as AO byte offset0x1034,
physical0x03d8d034, RSC HIDDEN_TCS_CMD0_ADDR, requested0. That offset/value is
source-bound inference from the count; the actual readback is still unknown.

Patch0130 caches the existing rejected comparison. Its private sample records
validity, phase, check, mapping window, byte offset, mask, expected and actual.
Check1 is the full-width store readback; check2 is the existing OOB-clear bit30
check. Validity distinguishes a RESET-phase sample from an absent sample.
The public success receipt and every comparison/callback remain unchanged.
`SWEET GMU FW READBACK` logs the cache after owner/watchdog quarantine and
the existing partial-work rows. No diagnostic MMIO or retry is added. Repeat
entry preserves the first sample. Synthetic12340000 fixtures are formatting
tests and must never be reported as the physical0129 readback.

Source0130 passes the full host suite and native firmware/board compilation.
The frozen original0129 model produces identical I/O request counts and digests
with both versions. A complete0130 kernel/image and coherent physical trial
are still required to capture the real rejected value and continue debugging.
