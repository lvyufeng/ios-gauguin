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
