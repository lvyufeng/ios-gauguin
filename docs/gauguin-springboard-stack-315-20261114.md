# 0315 candidate: locate the SpringBoard main-thread wait

0314 proved public touch delivery and repeated multi-second SpringBoard
main-thread stalls. Four long before/after-CA observer intervals ended within
419 microseconds of C4 command-buffer creation, before those buffers committed
or completed. The waiting function remains unknown. This candidate adds bounded
stack snapshots to the working observer; it changes no frame-rate request,
GPU policy or application input forwarding.

## Sampling boundary

The existing flush thread samples only between 220 and 270 seconds of the boot
clock, at most once per second and at most 64 times. It requires the body or
before-CA phase and a main-loop turn age of at least 250 ms; this is not a
measurement of how long that particular phase has lasted.
The target is a Mach thread right captured on SpringBoard's own main thread,
with its pthread-reported stack bounds. It refuses the sampler thread itself.

Each attempt initializes storage before suspension, suspends the target, and
rechecks the coherent watch word while the target is stopped. A changed watch
produces a stale-sample record. A valid attempt reads ARM64 PC/LR/SP/FP and up
to 16 monotonically increasing frame records within the registered stack and
a 64 KiB window above SP. VM reads copy 16 bytes into existing sampler storage;
there are no unchecked frame-pointer dereferences.

Every successful suspension reaches exactly one resume attempt, including
state/read errors, malformed frames, clock regression and budget exhaustion.
The 2 ms budget stops additional reads; it cannot preempt an individual Mach
call, so it is not a hard real-time maximum pause. Actual elapsed time is logged.
The target remains held across frame reads: the kernel's temporary hold inside
`thread_get_state` alone would not protect later stack reads.

No allocation, Objective-C call, symbol lookup, formatting or log write occurs
inside a successful target hold. The sampler warms its Mach wrappers, reply-port
path and checked VM reader before its first attempt. Symbol labels and output
are produced after a successful resume. On an uncertain resume result, it emits
one fixed message through `write`, disables further sampling, and leaves the
flush thread in its existing sleep loop without taking process locks or running
thread-exit cleanup. This is a failure state, not a qualified sample.

Stack snapshots perturb scheduling. Their purpose is to identify a waiting
path; any performance observed under this probe requires a later comparison.

## Validation

- The actual C collector and policy passed 269 ASAN/UBSAN assertions covering
  balanced resume attempts, state/read failures, stale watch, malformed and
  cyclic frames, depth/window bounds, time/clock guards, cadence limits and
  disabling further attempts after a resume failure.
- A disposable native Mac test paused only its own main thread, captured five
  frames including its known blocked test function, resumed it, and joined the
  sampler successfully. The final test measured 33 µs for that one capture.
  It used no sanitizer runtime while the real target was stopped; the fake
  failure-path model used ASAN/UBSAN. This does not qualify iOS runtime behavior.
- Existing actual ObjC forwarding/ABI tests passed 117 checks. An additional
  case exercised the actual stack formatter and parsed its output, including
  suppressing formatted output after uncertain resume. The log parser passed
  44 checks for malformed, partial, mixed, mistimed and failed observations.
- ARM64 iOS 16 compilation and strict signing passed. The final library is
  90,416 bytes, SHA256
  `10683efc71f95f1a79563727cfef10374df8d1ec94f6249a83328b7d6660683b`,
  with the existing `/usr/local/lib/gauguin/libGauguinEAGL.dylib` install name.
- All 69 imports resolve against the actual preserved 20H392 cache. The SDK
  rejects `mach_vm.h` for iOS; the final adapter uses its supported LP64
  `vm_read_overwrite` declaration, with compile-time 64-bit address/size checks.
  Actual XNU `thread_act.c`, `vm_map.defs` and `vm_user.c` were inspected for
  hold/resume and read semantics. The first compile failure and earlier receipts
  are retained; the final receipts below identify the corrected build.

The kernel can remain the exact already-run 0314 image; no new kernel or boot
image has been built. The separate C4 handler-wait correction and pending 0311
frame change remain uninstalled. 0314's one-shot permission was consumed and
its original files were independently restored. No 0315 device write or boot
is authorized yet.

## Evidence

Private artifacts are under `research/tmp/sb-stack-315/`.

| Receipt | SHA256 |
| --- | --- |
| Collector and live Mach test v2 | `339cfc6ef581c324baaf16ed4770c05bbcc1036580d9849d727098a506453f48` |
| Actual ObjC and formatter test v3 | `260a1e80313fe82de35bedbf561d05151d60f9f7b9fbb531f06558784f0db821` |
| Native library v3 | `6e21efd8cc82191ca493542a27e996493ea8dde49550db5fd77eea89fe9b92e6` |
| Actual-OS imports | `37ac63ccc25dd8b7ca154e0d47a120fa5ef97bf702f742f136f37bd9b094c45c` |

Standalone parser receipt SHA256: `256cca23e06e09589ed72e5abc9f868e2e6bde0989acff1c43043ce2147e1782`.

A 60 MB offline batch was admitted at 499,580,846,080 accounted bytes before
the sparse worktree and builds. The [0315 fixed trial plan](gauguin-springboard-stack-315-trial-20261114.md)
is now prepared from fresh four-file preimages. Eight-range installation and
restoration fault models, missing-consent/classification checks and wake-log
validation passed. All 70 fixed inputs were independently rehashed.

52 completed-0314 static duplicates were retired with retained identical copies,
freeing 72,978,083 logical bytes. A 450 MB whole preparation/trial batch was
admitted at 499,518,402,560 accounted bytes. The exact capture/log/rollback bound,
including worst-case UTF-8 replacement expansion for the kernel ring, is
385,363,808 bytes. A 384 MiB (402,653,184-byte) trial reserve was separately
admitted at 499,524,509,696 accounted bytes; the observer's Python children use
explicit UTF-8 mode. The current 0314 restored capture, originals, logs and
all pinned inputs are intact. No 0315 approval or execution claim exists.
