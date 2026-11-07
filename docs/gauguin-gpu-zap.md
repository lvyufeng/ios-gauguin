# A619 signed ZAP loader

Trial157 completed the first same-boot signed ZAP load after native GPU
ME_INIT/WHERE_AM_I completion. PAS13 INIT_IMAGE, MEM_SETUP4096 and AUTH_AND_RESET
all returned full64 transport/service zero. The owner copied and compared
exactly1984 bytes of the pinned b02 segment between MEM and AUTH. The phone
returned automatically to TWRP after131 seconds. This establishes the signed
load; unsecured-mode commands, rendering, Metal and high-refresh operation
remain unfinished.

The kernel was built locally with8 jobs from source157,5300 files and151
patches, then independently qualified and packaged. The trial used build ID
`xnu-4968d149ca024346ad2972681e7448a1` and marker `gzap-0157-a1`.
The actual606-byte command was decoded and checked in the boot image. It
replaces explicit `sweetpasinit=0` with `sweetgpuzap=1`; the omitted legacy
INIT flag defaults to0 in the qualified source and tested callers. All other
controls remain the same as154. No flash, format or partition-table change
was used.

The physical receipts were:

| Stage | Observed result |
| --- | --- |
| First CP initialization |15 native command words; device-written shadow RPTR15; busy bit23 clear |
| INIT_IMAGE |1 fresh attempt,5 SMC calls,4 continuations; final x0/x1 zero |
| MEM_SETUP |1 fresh attempt,1 call; span4096; x0/x1 zero, returned x4=4096 |
| Segment copy |1984 bytes written and1984 compared through the retained owner alias |
| AUTH_AND_RESET |1 fresh attempt,1 call; x0/x1 zero |
| Final owner/guard |owner8, phase7 complete, reason0; LATE scope2/FINAL phase6 |

The final guard interval was about0.119 seconds at the recorded19.2MHz CPU
timebase, including guards and logging; it is not a performance benchmark.
No GPU register or secure-buffer read followed AUTH0. The reported LIVE
values are cached pre-AUTH observations. Root mount, launchd, SpringBoard and
backboardd markers and3 framebuffer swaps were also observed. The user was
away, so this run supplies no new human screen or touch observation.

The strict runtime reader retained the prior clock/CMDDB/watchdog/BCM/CX/
SMMU/firmware/HFI/PERF/BW/TEST/DCVS/GPU-context/aperture/core/CP checks and added
signed-load identity, source, raw7, count, descriptor, owner, copy, ordering and
deadline checks. Its fixtures passed4 clock acceptances/95 refusals,
132 firmware acceptances/515 refusals,45 retained full-trace acceptances/678
refusals and20 additional signed-load acceptances/117 refusals. The physical
reader passed with the original text exactly matching the captured binary
decode, no console-framing recovery and all inputs unchanged. Raw device
logs, firmware and build products remain outside Git.

## Source and ownership contract

Patch0155 adds the optional immutable b02 source asset. `--zap-code` creates
an `A615ZapCode` raw1984-byte descriptor with16KiB reserved extent and14400
zero padding bytes. It appends after NVT, MDT, GMU and SQE and updates top/PAS
accounting. `sweet_gpu_zap_asset_view` checks the fixed hash, padding, direct-map
endpoints, five-descriptor layout and pairwise overlaps. The source stays in
the high DRAM bank, disjoint from any permitted below-4GiB PAS allocation.
The view performs no loading or allocation.

Patch0156 supplies the fixed `gpz_start_once` engine: three native frames,
serialized owner actions, copy receipts, continuation/BUSY handling and
terminal quarantine. A caller PA is only a comparison key, never authority
or a pointer setter. Continuations preserve all seven registers, with no
logging, sleep, GPU access or secure-buffer inspection inside the chain.
Full64 transport/service zero is required. Diagnostic limits are20s overall,
5s per transaction,2s for copy,1s for seal/final,68 fresh attempts and8 total
continuations per transaction. These limits cannot cancel a nonreturning SMC.

Patch0157 binds that engine to the actual private CLAIMED owner, retained
mapping and same-boot CP/core/firmware completion. Original MDT bytes and
zero tail are checked before INIT_ENTER only. Later owner checks validate
phase-aware geometry and private engine receipts without rehashing or
restaging the metadata. The owner writes and compares exactly1984 bytes in
64-byte batches, with no tail clear or new alias. Board guards include time
checks inside nested copy callbacks. Secure and late scopes exclude GPU and
low-buffer reads. Failure quarantines shared owners before cached diagnostics;
mappings and requests remain retained, without cleanup or retry.

