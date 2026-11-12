# Ordered desktop Metal frontend candidate

The `gauguin-ca-owned-c4` frontend now admits held and ordinary command buffers
through one serial queue. It is an offline desktop candidate linked to the
ownership core that passed two isolated A619 hardware trials. The installed
desktop still uses its earlier bundle and core; desktop GPU composition and
90/120 Hz remain unqualified.

## Source and behavior

`graphics/hakios-metal-ca/patches/0010-owned-desktop-commit-order.patch` applies
to the exact eight-file prepared desktop frontend audited in
`research/tmp/gauguin-metal-ownership-worktree-20261112/research/tmp/metal-ownership-v1/implementation-20261112/frontend-prerequisite-audit.json`.
Only `HakiosMetalCA.m` changes. `tools/prepare-metal-ca-c4.py` rechecks all
eight original file hashes before applying the patch with no fuzz, then proves
the other seven files remain byte-identical.

The queue enables the owned core's deferred recorder before its first command
buffer. Every `commit`, including one waiting for a shared event, enters a
single frontend FIFO under the queue's admission lock. The worker emits any
framebuffer turn work, waits for captured event values, submits to the core,
and drains that command buffer's deferred core work before announcing
scheduling. A deferred error that never reaches the GPU announces its terminal
stage from the completion callback.

Each buffer has broadcast `NSCondition` state for commit reached and completed.
Multiple scheduled and completed waiters can observe the same stage. Handler
admission uses these frontend stages, with a per-buffer serial delivery queue
preserving scheduled-before-completed invocation even when the client's chosen
completion queue is concurrent. The client's queue is retained while used.
The completion callback updates state before queuing handlers, so a handler
may safely call `waitUntilCompleted`. Pre-commit wait calls retain the existing
diagnostic return behavior.

## Local verification

`tests/test_metal_ca_c4.py` extracts the actual queue and command-buffer
methods from the prepared Objective-C source. Its fake core gates event reach,
GPU scheduling, completion and an ordinary error independently. The host test
passes under AddressSanitizer and UndefinedBehaviorSanitizer: an ordinary
buffer cannot bypass a held buffer; six scheduled waiters and three completion
waiters all release at the correct stages; scheduled, late scheduled,
completed and late completed handlers execute in order on a concurrent client
queue. The terminal error wakes a scheduled waiter, and a duplicate commit
does not submit again. The original host fixture compile failure (missing a
test-only protocol declaration) is retained in `host-01`; the corrected
`host-02` compiles and exits 0. This exercises the extracted method bodies,
with fake GPU/core operations.

`tools/build-metal-ca-c4.py` compiles the eight-file candidate for ARM64 iOS 16,
links the exact 8,407,792-byte ownership core, and signs and strictly verifies
the desktop bundle. Its runtime search path is
`/usr/local/lib/gauguin/owned`, the private library directory already checked
on the phone. The first local native build used the old runtime search path;
it is preserved as `native-final`. The corrected `native-final-v2` artifact is
428,624 bytes, SHA-256
`98ddaed6ab92c8de470b4036447be81a6c3854ffbc07d65773c8f85eea476f87`.
The bound core SHA-256 is
`c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674`.
Only the five expected optional M2V hooks remain weak/dynamic.

The read-only `abi-v2` check resolves **all 563** core/frontend imports against
the actual preserved iOS 20H392 cache or the exact owned core. It reads the
16 GiB full-volume backup and the cache's 2,710 image records; there are no
missing strong imports or unresolved weak additions. Relative to the old
desktop bundle, the new binary adds `_dispatch_sync` and `_objc_release_x21`
and drops two semaphore imports; the actual cache check resolves the additions.
Symbol resolution does not establish runtime behavior.

Private source, build, host and ABI receipts are under
`research/tmp/metal-ca-c4-20261112/`. The final receipt hashes are:

| Receipt | SHA-256 |
| --- | --- |
| Prepared source | `3c8591ef1cf01e5d0bc1f03d2a7ead6cefa171eaaff50024a7997fb51146c6b8` |
| Sanitized host gate | `56eda405a2ef4bb8eba46ae265101249177a12ad294610a121e392b3f145b1cd` |
| Final native bundle | `5d0c19f082083a847578afedcb373da3b5194085a2e1a673c9d4cbac1007874f` |
| Actual OS import audit | `a8ddc2945704caef0b8c3775961a6c163f6742600eb83991185cae791f13eace` |

No phone write, boot or CI run occurred for this frontend. The next acceptance
step is a fresh, reversible device package that installs the matched bundle,
uses the private owned core, and captures actual CoreAnimation desktop pixels,
callback timing and frame pacing. Only after that path is correct can a
separate 90/120 Hz modeset and optical display-link test use the panel's
advertised timing catalog. Physical refresh, input latency and smooth daily
operation remain open.
