# Current scanout, present cadence and high-refresh audit, 0297

This audits the current materialized 0297 source and the latest actual 0293,
0294 and 0296 captures. No device command, boot, write or network operation was
performed. The pending 0297 plan is unchanged and has not run: `ready297.json`
records `reviewed297-awaiting-individual-consent`, zero boots and zero
performed device writes. Its one temporary kernel boot remains Codex's separate
approval.

All `SRC/...` references below are under
`/Users/baai/Project/ios-gauguin/research/tmp/gauguin-fault297-worktree-20261111/.deps-cache/p0-20261105/source297`.
The applied 0297 source head is `6d78eb7`; its 0220 patch is
`xnu/patches/0220-gauguin-fault-subgroup-profiling.patch`.

## Conclusion first

1. The current desktop is a 60 Hz software-present profile, not a 90/120 Hz
   profile. The 0297 command ends in
   `sweet_dyld_probe=1 sweeteagl=2 gmt=2 sweetfb_hz=60 metal_fps`; it does not
   pass `sweetfb_hold`, `sweetfb_phase`, a panel mode or a scanout rate
   (`research/tmp/dsh-fault297-native/image-result297.json`). The plan is still
   `reviewed297-awaiting-individual-consent`
   (`research/tmp/dsh-fault297-trial/ready297.json`).
2. On that profile the desktop defaults enable held presentation and the
   absolute software clock. The software beat is fixed at 16,667 us. The 60 Hz
   argument only makes the copy divisor one; it does not select a 60, 90 or
   120 Hz panel mode.
3. The present path can CPU-copy valid layers' dirty rectangles into the live
   framebuffer; checks can skip a layer. There is no panel-scanout
   acknowledgement. A held surface is retired after `present()` returns, not
   after panel consumption is confirmed.
4. Recent Metal frontend windows report zero `presented` events while still
   reporting command buffers and GPU-timed draw passes; framebuffer swaps also
   occur. Their relationship is unproven: correlate the actual command, surface
   and swap IDs before attributing interactive lag to CPU or GPU.
5. The panel catalog contains 90/120 Hz configurations, but this audit found no
   running mode-set implementation or measurement of the current physical
   refresh. A boot argument, a 16,667 us timer, the `hz=19199967` log field or a
   fastboot/TWRP display state must not be counted as high refresh.

## Effective 0297 defaults

| Item | Current effective value | Deciding source |
| --- | --- | --- |
| Desktop predicate | true for this command: loader probe 1, EAGL request 2, Metal request 2 | `SRC/bsd/kern/kern_exec.c:5706-5710` |
| Held presentation | on by default on the desktop predicate; explicit `sweetfb_hold=0` opts out | `SRC/iokit/Kernel/arm/SweetFramebuffer.cpp:576-586` |
| Absolute present clock | on by default on the desktop predicate; explicit `sweetfb_phase=0` opts out | `SweetFramebuffer.cpp:630-651` |
| Timer period | 16,667 us, both legacy timeout and absolute beat | `SweetFramebuffer.cpp:88`, `:643-647`, `:697` |
| Copy divisor | `sweetfb_hz=60` gives `fFlushTicks=1`; values below 60 use `60/hz`, and all values above 60 also give 1 | `SweetFramebuffer.cpp:604-606` |
| Presented geometry | logical 1125x2436; real panel 1080x2400 at offset 22,18 | `SweetFramebuffer.cpp:94-99`, `:565-574`; `dsh-guard-profile-0296/trial-v3/observer.txt:4674` |
| Present operation | per-row CPU `memcpy` of the record's dirty rectangle into `fPixels` | `SweetFramebuffer.cpp:1387-1391` |
| GPU submission | synchronous single ring; submit polls to completion while holding the global GPU lock | `GauguinGPU.cpp:276-287`, `:553-560`; `gauguin_gpu_runtime.c:94-160` |
| Mode query ABI | selectors 74 and 79 return zero by design | `SweetFramebuffer.cpp:1590-1605` |

The default in `start()` without the desktop predicate is still 10 Hz
(`sweetfb_hz` default 10, divisor 6). The 0297 profile overrides it to 60, so
60 Hz is the effective cadence here, not a general driver default.