The coordinator preflights b02 before watchdog/RSC writes and dispatches only
after successful CP completion under the separate opt-in. Legacy standalone
INIT/MEM behavior and its original MDT validator remain independent. Their
incompatibility with concurrent CX/GPU use is resolved by this separate owner
path, rather than changing their meaning.

Source validation passed all3 changed ARM64 translation units,530 real-owner
cases using captured firmware/real SHA256/guard pages,444 coordinator cases,
237 new board cases running actual CP/ZAP engines under typed hardware seams,
and all75 host files. The engine also passed130 host cases and native-frame
comparisons against3 unchanged original PIL function bodies. Firmware-asset
validation includes84 real-SHA256 consumer cases,64 layout combinations,
128 exact pre155-compatibility comparisons and the actual shim loader path.
These source/model results are distinct from the157 physical receipts above.

## Native reference and next transition

The primary reference is LineageOS/android_kernel_xiaomi_gauguin commit
`19b63c8192b1c9b7c4d931d7d3be92024bc2d778`. Its native sequence is CP_INIT,
`a6xx_zap_load`, unsecured-mode submission, then post_start. ZAP loading calls
`subsystem_get("a615_zap")` and propagates failure. The real recovery DT selects
trusted PIL PAS13. The PIL loader orders INIT_IMAGE, MEM_SETUP, segment loading
and AUTH_AND_RESET.

| Item | Exact scope |
| --- | --- |
| MDT |6860 bytes, b00+b01 packed metadata |
| Loadable segment |b02 only,1984 bytes, relocated destination offset0 |
| Segment BSS |0 bytes; no tail-clearing operation |
| MEM_SETUP span |4096 bytes, distinct from the1MiB reserved allocation |
| INIT fresh x0..x6 |42000201,82,13,actual-owner-PA,0,0,0 |
| MEM fresh x0..x6 |42000202,3,13,same-owner-PA,1000,0,0 |
| AUTH fresh x0..x6 |42000205,1,13,0,0,0,0 |

Frame values above are hexadecimal. The b02 SHA256 is
`61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878`.
Do not reload MDT between calls, load the whole ELF, clear4096/16384 bytes or
access the secure region after AUTH merely because a CPU alias remains.

Patch0158 implements the fixed post-ZAP command-append engine. From native
`adreno_switch_to_unsecure_mode`, `cp_secure_mode` and
`adreno_ringbuffer_submit_spin`, it appends these5 words at RB0 DW15..19:

```
70e60001 00000000 70620002 fc010000 00000000
```

The new WPTR is20. The engine first seals provider authority, checks existing
WPTR/shadow15, idle/fault state, the15-word bootstrap prefix and the5 unused
slots. It writes and compares only the5 new words, preserves the rest of the
ring and scratch, then follows native keepalive/fenced-WPTR/counter/idle order.
Only WPTR and keepalive registers are writable. Completion requires a
device-written shadow20, AO busy bit23 clear and no decoded GPU errors.
Every callback has guards. Failure consumes the attempt, quarantines before
returning and leaves output untouched; it performs no cleanup writes.

The468-case ASan/UBSan model passed every callback failure boundary in the
normal and retry scenarios, ownership refusal, corruption, partial store,
all decoded fault bits, fence/idle exhaustion, nested entry and argument
checks. The actual ARM64 translation unit compiled against the157 native
recipe. The first compile's missing dependency include path was corrected
in a separate helper; source bytes and the failed report were preserved.

An independent fixture executes38 unchanged functions from the pinned native
source, including the full submission/idle path and actual unsecured-mode
functions. All34 earlier function hashes stay identical. It stops the native
bootstrap at the ZAP seam, sets the native `zap_loaded` field explicitly in
the fixture, then executes the next native functions. This seam is model
input, not new secure-authentication evidence. Five successful native traces
match the port byte-for-byte: normal, one dropped fenced write with delayed
shadow/busy,100 and199 dropped writes, and counter overflow. Native fenced-write
exhaustion is checked independently. These prove source/model sequencing;
159 supplies the separate live binding and physical command evidence below.

Patch0159 binds the append to the actual private same-boot signed-load receipt
and retained CP/core/firmware state. A separate read-only owner predicate
requires AUTH_DONE and validated private geometry, without rehashing or reading
the secure region. A new live stage checks private successful INIT/MEM/AUTH
receipts, sealed state, mappings, routes, clock, IRQ, reset, faults, watchdog
and monotonic4s total/2s phase deadlines. It preserves the signed loader's
SECURE/LATE rules; only the separately authorized stage may resume GPU/RB
access. All shared owners are quarantined before cached failure diagnostics.

The command contract now accepts exact `sweetgpuzap=0/1/2`:0 disables the
loader,1 keeps157's signed-only behavior and2 adds the native append after
this boot's successful signed load. Other values are rejected. The proposed
159 trial uses `gusr-0159-a1` and the same606-byte command length. Packaging
decoded and compared the complete command before the physical boot.

