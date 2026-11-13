# One-in-flight issued fence runtime: offline step toward asynchronous Metal

The user reports a laggy C4 desktop. The 0300 boot completed all 51 native
GPU submissions, but its GPU command-buffer sample had a 15.03 ms median,
59.25 ms maximum and 15 of 39 over the 16.667 ms 60 Hz budget. Those are
frontend-reported command-buffer durations, not direct hardware GPU time, a
measured physical frame rate or proof that synchronous submission is the only
lag source. The 0301 one-shot causal trace still lacks a new approval and has
not booted; this patch does not alter its pinned image or plan.

The same 0300 kernel log gives a more specific CPU cost. Across 51 submits,
the native submit path used 464,775,937 ns (9.11 ms per submit), including
450,272,187 ns in 2,293 full board guards (8.83 ms per submit, **96.9%** of
its measured CPU wall time). The guard's fault/configuration group accounts
for 243,788,333 ns during submits (4.78 ms per submit, 54.1% of guard time).
The user-client submit selector held its global lock for 640,928,125 ns total
(12.57 ms per call; maximum 40.28 ms). Those counters are aggregate CPU
wall time, not a paired touch-to-frame trace. A prior reduction in guard
checks did not make the user's desktop feel smooth, so optimizing this
measured cost alone is not yet evidence of a complete 60 Hz fix.

## Source comparison with HakiOS

