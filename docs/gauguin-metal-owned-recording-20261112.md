# A619 Metal recording ownership foundation

The `a619-ownership` core profile keeps command buffers, native queues and their
GPU transport alive through deferred recording and completion. It addresses a
prerequisite for asynchronous desktop rendering. The core subsequently passed
an [isolated real-device test](gauguin-metal-owned-hardware-20261112.md) from a
private library path. The normal desktop still uses its previous core;
asynchronous desktop composition remains unqualified.

## Changes

`0003-owned-deferred-recording.patch` follows the existing A619 device patch.
The graphics-images patch is excluded from this profile. Exactly four of the
228 prepared core files change; C API declarations remain identical.

- Queued jobs, synchronous recorder invocations and completion handlers retain
  the C handle. Application ownership is released separately. Pending counters
  are incremented after successful insertion and decremented before the job's
  handle lease is released. Worker exceptions mark recording as failed.
- Each recorder worker owns its state independently, with a per-recorder thread
  identity. Captures and leases are destroyed outside the recorder mutex.
- The queue and all its command buffers share queue control and GPU ownership.
  Recording mode is frozen when the first command buffer is created. Repeating
  the current mode is allowed; changing it reports an error.
- The last release from a recorder or completion callback transfers native
  storage to a process-scoped reaper without allocating a queue node. Shutdown
  joins the native waiter while its queue object is still alive, before queue
  destruction and GPU release. External closure is synchronous.
- Deferred pre-submit refusal, command-BO failure and transport submit failure
  complete on the native completion FIFO. Unsubmitted failures do not wait on
  a GPU fence or insert a null BO in the reuse pool. Synchronous recording keeps
  its existing inline error callback behavior.
- All eight synchronous encoding entry points use the recorder FIFO. Worker
  errors are returned to the caller's thread. Append also drains and retains
  its source; source mutation must be externally excluded during append.
- External command-buffer release waits through callback completion even when
  native status is already terminal. A completion-context release is
  nonblocking. Own-callback waits return, including nested callback scopes.

The default `a619-baseline` and `a619-graphics-images` source outputs were
regenerated and checked byte-for-byte against their previous patch sequences.
The installed baseline's 228 source hashes are unchanged.

The storage-budget correction already present in the ownership worktree was
reviewed and its integration test rerun. A linked worktree now accounts the
canonical main checkout; an invalid Git lookup cannot fall back to counting
only a small linked worktree. The ownership runner requires that corrected
whole-project admission before allocating its build output.

## Executed validation

Private evidence is under the ownership worktree's
`research/tmp/metal-ownership-v1/implementation-20261112/` (`W` below).
Original 0297/0298/repeat2 captures and the main `tools/mkadt.py` edit remain
untouched. No original baseline fault scenario was rerun.

`W/host-01/result.json` records 20 passing positive scenarios against the first
candidate. Source review then added nested completion scopes, synchronous
exception propagation and ordered indexed-draw refusal. The first candidate,
logs and exact test/runner source snapshots remain preserved.

`W/host-02/result.json` records 23 passing positive scenarios. Final source
review made recorder stop nonblocking from every recorder/completion context,
including a foreign recorder; external stop still waits for worker exit.
`W/host-03/result.json` records **23/23 passing positive scenarios**, exit 0,
against that final source. The v2 source and native build remain preserved.
The actual whole core (eleven translation units plus the real C API included
by the test translation unit) ran under ASan and UBSan, C++17, `-O1 -g`, with
other warnings fatal. The host-only unused `chipKnown` helper is excluded from
unused-function warnings; no production source was changed for that warning.

Coverage includes deferred and synchronous success, refusal, command-BO
allocation failure and submission failure; final-owner release inside a
callback; wrapper release before command-buffer completion; external release
blocked until a gated success/error callback returns; separate recorder
identity; nonblocking release from another recorder; FIFO encoding and actual
FakeGpu fill bytes; mode freezing; worker and synchronous invocation
exceptions; allocation failure during actual recorder insertion; caller error
propagation; source-drained append; copied render-pass arguments surviving
wrapper release and actual FakeGpu clear pixels; nested callback waits; and
ordered indexed-draw refusal. Expected blocking cases include positive release
signals. Each scenario runs in its own bounded process. External transport
counters verify all queues and BOs close, with no live BO at transport teardown.

`W/compatibility-final.json` records baseline/graphics profile equivalence, four
ownership source changes, unchanged C declarations and baseline preservation.
`python3 tests/test_storage_budget.py` exited 0 after review.

Final native build `W/native-03/result.json`, exit 0:

- 12 fresh ARM64 objects, iOS 16 deployment target, `-O2 -Wall -Wextra -Werror`.
- Linked against the existing 13 AIR/NIR/IR3/Mesa archives from the pinned
  `build-v2/build-ios` tree. No archive was rebuilt or downloaded.
- `libGauguinMetalCore.dylib`: 8,407,792 bytes, SHA-256
  `c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674`.
- Build identity `8a71fe61aded108fa9ba5a22`; code signing and strict signature
  verification passed. All source, archive and header input pins remained
  unchanged. Xcode's iPhoneOS 26.5 SDK was used with an iOS 16 target.

Initial batches were admitted with 2,147,483,648 planned bytes against the full
500,000,000,000-byte project limit. The final host/native batch was admitted with
1,073,741,824 planned bytes. Each host runner saved its actual admission in its
output directory. No native kernel build or GitHub Actions run occurred.

## Remaining GPU work

`W/frontend-prerequisite-audit.json` verifies all eight prepared frontend source
pins and records the following source observations. CoreAnimation frontend
admission and wait ordering (C4) remains a prerequisite
before enabling deferred/asynchronous desktop rendering. Its existing held
and ordinary commits do not share one atomic admission decision, and its
single-token `_sent` semaphore does not describe the pre-submit window to
multiple waiters. The current native frontend builder also pins the old core
hash, so this new core must not be substituted into an existing device plan.

Next: add a separate frontend profile with one ordered held/ordinary admission
path, broadcast commit-reached/completed state, honest scheduled/completed
waits and completion-handler ordering; validate the real frontend against
gated core operations; then build a matched bundle/package. Only a separately
reviewed device trial can establish actual CoreAnimation rendering, frame
cadence, physical input behavior and useful GPU acceleration.

Host sanitizer results establish the tested ownership and ordering contracts.
They do not establish general race freedom, arbitrary application wait-cycle
freedom, arbitrary C++ allocation recovery, complete Metal support or phone
performance. Encoding/mutation remains externally serialized per handle;
standalone resources outside queued work still require a live device.
