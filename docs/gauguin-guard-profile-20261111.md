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

## Prepared 0296 diagnostic image

The full kernel was built locally with fresh objects and passed the retained
provenance and symbol checks. The 20,021,248-byte temporary image has SHA-256
`5fdeb9bb584e6336ae2bab4f872971677b4e3e092b73aaf8653243e20cd025c8`.
The current recovery root's 27 files and four directories match the captured
post-0294 baseline; the recovery-marker preimage is backed up. The strict log
parser rejects incomplete, duplicate, interleaved and inconsistent snapshots.
All these results are preparation; 0296 has not been tested on the phone.

The concrete plan is one 13-byte misc recovery marker and one temporary boot,
with rollback of those marker bytes if marker write or readback fails. This
requires new individual authorization. The diagnostic counters add overhead
and do not qualify interactive frame rate or physical 90/120 Hz.