## Software cadence, copy and presentation

`vsyncFired()` runs on the timer work loop. With the absolute clock it advances
one or more logical beats, delivers the same payload to all registered
notification types, and only consumes a copy slot when the frame is dirty and
the beat is due (`SweetFramebuffer.cpp:700-781`). The clock header deliberately
calls these "software beats", not panel timing (`SweetPresentClock.h:1-3`).

Actual 0296 timing confirms 60 Hz software callbacks:

- `vsync interval 16666 us over 1800 frames` and
  `vsync interval 16667 us over 600 frames`
  (`dsh-guard-profile-0296/trial-v3/observer.txt:4735`, `:4788`).
- `callbacks=7200`, then `7500`, with `copies=4`, then `5` over the same
  interval (`observer.txt:4700`, `:4731`, `:4770`).
- The logged `hz=19199967` is not a refresh measurement. It is the timebase
  recovered by dividing elapsed ticks by `dframes * 16667 us`
  (`SweetFramebuffer.cpp:919-928`); it is the ~19.2 MHz timebase expressed in Hz,
  not a frame rate.

When a held frame is due, `takeHeldFrameLocked()` moves pending to a single
active frame and clears dirty (`SweetFramebuffer.cpp:1130-1139`). The timer then
calls `present()` outside the framebuffer lock and retires the frame after it
returns (`:992-1023`). While active, another swap may replace the pending frame
and increment `replaced`, but it cannot create a second active frame
(`:1206-1213`). This is a one-pending/one-active queue, not a scanout queue.

For a held frame, `present()` checks the already-held pointer's ID and retains
it; only the legacy unheld path resolves an ID through the surface table
(`SweetFramebuffer.cpp:1118-1127`). It takes the global GPU lock through
`SweetSurfaceGPURead` and, if further validation succeeds, copies each row of
the dirty rectangle (`:1262-1393`). The copy
target is the same memory the panel scans continuously. A full 1080x2400 frame
is 10,368,000 bytes, or about 622 MB/s of write traffic at 60 copies/s and about
1.24 GB/s including the source read. That arithmetic is not a measurement; the
source currently records no copy duration and no copied-byte count.

Two consequences follow directly from the source:

- The copy can overlap the panel's scan of the same buffer. There is no
  double-buffer latch and no scanout-position check, so tearing is possible and
  is not detected by any current counter. This is a source-level risk, not a
  measured observation.
- If the copy or the GPU-lock wait takes longer than the next beat, the held
  queue replaces the pending frame. That drops a frame, but the current logs do
  not report copy duration, so the drop cannot be attributed.

### `presents` is not a successful-present counter

`presents` is incremented before the frame is taken
(`SweetFramebuffer.cpp:773-781`). If a held frame is still active,
`takeHeldFrameLocked()` returns false, no `present()` call occurs, and
`presents` still increments. The same applies to an allocation failure in the
legacy path. Actual 0296 shows the divergence: `presents=7` against `copies=4`
(`observer.txt:4731`, `:4736`), and `presents=8` against `copies=5` (`:4770`,
`:4789`).
0293 shows a much larger divergence (`presents=125` at
`trial-v1/observer.txt:6564`, `copies=45` at `:6550`), so historical `presents`
values are not comparable with `retired`, `copies` or screen updates.

Neither `presents`, the clock's `copies`, nor `retired` proves a successful
pixel copy or panel scanout. `copies` advances when a record is selected,
before `present()`; `retired` follows its return. `present()` returns `void`
and can skip every layer, for example after a failed GPU-read guard or failed
geometry validation. Measure successful copied bytes separately.

## Held-surface and fence retirement

The hold is real and is the right ownership primitive. `sweet_surface_hold()`
increments both the surface-table user count and the object retain count;
`sweet_surface_drop()` releases both (`SweetSurface.cpp:210-236`). A plain
`sweet_surface_copy()` retains only the object, so the last client can still
unpublish the ID. `sweet_fb_frame_prepare()` holds every enabled nonzero layer
before the swap is accepted (`SweetFramebuffer.cpp:1079-1112`), and
`finishHeldFrame()` drops those holds after `present()` returns
(`:1152-1162`).

