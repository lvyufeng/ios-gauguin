# A619 signed ZAP integration plan

This is an implementation contract, not a completed loader. Trial154 proved
the first native ME_INIT/WHERE_AM_I completion. Historical trial117 separately
proved PAS13 INIT_IMAGE and MEM_SETUP4096 acceptance. Those are different boots;
neither run authenticated or loaded the ZAP code segment.

Patch0155 now implements the optional immutable b02 source asset. The packer
adds `--zap-code` and an `A615ZapCode` raw1984-byte descriptor with16KiB reserved
extent and14400 zero padding bytes. It appends after the four old assets and
updates final top/PAS accounting. The kernel's `sweet_gpu_zap_asset_view` checks
the fixed pin, padding, direct-map endpoints, coherent five-descriptor layout
and all pairwise overlaps. It requires the high DRAM bank, disjoint from any
permitted below-4GiB PAS allocation; it does not validate a current low owner.
It returns only an immutable source view and performs no firmware loading.

Validation passed the actual ARM64 asset translation unit,84 real-SHA256
ASan/UBSan consumer cases with captured b02,64 synthetic layout combinations,
128 exact byte/info comparisons with the actual frozen pre155 packer, the
actual shim loader's five-asset copy/zero/ADT/bootargs path and88 PAS metadata
cases. All73 host test files pass. The offline five-asset pack used the old154
kernel to verify packaging only; no155 full kernel or device trial was made.

The primary reference remains LineageOS/android_kernel_xiaomi_gauguin commit
`19b63c8192b1c9b7c4d931d7d3be92024bc2d778`. The read-only155 source audit
rehashes12 pinned native files, all seven captured firmware files and original
117/154 report inputs. Its private report records51 unchanged input hashes.
Captured bytes and device dumps stay outside Git.

The native order in `adreno_a6xx.c` is CP_INIT, `a6xx_zap_load`, unsecured-mode
submission, then post_start. `a6xx_zap_load` calls `subsystem_get("a615_zap")`
and propagates failure. The actual recovery DT selects trusted PIL PAS13,
with no no-auth flag or fixed memory-region binding. `peripheral-loader.c`
orders INIT_IMAGE, MEM_SETUP, segment loading and AUTH_AND_RESET. The signed
path must be implemented at this post-CP point; a TRUST_CONTROL0 fallback
does not complete it.

The fixed captured format is:

| Item | Exact scope |
| --- | --- |
| MDT |6860 bytes, b00+b01 packed metadata |
| Loadable segment |b02 only,1984 bytes, relocated destination offset0 |
| Segment BSS |0 bytes; no tail-clearing operation |
| Native memory span |4096 bytes passed to MEM_SETUP |
| Reserved allocation |1MiB, distinct from the4096-byte span |
| Fresh AUTH frame x0..x6 |42000205,1,13,0,0,0,0 (normal SCM64) |

The b02 SHA256 is
`61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878`.
The metadata is initially staged at the region base. Only after this boot's
INIT and MEM_SETUP succeed may b02 overwrite exactly the first1984 bytes.
Do not reload MDT between secure calls, load the full ELF, clear4096/16384
bytes or interpret a matching hash as successful signature authentication.

There are two current integration conflicts. `bcm_flags` rejects simultaneous
CX/GPU and old PAS INIT/MEM opt-ins, and its coordinator branches are exclusive.
Also, `sweet_pas_stage_owner_valid` checks the original MDT hash and zero tail;
the current GPU guards use that predicate. INIT permits SCM_RW changes and
b02 deliberately replaces metadata, so those predicates cannot authorize the
later loading phases. Their existing semantics must remain intact.

The implementation proceeds in these bounded stages:

1. Implemented in155: a fifth optional, pinned b02 asset through payload packing, shim layout,
   ADT descriptor and a kernel read-only view. Validate its exact1984-byte hash,
   raw/padded size, direct-map endpoints, DRAM/top bounds and separation from
   all existing assets and the low reservation. With the asset absent, retain
   existing payload bytes and options. Keep binaries outside Git. The remaining
   steps below are unfinished and start with integrated loader156.
2. Add a distinct default-off ZAP entry after successful live CP completion.
   Seal the actual same-boot CP/firmware/core/owner state before INIT. Retain
   original MDT checks before the transfer; use separate phase-aware geometry,
   mapping and ownership checks afterward. Never add a caller PA/pointer setter
   or accept a fabricated completion receipt as authority. Keep legacy PAS
   flags and old standalone tests independent.
3. Run one serialized INIT/MEM/copy/AUTH state machine under fresh watchdog,
   context, clock, IRQ, route, fault and retained-parent checks. The copy stays
   inside the owner module, uses its existing NC alias and writes exactly1984
   bytes, with bounded readback and a barrier before AUTH. Publish copy success
   privately only after verification. A failure quarantines shared authority
   before cached logs; retain mappings and requests, with no cleanup or retry.
4. Preserve normal SCM64 continuation and BUSY semantics. Keep full x0..x6
   across interrupted returns and require full64 transport/service zero.
   Existing8-continuation,68-fresh-attempt and5s diagnostic bounds are policy,
   not native AUTH guarantees. Review any changed bound explicitly. Logging
   must leave fresh entry budget; software cannot cancel a nonreturning SMC.
5. Validate exact pinned native call frames/order against the implementation,
   partial copy and permission failures, every state/once boundary, missing
   prerequisites, error/continuation/BUSY/deadline paths, and old behavior.
   Compile changed ARM64 translation units with the current154 manifest and
   run the applicable host suite. Link/package only the integrated live path;
   no separate copy-only physical boot.
6. Qualify one temporary combined boot with a new identity and strict reader:
   same-boot core/CP completion, INIT/MEM success, b02 copy/readback, AUTH raw
   result and terminal state. Preserve failures and raw logs. AUTH success
   qualifies this signed load only. Do not inspect/rewrite the secure region
   afterward or infer safe CPU access from an old mapping.

After authenticated ZAP loading, derive the native CP_SET_SECURE_MODE and
submission/completion transaction before adding the unsecured transition.
General command scheduling, rendering, the iOS graphics/Metal interface,
power management and high-refresh display remain separate unfinished work.
