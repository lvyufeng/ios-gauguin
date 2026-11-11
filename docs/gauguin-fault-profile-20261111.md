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

## 0297 hardware observation, 2026-11-12

After individual authorization, one temporary 0297 boot returned to TWRP after
745 seconds. The 13-byte recovery marker readback and exact kernel banner
matched. The first automatic postprocessor failed before capture because it
resolved a main-workspace-relative log path against the worktree; the retained
raw log, trial receipt and failure are preserved. A two-path read-only fix
verified the original completed process group and recovered the actual 27-file
capture. No second boot or direct userdata difference write occurred.

| Subgroup | Calls | Total CPU wall | Mean per call |
| --- | ---: | ---: | ---: |
| Global SMMU | 17,876 | 443.865 ms | 24.83 µs |
| Bounded settle | 17 | 1.221 ms | 71.82 µs |
| Context bank 0 | 17,859 | 671.236 ms | 37.59 µs |
| Context bank 1 | 17,859 | 667.878 ms | 37.40 µs |
| Host status read | 17,859 | 9.798 ms | 0.55 µs |
| AO status read | 15,443 | 7.580 ms | 0.49 µs |

The two bank groups account for about 74% of the sum of these six measured
subgroup intervals in this capture. They are measured for **all** callers,
while the separate runtime guard's fault timer covers only runtime guards;
their totals must not be subtracted from one another. These CPU wall intervals
include profiling overhead and may overlap GPU work. There is no confirmed
interactive input trace or per-frame latency measurement in this trial.

The final runtime counters report 27 submitted and 27 completed jobs. The
retained per-submit ring proves the first 16; the exact later 11 command
sequences are not individually recorded. All 17 bounded transient attempts
recovered, with zero expired budgets. Four buffer-object failures occurred
after the deliberately finite 600-second GPU service stopped; their existence
is recorded, not treated as a failure inside that service window. The run does
not qualify desktop pixels, interactive FPS, physical high refresh, persistent
GPU operation or daily use. Do not remove/cache a bank check without a separate
safety and latency design and real fault-injection evidence.