HakiOS [sends a ring command and returns an issued fence](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.adreno.c#L3461)
before the GPU finishes. Its [user client records the fence on every named
buffer and IOSurface](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L1070),
[waits outside its global lock](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L195),
and [keeps a returned buffer mapped until its fence finishes](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L475).
The [presenter holds surfaces and waits for drawing](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L1250).
These are linked lifetime rules, not a single switch that can be copied.

Gauguin's current `ggr_submit()` does not return until the EOP memory,
WHERE_AM_I ring shadow and idle status all agree. The user client's visible
queue fence therefore means **completed**, its wait selector checks only
completed, each IOSurface's `gpuState` becomes clear inside the submit call,
and display reads hold the global GPU lock. Returning early from that call
without changing these contracts could expose half-drawn pixels or free
GPU-owned pages.

## Scoped change and evidence

Patch `xnu/patches/0225-gauguin-issued-fence-runtime.patch`, SHA-256
`2879f0f67ac95db46a6dc9374df440776b786bc80cd25fc9e4b0125ea2a69912`,
changes only `gauguin_gpu_runtime.c/.h` in an isolated source derived from
the 0301 kernel. It separates:

- `ggr_issue`: validates and rings one command, then returns its **issued**
  fence after the existing doorbell/fence-off checks. A second issue is
  refused until completion, retaining the safe idle-ring wrap assumption.
- `ggr_poll`: returns `GGR_PENDING` until real EOP, shadow and idle agree;
  faults and impossible values quarantine. A first poll after the original
  two-second deadline may accept an already-completed fence; a still-pending
  one is quarantined.
- `ggr_wait`: bounded polling of that issued fence. The existing
  `ggr_submit` wraps issue plus wait and publishes the fence only after
  completion, so the currently used board/user-client semantics stay
  synchronous.

The patch applies with zero fuzz; a file comparison of the replayed source
shows exactly those two changed files. ASAN/UBSAN host checks used the actual
runtime with typed register/memory callbacks: 17,555 retained runtime/ABI
assertions, 72 service-health assertions and 127 new issued/pending/complete,
deadline, invalid-EOP and ring-wrap assertions passed. The existing
ring-span test passed 54,780 additional assertions, and a stale wrapper
fixture was updated to current perf fields; its 12,139 submit/fence/startup/
failure assertions pass on both the old 0301 source and this candidate.
The modified runtime and unchanged user client using its new header both
passed native ARM64 translation-unit compilation. Private host receipt
SHA-256 `9098efd5c894c3b4a5d3ff18e799e3e7ccd039f7b6344c6d0fc6b821bb5746e9`;
native receipt SHA-256
`b23fe6d8202b44324317c55893d9299fb7e536f26bb07c059bb3ece2794fb3bd`.
There is no full-kernel build, boot, device write or measured speedup from this
patch.

## Required before using the issued path

The board still calls the synchronous wrapper. To return an issued fence to
Metal, the user client must track **issued versus completed** queue fences,
retain every referenced BO/IOSurface and SMMU mapping until completion,
defer close/free of busy handles, and make CPU prep, explicit wait, display
read and client teardown use bounded completion checks. GPU failure must
keep memory quarantined. A multi-in-flight ring needs verified RPTR/space
logic; this patch deliberately permits only one. The 0301 trace and a
SpringBoard animation-request measurement should determine which part of
this work is on Gauguin's critical path before a new exact phone trial.

## 2026-11-12 follow-up: guarded board issued-fence API, offline only

Patch `xnu/patches/0227-gauguin-guarded-issued-board-api.patch` SHA-256
`e8173025d4e37d272ca6685e5cc5d3fbdcb521a1a52bdb0853e94c204ae9dc1a`
adds board entry points for **issue, poll and wait** over the existing
one-in-flight runtime. `sweet_gpu_runtime_issue` requires the same root,
READY and live-route checks as synchronous submission, then checks owner and
SMMU routes again after the doorbell. A failed post-doorbell check quarantines
the GPU; a future caller must retain all referenced pages even when it does
not receive an issued fence. `sweet_gpu_runtime_poll` remains reachable in
BUSY state, checks the live owner and SMMU routes before each completion
read, and allows an already-completed older fence while a newer one is
pending. `sweet_gpu_runtime_wait` repeats that guarded poll until completion
or the runtime's original two-second pending deadline. The current board
`sweet_gpu_runtime_submit` and user-client selector still call the synchronous
path; this patch enables **no** early return in the current desktop.

An APFS clone of source305 was admitted as part of a 200,000,000-byte batch
at 498,810,449,920 bytes accounted. A full-tree diff after editing source306
lists exactly `bsd/dev/gauguin_gmu_board.c` and
`bsd/dev/gauguin_gpu_runtime.h`; the patch replays those bytes exactly onto
unaltered source305. The 5,336-file source-state receipt SHA-256 is
`d76210659ce57c1169889d56f98b9da767bfced4eba5529086ee028ace3e54cc`.
The actual board and unchanged GauguinGPU user-client
translation units passed native ARM64 compilation against the 0301 generated
headers, private receipt SHA-256
`4e8f2e61d967c56402aff83e35d1f1e2ccf81c228d441cef8df7f2b6cd8095fd`.
An ASAN/UBSAN host run compiled the three **actual board function bodies**
with the actual runtime under typed CPU-only register/memory callbacks. It
passed the retained 17,555 runtime/ABI assertions, 72 service-health
assertions and 96 new board issue/poll/wait/route/quarantine assertions;
private receipt SHA-256
`a633307098f69cc084a32ecd9f8dbc9ed77056a74f28dd168a68f51270119062`.
The first fixture compilation failed because its mock `ready` function was
incorrectly `static`; the corrected second run passed. No GPU commands,
whole-kernel link, phone boot, 60 Hz improvement or physical high refresh is
claimed.

The next functional integration must hold the referenced BOs, IOSurfaces
and SMMU mappings until completion, maintain separate issued/completed queue
numbers, and make CPU prep, wait, display reads and close obey that state.
The source's `sweet_gpu_runtime_ready()` is READY-only; callers must not
mistake its false result during an expected BUSY interval for a dead GPU.
These contracts must be solved together before using the new board API from
Metal. The separately approved 0301 touch/HID/C4 trace remains the next
phone diagnostic for the immediate lag.

## 2026-11-12 follow-up: retain the GPU owner across faulted close

The [HakiOS close path](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L443-L500)
keeps a buffer's memory and SMMU address when a submitted fence is pending;
its measurements say waiting for such a close previously cost about 5 ms
per frame. Gauguin's current `gOwner` was only a raw pointer. If `drop()`
failed after a GPU fault, `clientClose()` intentionally kept that pointer
and the DMA-visible descriptors but terminated the client without retaining
the client object. That pointer cannot safely be used by a future async
completion path.

Patch `xnu/patches/0228-gauguin-retained-gpu-owner.patch` SHA-256
`2bb51f559878c389b5cc17a240af5866854cee9e3f9db8917721843ebf93108f`
balances one explicit owner reference: `start()` takes it immediately before
publishing `gOwner`; a clean close clears `gOwner`, terminates the connection,
then drops the reference. A faulted close keeps the reference and every
existing DMA allocation until reset, matching the current quarantine rule.
It changes no submission or display scheduling and does not yet defer a
busy BO close. A 5,336-file comparison against source306 found only
`iokit/Kernel/arm/GauguinGPU.cpp` changed; patch replay and `git apply
--check` passed. Private source-state SHA-256 is
`43baa5f75140220e8f035ecc383c953d4e9dc403ecd32d2053ef434e65b6be03`.
Native ARM64 compilation of the actual user-client TU passed, receipt
SHA-256 `64c25765866a8600c89384ef800dddc66da3929a6a8fea0f725a798e7a6a51f4`.
The 250,000,000-byte clone/native batch was admitted at 498,904,973,312
bytes accounted; the conservative clone is 86,564 KiB and private compile
artifacts 2,940 KiB. No whole-kernel link, phone boot or measured speedup.

The opt-in async user-client transition still needs a completion-owned
pending BO set, separate issued/completed queue counters, deferred close,
explicit wait and CPU prep handling, display read synchronization, and
watchdog heartbeat handling while the runtime is BUSY. A completed fence
must be the only path that clears `gpuState` or releases a mapped page; a
fault must leave those pages retained. The unmodified 0301 diagnostic stays
first for locating the user's current 60 Hz lag.

## 2026-11-13 follow-up: opt-in one-in-flight user-client escrow, offline only

HakiOS's [measured touch investigation](https://github.com/oosexgang/hakios-xnu-kernel/blob/main/docs/reference/metal-measurements.md#under-real-fingers-5-november)
also matters here: its missed touch-interrupt handling delayed finger lift
88–169 ms, then 5–6 ms after the driver fix, while the same report still
identifies SpringBoard main-thread turns and GPU fences as other sources of
jerk. The HakiOS [buffer close path](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L443-L500)
copies a busy handle to owned storage, defers its memory/surface/address until
the fence completes, and may wait outside the global lock. Those are concrete
comparators for Gauguin, not proof that Gauguin has the same touch bug or
that async submit alone will solve the current lag. W301's same-boot
HID→C4 trace remains the first phone measurement.

The controller comparison rules out copying that particular touch fix:
Gauguin's Novatek `nrt_poll` reads page, 67-byte report and restore page on
*every* cycle before decode/HID, then calls `IOSleep(8)`. It has no
interrupt-level predicate in that loop. Its actual sample period includes
SPI, HID and scheduling time, so 125 Hz is not a measured input rate. The
HakiOS report also records that merely doubling touch polling to 250 Hz did
not improve its synthetic gesture rate. The 0301 same-boot trace must measure
Gauguin's physical down/move/up timing and downstream frame path.

Patch `xnu/patches/0229-gauguin-one-inflight-async-escrow.patch` SHA-256
`9f97d5262b26816784f77799afd4931688fd505b279d307e7e8d4d4f98ca27fb`
changes only the Gauguin GPU user client and its runtime-header contract.
The default/root path remains synchronous. Only the compositor with
`sweetgpuasync=1` uses the new issued path: it escrows every BO before the
doorbell, keeps descriptors, surfaces and SMMU mappings through completion,
tracks issued and completed queue fences separately, defers handle close,
and lets CPU prep, explicit wait, framebuffer read and heartbeat observe the
pending fence. A failed issue or completion retains the submitted mappings
in fault quarantine; completion checks all retained aliases before clearing
any surface. A caller deadline expiring does not free the GPU's pages.

This is a **candidate contract**, not a performance result. The board still
allows only one submission in flight, and the Gauguin user client still holds
its global GPU lock across a blocking fence wait. HakiOS releases its lock
around that wait; changing Gauguin's concurrency needs a separate lifetime
and runtime-lock audit. The current implementation therefore may still hold
up display or touch processing and must be measured before any claim of
smooth 60 Hz. No whole-kernel link, opt-in boot, phone write, physical FPS or
high-refresh result exists for patch0229.

A 250,000,000-byte source/native batch was admitted before the 86,564 KiB
APFS clone. A 5,336-file comparison found only the two patch files changed;
`git apply --check`, reverse check and exact replay passed. Private
source-state receipt SHA-256 is
`62e7f1024de88d8da3d73f0e07b584cd8cedc28e1fca67111a06e749c25169c5`.
The actual user-client TU passed native ARM64 compilation, receipt SHA-256
`5e33eb34a8457e49cf1ec6bfc70c81a1069517a04720ca9fbc941b7c7d1a46c6`.
ASAN/UBSAN host runs extracted the actual submit, completion and deferred
close method bodies, used the shared C ABI validators, and covered early
return, pending BO retention, queue counters, issue failure, sync default,
deadline, route fault, two-BO alias failure and deferred close. Their private
receipts are `9e04f1a1597cc66bfeca997ad2716a41138f7853bd51221ca122d3a6523f9dab`
and `c64ff8888b39ca6dd318189aedf5079110243737b52a67d4f0454913f9f8fb1b`.
Patch-series tests and diff check passed. The W301/0301 plan and image were
not changed; its separate exact-scope phone approval is still outstanding.

## 2026-11-13 CI runner follow-up

The first full-kernel Actions dispatch, run `43258091414` at commit `35e7026`,
was cancelled before any step ran with the job annotation
`The configuration 'macos-14-arm64-us-default' is not supported`. This is a
runner-scheduling failure, not a compile result. GitHub's
[runner retirement notice](https://github.com/actions/runner-images/issues/13518)
says macOS 14 Actions images ended on 2026-11-02, and its
[current runner list](https://github.com/actions/runner-images/blob/main/README.md)
includes the arm64 `macos-15` label. Commit `07443e2` changes this workflow's
runner label from `macos-14` to `macos-15`; fixed 13.5 dependency profile and
requested gauguin DEVELOPMENT build are unchanged. Dispatch `43258392712`
at that exact commit acquired a runner and passed checkout, profile and deps.
It then failed before any kernel compilation: the workflow's generic
`tests/run-all.sh` invoked every host script without the arguments,
environment and source fixtures required by many newer tests, and reported
43 test-file failures. These include stale GPU fixture compilation as well
as missing parameters; they are not evidence that patch0229 fails a kernel
build. Only `dxb-bootstrap.log` was uploaded, and the small xnu-kernel
artifact contains no built kernel. The full failed-step log was retained
privately with SHA-256
`12727f1faa321d39afe6af0c49308c2e1b60ea0f7578be0d8fefb60aae1fe4f3`.
The next workflow revision moves the unchanged host-suite gate after the
kernel-build loop. It still returns failure on any host test error, while
collecting a real compile/link result first. The workflow records actual
Xcode/SDK in its build manifest when that stage runs.

The legacy GPU host fixtures were refreshed against source308 without
changing production code. `tests/test_gpu_iokit.py` now supplies the UI trace
and issued-fence seams and passed its actual user-client submit, sync, queue,
read-only scatter/fault, slot and pilot cases. `tests/test_gmu_board.py` now
supplies the added trace, continuous-delay, clock, WDT and profile seams;
its actual board adapter, cold GPU pipeline and texture scenarios completed
under ASAN/UBSAN. Four focused issued/async host scripts now accept the
workflow's `XNU_SOURCE` environment and make unique private output directories
when no CLI path is supplied; all four passed with that entry point. These
fixtures do not assert that the pending asynchronous mode works on hardware.
Other generic-suite failures remain and are still reported by CI.

Dispatch `43261798908` on commit `4586bed` proved the missing kernel-build
stage: exact patch0229 was applied, `build-gauguin rc=0`, and the
`DEVELOPMENT_ARM64_GAUGUIN` manifest says `state=built`, `make_exit=0` under
Xcode 16.0 on macOS 15 arm64. The downloaded Mach-O arm64 kernel is
17,883,112 bytes, SHA-256
`5fd6803ed89ddfca6af30eb9de1c66a088f1fa62446222f69b706cd07872b3a9`;
the artifact's `SHA256SUMS` check passed and its strings include
`sweetgpuasync` and the compositor opt-in log. Manifest SHA-256 is
`06d160050c718f304ef1d413817aa5d92c07a100a6a6969346528de66e660d33`;
private run/build receipt SHA-256 is
`2f0106974753c9ab565bba227e0f2afa2e61f9815d7c10fc788a159b42cd18bd`.
The Actions run is still **failure** because the unchanged generic host suite
reported 43 test-file failures after the successful kernel build, mainly
missing local input fixtures/arguments and stale host seams. Commit `cf74d32`
fixes the directly relevant GPU seams and four focused CLI defaults; that
commit was made after the run and is not covered by its remote test log.
This kernel has not been packaged, booted or measured on the phone.

## 2026-11-13 storage cleanup for the pending phone trace

The 0301 trial's live 1 GiB capture reserve failed the 500 GB project cap
after this branch's CI artifact download. Source305, source306 and source307
were superseded by the retained source308 and exact patches0227–0229. Each
reverse patch check passed before retiring only those three APFS clones.
Their 5,336 files each and conservative total of 259,692 KiB were recorded
in a private cleanup manifest SHA-256
`0cf9792e016035ffcffdf5adfc17ab148ff3dc4ff90241868ca5ffbd19088c70`.
None of the 110 W301/W302 active trial pins was under those directories.
Current source308, W301/W302 pins, original phone backups and rollback
snapshots remain. The full 1,073,741,824-byte capture reserve then passed
at 498,900,963,328 bytes accounted. The 0301 executor will repeat this
check and all device-preimage checks after its separate exact-scope consent.

## 2026-11-13 observed synchronous GPU cost in 0301

The separately approved 0301 diagnostic boot returned safely and restored
the original desktop, but no physical contact was recorded: Novatek accepted
63,904 packets with mask zero and the touch-linked trace had zero gestures.
The user's follow-up says they are currently away from the phone, which does
not prove whether they touched it during the trial. It cannot qualify a
touch-to-frame bottleneck or a physical refresh rate; see the
[0301 result](https://github.com/lvyufeng/ios-gauguin/blob/codex/gauguin-causal-trace-20261112/docs/gauguin-causal-ui-trial-results-20261113.md).

The same boot did measure the still-synchronous GPU bridge: 14 submit calls
held its global lock for 153,018,229 ns in total, 10.93 ms/call on average
and 24.61 ms maximum. Native board submit used 72,724,947 ns, with
71,043,697 ns (97.7%) in full guards. The 597 heartbeat calls held the lock
for 3.02 ms/call on average and 12.07 ms maximum. These are aggregate CPU
wall measurements across mostly startup/idle activity; there is no frame or
touch pairing. They show that patch0229's issued-fence path still has guard
and heartbeat lock costs to measure, and do not establish that enabling it
would make the desktop smooth. Private aggregate receipt SHA-256 is
`30c563d44bdf80b65c2a86b837c26bd6e0c2bf1cb5212b85eb700f48a111e379`.
No new phone trial is scheduled while the user is away.
