# Bounded kernel UI latency capture, 0254

The HakiOS review identified a missing correlated trace of real input, GPU
requests and presentation. This change supplies the kernel portion of that
trace. Source, host and selected native translation units pass; no new kernel
has been linked, packaged or run on the phone. It is not a fluidity result.

Active branch: `codex/gauguin-ui-latency-20261111`, worktree
`research/tmp/gauguin-trace254-worktree-20261111`, parent `5c05a1e`.
Initial source `724f5b7`, integration/fixtures `99b99ad`, fixture correction
`90a38b5`, final native verifier
`857b16ad612e5b053919bc94e877b5d7eaafd22b`.
Kernel patch: `xnu/patches/0216-gauguin-bounded-ui-trace.patch`, SHA256
`d42fdac80b17c102135df85e07dcccfab70075db06bacbf8b3abcc2cc12ab0a5`.

## Capture contract

Tracing is off by default. The existing exact Metal desktop profile plus
`sweettrace=N`, where N is 1 through 16, arms a one-shot capture starting on
the Nth observed physical transition from no contacts to at least one. N=2
can skip an initial unlock gesture. Synthetic input does not trigger it.
This is an observed report boundary, not a measurement of the instant a
finger first contacts the glass.

The capture ends after four seconds, at 4,096 records, on a backwards clock
outside the window, or on a GPU stop request. The first bounded prefix is
preserved; it never silently wraps. Capacity and contention are reported.
Missing endpoints remain unknown. No rearm or runtime user-control API is
added.

Only an enabled, accepted profile allocates its 256 KiB event array. Writers
use a nonblocking atomic try-lock, record numerical IDs and CPU ticks, and
drop a contended record with an observed-loss count. No hot-path allocation,
console output, additional hardware read, DMA operation or sleep is added.
The frozen prefix closes its loss counter before export; late calls cannot
change that prefix. Configuration is published once.

After capture freezes, the existing single log worker prints at most sixteen
records per iteration into the existing console/persistent-log path. No new
disk region or filesystem writer is introduced. Header and footer carry the
version, record count and loss count; the header also carries the kernel's
actual timebase numerator and denominator. A missing footer is incomplete
evidence, not an empty or fast session.

## What is connected

| Boundary | Evidence |
| --- | --- |
| Novatek poll | Start/end of the existing three transfers, decode/report time, status and active mask; no coordinates are logged |
| HID | Report ID carried through the existing work-loop request; dispatch begin/end around the actual callback, then the physical caller's return status |
| GPU API | Request token, PID, selector, time queued and time locked, followed by the existing result |
| Synchronous submission | Before the runtime call and after final cache/state handling; queue fence, native fence and result |
| Shared surfaces | Request token, surface ID, read/write flags, native fence and success for each submitted surface |
| Display | Accepted swap ID, layer IDs, present begin/end, GPU-read lock queue time and end of the protected CPU-read scope |

The shared HID snapshot struct and original entry remain unchanged. A new
kernel-internal traced entry carries a report ID; unchanged frames still
succeed without dispatch. Allocation failure and callback reentry retain
their existing behavior. GPU authorization, synchronous completion, buffer
ownership, failure quarantine, presentation retention and clock policy are
unchanged.

These are CPU-clock boundaries. A submit span includes runtime checks,
polling and cache work; it is not GPU-only duration. A protected read scope
can include sampling, clipping and cleanup. Present returning does not prove
that every layer drew correctly or that the physical panel latched a frame.
Surface IDs alone do not prove allocation-generation identity after reuse.
Temporal proximity does not prove that a touch caused a particular CA frame.
CoreAnimation commit/encoding, hardware GPU timestamps and panel latch still
need their own correlated observations.

## Reader

`tools/ui_trace_log.py SAVED_LOG --out NEW_JSON` accepts the versioned text
prefix. It checks field bounds, record sequence, time window, counts and
footer, and pairs explicit identities for HID/API/submit/present/read scopes.
It retains unpaired endpoints and labels contention and capacity truncation.
It does not emit GPU-only time, display fps or a causal touch-to-frame claim.

`tests/test_ui_trace.py` runs against `--source XNU_TREE`, or extracts the
three actual added source files from patch 0216 for a standalone CI check.
The latter mode needs no downloaded OS artifacts or local XNU checkout.

## Qualification

All test and compiler execution was performed by DSH with the existing full
access configuration. Codex wrote/reviewed the source and independently
checked hashes, compiler dependency files and native symbols. No provider
fallback was used.

The trace core/board tests execute the actual implementation under ASan and
UBSan: disabled/invalid profile and allocation failure, gesture selection,
reinitialization refusal, deadline/capacity/clock/stop boundaries, nonblocking
reentry, eight writers, immutable bounded draining and loss closure. Actual
board printf output passes the reader; nine genuinely changed invalid logs
are rejected. The clock, allocator and kernel profile calls are typed host
seams, not a running device.

The actual HID methods retain their geometry, identity/up, rollback, reentry,
concurrent input and stop-lifetime checks. Added cases verify report IDs at
the real dispatch callbacks, no dispatch for an unchanged frame, rejection
without trace on allocation failure, and no nested callback dispatch.

