# Five-second synchronization paths in the actual 20H392 framework

This read-only inspection uses the verified HFSX backup and the installed OS
build's ARM64 shared cache. QuartzCore UUID is
`9e40b2eb260c3af1ae45a1a551a8c1b9`. No phone command, binary patch or new trial
input was used. The 0313 image, observer, executor and ready pins remain fixed.

## What the existing C4 trace proves

The `tl: M made ... committed ... done ...` line is emitted by `hm_completed`.
Consequently the 0310/0312 creation-gap statistics describe buffers that reached
that callback. They do not count all buffer allocations, uncommitted buffers,
or callbacks that have not yet run. Thirty-one completed-buffer records cannot
rule out other work held before commit. The observed five-second spacing is
real, but "the producer created nothing else" needs stronger evidence.

The actual C4 queue reports a 64-buffer maximum. Its completion wait metric
also begins after the frontend NSCondition wait, so it does not measure that
whole wait. Neither fact proves a semaphore starvation or callback deadlock.

## Static synchronization paths

| Function, unslid address | Verified behavior | Limit of the conclusion |
| --- | --- | --- |
| `CA::Render::Context::request_synchronize`, `0x1883281dc` | Constructs a default 5.0-second deadline and 5,000,000,000 ns delay. A positive timeout is capped at 5,000 and multiplied by 1,000,000. One path registers a server callback; the fallback resolves to `dispatch_time` and `dispatch_after` on a global queue. | This function schedules a timeout. It is not itself evidence of a five-second blocking wait on the handset. |
| `CA::Render::Context::wait_for_synchronize`, `0x1883376ac` | Calls the actual `mach_msg` export with receive/receive-timeout flags `0x102` and a 1,000 ms timeout. Checks `MACH_RCV_TIMED_OUT` (`0x10004003`) and a `sync` reply identifier. | Runtime message delivery and the path taken are unobserved. |
| `CA::Context::synchronize`, `0x18843c2d0` | Calls the request and receive helpers, with handling around repeated receive results. `CASSynchronize` also directly calls the request helper. | Call graph reachability does not show which process is waiting during a stalled gesture. |
| `-[CAWindowServerDisplay freeze]`, `0x1884e77dc` | Resolves to `dispatch_time(0, 5,000,000,000)` followed by `dispatch_semaphore_wait`. | It is a concrete five-second wait candidate, but its invocation frequency during these trials is unknown. |
| `CA::OGL::MetalContext::Pipeline::wait_for_completion`, `0x188485634` | Calls `dispatch_block_wait` with the all-ones deadline, then releases and clears the stored block. | This site does not have a fixed five-second timeout. Its block completion still needs runtime evidence. |

External call names were checked against actual cache export tries, including
intermediate import stubs. Merely following a stub to its final internal target
missed several public names in the first pass; the final export report includes
the intermediate exported entries. The kernel's own Mach message header confirms
the receive flags and timeout result constant.

## Next runtime distinction

The actual `CA::Transaction::ensure_implicit` code registers a repeating
`CFRunLoopObserverCreate` observer with activities `0xa0` and order 2,000,000
at `0x1882c71c0`, then calls `CFRunLoopAddObserver`. These call names were also
resolved through the actual CoreFoundation export trie. This confirms the
static observer order used by the 0313 before/after probe; it does not establish
which callbacks execute in a particular runtime turn. Order-export report SHA:
`c064cd3b807379a48c62a9c2347b610092509e6e75805a3ded3aa32936b7bb8d`.

Use 0313's activation and startup logs first. Then compare the kernel queue
progress, public SpringBoard touch entries/returns, main-loop milestones and
completed C4 timestamps. If long main-loop turns overlap the five-second gaps,
the synchronization paths above are specific candidates for a later stack or
call-span observation. If the main loop stays responsive, inspect the compositor
and callback/presentation path instead. A literal timeout value alone does not
justify shortening a framework wait, forcing a clock or claiming a root cause.

## Private evidence

All raw instructions and helper scripts remain ignored under
`research/tmp/cadence-static-20261114/` (about 200 KB before the order census).

- Timeout census SHA256:
  `a0d873998a153b27d0c3cd3cab0f169d2c94fc6905a03e3d97cafee60b689be9`.
- Synchronization callsites SHA256:
  `ecd8ab1f65cc4a18b81132652e563cdd19322f3c844cbe21b449ec91e34a74e3`.
- Wait-site inspection SHA256:
  `2d5c1dd176121747093d7b187592af17678638f05a05c14495232e1bcd1db293`.
- Final export mapping SHA256:
  `712589ee0544e15b225d93a8071707da46cac6649a7a6eec3db33050032baccd`.

This is diagnostic progress toward GPU-backed smooth 60 Hz operation, not its
completion. Physical frame cadence, input responsiveness and full GPU use still
require successful runtime verification.
