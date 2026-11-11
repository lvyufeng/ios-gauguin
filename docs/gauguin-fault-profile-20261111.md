# Fault-check subgroup timing

The 0296 hardware capture identified the `gfw_faults` check as the largest
of six timed guards. Its measurements do not isolate individual reads or
establish an interactive frame rate. Patch 0220 instruments five existing
expressions and reports six subgroups: global SMMU status/control reads,
bounded settle calls, context bank 0, context bank 1, host status read and AO
status read. It retains short-circuit ordering, existing predicates, reads,
early returns and retry behavior. An unavailable AO mapping produces zero AO
calls; repeated recovery can cause extra global reads or settle calls.

The counters cover **all** callers of `gfw_faults`, not only runtime submission
guards. Bank timing excludes validation that precedes the measured read chain;
host and AO timing cover the existing read itself, not their following
comparison. Times are CPU wall intervals including instrumentation effects and
may overlap GPU activity; they cannot be used as GPU busy time, per-submit
attribution or measured display FPS. Instrumentation itself can change timing
and deadline outcomes, even when source normalization preserves control flow.

The host tests compare normalized full source against the pinned 0296 applied
source and exercise the actual timing macro with sanitizer-enabled mocks. They
are not hardware validation. A physical trial requires a fresh specific
authorization for any recovery marker or other partition write, and separate
interactive validation is needed before claiming a performance improvement.