The actual NVT coordinator/protocol tests preserve unmodified production-pin
rejection with real XNU SHA, plus the existing temporary synthetic-pin flow.
Tracing is modeled disabled in those orchestration cases; positive trace
capture is exercised separately by the core/board and HID fixtures.

The actual GPU transport runs its four existing ownership scenarios with a
trace collector replacing only the trace sink. Desktop: 1,223 ownership
checks, thirty imported layouts, twelve malformed inputs, 38 submit pairs
and thirty surface edges. DMA fault: 66 checks, nine submits and one surface
edge, with memory retained. Legacy/unarmed: 38/33 checks and eight submits
each. Hardware/memory operations remain the existing host seams. Held display
tests pass 3,236 checks and retain the old raw-ID driver's functional RED42.

Native ARM64 compilation passes for all nine affected TUs: core, board, NVT,
UFS logger, GMU owner, BSD initialization, GPU transport, HID and framebuffer.
The reference is the successful 0250 full-kernel recipe, manifest SHA256
`ac4e0db77dfaa611f10f8b6632b7d27fd2e6f930d9a5fb225002cf126723413a`.
There are 2,131 source header/config checks. Compiler warnings remain; this
does not claim a warning-free build.

The native checker now supports a complete candidate tree. Source includes
bind to it; a changed byte-preserving exported HID header is copied into an
isolated include override before the old generated headers. The reference
export must equal its original source bytes, otherwise regeneration is
required. Original generated headers, objects and recipes are preserved.
Both NVT and HID compiler dependency files identify the new override.
All thirteen trace-interface references resolve among these nine native
objects. This is not a whole-kernel link or ABI/boot acceptance.

## Exact execution record

| Stage | Actual result |
| --- | --- |
| Host v1, PID33730 | Exit1, 12 pins, 1.427 s; Darwin rejected enabled ASan leak detection before tests ran |
| Qualification v2, PID34932 | Exit1, 6,333 pins, 4.471 s; strict source staging and core/board execution passed; one malformed-log test accidentally left its input unchanged |
| Qualification v3, PID35477 | Exit1, 6,334 pins, 16.893 s; core/board, reader, HID, NVT, GPU and held-display tests passed; native NVT correctly failed against the old generated HID header after core/board native compilation passed |
| Native v4, PID36309 | Exit0, 6,334 pins, 10.096 s; corrected isolated header binding, all nine native TUs passed |
| Standalone v5 | Launch refused a relative output path before any dispatcher or test ran; retained separately |
| Standalone v6, PID37265 | Exit0, 6,334 pins, 2.627 s; source extraction from patch plus actual core/board/reader tests passed |

Failed stages are retained. Historical pin changes after their terminal
results are recorded, not relabeled as unchanged current inputs. Before this
handoff documentation, final v4/v6 profile pins were independently unchanged;
native source/object/header pins remain valid after documentation changes.
All launched dispatchers and their outer DSH sessions are terminal.

The fresh candidate is a verified 0250 source clone plus strict zero-offset,
zero-fuzz patch 0216: 208 active patches, 5,335 files, twelve changed/added
paths. Source SHA256:
`24577f7277a76e15d84d157ce45a8f1077c22db3bf19b678a6813544782b4f6f`.
The original 0250 tree remains unchanged. No full kernel, combined image,
native frontend rebuild, CI run, push, device command or userdata write was
performed this turn.

## Next action and retained gates

The pending 0240 delta still requires the genuine user reply. Its exact paired
0239 image must run first after installation; then take a fresh root capture,
regenerate/review the desktop installation and obtain its individual write
approval. Qualify the existing 0250 desktop's complete picture before using
0254 to diagnose its latency. Current physical baseline stays kernel0239/root0237.

Before packaging a trace image, complete the whole-kernel build and review a
boot profile that fits the actual 607-byte command limit. The existing 0250
command is already 607 bytes: simply appending ` sweettrace=2` is invalid.
Keep board/GPU/storage/health settings and verify the exact payload-field
round trip; do not silently truncate. Disk free space was about 3.6 GiB,
below the previous fresh-full-build estimate plus its 2 GiB reserve. Existing
artifacts were not deleted. A scoped profile correction and an authorized CI
build are available next work; no new write/boot consent is implied.

Then capture a real gesture, add the missing CA/encoding and hardware-display
boundaries as needed, and choose optimizations from measured gaps. Sustained
correct 60 Hz precedes physical 90/120 Hz acceptance. The full RAM, storage,
peripheral and daily-phone goal stays active; this trace does not complete it.

Private evidence: `research/tmp/dsh-ui-0254-trace` in the active worktree.
Final native result SHA256:
`e3d230a1e0ac52bcad1696d266ad60d9eed375904955b7603c78e55ca0223688`.
Independent `review254-v1.json` SHA256:
`9da2ded9547a977922afecb79bcd27be9bca4f0abfa900aab1ae524268e45eb1`.
The pending 0240 plan9d943e79, 0250 image18d3196f and unrelated MAIN mkadt
diffa74a0418 remain unchanged.
