# A619 firmware asset and bootstrap

The packer, native asset reader, bounded bootstrap engine, physical callback
adapter and opt-in coordinator are implemented. Host controller seams exercise
the engine and actual HFI rings. Physical0138 now qualifies fresh GMU firmware
execution and INIT/version replies; GPU command execution remains unqualified.
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
   ACK type2, a bounded3/4-word required prefix within19 received words and
   matching12-bit request sequence. Other echo bits and extra payload remain
   unqualified. INIT rejects the native
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
Software timeouts cannot cancel hung fabric IO. The full0138 kernel/image and
one coherent temporary-boot trial qualify this bootstrap stage only.

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

Physical0133 passes the AO named-source check with raw0x3f, then stops at
store59: CSR offset0x20b4/PA0x03d7e0b4, CM3_CFG requested0x4052 reads0x52.
The full TCM copy/readback remains8192 words, with reset1/release0 and no
firmware execution or ACKs. Full success remains rejected.

The native initialization comment requires restoring CM3 configuration before
boot to avoid entering its NMI handler. Pinned `adreno.c` defines the NMI bit
as9 and sets it to send an NMI; the physical0x52 has this bit clear. The next
candidate will keep native0x4052 at this word only, retain guarded I/O and
all-ones refusal, and explicitly verify NMI clear. Other fields, including
the differing bit14, remain unqualified. No inferred bit14 mask or read-only
semantics is justified; actual firmware result and ACKs remain mandatory.

Patch0134 keeps the fixed0x4052 write and existing guarded I/O for CM3_CFG
only. It checks documented NMI bit9 clear (`GMF_CM3_NMI`,0x200), refuses an
all-ones read, and privately caches the complete raw value. Its record follows
the AO mask record after completion or quarantine, identifying only the
NMI-clear check and explicitly leaving other fields unqualified. All other
configuration comparisons, reset/GX/IRQ/fault/budget guards and the public
receipt remain unchanged. Host cases include physical0x52, original0x4052,
synthetic other bits, NMI set and all-ones; refusals preserve output/cache and
occur before reset release. Native fixed-write order is checked separately
against the frozen original model; software success is not firmware proof.

Physical0134 passes the NMI-clear check with CM3_CFG raw0x52, then stops at
store62: CSR offset0x1000/PA0x03d7d000, native GMU_ICACHE_CONFIG word0x1f400,
requested1/read0. Complete TCM copy/readback remains8192 words; reset1,
release0, no firmware execution or ACKs. Full success remains rejected.

The pinned native `a6xx_gmu_power_config` writes SYS_BUS_CONFIG1 first,
then ICACHE_CONFIG1 and DCACHE_CONFIG1. Current0134 has those three writes
in cache/cache/bus order. This source-order difference is established; its
causal role in the zero readback is unproven. The next candidate should
restore bus/instruction-cache/data-cache order while retaining every
full-width readback comparison, value and guard. There is no evidence for
self-clearing or read-only cache-bit semantics, and a zero read must still
refuse before reset release. Only actual firmware-result/ACK evidence can
qualify the later execution stage.

Patch0135 restores only that three-write order: SYS_BUS_CONFIG, then ICACHE
and DCACHE, each with the original fixed1 value and unchanged guarded
write/barrier/read/full-width comparison. It adds no MMIO, retry or relaxed
comparison. Host coverage checks this native order before reset release,
each zero/other/all-ones read, each ignored write, output/repeat preservation
and the existing failure at every I/O callback. A separate frozen original
fixture compares all1,009,420 requests against0134: the only difference is
the predicted CSR address rotation across those three stores/reads. This is
source fidelity and software validation; no0135 physical result exists yet,
and the reason0134 read zero remains unproven.

Physical0135 stops at the first entry in the restored native sequence:
store62, SYS_BUS_CONFIG word0x1f40f, CSR offset0x103c/PA0x03d7d03c,
requested1/read0. ICACHE/DCACHE have not yet been attempted in that run.
Complete8192-word copy/readback, CM3 NMI-clear, PDC/AO and SMMU checks pass;
reset stays1/release0, with no firmware execution or ACKs. Restoring native
order alone therefore does not resolve the non-echoing configuration read.

