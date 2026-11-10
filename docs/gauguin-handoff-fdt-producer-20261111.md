# Original-FDT and loader ownership capture producer, 0252

The [0251 RAM review](gauguin-current-preflight-and-ram-20261111.md) found that
static recovery data cannot qualify the lower candidate pages: six dynamic
pools have unknown placement at the iOS handoff. This change supplies an
optional loader-side producer of the original ABL FDT and loader context.
It does not resolve every dynamic owner, admit more RAM or change the working
0250 image. A kernel reader and physical capture are still required.

Active worktree: research/tmp/gauguin-memory252-worktree-20261111, branch
codex/gauguin-handoff-fdt-20261111, parent410a8c0. Implementation
dee42315bbfd2499d0851f799e7ff95c6c261220; golden-fixture correction
e53d9eeaaa858d26f41f264bcc8191a8e45efd77; final source
a4e29f00b7d5e362d96fd3a0e977415c391e57a0.

## Producer and failure boundaries

mkpayload has a default-zero handoff_fdt_capacity option. With PAS enabled,
a nonzero page-aligned capacity from 16 to 768 KiB creates one zero-backed
/chosen/GauguinHandoffPending property. The complete enlarged ADT must still
fit the existing one-MiB bound. No new payload version, segment, boot argument,
physical base or managed-memory size is introduced.

The new loader first validates the request and existing PAS owner with the
actual handoff context, before copying any kernel destination. It then copies
the original FDT into the normal high-memory ADT allocation, writes the
context header and publishes /chosen/GauguinHandoffFDT last. Normal PAS metadata
commit follows; the kernel branch occurs only after both commits succeed.
No mapping, firmware operation, secure call, PAS data access or allocation/free
decision is added.

The source payload is unchanged. The input's PAS tail is never accessed.
The commit revalidates the original context and copied request before its
first write; rejection preserves the copied ADT. Invalid capture requests also
stop loader_announce from modifying input diagnostic arguments. These are
validation/publication guarantees; hardware faults during a copy are not a
transactional RAM rollback mechanism.

The producer requires the proven PAS baseline for an enabled capture. An
absent request leaves the legacy paths selected. Prepublished input, malformed
or nonzero requests, bad capacity, insufficient capacity, missing PAS, tampered
plans and repeat commits are refused. There is no truncation fallback.

## Wire version1

The property is160+capacity bytes, little-endian. Parse fields as bytes rather
than assuming a naturally aligned uint64_t structure.

| Offset | Field |
| --- | --- |
| 0 | Magic GHFDREQ1 before handoff, GHFDOWN1 after complete copy |
| 8 | uint32 version1 |
| 12 | uint32 flags;1 means COMPLETE_COPY_ONLY |
| 16 | uint32 actual FDT bytes, initially0 |
| 20 | uint32 reserved capacity |
| 24,32,40 | FDT source PA, input payload PA, input payload bytes |
| 48,56 | Actual shim PA and extent, including its reserved storage |
| 64,72 | Managed-memory base and size; a domain, not an occupied allocation |
| 80,88 | Copied ADT PA and complete size |
| 96,104 | Boot-args PA and topOfKernelData |
| 112,120 | Proven PAS subrange PA and size |
| 128,136 | Framebuffer range used by the console; no new scan-rate claim |
| 144 | End of loaded segments/assets, also the copied ADT start |
| 152 | Reserved zero uint64 |
| 160 | Complete original FDT, followed by zero unused capacity |

The FDT is copied intact, including unresolved size/alloc-ranges declarations.
COMPLETE_COPY_ONLY is not complete ownership resolution or a RAM whitelist.
Parent/child ownership can overlap, such as the input image and its PAS
subrange. Future reclaim logic must preserve live subowners and require their
release; a copied source record alone does not make that source reclaimable.

## Host and native evidence

DSH executes the actual loader and helpers under ASan/UBSan, replacing only
privileged instructions, stop/final-entry boundaries, linker-image bounds and
logical input-PA resolution with declared host seams. The captured bytes,
header, PAS commit order, destination checks and error paths are actual C.

Sixteen capture cases pass: capacities16/256/512/768 KiB; malformed headers,
nonzero body/reserved fields, prepublished input, missing PAS and a too-large
valid FDT. Plan-byte and destination corruptions, repeated commit and original
source preservation are checked. The PAS input tail is PROT_NONE. The old
actual loader reaches the final branch without publishing the requested
capture and gives functional RED42. These are host controls, not a phone boot.