The captures are consistent with prompt retirement and balanced ownership; they
record no retirement latency, so they do not prove promptness:

- 0293: `submitted=46 replaced=0 consumed=45 retired=45 canceled=1 rejected=0
  pending=0 active=0` (`trial-v1/observer.txt:6567`).
- 0296: `submitted=6 replaced=0 consumed=5 retired=5 canceled=1 rejected=0
  pending=0 active=0` (`trial-v3/observer.txt:4792`).

There is no panel fence in this path. The GPU side is synchronous: a native
submit returns only after the completion value and shadow pointer match
(`gauguin_gpu_runtime.c:94-160`), and `GauguinGPUSurfaceBegin()` merely takes the
global GPU lock and refuses a surface whose `gpuState` is nonzero
(`GauguinGPU.cpp:276-287`). The trace does not establish how each swap relates
to its producer's GPU completion. This is not a scanout completion contract. The held frame
protects the CPU reader from ID reuse and object free; it does not protect the
panel from a concurrent overwrite, and it does not tell us when the panel
consumed the pixels.

## What the latest actual runs do and do not show

| Run | Actual result | What it means |
| --- | --- | --- |
| 0293 | 46 swaps, 45 consumed/retired, no rejects; the user still reported unchanged lag (`dsh-swap-flags-0293/user-observations293-performance.json`) | The sampled counters are consistent with consumption and retirement, but do not establish per-frame correctness or localize lag. The 46 swaps may be concentrated in short bursts; no per-frame copy or input timing exists. |
| 0294 | Frontend `fps: 0.0 frames/s ... (0 presented, 2 command buffers)`; 13 native submissions, all accounted; `desktop_pixels_qualified=false`, `FPS_qualified=false` (`dsh-metal-metrics-0294/physical-review294.json`, `post294-capture-v1/current-backboardd.log:92`) | This counter did not record presentation in the sampled windows; command buffers and draw passes were still recorded. Its relationship to framebuffer swaps and interactive latency remains unknown. |
| 0296 | Same zero-presented counter; at the 8400-callback sample, `submitted=6`, `consumed=5`, `retired=5`, no rejects; guard groups total 1.992 s over 10,936 calls in a ~600 s service window (`observer.txt:4792`, `:5878-5883`) | The measured groups total about 0.33% of elapsed service-window wall time; fault checks account for 1.106 s. The sample was not an interactive latency test and cannot rule guard checks in or out during interaction. |

The 0296 guard arithmetic is: 37,417,239 + 105,937,916 + 339,865,729 +
353,392,812 + 50,274,375 + 1,105,505,677 ns = 1,992,393,748 ns, or 1.992 s.
Against 600 s that is 0.332%, an average of 182 us per guard call. This is CPU wall
time including instrumentation, not GPU time, and covers the measured runtime
guards rather than all `gfw_faults` callers. This whole-window average cannot
bound per-frame latency during an interactive burst. The 0297 fault-subgroup
patch is useful for attribution, not for a speedup claim.

The frontend reports 1-2 command buffers over sampled multi-second intervals and
zero counted presentations while the framebuffer receives swaps. The command
selects both EAGL injection (`sweeteagl=2`) and the Metal request (`gmt=2`).
These counters do not identify the producer of each swap or exclude a Metal
render-to-IOSurface handoff; correlate actual command, surface and swap IDs.

## High-refresh evidence

There is real panel capability evidence, and no real mode-operation evidence.

Positive, capability only:

- The panel source advertises `qcom,dsi-supported-dfps-list = <120 90 60>` and
  a 120 Hz timing with 1080x2400 active, 33-line vertical front porch and two
  dynamic-clock entries
  (`dts/gauguin/dsi-panel-j17-42-02-0b-dsc-video.dtsi:55-76`).