The pinned native driver issues these three fixed1 writes without equality
verification. That is a native programming protocol, not documentation that
the fields are read-only, self-clearing or accepted on this device. A later
narrow experiment can preserve the same writes/order/guards and existing raw
reads, reject all-ones/IO failures, and record the entire values as explicitly
unqualified instead of inventing per-bit masks. Such records cannot prove
write acceptance or cache state. Actual fresh firmware-result and INIT/version
replies remain the required execution evidence; all other control/fault/
IRQ/reset/deadline checks must remain intact. No0136 candidate exists yet.

Patch0136 applies that native protocol only to SYS_BUS_CONFIG, ICACHE_CONFIG
and DCACHE_CONFIG, in0135 order. The fixed1 writes and existing guarded
write/barrier/read calls stay identical. Each non-all-ones raw read is cached
privately, with no invented field mask or claim of write acceptance/cache
state; all-ones remains a full-width refusal. Other registers' comparisons,
reset/GX/IRQ/fault/deadline guards and the public success receipt stay intact.
Three `SWEET GMU BOOT CFG` records follow the CM3 record after completion or
quarantine, in byte-offset order0x103c/0x1000/0x1004, requested1 and equality
explicitly unqualified. No diagnostic performs extra MMIO or a retry.

Host cases retain native order and cover raw0/1/synthetic other bits, each
all-ones slot, partial raw-cache preservation and output/repeat behavior.
An ignored write is explicitly an unqualified observation, distinct from a
failed I/O callback; all original callback failures still refuse. Separately,
zero observations plus missing fresh firmware result or missing INIT ACK
must fail. Mock replies and board callback seams remain software evidence;
only a real boot's fresh result and INIT/version replies can qualify the
execution stage. No0136 hardware evidence exists yet.

Physical0136 first reaches fresh GMU firmware execution: the cached native
FW_INIT_RESULT is0xbabeface after its mandatory zero-clear and owned reset
release. The final reset read is0 and GX_GDSCR is0xf8222000 (power-on bit set).
The pinned engine then reaches HANDSHAKE, which requires successful fresh
boot-slumber ACK/clear and HFI-ready polling first. Those latter transitions
are source-bound passed paths, whereas BABEFACE/reset/GX are directly logged.
All three boot-config raw reads are0; their bit semantics and cache/buffer
state remain unqualified. Earlier SMMU/TCM/PDC/AO/CM3 checks still pass.

The run stops at phase5/GMF_ACK, writes80/polls4, copied/compared8192,
reported version0. No packet payload is captured, so neither the failed
request nor the type/size/echo/status reason is established. A queued packet
while draining before or after INIT can also produce that result. INIT
transmission/validation is unknown; the complete INIT/version handshake
remains rejected. This is GMU CM3 firmware execution evidence, without GPU
command execution, normal HFI_ON/DCVS/ZAP or Metal qualification.

The next diagnostic candidate should cache the first rejected packet already
returned by the ring helper, covering both drain and request refusal paths,
and log its site/reason, queue, expected request and bounded raw words after
quarantine. It must preserve acceptance/refusal behavior, all guards, I/O
order and the public success receipt. A real captured packet, rather than
an inferred protocol mismatch, should determine the following fix.

Patch0137 adds only private rejected-packet diagnostics. It preserves every
acceptance/refusal rule, initialization value, ring operation and I/O order.
The first `GMF_ACK` refusal caches phase, drain/request site, reason, queue,
request header, expected ACK words and the already-read packet (at most19
words). The request header at a drain site identifies the upcoming request;
it does not claim that request was sent. Size/echo/status/version-status,
unexpected queued ACK/message and the16-debug budget have distinct reasons.
A drain budget exhausted without receiving a packet records zero words.
No raw reads or retries are added; successful ACKs never become refusal
diagnostics. Cache clearing occurs only after the first successful claim,
and repeated calls preserve the cached failure and caller output.

