# From task sampling to compositor presentation

The full phone goal includes real GPU rendering, correctly recognized usable
RAM and storage, peripherals, sustained power management and 90/120 Hz operation.
Offscreen pixel tests alone do not establish desktop acceleration or daily use.

The 0237 trial independently verified R8, RG8 and BGRA8 task inputs, plus the
original FP16 and five CA scene pixel arrays. It failed after releasing the
original task VA in the RGBA16F case. Kernel 0238 now caches its read-only kernel
alias before that release. The unchanged probe is running against that kernel;
all five input formats, final ownership release and native counters must pass
before treating the lifetime fix as physically qualified.

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
