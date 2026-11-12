# 60 Hz display latency: read-only GPU status batch candidate

The user reports that the iOS screen is visible but still very laggy and asked
to establish smooth 60 Hz before high refresh. This candidate addresses one
measured source of missed frame time. It has not run on the handset and does
not establish physical 60 Hz frame delivery.

## Current handset evidence

The completed C4 trial used the 0298 kernel with `sweetfb_hz=60` and CPU copy
statistics. Its software clock reached 42,000 callbacks; 21 swaps were
accepted, with zero held-frame replacements or rejects. The latest sampled
prefix records 16 copy attempts, 15 full 10,368,000-byte copies and one
zero-byte attempt. All 15 copy intervals fall in the 2–4 ms bin. The time to
obtain the GPU surface read guard spans bins from below 0.5 ms to 16–33.333 ms:
`1,1,1,2,5,3,2,0`. Two sampled guards alone exceeded one 16.667 ms frame
budget. The guard interval includes acquiring the global GPU lock and its
checks; it is not a pure lock-wait measurement.

The earlier same-image repeat2 sampled 31 complete copies, all 2–4 ms, with
all 31 GPU-read guard intervals below 0.5 ms. The workloads and input were
not matched, so this contrast does not prove a causal performance regression.
The current source nevertheless holds the same global GPU lock while a native
submit polls to completion and while the display obtains its surface read
guard. C4 recorded 27 submissions, 300.441 ms of submit intervals and 1,584
full board-health checks during those intervals. Their recorded 298.198 ms
overlap GPU execution and cannot be subtracted as CPU-only cost.

The panel's 60 Hz mode was independently measured in TWRP at about 60.244 Hz.
The iOS `sweetfb_hz=60` argument selects one CPU copy slot per 16.667 ms
software beat. It neither sets a panel mode nor proves physical scanout phase.
The 21 C4 swaps over the diagnostic window were not a continuous-animation
test, so they cannot be called an observed app frame rate.

## Candidate

Patch `0222-gauguin-batched-readonly-submit-status.patch` changes only
`ggr_submit`'s preflight, fence-off status and completion-poll reads. The full
board guard runs before and after each read-only batch, and again immediately
before returning a completed fence. Every low-level read and barrier still
checks the operation deadline before and after its callback. The existing
latched RBBM/CP fault bits are read during every completion poll. All ring,
doorbell and WPTR writes keep their original full guard boundaries. A failed
read, deadline or guard still quarantines the runtime and returns no fence.
`ggr_open`, `ggr_check_idle`, the board guard body, hardware lock and display
surface ownership are unchanged.

In the typed host model, a two-IB submit with the same CPU-owned ring-span
path used by the handset needs 31 full health callbacks instead of 52. The
fallback per-word ring path needs 91 instead of 112. These counts show the
intended reduction in *checks*, not a measured kernel latency or device FPS.
The model injects a fault at every remaining health boundary and after each
preflight, fence-off and completion status read. The checks require quarantine
and no output fence; a delayed four-poll completion also succeeds. The actual
runtime and fixture pass ASan/UBSan in both baseline and candidate builds.
Single-file ARM64 macOS syntax checking passes with `-Wall -Wextra -Werror`.

A separate proposal to release the display's global lock on a per-IOSurface
object was abandoned before production patching: task-backed IOSurface objects
can alias the same physical pixels. Per-object arbitration would not preserve
the current cross-alias exclusion. The private scratch has not been booted.

## Next gate

The complete local macOS ARM64 `DEVELOPMENT` kernel build passed with make exit
0, build identity `xnu-355bac7a07774f6585bb66ee521f9ce7` and kernel
SHA-256 `ff30b0829be9049645e96a3415441c172af1f3fe396c79314f1396bfa4b68241`.
The source snapshot differs from the verified 0298 source in only the runtime
C file. Its manifest SHA-256 is
`b36a76cf0917b890dfffaeda4978454d949031e026d5c566999e38fae140472e`.
The full host suite could not run from this isolated worktree because older
source202 fixture cache files are absent. The build used `SKIP_TESTS=1` after
the focused runtime, guard and present-copy tests above passed individually.
GitHub Actions run 43200631136 was cancelled twice before runner assignment;
there is no CI compile result or error log for this patch.

An offline 20,021,248-byte temporary boot image now contains the candidate
kernel, SHA-256 `63c085a7bcbaacd494cc94b965b1386ffa8770f4e77cd4e415e7bf9389636f73`.
Its 605-byte boot command, shim, DTB, outer geometry, ADT, firmware physical
addresses, firmware bytes and padding match 0298 exactly. The independent
offline review found the same ten kernel segment virtual ranges; one kernel
file segment grew by 112 bytes. The review SHA-256 is
`01dc87f491b3c4a6117911306ab81fa4fcaac351d227a39d4f32d395a3bdc937`.
No device command, partition write or boot used this image. Private outputs
and the exact build log are under `research/tmp/gpu-poll-guard-20261112` and
`.deps-cache/p0-20261105/build299-60hz`. A cleanup manifest records 899,872,503
bytes of duplicate logs/abandoned per-object-lock scratch removed while
retaining the complete build log and all pinned inputs.

Next compare this image with the unchanged 0298 control under the same bounded
continuous 60 Hz workload, real gestures and physical screen capture. Measure
submit/guard intervals, copied bytes, missed software beats, visible distinct
frames and first response. A lower health-check count by itself is not a 60 Hz
fix. A device boot requires a fresh reviewed trial plan and exact user approval.