`SWEET GMU HFI REPLY` and indexed `SWEET GMU HFI WORD` records are emitted
only after the board and watchdog lease are quarantined, following the
existing boot-config records. The public success receipt stays unchanged.
Host models cover both sites/queues, each reason, short/max19/no-packet bounds,
and a valid INIT followed by a refused queued message before VERSION. That
last case demonstrates why phase5/GMF_ACK alone does not identify INIT as the
failed command. A full physical0137 trial is still needed to capture the real
packet; no new packet type or relaxed ACK policy is introduced here.

Physical0137 captures the refusal in the request path for INIT sequence1:
the ACK has type2 and4 words, whereas the port expects exactly3. Its echoed
request retains sequence1 but omits length/type fields, and its status word
is0. The remaining word is opaque and unqualified. Fresh BABEFACE/GX-on and
the earlier initialization checks repeat. The current port still rejects
before accepting INIT or sending VERSION; full handshake qualification is
unchanged. Fixing only the length check would expose the full-header echo
comparison as another refusal for this same packet.

The pinned native `receive_ack_cmd` matches only the12-bit sequence and
copies the message's header-reported length. Its INIT generic request treats
status0 as success (only0xffffffff is failure), and its version request
requires status0 before reading the version field. It does not require the
complete echoed header or compare command ID. The next candidate should
follow that correlation rule while retaining explicit bounded lengths:
at least3 words for INIT or4 for VERSION, no more than the existing19-word
ring capacity, and copy only the required public receipt prefix. Extra
fields and other echo bits stay unqualified. Type/status/version and all
ring/guard/reset/deadline/copy checks remain required. Real complete INIT and
VERSION replies must then be observed; this analysis does not retroactively
turn0137 into a successful handshake.

Patch0138 changes only request ACK length and echo correlation. It accepts
a bounded prefix: INIT needs at least3 words and VERSION at least4, with the
existing19-word complete-packet capacity retained. It matches only the
echoed12-bit sequence (`0xfff00000`), following the pinned native matcher.
Other echoed fields and any additional payload stay unqualified. Only the
existing3/4-word receipt prefix is copied; public receipt layout is unchanged.
ACK type2, INIT status other than0xffffffff, VERSION status0 and the existing
reported-version compatibility check remain mandatory. Ring inspection,
guard/fault/reset/deadline/one-shot behavior and native initialization stay.
The cached SIZE reason now describes a short required prefix; ECHO describes
sequence mismatch. Failed packet diagnostics still emit only after quarantine.

Host cases use the captured INIT4/sequence-only/status0 shape with a synthetic
opaque tail, all3..19/4..19 lengths, original full echoes and synthetic other
echo bits. Short/oversized packets, corrupt queues, wrong sequences/types/
statuses and missing version data refuse with unchanged caller output.
Tests also check that an extra INIT word cannot spill into the VERSION
receipt, and retain full19-word refused-packet diagnostics using a sequence
failure. This is protocol compatibility and software validation; physical
complete INIT and VERSION replies are still required for0138.

## Physical0138: firmware and INIT/version handshake qualified

One temporary0138 boot used the independently reviewed19546112-byte image
SHA256 `0550c64cc5e0e9c67282384de63f44380f8b97315645e3bfba8f9e2c04fe5a5a`,
kernel `xnu-f19772512a1d4117b143ce75e7c2cd4c`, and unique trial
`gmuf-0138-20261107-a1`. The unchanged strict runtime reader bound the source,
manifest, qualification, image, kernel banner, command line and fresh logs.
Its full technical checks passed. The first report's exit3 recorded pending
manual-reset attribution. The user then confirmed this0138 self-restarted
without manual operation; the unchanged reader produced a separate exit0
report. The original report remains preserved.

The hardware completed all8192 TCM writes/comparisons, fresh0xbabeface,
boot-slumber OOB and HFI-ready transition0->1. Both replies were accepted:
INIT header announces4 words, sequence1/status0; VERSION announces4 words,
sequence2/status0 and reports0x10110000. Only the required public receipt
prefixes are retained; the extra INIT payload remains unqualified. Source-
bound guards,131 SMMU mappings/140 ATOS checks, clock and CX/controller stages
also passed. No refused-packet diagnostic was emitted.

