# Guard group timing for Gauguin GPU submissions

The 0294 capture recorded 590 full health checks inside 13 GPU submissions.
The checks occupied 115.440 ms of the submission path's 116.101 ms wall time.
They may overlap GPU execution; this is not a subtractable CPU/GPU breakdown.
The capture includes only five post-bootstrap jobs and no confirmed interaction.

Patch 0219 times six existing checks: owner authentication, watchdog lease,
unsecured state, clock snapshot, interrupt state, and firmware faults. Every
original guard expression remains in the same order, is evaluated once, and
retains its original result and failure path. The existing pending flag becomes
atomic for the new observations. The group counters are atomic. `pending_end`
means the global submission flag was set at the end of a check; it is not a
per-thread attribution or proof that the whole interval overlapped GPU work.
The added timestamp reads and atomic updates perturb timings and may affect a
deadline boundary; this diagnostic is not an optimization.

A source-level normalization test checks that removing the instrumentation
reproduces the entire earlier board C source. A host ASan/UBSan test executes
the actual macro for six groups on true and false predicates, checks single
evaluation, timing and pending counters, and rejects a reversed timestamp.
The actual board C translation unit compiles under the retained 0294 ARM64
recipe. The source and TU results do not prove hardware safety or performance.
The native submission guard, fault, lease, reset and page-table rules remain in
place. A future explicitly authorized trial must validate its real trace and
collect interactive observations before changing those rules.

## 0296 hardware observation, 2026-11-11

One individually approved 0296 temporary boot returned to TWRP after 745 s.
The 13-byte recovery marker was verified, the kernel banner matched the image,
and the read-only post-boot capture and strict six-group parser both passed.
There were 15 recorded GPU submissions, all completing their sampled fences;
seven followed the eight-stage bootstrap. There was no confirmed interactive
test, and the trace does not qualify desktop pixels, physical FPS or high
refresh. No direct userdata delta was written.

Each of the six groups was called 10,936 times. Wall times were owner 37.42 ms,
lease 105.94 ms, unsecured 339.87 ms, clock 353.39 ms, IRQ 50.27 ms, and
faults 1,105.51 ms. The full checks totaled 2,083.39 ms, so the fault group
accounts for about 53% of the measured full-check wall time in this run; its
mean is about 101 microseconds per invocation. All values include measurement
perturbation, and elapsed intervals can overlap work on the GPU. The 754 group
samples with the global pending flag set at the end are not per-submit
attribution. Guard timing cannot establish a physical frame rate or quantify an
expected UI improvement.

The fault group contains global SMMU checks, two context-bank control and
status checks, host/AO checks, and bounded transient recovery. The trace
reported nine transient attempts and nine recoveries, with no expired budget;
it does not separately time these components. Next, measure those components
without changing the predicate order, MMIO reads, error paths, or fault
handling. Test any eventual optimization against individual fault injections,
deadline boundaries, and real device evidence before claiming an improvement.