- The 0295 cached DTB model matches twelve advertised modes, including 90 and
  120 at two clocks. Its captured active mode is `[60, 136659]` with
  `active_type=8`, and it records `physical_refresh_qualified=false` and
  `modeset_qualified=false` (`dsh-mode-contract-0295/qualification295.json`).
  The matching contract document also states that clock generation, scanout
  latch and application cadence remain unqualified
  (`gauguin-mode295-worktree-20261111/docs/gauguin-display-timing-contract-20261111.md:34-35`).

Negative, current implementation:

- No MDSS/DSI/panel mode driver was identified in the reviewed XNU source. `SRC/bsd/dev`
  contains the GPU runtime and board code, not a display controller, DSI host or
  panel command path; the only `AppleCLCD` implementation is this framebuffer
  stub. It describes the panel as scanning the ABL's memory "by itself"
  (`SweetFramebuffer.cpp:1-4`, `:27-30`).
- `kSweetFBTimingInfo` (74) and `kSweetFBDisplayModes` (79) are explicitly
  all-zero stubs (`SweetFramebuffer.cpp:1590-1605`). The driver never parses the
  DTB mode list, never selects a mode and never writes a panel timing register.
- `sweetfb_hz` changes only `fFlushTicks`, a CPU copy divisor. `sweetfb_hz=120`
  still arms a 16,667 us timer because the period is the fixed
  `SWEET_FB_VSYNC_US` (`:88`, `:604-606`, `:643-647`). The present clock is
  explicitly "software only" and prints `physical_rate=unqualified`
  (`:646`, `:988`).

Therefore the panel can plausibly do 90/120, but the current OS has no path to
put it there and no evidence it is there. A genuine high-refresh qualification
needs an actual mode set plus an independent scanout/vblank measurement. It
cannot be established by the DTB catalog, a boot argument, a software callback,
a reported timebase, fastboot/TWRP's display state, an emulator or a timer.

What remains unknown about the physical panel:

- the live active mode and refresh after this boot (the 60 Hz actives are
  captured DTB metadata, not a live readback);
- the panel's scanout position and vblank phase relative to each CPU copy;
- whether a copy tears, and whether the panel latches a frame atomically;
- DSI clock, lane state, underrun/error counters and any DFPS/self-refresh
  transition;
- whether the bootloader's panel configuration persists across the handoff, and
  which panel variant is physically installed;
- input-to-photon latency. No current log contains a touch timestamp paired with
  a panel-visible result.

## The most actionable offline change

The missing measurement is a bounded per-present trace with an accurate success
counter. It is small, host-testable, and requires no ownership relaxation.

Design a bounded trace that distinguishes attempted, skipped and successfully
copied layers. It should contain at minimum:

- `seq` (swap ID), `submit_ns`, `take_ns`, `copy_start_ns`, `copy_end_ns`,
  `retire_ns`;
- `layers`, `rect`, `bytes` actually copied, and `result`
  (`copied`, `no_surface`, `held_busy`, `alloc_fail`, `gpu_refused`);
- `pending`, `active`, `replaced`, `retired` snapshots.

Emit it at a bounded rate (for example, first 32 records and then every 600th;
independently rate-limit failure samples while preserving aggregate failure
counts), not once per callback. Use the existing monotonic clock. Reuse the
already-held `sweet_fb_frame` and the already-retained surface; do not perform a
second raw-ID lookup, do not extend the hold past `finishHeldFrame()`, and do
not move the drop earlier or later. Correct `presents` so it increments only
when a frame is actually taken, or rename it to `flush_attempts` and stop
reporting it as presented frames.

Maintain bounded aggregate latency histograms and counts for every eligible
frame as well as sampled detailed records: a handful of sampled records cannot
support p95/p99 claims over hundreds of frames. Separate GPU-lock wait from
the bytes actually copied, and measure instrumentation overhead with an
otherwise identical disabled-trace control. A completed attempt with zero
copied bytes is not a successful copy.

This can distinguish submit-to-take scheduling, actual CPU copy duration and
pending replacement. Identifying the userland producer also requires correlating
surface and submission identities. Whether GPU guards or the timer lie on an
interactive critical path remains to be measured.

### Smallest failing host-level checks

