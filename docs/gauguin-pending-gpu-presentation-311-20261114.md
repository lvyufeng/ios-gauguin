# Preserve a held frame while its GPU fence is pending

The completed 0309 boot recorded a GPU-read refusal. Its framebuffer timer
still retired the held frame after that refusal, so a last submitted frame
could disappear without ever reaching the pixel copy. The source path is
unconditional retirement after `present`, whose per-layer guard can return
early. This is a specific correctness defect; it does not establish that
this defect explains all the reported lag. That trial's gestures also ran
with display power requested off, as recorded in the
[0309 results](gauguin-unattended-gpu-309-results-20261114.md).

Patch0233 is a follow-up to source310. Code commit `ee0b1af` has now been
locally linked and packaged as an independently reviewed 0311 candidate.
It has not been executed on the phone. The separately prepared 0310
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
The reference manifest, inputs and reference files remained unchanged. These
selected-file checks are separate from the subsequent local link below;
neither is a clean CI build or a device result.
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

## Linked and reviewed 0311 image

The native link uses the same verified 0301 object list, flags and libraries
as 0310. Five implementation objects differ from that original build: three
unchanged 0310 replacements, plus the freshly compiled GPU and framebuffer
objects for patch0233. A new version object supplies the unique identity
`xnu-local311-75192593c4454281a8b4d3aeefc7779e`. The retained version template
still carries its old date; use this identity and the manifest's creation UTC.

The existing 0310 baseline reproduction was reused rather than written
again. Its complete bytes still match the original unstripped 0301 kernel
after normalizing only the 16-byte `LC_UUID`, and all of its original link
inputs retain their recorded hashes and modification times. The source union
of source310 plus the small overlay was checked across 5,336 entries. This
link retained and rechecked 6,511 inputs, including source, replacement
objects, original objects, flags, libraries and receipts. No full clone,
clean rebuild or new GitHub Actions run was performed.

| Artifact under `research/tmp/pending-311/` | Bytes | SHA-256 |
| --- | ---: | --- |
| `local-link/kernel.development.gauguin` | 17,365,752 | `4cdb2a5f60802f082f16788ea928a395e86cd0e055e9a652bd09dcda68fc4190` |
| `ui311-image.img` | 20,054,016 | `6ba24020212e5dcc8858e17ace112e865991b51c13dfe28641513a0c298ffd74` |
| `local-link/build-manifest.json` | 2,794,925 | `c5079951137e80cbbaff8ec44c9bd2cf897ef97b34793e86d0f71c127a9a6cad` |
| `ui311-review.json` | 1,859 | `acdef8d010db5321ce81537c5dfa224d36a0e5aa2b99720e302c66edcc6369a4` |

Packaging preserves the exact 606-byte 0310 command, including `swp=3`,
`sweetnvt=0` and `sweetgpuasync=1`. The shim, DTB, all firmware contents and
physical addresses, full ADT and low-PAS request are unchanged. The payload
was built in memory and written once inside the boot image, avoiding a
redundant payload file. A separate parser checked the outer header/padding,
every embedded kernel segment directly against Mach-O, the entry point,
managed RAM, firmware ranges and low-PAS zero tail. There are no chained
fixups and no undefined symbols. All five expected new guard/render/cancel
symbols have addresses inside executable Mach-O segments.

Private link/package/review scripts are `relink311.py`, `package311.py` and
`review311.py` in the same directory. Their SHA-256 values are respectively
`8960e975ae21a016e58ba82a939c22f75fe0e9ebbf5f7196ee144780c9490e39`,
`da8540d4d71672536c3589a20cb4e06d8d510a7f90bd6ba6c1267705eb31f177` and
`c83b127c157c8bf419c69920cab94190f15e6d1f2c660661227bed7392a268f6`.
The scripts refuse existing build/image outputs. Image metadata SHA-256 is
`f16e8f82bea109581ec4e6acbe8adef7d6ab7b12d506d871c265e68c7e131978`.

The 600,000,000-byte link/image/capture batch was separately admitted at
499,392,094,208 bytes accounted. It includes the pending 0310 trial's entire
536,870,912-byte capture reserve. The retained link outputs and boot image
use 61,787,407 file bytes; scripts and receipts fit the remaining allocation.

## Device and next action

The phone was read-only checked as `recovery`; no partition write or boot
occurred during this work. All 93 frozen 0310 input pins, including the
original backup, were rehashed unchanged (17,288,627,432 bytes). There is no
0310 `approval.json` or execution directory. Ready receipt SHA remains
`431efde8befffb4577c4378d68e2a154e7ed31e5bfb2b6affb022e6b0dca813f`.

The 600,000,000-byte offline batch was admitted before creating this sparse
worktree, including 536,870,912 bytes reserved for the pending 0310 capture.
Original backups, current rollback files and all active pins were preserved.
After the source/test milestone, the same 536,870,912-byte reserve was
admitted at 499,388,981,248 bytes accounted. After linking and packaging, it
was admitted again at 499,453,988,864 bytes against the 500,000,000,000-byte
project cap. Only about 9.14 MB remains beyond that reserved capture budget;
another build batch must pass a fresh capacity check.

First run the exact reviewed
[0310 display-wake trial](gauguin-display-aware-wake-310-20261114.md) only
when its matching approval arrives. Do not substitute 0311 into that scope.
It will establish whether the unattended script actually produces repeated
frames while the display is on. The reviewed 0311 image is then available
for a separately prepared comparison of pending-to-copy behavior, frame
gaps and GPU/CPU timing under the same workload. It has no execution plan or
approval yet. Physical touch,
physical refresh, high refresh and smooth 60 Hz remain unqualified.
