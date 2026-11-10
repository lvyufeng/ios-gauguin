# Metal bootstrap ownership candidate, 0245

Source commit `ad9eca4` on `codex/gauguin-metal-bootstrap-20261111` adds an
explicit root-to-compositor readiness handoff above 0244. This is source,
host-test, native translation-unit and userland-build progress. No complete
0245 kernel or boot image has been built, and nothing has run on the phone.

## Implemented behavior

Patch 0212 adds an exact 24-byte root request at selector `0x7c`, plus a small
state helper. It activates only with the existing compositor pilot and `gmt=2`.
The previous root diagnostic and EAGL handoff retain their existing behavior.

The mode-2 root client must complete 8–64 successful native submissions. The
bootstrap program performs the existing eight native compute/render/pixel
checks, then supplies its exact completed-job count. The driver verifies that
count against its own per-client counter, records the current native fence and
returns an epoch. This arms the handoff; it does not yet make the compositor
eligible to open the GPU.

Readiness becomes true only when that same root owner closes and all its
buffers are cleaned up successfully with unchanged completed-job/fence values.
A duplicate arm, submission after arming, failed cleanup or runtime stop cannot
publish readiness. A new root owner invalidates previous readiness and starts
a new epoch. Epoch overflow is refused. Existing root privilege, protected
backboardd provenance, exclusive ownership and DMA fault retention remain in
force. This is a coordination mechanism, not a new privilege grant or a kernel
verification of pixel values.

The new `gauguin-metal-bootstrap --bootstrap245` binary uses the unchanged
qualified A619 core and the original eight actual GPU/pixel stages. Its
separate build mode removes the old diagnostic's 90-second initial delay and
sets a 30-second alarm. It checks the exact mode-2 boot arguments, root role,
program name and 128 MiB hard memory limits. The ordinary `--metal223` path
retains its original delay and behavior. The bootstrap's success log means
the checks passed and teardown was requested; kernel close/admission evidence
is still required to prove the handoff on hardware.

## Verification and limits

Strict replay from pristine `1b191cb5` applies all 204 patches. The resulting
5,332-file source SHA256 is
`509f4f1da97ff081b2174af23ca4de94a3ac8f285dcebc971ad9912c8ae7e58e`.
Only `GauguinGPU.cpp` and the new `SweetMetalBootstrap.h` differ from 0242.
The public wire/state header matches the header emitted by the kernel patch.

DSH's actual-driver host checks cover normal handoff, duplicate arm,
post-arm submission and failed cleanup: 211 assertions under ASan/UBSan.
The original driver functionally rejects the new arm with exit 42 under the
positive expectation. The new path also checks malformed wire shapes and
fields, early compositor denial, forbidden compositor arm and invalidation
when a new root owner opens without qualifying.

All existing IOKit cases pass, including queue ordering, readonly task input,
fault retention, slot saturation, the original six-fence EAGL handoff and early
task-VA release. The wire/runtime test reports 17,214 assertions plus 72
service-health assertions. A focused profile check preserves the actual
hardware submit/add/drop/surface, heartbeat, mapping and board/runtime bodies
against 0242; the expanded seventeen-selector sampler passes 95 controls.
These use typed seams and a CPU clock, not real GPU execution.

`xnu-check-tu.py` derives the successful 0242 native recipe and checks 2,130
header/config inputs. The changed driver compiles to an ARM64 Mach-O object,
356,064 bytes, SHA256
`508553955ef118865061ae79ff6a79b42e1d62854791fd46796ffe2210f0e85c`.
All 5,334 recorded source/tool inputs and protected reference files were
independently rechecked. This compile retains 1,272 diagnostics, including
existing headers and an existing IOReturn format warning. It is not a full
kernel link or hardware result.

The signed iOS bootstrap is 115,968 bytes, build
`e412469fc63787adad4de7fb`, SHA256
`2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c`.
Its compiler/linker emits no diagnostics. The unchanged core is
`8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1`.
DSH resolves all 286 bootstrap/core imports against the verified 20H392 backup,
using 35 export images. No strong or weak import is unresolved.

Evidence remains private in the 0245 worktree at
`research/tmp/dsh-bootstrap-0245-owner`. Final step lineage:

| Stage | Actual result | Retained evidence |
| --- | --- | --- |
| v5, PID 87579 | terminal 1 | Strict corrected replay, new/old dispatcher cases and existing driver/runtime tests pass; an inapplicable historical profiling comparison fails afterward |
| v6, PID 88455 | terminal 1 | Applicable 0242 comparison/sampler and native driver TU pass; the orchestration helper then lacks its core-path variable |
| v7, PID 88806 | terminal 0 | Only the unfinished native bootstrap build resumes, with 260 unchanged pins |
| ABI v1, PID 89154 | terminal 0 | Fresh-cache import resolution passes, with 268 unchanged pins |

Earlier failures remain available: fixture struct/function name collision,
copying unused header helpers into the main translation unit, expecting the
new wire-shape error from the old unsupported API, and an ambiguous kernel
boolean expression rejected under `-Werror`. Those were corrected without
weakening the new wire checks. The historical profiling test was specific to
the pre-profiling source; its replacement preserves every applicable hardware
body and runs its complete sampler controls against 0242.

Codex independently rehashed the current v5/v6/v7/ABI inputs, logs, complete
source, native object and bootstrap. `review245-v1.json` SHA256:
`d2c39236bd5567b0cb6f87726920bfe595f4bed751daf9095960b91861512cb6`.
The failed stage receipts retain their actual terminal status; they have not
been relabeled as successful whole stages.

## Next integration

The existing backboardd job still explicitly injects the old EAGL admission
library, and the kernel can append it as well. Its worker would compete with
the new Metal frontend after readiness. The next candidate must disable that
automatic injection in the new mode and remove the old job/cache environment
entries for that mode. The protected proxy and executable checks do not depend
on loading that library and must remain intact.

The desktop frontend also needs a bounded wait for this new readiness gate
before returning from its first device construction. Its current single open
could return nil too early and become cached by Metal. Coordinate the root
bootstrap job, exact hard memory policy, frontend wait and single system plugin
publication before any physical desktop trial. Compositor task input, shared
output and producer/presentation completion still require the planned tests.

No device commands, writes, reboots, CI builds or pushes were performed. The
pending 0240 proposal is unchanged and still awaits the genuine reply; do not
repeat its question or stale it with another boot. Its exact paired physical
0239 kernel must run first after that reply. The full daily-phone, memory,
storage, peripheral and physical high-refresh goals remain unfulfilled.
