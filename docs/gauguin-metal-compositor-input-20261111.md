# Compositor readonly task-input candidate, 0248

Source 228372eab3db0b591c1fdefb3aeeed95a414eff1 on
codex/gauguin-metal-compositor-input-20261111 lets the new Metal desktop owner
import readonly caller-backed surfaces through the existing qualified mapping
path. It changes one kernel source file. This candidate has host/native-unit
evidence and has not run on the phone.

## Behavior and scope

The previous transport refuses a generic readonly task surface for the
compositor even at the surface-description request. The actual old-driver
control reproduces that refusal after successfully completing the root
bootstrap and opening the compositor client.

Patch 0214 admits that input only when the client is the compositor,
gMetalBootstrapMode is enabled and the root bootstrap is ready. Existing
protected caller and owning-task checks, exclusive GPU ownership and clean
root handoff remain prerequisites. Root diagnostic behavior is unchanged.
Legacy compositor mode continues to refuse generic task input.

The new branch reuses the existing descriptor prepare/reference, physical
scatter-page validation, readonly GPU PTEs, independent readonly kernel alias,
byte limits and cleanup path. Mutable generic task backing and readonly
IOBuffer-backed surfaces remain refused. The compositor cannot obtain a
writable CPU alias, request CPU write preparation, or list the borrowed BO for
GPU writes through the submit interface.

Readonly describes this client's permissions. It does not prove that another
process cannot update the backing or that every application's producer
synchronization has been implemented. The change supplies neither general
application GPU access nor asynchronous completion. The current synchronous
transport and global copy lock are unchanged.

## Evidence

DSH replays the pinned XNU base and all 206 patches. The resulting 5,332-file
source has SHA256
2e62225c17d0886bdd018a13fd1e958f9def5c8dabc7f888e07a79f7da6ca80f.
Only iokit/Kernel/arm/GauguinGPU.cpp differs from the 0246 kernel source;
frontend, core library, framebuffer, runtime and surface implementation remain
byte-identical.

The new host fixture executes the actual root bootstrap, client admission,
surface description/import, mapping, submit and close methods under ASAN/UBSAN.
IOKit, credentials and hardware remain typed seams.

| Scenario | Assertions | What is checked |
| --- | ---: | --- |
| New desktop | 1,223 | 30 layouts across 1/2/4/8/16-byte elements and six page biases; metadata, readonly PTEs, handle reuse, write refusal, wrong-task refusal, early original-VA release, balanced cleanup and 12 malformed inputs |
| Legacy compositor | 38 | Root-to-compositor handoff still works; generic task input stays refused |
| Unarmed root | 33 | Eight completed root jobs without explicit readiness do not admit the compositor |
| DMA failure | 66 | Uncertain DMA retains descriptor wiring, surface alias and GPU mapping |

The old 0246 driver returns the named unsupported result at the first
compositor surface-description request; the negative control exits 42.
That is a functional difference, not a compilation failure.

Existing root/client cases also pass, including readonly inputs and fault
retention, queue namespaces, 1,024 live BO slots, owner-task checks and early
VA release. The surface wrapper runs 318 assertions. The independent task-map
test runs 151 assertions and reuses actual host virtual addresses in five
layouts; its XNU VM behavior is still modeled. Existing bootstrap regression
scenarios pass. No real GPU sampling pixels are produced by these host tests.

Native ARM64 compilation uses the successful 0242 kernel recipe, checks 2,130
header/config inputs and records 5,334 source/tool inputs. The GPU object is
355,896 bytes, SHA256
186e2b54fe2d867c656c2d3ff6ca260bdd44bfed37f5f071fcbe6a293b8f6a7e.
Its 378 undefined symbols exactly match the 0246 object. The surface method is
present once. Reference files remain unchanged. Existing compiler/header
diagnostics are retained in the native log. This is not a full kernel link,
boot image or hardware result.

## Execution record and next action

DSH v1, PID 1895, exits 1 after clean source replay: the new C++ fixture needs
the struct tag because ggr_submit also names a C function. V2, PID 2657, exits
1 after compilation: the old driver refuses the earlier describe call, before
the initially placed negative-control check. Both fixture issues are corrected
without changing the kernel candidate. Original outputs remain preserved.

V3, PID 2887, exits 0 in 15.531551 seconds with 407 unchanged pins. It reuses the
completed pristine replay and performs the corrected functional control,
candidate/regression tests and native compile. Codex independently verifies
the source snapshots and exact one-file difference, final stage pins/logs,
5,334 native input pins, object hash and native symbol. Private evidence is at
the 0248 worktree's research/tmp/dsh-input-0248-compositor.
Review SHA256:
b83f90b38a87dc084bd59858519bc0ce1b05829a1013ce50d06969bfcf7063bf.

Next, assemble a complete reviewed desktop candidate with the 0244-0248
frontend, root bootstrap/router, launch configuration and shared output/display
handoff. The pending 0240 shared-output proposal still needs its genuine write
reply and exact paired 0239 trial first. No other boot should stale that delta.

Physical acceptance must show native jobs from actual backboardd, populated
icons/widgets, correct effects, repeated transitions, stable shared output and
buffer reuse. Then measure the complete latency chain and qualify asynchronous
overlap and usable 60 Hz before physical 90/120 Hz. An import-unit result does
not establish these outcomes or daily-phone readiness.

No device command, userdata write, reboot, CI build or push occurred.
The physically qualified 0239 kernel, installed 0237 root and pending 0240 plan
remain unchanged.
