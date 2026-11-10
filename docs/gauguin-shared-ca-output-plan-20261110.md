# From task sampling to compositor presentation

The full phone goal includes real GPU rendering, correctly recognized usable
RAM and storage, peripherals, sustained power management and 90/120 Hz operation.
Offscreen pixel tests alone do not establish desktop acceleration or daily use.

Actual 0239 now qualifies all five immutable task inputs, including both
FP16/FP32 cases after original VA release, source allocation guards, permissions
and final owner reacquisition. Its [physical acceptance report](gauguin-readonly-task-input-20261110.md)
records the bounded scope. The next shared-output candidate is prepared in the
0240 worktree and has passed native compilation, the exact 20H392 import audit
and modeled reader controls; it remains uninstalled and physically unqualified.
The renewed [HakiOS desktop review](gauguin-hakios-desktop-recheck-20261110.md)
adds decoded-image upload, real compositor admission and presentation to the
next integration milestone.

The 0240 runtime is now prepared under its existing local worktree. DSH's
`runtime-gates-stage-v1` dispatcher 92912 exits 0 in 9.478989 seconds with all
38 input pins unchanged. The new correlated reader rejects actual 0239's old
logs and 27 inconsistent modeled combinations. Four actual runtime entry
functions stop on the missing new approval before any recovery IO or output
claim. A local-only read of the complete staged image verifies the expected
22 files. These are host controls, not a successful 0240 installation or boot.

The prepared sequence binds the exact 194-block plan and completed 33-range
readbacks to one temporary boot of the physically qualified 0239 kernel. It
retains the three complete old log prefixes, all old FP16/CA/task checks and
final owner reacquisition, then adds both shared output views and aggregate
native-job correlation. The old CA result line's `explicit_jobs=10` continues
to describe that original block; the whole binary's final counter check
requires 26 explicit command buffers, with ten additional framework jobs and
36 native successes. The later 20 native successes are unsampled and must not
be described as exact per-submit IB evidence.

Runtime source and review receipts remain local in
`research/tmp/gauguin-shared240-worktree-20261110/research/tmp/dsh-shared-0240-ca-output/`.
The reviewed helper entry points are `verify240.py`, `trial240.py`,
`boot_pilot240.py`, `post240.py` and `evidence240.py`.
`runtime-review240-v1.json` has SHA-256
`db6c9f8d6e1d3c24df569807441c84508bca4038eec3dc6ca05ebc6731889ea4`.
The concrete proposal and corrected probe remain unchanged. A real answer to
the pending 0240 write question is still required; no approval, apply receipt,
installed capture or trial output has been fabricated.

The next bounded test should exercise shared output directly:

1. Keep the existing FP16, original-image CA and task-input tests as regressions.
2. Allocate a real, owned BGRA IOSurface and import it as a Metal render target.
   Require the original IOSurface identity and a direct texture, with no shadow.
3. Run the same five real CARenderer scenes into that target. After each scene,
   commit an actual GPU marker fill on the supplied queue and wait for its
   completion. The marker must not copy or read the target. This establishes an
   observable queue completion without substituting a GPU blit readback.
4. Read the original IOSurface CPU view and the exact core BO's CPU view after
   completion. Emit raw rows and independently compare every channel against the
   existing CPU scene oracle. Verify the two views describe the same shared
   allocation, with writable target rights and preserved bounds.
5. Release the renderer, target, IOSurface, marker and queue, then verify owner
   reacquisition and bounded memory. Record IOSurface seed behavior without
   assuming a GPU seed-update contract that has not been established.

If added after the existing 0237 suite, five new poison clears, five framework
render jobs and five marker fills imply 36 native successful jobs in total.
There would be 26 explicit command buffers, including the original 16; framework
jobs remain counted separately. The five intentional WRITE refusals on read-only
inputs must add no successful GPU jobs. Native logging samples the first 16, so
later jobs require raw pixels, completion receipts and aggregate service/fence
checks without claiming an exact later IB sequence.

Display handoff then needs its own ownership and timing qualification. Current
`AppleCLCD::swap()` stores the latest record containing surface IDs; the timer
looks up surfaces later in `present()`. Surface table membership has its own
user count, separate from an object's retain count. A real presentation path must
hold the right ownership through consumption, replacement, client exit and
failure. `SweetSurfaceGPURead` currently serializes a CPU read with GPU activity;
it does not by itself establish a presentation completion contract.

The current framebuffer path copies dirty rectangles on the CPU. Its advertised
vsync notifications come from a 60 Hz software timer, and the current boot caps
copies with `sweetfb_hz=30`. Its physical panel surface also falls outside the
current importer admission: it is neither an owned IOBuffer target nor an
immutable task input. These are separate display work, not evidence of a real
90/120 Hz mode. Higher refresh ultimately needs actual panel/display timing and
buffer handoff verification, followed by measured input-to-present behavior.

Only after shared inputs, outputs and presentation are qualified should the
native Metal device be admitted to the compositor. Existing root-only admission
and truthful capability checks should remain until the actual compositor shader
and resource workload is covered. The current EAGL desktop, general Metal
discovery and higher refresh have not been qualified by the root tests.

Source observations above use the materialized 0236/0238 implementations of
`SweetFramebuffer.cpp`, `SweetSurface.cpp` and `GauguinGPU.cpp`. The framebuffer
baseline is introduced by patches 0046 and 0056; later guards and importer
changes are retained in the corresponding active patch series.

An isolated held-presentation implementation is now committed as
`18c5b175c08b5e2326d906eaed37204376112a39` on
`codex/gauguin-present-lifetime-20261110`. Patch 0210 adds the opt-in
`sweetfb_hold=1` path: balanced object/table holds, original-pointer handoff,
one pending and one active frame, cancellation and prompt retirement. The
old raw-ID lifetime fault is reproduced by an extracted-code host control;
the candidate and related DMA/Surface regressions pass. Full pristine replay
and fresh native compilation are complete, with the final qualification
passing in a separate stage after two verifier adaptations. Failed receipts
are retained. Detailed evidence is in that worktree's copy of this document
and `NOTES.md`. MAIN retains its physically qualified source baseline.

This candidate has not been packaged or booted. It keeps the current cadence
and does not provide a deferred producer-completion fence. The pending 0240
proposal remains unchanged and must use its exact paired 0239 kernel first;
another boot before installation would grow logs and stale the concrete delta.

The subsequent isolated source commit
`9da060b890627b20fb28c05cd0a27f45633157c3`, branch
`codex/gauguin-present-cadence-20261110`, adds opt-in absolute software cadence
with `sweetfb_phase=1` above held presentation. Its virtual-clock regression
and related host checks pass. A complete pristine 203-patch replay, fresh
native build and generic qualification also pass in one DSH stage. Source
and physical-result scope are documented in that worktree's copy of this
plan. It has not been packaged or booted and does not establish physical
refresh or desktop latency. MAIN's active patch series and pending 0240
installation remain unchanged.