1. **Present accounting.** Reuse the extraction style of
   `tests/test_present_lifetime.py` and `tests/test_present_clock.py` to compile
   the actual `vsyncFired` and held-frame helpers against a virtual clock.
   Submit frame A, hold it active, submit frame B, then fire one due tick.
   Current source increments `presents` for B's flush attempt although
   `takeHeldFrameLocked()` refuses because A is active, and no copy occurs.
   In a host fixture that can hold an active frame across a tick, assert that
   a successful-copy counter remains unchanged when take fails. Current
   `presents` counts the attempt, not a successful copy. The actual 0296
   `presents=8`, `copies=5` illustrates differing counters but alone does not
   prove this specific fixture occurred.
2. **Trace completeness.** In the same harness, require exactly one record per
   successful copy, `bytes == sum(w*h*4)` for enabled layers,
   `take_ns <= copy_start_ns <= copy_end_ns <= retire_ns`, and no *success*
   record for a refused or replaced frame. Rate-limited failure records are
   separate. Current source has no record type or fields, so
   this fails at extraction/compilation.
3. **Ownership balance.** For every accepted frame, require the held table-user
   and object references to return to the pre-submit values after
   `finishHeldFrame()`, including `no_surface` and GPU-refusal cases. Assert
   `pending <= 1`, `active <= 1`, and no held pointer remains after retirement.
   This preserves the existing 0293/0296 invariant rather than weakening it.
4. **Mode-claim guard.** A profile/parser check must reject any claim of 90 or
   120 Hz unless an active panel timing was read back, and must show that
   `sweetfb_hz=120` leaves the 16,667 us beat unchanged. Current driver passes
   the beat check only because it has no mode path; the check is there to stop a
   future boot profile from relabeling a copy divisor as a panel mode.

### Trial acceptance criteria

Proposed initial acceptance targets for smooth 60 Hz, to validate against
interactive traces and the actual device before treating them as requirements:

- over at least 600 dirty frames of a scripted animation, after the queue drains
  `retired` equals `successful copies`, `replaced` is under 1%, and
  `pending`/`active` return to zero at the end of each sample;
- submit-to-retire p95 is at most 16.7 ms and p99 at most 33.3 ms;
- copy p99 is at most 8 ms, leaving half a 60 Hz period for the producer and
  scheduling;
- no record has `retire_ns < copy_end_ns`, and the held-reference balance is
  exact across normal, replacement, cancel, client-exit and failure paths;
- input-to-copy timing is correlated with an actual touch/HID marker; a kernel
  copy timestamp without a producer timestamp is not an input-latency result.

For genuine 90/120 Hz, additionally:

- an independent panel readback or TE/vblank counter shows 11.111 ms (90 Hz) or
  8.333 ms (120 Hz) periods, not a 16.667 ms software callback;
- the active DSI timing and clock match the selected mode, and no underrun,
  DSI error or repeated-frame condition appears;
- copy p99 is at most 4 ms at 120 Hz with at most one pending replacement per
  600 frames;
- a physical capture shows distinct frames at the advertised rate without
  tearing. Until those exist, 90/120 remains a panel capability, not a result.

## Risks and boundaries

- The single live panel buffer plus CPU copy is the main correctness risk for
  smoothness: a copy can overlap scanout. The trace will measure copy time but
  cannot prove the absence of tearing; that needs a panel-side signal or a
  physical capture.
- The one-pending/one-active queue intentionally drops stale frames. That is
  safe, but it means low swap rates and high `replaced` counts have different
  causes and must be reported separately.
- `presents` and the `hz=` field in existing logs are misleading. Any prior
  conclusion that used them as frame rate or successful-present evidence must
  be treated as unproven.
- No DTB panel data was added or inferred. The 90/120 entries cited above are
  existing local source or the existing 0295 capture. The audit does not claim
  which physical panel variant is installed.
- The pending 0297 fault-profile plan, its image, approval, outputs and any
  0297 boot decision are untouched. The trace work above is offline and does
  not consume that approval.

The current system has a software-timed copy path and sampled held-frame
retirements, but no successful-copy duration trace or verified panel mode
control. Measure the real copy and scheduling path, then validate sustained
interactive behavior and physical refresh separately.