All3 changed ARM64 translation units pass. Actual-owner tests pass532 cases,
including all64 page attributes and a PROT_NONE secure buffer through AUTH
and the new predicate. The coordinator passes470 cases, retaining all444
old cases and adding26 mode2/order/failure cases. The actual CP/ZAP/GGU engines
run together in217 new board cases, with the secure region PROT_NONE during
the new stage; old board cases remain. Those checks cover21 injected faults
in each phase, private-receipt failures, partial stores/readback corruption,
fence exhaustion, deadlines, default/invalid modes and once semantics.
All76 host files pass. Two original fixture refusals are preserved: one lacked
the new failed-helper quarantine branch, and one injected an ACK bit into a
software cache that the driver refreshed. Separate corrected versions extend
only the exact new legal branch and inject the actual register respectively.
No native-source change or acceptance-rule waiver was needed for those fixes.

The complete159 kernel passed the local build and artifact qualification,
followed by independent image review. Strict runtime fixtures retain the old
clock, firmware, full-trace and signed-load checks and add21 accepted native
append cases and150 refusals, including invalid command-mode combinations.
The original pre-test wrapper's stale input reference and its separately
corrected version are preserved.

One temporary159 image was booted on2026-11-07 at10:08:31 UTC. It returned
automatically to TWRP after131 seconds. The source-bound reader accepted the
fresh matching kernel banner, complete CP/signed-load receipts and separate
native command completion:

| Stage | Observed result |
| --- | --- |
| Entry | Same-boot signed-load authority sealed; existing WPTR/shadow15 |
| Append | Exactly5 words written/compared at DW15..19;15-word prefix preserved |
| Submit | WPTR20; one fence check, status0; keepalive set/clear recorded |
| Completion | Device-written shadow20; one idle poll; AO busy bit23 clear |
| Fault/guard | RBBM/CP errors0; final guard reason0, phase6 |
| Ownership | Requests/mappings retained; no secure-buffer read or ring reinitialization |

The guarded stage took about0.04723 seconds at the recorded19.2MHz CPU
timebase, including logging; this is not a performance benchmark. The raw
text exactly matches its captured binary decode, no console-framing recovery
was needed, and all pinned verifier inputs were unchanged. Independent review
rehashed the14 wrapper and18 full-reader inputs. Root, launchd, SpringBoard
and backboardd markers and4 framebuffer swaps were recorded; the user was
away, so this adds no human screen/touch observation or refresh-rate evidence.

This qualifies source-bound native `SET_SECURE_MODE 0` command completion.
The earlier signed-load receipt's stage-local unsecured-mode flag remains
false; the separate native completion receipt carries this later result.
Ordinary GPU buffer access, shader execution, general scheduling, rendering
and Metal remain separate work. The next step is an ordinary user-RW GPU
buffer and bounded data-path submission derived from the pinned native
driver. Existing privileged scratch writes alone would not establish it.

Patch0160 adds pure constructors for that optional data page. It leaves
the existing18-leaf bootstrap constructor and all live dispatch paths
unchanged. A separate plan reserves16KiB at owner offset `0xb8000`, maps
only its first4KiB at GPU address `0xfc018000`, and keeps the remaining12KiB
unmapped. The page is normal GPU user-RW, noncacheable and nonexecutable;
this describes SMMU permissions, not a CPU userspace mapping. The separate
table emitter copies the legacy layout and adds only L3 entry24, preserving
all old leaves, configuration values, other holes and the empty TTBR1 root.
It constructs inactive table bytes and must never patch live tables.

The fixed command builder emits two native `cp_mem_write` packets to the
page's first and last dwords. An independent fixture executes10 unchanged
functions from the same pinned primary source: the6 earlier protection,
LPAE and CP_INIT functions plus the actual type3, memory-packet, GPU-address
and memory-write helpers. Across144 owner/IAS/OAS combinations all2736 leaf
comparisons match native encoding, and both native calls match all8 command
words. The actual constructor model also checks the full32-bit address space,
padding holes, unchanged18-leaf bytes, overlaps and failure atomicity. These
remain CPU model and ARM64 translation-unit checks, without live table
activation, GPU data writes, shader execution or rendering evidence.

Live integration must explicitly authorize this optional mapping before
GPU startup, verify its NC CPU reservation and all19 translations, and carry
that exact variant through private owner and retained-table guards. The
current bootstrap guards authorize only18 leaves. Only after same-boot signed
load and native-mode completion may a new bounded stage append the two
data writes and native completion marker, verify device writeback and faults,
and compare the page's remaining bytes. The original signed-only and native
mode controls must retain their behavior. No such live binding exists in160.
The fresh154-patch source replay and all77 host files pass. The constructor
model passes1594 cases with4464070 checks, and the actual ARM64 translation
unit compiles on the159 native recipe. No160 full kernel or image was built.

