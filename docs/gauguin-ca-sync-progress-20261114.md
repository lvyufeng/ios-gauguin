# The CA five-second callback does not always release a waiter

Further inspection of the actual 20H392 QuartzCore code distinguishes its
diagnostic deadline from its reply deadline. The five-second constant in
`CA::Render::Context::request_synchronize` alone does not establish a five-second
blocking timeout. This narrows the runtime question without changing the fixed
0315 trial, its observer, its kernel image or any phone file.

The image UUID remains `9e40b2eb260c3af1ae45a1a551a8c1b9`. The following cases
apply after initial validity and already-satisfied-progress checks. The signed
timeout argument is measured in milliseconds on its positive branch.

| Request case | Diagnostic deadline at request + `0x10` | Reply deadline at request + `0x18` | Consequence |
| --- | --- | --- | --- |
| Timeout is zero | No queued request on this path | No queued request on this path | Branch at `0x188328250` reaches the immediate reply path at `0x188328304`. |
| Timeout is positive | Infinity | Now plus `min(timeout, 5000)` ms | Deadline expiry can cause a reply even when progress is insufficient. |
| Timeout is negative and the diagnostic-level global is at least 1 | Now plus 5 seconds | Infinity | Schedules a check and can report a long synchronization; it does not unconditionally reply after five seconds. |
| Timeout is negative and that global is below 1 | Infinity | Infinity | This branch queues the request without scheduling the five-second callback. |

The default five-second branch stores its two distinct deadlines at
`0x18832843c`. Its dispatch block at `0x1884140d4` tail-calls
`CA::Render::sync_req_timeout` (`0x1883923e4`). That callback takes the context
lock and invokes `CA::Render::Context::check_sync_reqs` (`0x18831105c`).

In `check_sync_reqs`, the first deadline comparison at `0x1883110f8` controls
diagnostic reporting. The second comparison at `0x188311274` controls the
expiry path that can reach a reply. If that deadline has not expired and the
progress predicate is false, execution advances to the next pending request
without replying. The actual diagnostic strings distinguish “long synchronize”
from “synchronize timed out.” These are separate branches, not interchangeable
names for the same event.

Progress uses the requested seed and context fields at `0x38` and, for
render-qualified requests, `0x3c`; `context + 0x130 == 0` is an alternative
condition after commit progress is satisfied. The actual
`increment_commit_seed` implementation increments `context + 0x38`, then calls
`check_sync_reqs(0)` at `0x1882ce24c`. A conditional path in
`CA::Render::Update::~Update` advances `context + 0x3c` and calls the same checker
at `0x1882c28f4`. The second counter is therefore tied to update teardown in
this inspected path; neither counter is evidence of a physical panel latch.

The reply helper at `0x188344658` sends a 36-byte Mach message with identifier
`0x73796e63`. Its call target was resolved through the actual cache export trie
to `mach_msg`. The direct in-image call scan finds progress-driven checks and
the timeout callback. It does not cover indirect calls or other images.

This is static evidence. No runtime invocation of these paths has yet been
proved. The next useful distinction remains the unchanged 0315 stack probe:
if a long SpringBoard turn is inside `Context::synchronize` /
`wait_for_synchronize`, investigate which progress or reply path is missing.
If it is elsewhere, follow that observed stack. Shortening this diagnostic
constant would not by itself establish a fix for the missing progress.

Private evidence under `research/tmp/sb-stack-315/`:

- `sync-callback-path-v2/result.json`, six functions, local symbols, export
  targets and direct in-image references; SHA256
  `fd407dff1a13b21279c5bc9867a5059937081e3ae91fb3ab7ee1661bf49224f8`.
- `sync-progress/result.json`, the two progress functions and actual diagnostic
  strings; SHA256
  `4de737a390a421cb2bfc8fcbc87633d3544007991b499abea1204b6e25abe610`.
- `sync-progress-interpretation.json`, interpretation and source pins; SHA256
  `01e82f3a1fac45d47f2334f259916711df0f0c2e80b85ad7ce81bd57c0919e17`.

All readers completed against the preserved backup. No device commands, new
native build or CI run occurred. 0315 permission remains pending; 60fps and
physical input responsiveness remain unverified.