The retained eight PAS groups /88 metadata cases and actual legacy loader
controls pass. Four command-ABI groups and17 firmware payload tests pass.
The PAS golden fixture originally still supplied an800-byte command; it now
supplies the identical valid607-byte prefix while retaining the original
golden digest. Overflow refusal remains separately tested.

The full AArch64 shim links successfully with no undefined symbols and no
ABS64 relocations in C objects. Its Image is233,472 bytes, SHA256:
9a802d924bfdce64ec7fdb8ce426dc89a2a5975ad1eeb4582b9f179b512922f4.
The image remains below the linker addressing bound. Compiler stack reports
give a conservative8,048-byte loader-C-path bound, including17 ADT recursive
frames and auxiliary frames, within the32,768-byte reservation. This is
static native evidence, not EL1 execution/latency acceptance.

## Actual payload and FDT corpus

With capture disabled, the current packer reproduces the entire real0250
payload byte for byte, SHA256:
189a88aafb532c3ef6eadb7be7695d64fdc18a203f5f6f2efcf75eb196ad8a57.

The enabled local payload uses the same0250 kernel
dc220b5b24c38f0bd641c2a41693ba664447d18a0735e8c342df6b2fbfd8cae8,
607-byte command, managed range, segments and five exact firmware assets.
The only ADT additions/changes are the capture property and two existing PAS
request values for the enlarged input extent/tail.

At768 KiB capacity, ADT size grows11,652 ->798,280 bytes and topOfKernelData
grows by786,432 bytes. Those additional pages stay reserved. Managed size is
still6,441,402,368 bytes; this reduces the boot's otherwise free prefix space,
not increases RAM admission. Payload20,480,000 bytes, SHA256:
552043b116a285fb50894501353060e58cabb866f19754d99002f25bc4b5df0b.

The fresh251 recovery FDT is588,757 bytes. The first corpus attempt requests
256 KiB under an initial512-KiB maximum; actual PAS planning succeeds but
capture correctly refuses with PAS_RANGE. The maximum and requested corpus
capacity are then raised to768 KiB. The failure and partial artifacts remain
retained; it is not reported as a passed capture.

The final local model changes only that FDT's two chosen initrd address values.
The actual C planner accepts it with21 fixed reservations and six unresolved
dynamic pools. The input/FDT/shim addresses are modeled. This is not an
observed iOS bootloader allocation or a newly recovered physical RAM region.

## Execution and independent review

| DSH stage | PID | Exit | Result |
| --- | ---: | ---: | --- |
| Software v1 | 22964 | 1 | Legacy golden still requests forbidden800-byte command |
| Software v2 | 23529 | 0 | Corrected legacy/15 capture/command/assets/native checks,383 pins,13.530 s |
| Production v1 | 24746 | 1 | Actual588,757-byte FDT exceeds initial capture reservation,387 pins |
| Software v3 | 25328 | 0 | Final16 capture cases, command checks, rebuilt native shim and production corpus,391 pins,5.925 s |

The final capacity change affects the new capture branch; retained legacy and
firmware results are not presented as repeated runs. Original logs/receipts
remain available. Codex rehashes final inputs/results/binaries, records the
intentional later changes to historical-stage inputs and independently checks
the enabled payload prefix, unchanged command/segments, zero PAS tail and
the two-field-only modeled FDT modification.

Private evidence: research/tmp/dsh-handoff-0252-capture in the active worktree.
review252-v1.json SHA256:
41edfdd51b406e6a2da43241cfdc2e6a6e840eac63e30d1b5053b99de81e341e.

## Remaining work and preserved baseline

A read-only kernel consumer still needs to validate the ready property,
sizes/version, live boot context and captured FDT, and expose a bounded
capture path. An unpublished request must remain an explicit missing result.
Do not read the original low FDT through a new mapping, infer dynamic placement,
or allow the record to change VM admission.

The pending0240 plan still needs its genuine write reply and exact paired239
trial first. Then fresh post240 staging and its own consent precede the real
0250 desktop trial. This producer remains separate from that baseline; it
cannot replace the pending trial. Later physical memory work needs actual
handoff capture, remaining owner/release evidence, hole-aware mapping and
allocation-integrity/pressure/DMA validation.

No XNU source change, full kernel build, combined boot image, kernel consumer,
device command, userdata write, boot, CI run or push occurs here. Original0250
image18d3196f, pending240 proposal, backups and MAIN's original mkadt.py diff
remain unchanged. The full GPU/RAM/storage/peripheral/physical-high-refresh/
daily-phone objective remains active.
