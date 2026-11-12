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
