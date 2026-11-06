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
source-bound inference from the count;0129 did not log the actual readback.

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
with both versions. The complete0130 native kernel/image then booted once:
SMMU again completed131 mapped pages/140 ATOS checks, and its cached rejected
comparison was phase0/check1/windowAO/byte offset0x1034, full mask, requested0,
actual0x82204514. Only five stores completed; no TCM copy, reset release or
firmware execution. The full success verifier rejected the trial, as required.

The native mapping independently gives the same physical0x03d8d034: GMU
resource0x03d6a000 plus raw RSCC byte offset0x23000 plus register word0xd*4.
Native initialization writes zero to all three HIDDEN_TCS_CMDn_ADDR registers
(words0xd/0xf/0x11) without checking equality. Neither the pinned definitions
nor upstream v6.12 XML establishes their per-bit readback semantics. The
physical mismatch alone does not prove an unsuccessful write or justify an
invented mask. The next candidate will use the native fixed-write policy for
only those three addresses, record their existing readbacks as equality
unqualified, and retain all-ones/IO/guard refusals plus every other store,
TCM, reset, fault and firmware ACK check. This is a bounded experiment, not
hardware qualification of those fields or proof of firmware/GPU operation.

Patch0131 implements that narrow policy at AO offsets0x1034/0x103c/0x1044.
Each still performs exactly one guarded zero write, barrier and guarded read
at the same position in the native sequence. A failed callback, guard or
all-ones read refuses the transaction. Other values are cached privately and
do not establish bitwise write completion; all other registers keep the
original comparison. Successful samples emit `SWEET GMU FW IMPL` only after
the transaction completes or, on failure, after shared-owner/watchdog
quarantine. A later failure may produce a partial set; full success requires
all three distinct addresses plus the original FW-result/INIT/version ACKs.
The public success receipt, firmware asset, TCM copy/readback, write order,
deadlines, IRQ/reset/GX/fault guards and one-shot lifecycle are unchanged.

Host coverage injects the physical0130 value0x82204514 at the first address
and explicitly synthetic nonzero values at the other two, exercises each
all-ones refusal before copy/release, and checks cached samples survive repeat
entry. Non-exempt DATA readback and OOB-clear failures remain negative tests.
The board seam covers full and partial cache logging after quarantine; actual
engine sequencing is checked separately. Host success cannot qualify the
physical meaning of these values or the next firmware operation.

Physical0131 completes the RSC and sequence-memory stores, then stops at
store27 before any firmware copy or reset release: PDC window offset0x15d4,
physical0x0b2955d4, TCS1 CMD0 MSGID. Requested0x00010108 reads0x00010100.
The three cached hidden-address reads are0x82204514/0x82204510/0x82204520;
their bitwise effects remain unqualified. The full verifier rejects the run.

Pinned `rpmh-rsc.c` defines WRITE at bit16 and RESP_REQ at bit8, while the
native GPU PDC sequence writes0x10108 to its six MSGID words. The observed
PDC value preserves both named control bits. Generic RPMh/BCM registers are
distinct and do echo the original length value; their checks stay intact.
The next candidate will preserve the native PDC write and read order, check
only the documented WRITE/RESP_REQ mask0x10100, retain all-ones/IO/guard
refusals and cache full raw samples. Other bits remain explicitly unqualified;
this does not establish read-only length semantics or successful PDC command
execution. All other PDC stores and later firmware completion checks remain.

Patch0132 applies this to only TCS1/TCS3 CMD0–2 MSGIDs, at PDC byte offsets
0x15d4/0x15e4/0x15f4/0x1764/0x1774/0x1784. Each retains its native0x10108
write, barrier and guarded read. `GMF_PDC_MSGID_FIELDS` names bits16/8;
missing either is READBACK refusal with the checked mask, while all-ones is
still a full-width refusal. A private six-value cache emits raw
`SWEET GMU PDC MSGID` records after completion or quarantine. Those records
state which bits were checked and explicitly leave other bits unqualified;
they never prove length-field semantics or actual PDC transaction execution.
The public receipt, other register comparisons and generic BCM path remain.
Host coverage models the physical0x10100 value, synthetic unrelated bits, all
six slots with each missing control bit/all-ones, repeat/output preservation,
partial cache logging and the original failure at every I/O boundary.

Physical0132 completes all six MSGID checks with raw0x10100, then copies and
compares all8192 firmware words under reset. Register store51 refuses the AO
HOST_INTERRUPT_MASK at byte offset0x2c18/PA0x03d8ec18: requested0xffffffff,
actual0x3f. No reset release, firmware execution or ACK occurred. The full
verifier correctly rejects the run; PDC execution and other field semantics
are still unqualified despite completing its programming sequence.

Pinned `kgsl_gmu.h` defines five AO sources at bits0/1/3/4/5 (union0x3b), all
set in the observed mask. The next candidate will keep the full native mask
write and existing I/O, check all five named mask bits, cache the raw value
and mark other bits unqualified. The observation does not establish the
implemented register width or read-only behavior. Full0xffffffff readback is
also valid for this requested mask; the separate CSR mask and other register
guards retain their existing checks. Actual firmware completion remains the
required later evidence.

Patch0133 changes only the AO mask word's comparison. It keeps the full
0xffffffff write and the existing guarded write/barrier/read sequence,
requires all five named bits in `GMF_AO_IRQ_FIELDS` (0x3b), and caches the raw
sample privately. `SWEET GMU AO MASK` records follow the six PDC records after
completion or quarantine, explicitly leaving other bits unqualified. A full
0xffffffff read remains valid for the requested mask, preserving the earlier
behavior. The CSR mask, status/fault checks, GIC delivery policy, deadlines,
one-shot lifetime, public receipt and later FW/INIT/version checks remain.
Host cases include physical0x3f,0x3b, the full mask and explicitly synthetic
other bits, plus each named mask bit missing and zero. Rejections occur after
the required copy but before reset release; repeat/output/cache preservation
and the original I/O-boundary coverage remain required.
