# C4 handler wait correction, prepared offline

The actual C4 frontend returns from `waitUntilScheduled` and `waitUntilCompleted`
while the corresponding client handlers can still be blocked. The GPU/core
completion and asynchronous Objective-C handler delivery are different stages.
The existing core wait only covers the former. Apple specifies that
[scheduled waits include scheduled handlers](https://developer.apple.com/documentation/metal/mtlcommandbuffer/waituntilscheduled%28%29)
and [completion waits include completion handlers](https://developer.apple.com/documentation/metal/mtlcommandbuffer/waituntilcompleted%28%29).

This is a reproduced API behavior defect, not proof of the handset's five-second
stall. The frozen 0314 SpringBoard observation trial remains unchanged and still
needs its own authorization. This correction is a separate, uninstalled C4
candidate; it must not be substituted into 0314.

## Reproduction and correction

The host test extracts the actual methods from the exact C4 source used by
0310–0314, SHA256
`0cfb2ac2a1bcac321a888a5f8fdc93fcf7279bbc9e83c5c59e52f69ae5056195`.
Its fake core separately gates GPU scheduling/completion. A real dispatch
handler signals that it has entered and then waits on a test semaphore.
Three independent waiters call the production wait method while that handler
is held. All three returned early for both methods, on normal and error paths.
The test records the result before releasing the handler.

Patch `0011-owned-desktop-handler-waits.patch` counts admitted scheduled and
completed handlers under the existing condition lock. Normal callers wait for
the requested stage and its handlers to finish. Each handler decrements its
count and broadcasts on exit, including exception unwinding. Existing FIFO
submission, callback order and slot repayment stay in place.

A callback cannot wait for its own return. A thread-local scope therefore
allows the existing same-buffer reentrant behavior while still waiting for
GPU progress. The scope is installed on the thread actually invoking the
client handler, including when a client completion queue is selected, and is
restored on exit. A callback for buffer A cannot bypass buffer B's handlers.
The scope is a linked stack so nested callback contexts remain distinct.

## Validation

The final ASAN/UBSAN driver reproduced four baseline failures and passed nine
candidate scenarios:

- Scheduled and completed waits each hold three waiters until the client
  handler exits, on normal and error paths.
- A scheduled handler can wait on its own scheduled stage, but its completion
  wait still blocks until GPU completion; subsequent completion delivery runs.
- A completed handler can wait on its own buffer without deadlocking.
- A handler waiting on another buffer does not bypass that buffer's held handler.
- An already-admitted late handler is included in the project's late-handler
  extension. This does not assert that Metal defines late registration.
- The prior FIFO/multiple-waiter/handler-order regression also passes. The
  error-path waiter in that harness now starts after commit, removing a
  pre-commit race in the test setup.

Patch replay and reverse dry-run passed; the other seven prepared frontend
files are unchanged. ARM64 iOS 16 compilation, linking and strict bundle
signature verification passed. The binary is 429,712 bytes, SHA256
`2f7891bf7372de4cb805767cb76d6d06ed930c6884cebcd94d3ddf7562d8ba4b`.
It fits the existing 430,080-byte executable allocation with 368 bytes spare.
That fit alone does not prepare or authorize a device installation.

All 568 core/frontend imports resolved against the actual preserved 20H392
cache and exact owned core. The five new imports are `__tlv_bootstrap`,
`_objc_begin_catch`, `_objc_end_catch`, `_objc_exception_rethrow`, and
`_objc_terminate`; none is missing. There was no new CI or phone operation.
Host completion is simulated; real GPU scheduling, callback latency and FPS
remain unqualified for this candidate.

## What the five-second trace still does not measure

For 0313's fourteen near-five-second completed-buffer creation gaps, the prior
buffer's observed lifetime has median 36.616 ms and maximum 196.546 ms.
The interval from that buffer's completion log to the next logged creation has
median 4.971686 s and minimum 4.786308 s. Most of the gap lies outside the
recorded lifetime of that prior completed buffer. This does not exclude other
uncommitted or incomplete work.

The `made` timestamp is assigned after the superclass acquires a command-queue
slot and after `hakios_metal_cb_new`; waiting before either returns is invisible
to that timestamp. The completion log is emitted before Objective-C client
handler delivery. Also, the existing `hm_fps_waited` timer starts after the
frontend condition wait; it excludes that wait and the new handler drain.
A near-zero printed wait cannot rule out blocking there.

0314 should first establish observer activation, SpringBoard input receipt and
main-loop progress. A later C4 comparison can use this correction with direct
allocation-entry, callback enqueue/start/end and whole-wait spans if the
runtime evidence points to this path. No wait timeout or refresh policy was
shortened based on the five-second number.

## Evidence and isolation

Private artifacts: `research/tmp/c4-wait-audit-20261114/`.

| Receipt | SHA256 |
| --- | --- |
| Baseline reproduction | `4282f37843b7164e5a9b0289403d17b99bfca7fe5f59ebf2069316046bf0a7fc` |
| Nine candidate scenarios | `c7f6fdab8174b703094742bf95c4a2e370c2b9a9ff973fcdec44306d6249d739` |
| Prepared eight-file candidate | `bb1967a4e5eb08ff6de5ee13b7d264af8d1711e244e7b83ec9f77bb943a74031` |
| Native build | `9fc1d6ec7cefbe3738b320a20ba22ba6ca16c066dc6b0069e489206eaf7b9b56` |
| Actual OS imports | `ded0264f96e368dbd65ddad6a558ccac9a8db429f7608d2134d7d5ac1e9ef300` |
| Gap decomposition | `028cca4abbb1679c56697ee7c8bd469d601e07ddeb3f87643b20786084efb92f` |

A 20 MB offline batch plus the existing 512 MiB 0314 reserve was admitted at
499,419,611,136 accounted bytes. All 65 frozen 0314 inputs were checked again;
the original backup hash was independently recomputed by the actual-OS audit.
No 0314 approval or execution claim exists at this checkpoint. The earlier
driver import failure is retained; the final test is self-contained and uses
the exact production methods and callback scope. The initial host/native checks
are retained, and the final receipts above identify the complete tests.