The observer ran2026-11-06T22:56:28.482093Z to22:58:40.256573Z and observed
recovery after130s. This includes boot, logging and recovery; it does not
independently establish a PMIC reset cause. The coordinator deliberately
awaits its diagnostic watchdog after completing the handshake. Explicit user
attribution qualifies autonomous diagnostic runtime reset; this run adds no
user confirmation of UI, touch or daily stability.

Next follow the pinned native legacy `hfi_start` ordering: v1 PERF table,
bandwidth table, then TEST when HFI_USE_REG applies. Derive tables from the
exact device frequency/voltage policy and same-boot CMDDB data before sending
them. Do not mark normal HFI_ON, GPU command execution, ZAP, rendering, Metal
or high refresh as qualified by INIT/version success. Keep the0138 bootstrap
as a reproducible baseline and test each new command's refusal and success
paths before a coherent temporary hardware trial.

## Pure0139 PERF table construction

Fresh recovery reads show six active frequencies, descending800,650,565,430,
355,253MHz. The native `num_pwrlevels` sysfs value6 excludes the off entry.
The live device-tree table whose rows uniquely match that list has speed-bin
property169. This is a table match, not a direct fuse read: the `speed_bin`
sysfs file is absent. In this recovery, `adb exec-out` returned transport exit0
even for the missing file; the audit rejects that error text as a fuse value.

Patch0139 adds `gmf_perf_table_build` as a pure constructor in the firmware
translation unit. It consumes the validated same-boot ARC plan and a nonzero
12-bit sequence. Its172-byte legacy v1 PERF message has43 words: header,
7 GX levels,2 GMU levels,16 fixed-capacity GX pairs and4 CX pairs. Unused
pairs are zero. The off-inclusive ascending GPU curve is:

| MHz | ARC virtual level | GX index | MX index |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 0 |
| 253 | 64 | 1 | 2 |
| 355 | 128 | 2 | 3 |
| 430 | 192 | 3 | 4 |
| 565 | 256 | 4 | 5 |
| 650 | 320 | 5 | 6 |
| 800 | 384 | 6 | 7 |

Each native vote packs virtual level in bits31:16, MX index15:8 and primary
index7:0; frequency is in kHz. The two GMU rows are off and200MHz. The latter
uses native MIN_SVS48, rounded up by the captured CX table to64/index2 and
MX64/index2. These are virtual policy levels, not measured microvolts.
See the pinned [ARC dependency builder](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/kgsl_gmu.c#L640),
[legacy PERF sender](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/kgsl_hfi.c#L439)
and [regulator levels](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/include/dt-bindings/regulator/qcom,rpmh-regulator-levels.h).

Invalid plans/sequences/spans and overlapping input/output refuse before
changing the output. This API sends no HFI packet and changes no controller,
clock, rail, context, receipt or bootstrap sequence. Physical0138 remains the
qualified firmware baseline. A future opt-in PERF transmission must follow
VERSION on the same retained channel, verify its actual bounded native ACK,
and preserve quarantine/deadline/one-shot and default bootstrap behavior.
Bandwidth-table construction and HFI_USE_REG TEST remain subsequent stages;
do not substitute the temporary saturated BOOT BCM votes for native GPU
bandwidth tables or declare normal HFI_ON from this byte constructor.

The initial hand-written test oracle incorrectly used CX's primary indices
for GX. That run was rejected and retained; six oracle literals were corrected
without changing the production source. An independent test then compiled the
exact pinned native ARC dependency helper, v1 PERF sender and wire structs,
stubbing only the send seam. All4095 permitted sequence packets matched the
new constructor byte-for-byte. All61 host suites, original bootstrap I/O
equivalence and real ARM64 firmware/board compilation passed. This qualifies
byte construction only;0139 has no full kernel/image or hardware PERF trial.
