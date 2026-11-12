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
