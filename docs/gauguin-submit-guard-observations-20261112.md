# GPU submission guard observations

The 0297 capture recorded 27 completed native GPU submissions and 1,486
`ggrb_live` checks in the corresponding submission timing intervals. Their
reported wall times were 282.931 ms for submission intervals and 280.877 ms
for the differences in accumulated check time. The counters are global, and
GPU execution can overlap these intervals; their ratio is not a CPU/GPU
breakdown or a per-frame measurement. Eight submissions belonged to the
bootstrap, only the first 16 submissions have individual retained traces,
and no interactive workload was confirmed.

Across all 11,768 runtime checks, the recorded full-check wall time averaged
about 191 microseconds, including timing overhead; the nested firmware-fault
group averaged about 102 microseconds. The fault-subgroup counters cover a
different, all-caller population, so their bank totals cannot be subtracted
from these runtime-only measurements. The 0297 software framebuffer clock
also counted 21 copy attempts in its last reported snapshot. These GPU and
display counts do not establish a pairing, screen frame rate, or input latency.

## Host model of the current submit core

The unmodified `gauguin_gpu_runtime.c` was compiled against fake typed hardware
callbacks. For one IB, the configured ring-span path called `healthy` 40 times
when the first completion poll succeeded, 54 times after one not-ready poll,
and 82 times after three. Two busy fence-status polls gave 56 calls. The legacy
per-word fallback control produced 84, 98, 126 and 100 calls respectively.
Each extra not-ready completion poll adds 14 calls in this model. These are
callback counts, not real GPU timings; the fake ring-span callback models only
CPU RAM, state and deadline behavior, not the actual board callback. The real
board callback additionally checks board state and its global deadline.

The experiment injected a failure at each of 832 reached health boundaries
across the eight scenarios, including open and idle checks, and exercised 21
simulated deadline boundaries. These checks showed quarantine and no success
fence for the injected paths; they do not cover every hardware fault or every
possible concurrent interleaving. The fixture records no `nanoseconds` calls
as trace events. Consecutive `healthy` callbacks without an intervening logged
I/O still have state/deadline evaluation between them, and asynchronous GPU or
SMMU state may change. Their adjacency is not evidence that either check can
be removed.

The pinned baseline can be reproduced with
`XNU_SOURCE=/path/to/the/patched/xnu python3 tools/characterize_gpu_submit_guards.py`.
The driver refuses a different runtime source or header, validates its traces
in a temporary directory, and is a characterization of this baseline rather
than a rule that future optimized implementations must retain these counts.
The original synthetic traces are under `research/tmp/submit-count-20261112/`
in the fault-results worktree. Source and header hashes were unchanged during
the recorded run.

## Implications for the next change

The two SMMU banks contain conditional and unconditional status, routing and
translation checks. A successful full pass reads 27 SMMU values, or 29 when
both optional stream-match reads apply, in addition to host and optional AO
status. It can reread the global checks after a bounded transient. Caching bank
values across a submission, joining later route samples to an earlier sample,
reordering reads, widening accesses or dropping barriers changes which faults
or route changes may be observed. No such change has been qualified here.
Even the current ordered samples do not create an atomic hardware snapshot.

The practical next measurement is 0298's opt-in present/copy diagnostic,
subject to the separate device authorization. It can distinguish CPU copy
and read-guard intervals for the records observed, but not physical refresh,
GPU busy time or touch-to-display latency. A representative interactive run
and a comparable trace-disabled control are needed to assess UI responsiveness
and instrumentation overhead. Preserve the existing fault checks until any
specific candidate has ordered fake-MMIO failure coverage and independent
hardware validation.
