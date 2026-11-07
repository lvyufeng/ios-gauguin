# A619 first CP submission contract

Patch0153 implements `ggq_start_once`, the first native RB0 command transaction.
Patch0154 supplies its live board adapter and coordinator dispatch behind the
existing default-off `sweetgpustart=1` entry. The accepted152 core, restore list
and cold SQE remain prerequisites. This engine alone does not make
GPU rendering, Metal, ZAP, unsecured mode or daily use available.

The reference is LineageOS/android_kernel_xiaomi_gauguin commit
`19b63c8192b1c9b7c4d931d7d3be92024bc2d778`. Full native platform setup matters:
`A6XX_CP_RB_CNTL_DEFAULT` is0x20c, then `a6xx_platform_setup` sets bit27 when
APRIV is absent. A619 therefore uses **0x0800020c**. The earlier152 proposed
first-command audit recorded only the default value; no CP was booted with it.
The153 reference executes the complete original platform-setup function.

The packet is12 native `ME_INIT` words from `ggp_cp_init_build`, followed by
`70620002 fc010000 00000000`: native `WHERE_AM_I` to RB0 scratch offset0.
There are15 DWORDs total, so the first WPTR is15 in an8192-DWORD ring.
The native64-bit addresses are SQEfc000000, ringfc008000, scratchfc010000 and
restore listfc014000. These derive from the canonical private memory plan.

The transaction captures initial hardware RPTR/WPTR and SQE control, rejects
pending pointers or decoded errors, fills32KiB of ring with0xaa and zeroes and
checks4KiB of private scratch. It programs RPTR-shadow/RB/SQE addresses and
RB control, releases SQE with the native value1, writes the15 words and checks
the whole ring before any WPTR submission. Only bounded64-word NC batches
relax per-word full-guard overhead; every word still checks IO/value results.
Every peripheral access and barrier has full pre/post guards.

Submission follows native keepalive1, WPTR15, AO counter sample, then a posted
barrier and `WRITEDROPPED0` check. A dropped write waits10us and reissues the
same WPTR, bounded by the original200 checks. At100 or more retries the native
second counter sample is retained. Failure after200 checks can involve201
WPTR attempts because the original loop reissues after its last failed check.
No fence-status clear, IRQ enable or speculative register cleanup is added.
After an accepted fence, the native keepalive vote is cleared.

Idle requires the scratch shadow RPTR to equal15 and GMU AO CX busy bit23 to
be clear. Decoded RBBM and CP errors are polled; informational interrupt bits
are not misclassified as faults. The read pointer must remain in ring bounds.
The board must additionally impose the native2s idle deadline and live owner,
clock/IRQ, SMMU-route/root/permission/fault, context, SQE and watchdog checks.
A finite polling count backs up those deadlines; it does not replace them.
A CPU packet copy or fenced WPTR alone is insufficient completion evidence.

The native model retains A619 PREEMPTION capability and four software rings,
with runtime preemption disabled. Its unused rings remain empty. This initial
port owns only the selected RB0; scratch is zeroed for all slots. Matching the
first selected-ring prefix does not implement the full multi-ring/preemption
backend or allocate its normal and secure context records.

The context is one-shot. Invalid or overlapping ordinary-RAM inputs cause no
IO; a started failure permanently poisons the context and preserves caller
output. The live board must quarantine shared owners before cached diagnostic
records, retaining mappings and HOST requests. It must not retry the stage or
perform keepalive-clear/reset/rollback after refusal. Native bounded WPTR
reissues are part of the submission protocol, not a failed-stage retry.

Validation runs34 unchanged native function bodies, including platform setup,
packet encoding, ring allocation/start, fenced writes, shadow-RPTR reads and
idle checks, under typed platform seams. Five complete positive command/MMIO/
fence/counter/shadow/busy traces are byte-identical to the port: immediate,
dropped-write, slow100/199 retries and counter rollover. A sixth native case
independently proves the200-check/201-write timeout bound. The native run stops
at an explicit ZAP seam after CP completion, without loading or claiming ZAP.
Port failure quarantine deliberately replaces native recovery cleanup.

Actual CP tests cover133682423 assertions, all938/1004 boundaries injected in
the two short paths, long retry paths, finite timeout, each kind of memory IO
failure/corruption, named faults, parent validation, recursion, once-state and
output preservation. All70 host test files and the actual ARM64 CP translation
unit pass. These are source/model/TU proofs, not a linked-kernel or device result.

The154 adapter requires complete same-boot core/RGL and READY firmware/GGX
parents, using an independent CP guard. It reuses core/CSR/AO Device aliases
and checks their attributes and physical endpoints, plus the two ring and one
scratch16KiB NC reservations and existing restore-page ownership. Only32KiB
ring and4KiB scratch bytes are exposed to engine memory callbacks. It creates
no new mappings and preserves earlier board function bodies.

The new stage has4s total CPU,2s phase/native-idle bounds,8s entry watchdog
budget and the existing3s minimum. It checks live clocks, masked IRQ state,
CM3 reset, GPU/GMU routes/roots/faults and accepted current SQE/core receipts.
Failure quarantines CP/core/GGX/firmware/board/shared lease before cached
records, with no cleanup or retry. Success records initial pointers, memory
checks, fenced submission/counters, actual shadow/busy/fault observations,
final guard ticks and all15 command words. Coordinator failures are terminal.

Its238 new actual CP/core/GGX board cases,416 coordinator cases and all70
host files pass; the changed board/coordinator ARM64 TUs also pass. The full
local154 kernel and four-asset image passed source, identity, symbol, layout
and strict runtime-reader checks, then completed one temporary physical boot
with trial token `gcpi-0154-a1` on2026-11-07.

That device run reports phase9/rc0,12 reads/11 writes,15 command words and
8192 ring comparisons. All1024 scratch words were initialized and checked
before SQE release. The fence succeeded at its first check with status0;
the final device-written shadow RPTR is15, AO busy is0x71000000 (bit23 clear),
and decoded RBBM/CP errors and final guard reason are0. Source-bound control
flow performs no CPU shadow store after SQE release. This qualifies the first
native ME_INIT/WHERE_AM_I transaction only. Rendering, ZAP, unsecured mode,
full scheduling, Metal and improved UI performance remain unqualified.

The observer found automatic recovery after131s; the user supplied standing
no-manual-intervention attribution. The retained-owner terminal intentionally
awaits watchdog reset, but no reset-cause register was read. Process/framebuffer
logs are not a human UI/touch observation during this unattended run.

The original reader rejected a WDT arm record that was intact but appended
behind concurrent IOKit XML output. Raw text/binary and that rejected report
are preserved. A separate reader uses `tools/console_framing.py` to detach
only complete known diagnostics following a validated interrupted XML key,
without repairing fields or relaxing technical gates. It records raw line,
column and substring hashes; duplicate, malformed and failure records remain
subject to the original checks. Six framing units and the retained runtime
cases pass, including45 full-trace acceptance and678 refusal cases. These
synthetic tests validate the reader; the same immutable physical log supplies
the GPU execution evidence in the separate accepted report.

The next native stage is signed a615_zap loading through the correct PIL/PAS
path, followed by the proper unsecured transition and bounded real submission.
The currently staged MDT bytes do not establish firmware authentication or
segment loading. The native TRUST_CONTROL0 fallback is not an accepted
substitute for completing the signed firmware path.
