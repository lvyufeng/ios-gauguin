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

The separate 0241 candidate adds `0210-gauguin-held-presentation-frames.patch`
above the qualified 201-patch baseline. `sweetfb_hold=1` holds each enabled
surface's object and ID-table user at submission, transfers the exact pointers
into a single active frame, and retires them as soon as the existing guarded
CPU copy returns. One latest pending frame may wait behind that active frame.
Replacement, the submitting display client's exit and display-off cancel an
unconsumed frame. Valid submissions while off are accepted and immediately
retired, so ordinary power transitions do not manufacture a driver error.
Failed lookups unwind partial holds without replacing the previous good frame.
The hold path checks the submitting client is still attached while holding the
framebuffer lock. It records submitted/replaced/consumed/retired/canceled/rejected
counts with pending/active occupancy for a later physical trial.

DSH dispatcher 96080 exits 0 with all 39 input pins unchanged. An extracted-code
host fixture functionally reproduces the old raw-ID reuse error, then passes
3,236 checks on the candidate, including 1,000 concurrent submissions, repeated
layer IDs, cancellation, prompt retirement and the disabled pilot behavior.
Existing transport, read-only DMA-fault retention, caller-memory creation and
independent task-map controls also pass. These use typed host object/lock seams;
they do not establish XNU execution, correct pixels on the phone or frame rate.
The source candidate is not installed or booted. Full pristine-source replay
and the native build have subsequently completed. Source commit
`18c5b175c08b5e2326d906eaed37204376112a39` replays all 202 patches from pristine
XNU `1b191cb58250d0705d8a51287127505aa4bc0789`; source SHA-256 is
`eeaae16e10996e30e0ca7ff6052878d39ddf3e7e898c6310477db022678b59b9`.
Exactly `SweetFramebuffer.cpp`, `SweetSurface.cpp` and `SweetSurface.h` differ
from physical 0239. The GPU driver and every unrelated source file match.
The fresh-object kernel is 17,330,056 bytes, SHA-256
`87f0c2a41c877d464910a07db235595294fa9773bc354b89f5804a16c246bd67`.
Generic provenance, required symbols, archive/install identity and native
64-bit cache-flush checks pass; all five new held-frame entries are defined in
`__TEXT_EXEC,__text`. Eight functions are retained as native disassembly.
Existing header warnings remain.

The first overall build stage exits 1 after successful compilation because
the inherited qualifier requires a historical dirty `mkadt.py` worktree.
The isolated source was built clean. A separate qualifier preserves all other
checks, requires the captured/current checkout to be clean and verifies the
original MAIN edit separately. A second qualification attempt rejects our
overly specific `__TEXT` section filter. The final exact `__TEXT_EXEC` symbol
check passes in qualification dispatcher 34992, exit 0. Neither correction
changes or rebuilds the kernel; both failed receipts remain intact. The local
`native-review241-v1.json` receipt has SHA-256
`7a7846750005053b54fcfb4e911b80466e42b539eec81184f48ba2f63ffa7cdc`.

The cadence change is separate unfinished work; this patch keeps the current
timer/copy-rate behavior. The pending 0240 proposal remains paired with its
unchanged physically qualified 0239 kernel and is not modified by this branch.

The 0242 source candidate adds a separate `sweetfb_phase=1` option, requiring
held presentation. Patch 0211 uses XNU absolute ticks and `wakeAtTime()` to
choose the next future nominal software beat after work. A late callback
accounts for skipped logical beats once, without replaying old notifications.
Copy slots follow delivered logical beats rather than callback count or copy
completion time. A slot is consumed only when a pending record is actually
taken; failed allocation/handoff leaves it due. The driver samples time again
after acquiring its lock. The software interval remains 16,667 microseconds;
this change does not select a new physical panel mode or certify 90/120 Hz.

The option is disabled by default. Invalid configuration, non-monotonic or
overflowing clock values and a failed `wakeAtTime()` produce explicit records
and select the existing relative timer. These outcomes must fail a future
phase acceptance test. The counter called `copies` counts consumed copy slots,
not successful panel updates; the existing guarded copy may still refuse a
surface. Writer-completion and physical scan timing remain separate work.

DSH's 0242 host stage, dispatcher 38032, passes six tests with all 40 pins
unchanged. The executable uses the actual clock header and driver methods,
with a virtual clock and timer. The old relative-arm statements reproduce
45.334 ms copy intervals with modeled 12 ms work; the candidate keeps 33.334 ms
in that case. 7,264 clock controls cover overload, idle, unconsumed slots,
early/duplicate callbacks, rejection/fallback, counter saturation and 64-bit
arithmetic against a bounded loop oracle. The held-frame and related DMA/VM
regressions also pass. The raw dispatcher result retains an inherited 0241
state label; its source pins, six named tests and clock log identify the actual
0242 execution. Native compilation and all physical behavior remain unproven.