Patch0161 adds the explicit cold `ggs_configure_data_once` API. The original
API always selects18 leaves; pre-seeded context fields or callback output
cannot opt into the extra mapping. The new API validates the complete fixed
data plan, maps19 leaves and tests all three data-padding holes. Together
with all retained GMU and hole checks it requires171 address translations.
An explicit receipt tag distinguishes18/168 from19/171. GPU-start and core
consumers accept only coherent tag/count combinations and retain all their
other checks. The live private board must still authorize and bind the exact
selected layout; a structurally valid receipt alone provides no ownership.
ATOS validates translations and does not replace exact PTE permission checks.

The actual SMMU model passes27153210 assertions including every callback
failure across four controller geometries in both layouts, data and padding
corruption, API mismatch, nested/once and full-plan alias checks. Consumer
models cover both valid shapes and the full tag/page/count refusal matrix.
All4 relevant ARM64 translation units and all77 host files pass on a fresh
155-patch replay. The board does not select this new API yet; no161 kernel,
image, live data mapping, submission or rendering result is claimed.

Patch0162 implements the fixed ordinary-page write/readback engine. It seals
provider authority, checks existing WPTR/shadow20 and the original20 command
words,11 unused ring slots and a zero data page. It appends exactly two native
`cp_mem_write` packets plus `submit_spin`'s WHERE_AM_I marker at DW20..30,
then follows native keepalive, fenced WPTR31, counter and idle checks.
Completion requires device shadow31, no busy/error indication, both new edge
words, all1022 untouched middle dwords, the complete31-word ring image and a
final fault check. It never writes data or scratch from the CPU. Failed
callbacks consume the attempt and quarantine before returning, without
cleanup/retry or output publication. The live provider must separately bind
the actual private signed/native-mode receipt and cold DATA19 mapping.

The actual model passes16202 cases with280360152 assertions, including every
normal/delayed callback boundary, all pre/post data/ring corruption positions,
partial command stores, fake-device corruption, missing writes and timeout,
fault, ownership and argument cases. The ARM64 translation unit compiles.
An independent fixture executes41 unchanged native functions, retaining all
38 previous body hashes and adding the actual memory-packet, memory-write and
post_start functions. Runtime preemption remains disabled and post_start is
a verified no-op. Five complete command/submit/idle traces match the port
byte-for-byte, with fenced-write exhaustion checked separately. The earlier
ZAP seam and device memory publication in this fixture are explicit model
inputs. This raw CP memory path makes no rendering/EOP timestamp claim.
Fresh156-patch replay and all78 host files pass. There is still no live163
board binding, new kernel/image or hardware data-write result.

Patch0163 adds the live binding under explicit `sweetgpuzap=3`. Modes0/1/2
retain their behavior. Mode3 selects DATA19 before cold SMMU activation,
validates and initializes its extra16KiB NC CPU reservation, and binds the
private selected plan, tagged context and completion receipt. A canonical
read-only matcher checks every word of the complete16KiB table image,
including all unused slots and the empty TTBR1 root. Live guards check these
bytes and CPU aliases; cached-only geometry checks preserve the signed
loader's SECURE/LATE exclusion rules.

The separate ordinary-write owner requires actual private signed, native-mode,
CP, core and firmware completion. It uses fresh monotonic4s total/2s phase
deadlines and watchdog budgets, phase-specific memory offsets, WPTR31 and
keepalive writes only. Its cached before/after data samples come from actual
CPU read callbacks and must match the engine's complete-page verification
before publication. Every shared owner is quarantined before failure logs.
It never writes data from the CPU or reuses an expired RUNNING-stage guard.

All4 changed ARM64 translation units pass. The table model rejects every one
of131072 single-bit mutations; real-owner tests cover533 cases with the
secure page inaccessible afterAUTH. The coordinator passes500 cases, retaining
all470 earlier cases. The actual integrated board passes369 additional cases,
including faults in all7 phases, data/PTE corruption, all8 retained NC/PA
pages, late mode changes, offset boundaries, partial writes and quarantine.
The secure page remains PROT_NONE throughout the two post-AUTH stages.
All78 host files pass. Full kernel, image and physical163 data-write evidence
are still required; source/model completion does not establish rendering.

Do not substitute a TRUST_CONTROL0 write for the native signed-load/unsecured
path. Completing the transition will still leave general scheduling,
rendering, the iOS graphics/Metal interface, power management and high-refresh
display to implement.
