# Preserve a held frame while its GPU fence is pending

The completed 0309 boot recorded a GPU-read refusal. Its framebuffer timer
still retired the held frame after that refusal, so a last submitted frame
could disappear without ever reaching the pixel copy. The source path is
unconditional retirement after `present`, whose per-layer guard can return
early. This is a specific correctness defect; it does not establish that
this defect explains all the reported lag. That trial's gestures also ran
with display power requested off, as recorded in the
[0309 results](gauguin-unattended-gpu-309-results-20261114.md).

Patch0233 is an offline follow-up to source310. It has not been linked into
a boot image or executed on the phone. The independently prepared 0310
display-wake trial remains frozen and awaiting its own exact-scope reply.

## Frame and lock behavior

The new path is enabled only when held presentation, the desktop compositor
and `sweetgpuasync=1` are all enabled. A frame guard first checks every held
layer under the GPU lock. If any layer is pending it polls the existing
owner once with `wait=false, reap=false`. A pending result copies no layer
and releases the GPU lock. A faulted layer or a reportedly completed owner
with a still-busy layer is rejected, rather than retried indefinitely.

Once all layers are ready, the guard keeps the GPU lock for the entire
presentation. Per-layer guards borrow that lock, preserve their read trace
spans and do not recursively acquire or release it. The prepublication CPU
token retains the existing rule that it must not unlock a newly published
GPU lock. The default synchronous path still uses its original layer guard.

A pending frame remains the single active frame in a deferred slot. The
next eligible software refresh resumes that same frame, without counting a
second consumption. A newer accepted swap supersedes it; an invalid swap
does not. Client removal and display-off cancel the deferred slot. If a
new swap, close or sleep occurs while the frame is local to the callback,
the retry admission rechecks those conditions and retires the old frame.
Each prepared frame retains its client as well as its surfaces, preventing
client-pointer reuse during registration checks. Releases occur outside the
framebuffer lock, after the GPU guard has ended.

The existing accounting equations remain valid:

```
submitted = replaced + consumed + canceled + pending
consumed  = retired + active
```

The deferred frame counts as active. There is at most one pending frame
and one active frame; the deferred slot is the active frame between calls,
not another queued frame. `SWEET FB GPU RETRY` reports retry and waiting
counts. Pending attempts do not advance `presents` or the software clock's
copy count. These counters still describe software work, not panel scanout.
In the new path, guard timing/refusals are counted once per frame; completed
per-layer read spans and byte/layer copy statistics remain available.

## Verification

The new host fixture extracts the actual table lifetime, frame preparation,
swap, take, render, finish, cancellation and GPU guard implementations. It
passed 9,612 assertions under AddressSanitizer and UndefinedBehaviorSanitizer.
Cases include a ready first layer with a pending second layer, repeated
pending beats followed by completion, accepted and rejected replacements,
close/sleep both between beats and before requeue, client lifetime, terminal
faults, inconsistent completion and CPU-token publication. A competing
writer cannot acquire the GPU lock during any ready layer copy. The fixture
also preserves the original lifetime cases and concurrent producer checks.

The existing complete GPU IOUserClient host integration test passed 10,946
assertions across submit, synchronization, queues, imported surfaces, fault
retention, BO capacity and compositor ownership. Host completion, objects,
locks and pixel copying remain seams; neither test runs an Adreno or XNU VM.

Both changed implementation translation units passed native ARM64 compilation
against the verified 0301 reference build's 2,133 header/configuration inputs.
The reference manifest, inputs and reference files remained unchanged. This
is a selected-file compile, not a full link, clean CI build or device result.
The source overlay contains only eleven selected files, not a full clone.
Exact patch replay changed only `GauguinGPU.cpp`, `SweetFramebuffer.cpp` and
`SweetSurface.h`; the reverse dry run also passed. All 228 series entries exist.

Private receipts are in `research/tmp/pending-311/` in this worktree:

| Receipt | SHA-256 |
| --- | --- |
| `source-state.json` | `c02d8da284ee41215973259e4e21c0507af2b0e98c2703254115e5991344ad66` |
| `host-v1.json` | `7b8db3f25e1a938e7d83f6f748d5918cb66de46e1fecb8428fcbd089496676c0` |
| `native-v2/result.json` | `bfe586caf7f7029f1c68e2e209a48c48d8b8aa298cca6610079780810aadca62` |
| `iokit-v1.log` | `08b2b84121c310af7573cc5f626ed92c1e85aae0a606e473dcf28e06f75f87ac` |

Patch SHA-256 is
`4b9ce9fe000dee5c582e1152d88c26a0b49790e379b89a7e9384d38fb09f135d`.

Reproduction from the retained source overlay:

```sh
python3 tests/test_gpu_pending_present.py --candidate-root research/tmp/pending-311/source
XNU_SOURCE=research/tmp/pending-311/source python3 tests/test_gpu_iokit.py
```

## Device and next action

The phone was read-only checked as `recovery`; no partition write or boot
occurred during this work. All 93 frozen 0310 input pins, including the
original backup, were rehashed unchanged (17,288,627,432 bytes). There is no
0310 `approval.json` or execution directory. Ready receipt SHA remains
`431efde8befffb4577c4378d68e2a154e7ed31e5bfb2b6affb022e6b0dca813f`.

The 600,000,000-byte offline batch was admitted before creating this sparse
worktree, including 536,870,912 bytes reserved for the pending 0310 capture.
Original backups, current rollback files and all active pins were preserved.
After this work, the same 536,870,912-byte reserve was admitted again at
499,388,981,248 bytes accounted against the 500,000,000,000-byte project cap.

First run the exact reviewed
[0310 display-wake trial](gauguin-display-aware-wake-310-20261114.md) only
when its matching approval arrives. Do not substitute this unbooted code
into that approved scope. It will establish whether the unattended script
actually produces repeated frames while the display is on. A subsequent
candidate can then include this patch and measure pending-to-copy behavior,
frame gaps and GPU/CPU timing under the same workload. Physical touch,
physical refresh, high refresh and smooth 60 Hz remain unqualified.
