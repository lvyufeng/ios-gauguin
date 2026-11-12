# Ordered desktop Metal frontend candidate

The `gauguin-ca-owned-c4` frontend admits held and ordinary command buffers
through one serial queue. It is linked to the ownership core that passed two
isolated A619 hardware trials. A subsequent
[one-boot desktop trial](gauguin-metal-ca-c4-trial-20261112.md) confirmed that
the new backend loaded the private core and completed GPU work, then restored
the original bundle. Desktop pixels and 90/120 Hz remain unqualified.

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
stage from the completion callback. Queue creation also checks `dladdr` for
the exact private owned-core path. It refuses a different loaded core and
reports the actual path in backboardd's log.

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
test-only protocol declaration) is retained in `host-01`; the current
`host-03` compiles and exits 0. This exercises the extracted method bodies,
with fake GPU/core operations.

`tools/build-metal-ca-c4.py` compiles the eight-file candidate for ARM64 iOS 16,
links the exact 8,407,792-byte ownership core, and signs and strictly verifies
the desktop bundle. Its runtime search path is
`/usr/local/lib/gauguin/owned`, the private library directory already checked
on the phone. The first local native build used the old runtime search path;
it is preserved as `native-final`. `native-final-v2` fixed that link path.
The current `native-final-v3` additionally checks the loaded path at runtime.
It is 428,720 bytes, SHA-256
`560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5`.
The bound core SHA-256 is
`c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674`.
Only the five expected optional M2V hooks remain weak/dynamic.

The read-only `abi-v3` check resolves **all 563** core/frontend imports against
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
| Prepared source v2 | `41d0223c7f2c91e7b51fe693fb16b01e127f389ee70e6609d0b241782f28aaf1` |
| Sanitized host gate v3 | `1df633a99fd41b65deb2bbabc1c1e19e69c59c974ce28a78b30de1e4e106a388` |
| Final native bundle v3 | `5b357ac75eea5878dc8a3bccc450fe26464d20dbd161c86d3c1f5f900a37f42a` |
| Actual OS import audit v3 | `4a67085cb9f8809ec94cec52017487e7ca7c51c04a93fe030bf96d9c3ebb533c` |

The frontend build itself had no phone write, boot or CI run. The subsequent
one-boot trial established backend activity, with zero presented drawable
events. Desktop pixels need a separate physical observation. After that path
is correct, a
separate 90/120 Hz modeset and optical display-link test use the panel's
advertised timing catalog. Physical refresh, input latency and smooth daily
operation remain open.

## Historical read-only device delta model

After the offline build, a fresh recovery capture read all 29 selected files
and five directories. Every file hash and the root header matched repeat2's
restored state; no partition write or reboot occurred. The installed desktop
`Info.plist` and `CodeResources` are byte-identical to the new signed bundle.
The installed executable is 428,400 bytes; the new signed executable is
428,720 bytes. Both fit the same allocated 105 four-KiB file blocks.

`research/tmp/metal-ca-c4-20261112/prepare_device_trial_v2.py` read the current
unmounted HFSX catalog and produced an **unexecuted** two-range model:

| Range | Current location | Proposed change |
| --- | --- | --- |
| Desktop executable fork | Block 3,817,791, 105 blocks | 430,080 bytes, with the signed binary and preserved tail |
| HFSX catalog leaf | Block 44,139, byte offset 1,434 | Change the eight-byte logical length from 428,400 to 428,720 |

The total range scope is 434,176 bytes. A virtual overlay re-parsed all
325,681 HFSX catalog records: only this file's logical size changed, its
extents stayed fixed, its content matched the exact signed binary, and the
volume header stayed unchanged. Plan SHA-256:
`886f11d68dbc05c071884431b706c23a83aaea061e3e79793cf1b2781e7a1fd6`.
The current misc marker begins with zeros; a later temporary trial would need
its own 13-byte recovery-marker write.
Fresh capture SHA-256 is
`98968afae8a7a5af6c9378b7b9618b7935325e89806d962975e95e35a5ea1197`.
The complete planned trial batch of one GiB is admitted at 486,109,007,872
accounted bytes against the 500,000,000,000-byte cap.

The exact writer and restoration passed 24 in-memory fault controls, and a
virtual activation followed by read-only HFSX parsing yielded the original
ranges. The one-shot runner refused an absent approval before claiming
execution or opening device IO. The later separately approved
[hardware trial](gauguin-metal-ca-c4-trial-20261112.md) completed this scope
once and restored the old desktop bundle. Its approval is consumed.
