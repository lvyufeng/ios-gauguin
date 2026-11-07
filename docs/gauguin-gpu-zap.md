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

The next implementation must derive `adreno_switch_to_unsecure_mode`,
`cp_secure_mode`, `adreno_ringbuffer_submit_spin` and its submission/idle
helpers from the pinned source. Native A619 appends CP_SET_SECURE_MODE0 and a
WHERE_AM_I to the existing RB0; it does not reset/reinitialize the ring or
rewrite the GPU shadow. Starting from this trial's RPTR/WPTR15, the candidate
5-word append would publish WPTR20. Exact words, placement, fence/keepalive
sequence and completion predicates still require native-function comparison
and source/model tests before any new image.

Authorization for that append must come from the actual private same-boot
157 signed-load receipt and retained CP/core/firmware state. It must use a
new post-AUTH guard path, without the old MDT hash check or a secure-buffer
read, and quarantine on failure. Do not substitute a TRUST_CONTROL0 write
for the native signed-load/unsecured-mode path. Completing this transition
will still leave general scheduling, rendering, the iOS graphics/Metal
interface, power management and high-refresh display to implement.
