# HakiOS pipeline recheck, 2026-11-11

The newly explicit gap is synchronous transport and global serialization.
Connecting a Metal device to backboardd is necessary, but it will not by itself
give gauguin the overlap between CPU work, GPU execution and presentation used
by the reference. This is a source-level finding, not a measured attribution
of all current phone latency.

The GitHub connector rechecked main: it remains
63fc2b4633bac3af8e57dadab9f5a8d4cb940438, dated 2026-11-06. Nineteen fresh
source/document files, 1,282,318 bytes, match their Git-tree blob identities.
This supplements the [previous integration audit](gauguin-hakios-integration-audit-20261111.md).

## What the earlier plan understated

### Submission, completion and copy currently serialize

The current transport, including the 0246 candidate, holds the global GPU lock
while submitting. Its underlying runtime accepts exactly one hardware
submission in flight, polls completion, ring shadow and idle state, and only
then returns the fence. The client queue's counter therefore names already
completed submissions. Its wait request checks that completed counter; it
does not provide an independent asynchronous completion path.

The display's SweetSurfaceGPURead takes the same global GPU lock and retains
it through the CPU copy. Even rendering into another output surface cannot
overlap that copy under the present lock. 0241 fixes surface retention and
0242 fixes the relative timer's accumulated work time; neither removes this
serialization.

HakiOS normally submits ring commands and returns an issued fence, records
that fence on the involved buffers/surfaces, and waits in its presenter.
Buffer close/reaping retains resources while they remain busy. The presenter
has a finite queue and retires surfaces after copying. Its separate
metal_defer option moves command recording to a queue worker; asynchronous
recording and asynchronous GPU submission are different mechanisms.
See [hardware submission](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.adreno.c#L3461),
[buffer/surface fence association](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/drivers/gpu/hakios.gpu.cpp#L1063),
[presenter queue](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L358)
and [deferred recording](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/hakios-metal/src/c_api.cpp#L40).

This is an architectural performance ceiling and a priority after basic desktop
correctness. It does not prove an expected A619 frame rate. Removing a lock or
returning early alone would invalidate current completion/lifetime guarantees.
An asynchronous candidate needs distinct issued/completed state, retained BOs
and mappings, per-output producer completion, bounded in-flight work, close and
timeout handling, and fault quarantine. CPU copies must consume only completed
output without unnecessarily excluding work on other output buffers.

### A fast submission average is not a frame or GPU measurement

Our elapsed whole-request measurements include CPU validation, cache work,
hardware polling and time holding locks. The earlier reduction from 42.3 to
16.9 ms does not establish GPU-only time or 59 desktop frames per second.
A frame may include several submissions and additional CPU/display work.

Even the reference's frames.py explicitly treats Metal draw/idle durations as
unknown when the GLES-only trace is absent; it represents those missing
durations as zero. Such zeros are not measurements of no CPU cost.
See [the script's stated semantics](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/frames.py#L25).
The acceptance trace must correlate touch/HID, CA commit, CPU encoding, issued
fence, actual completion, copy and display timing, and separate frame intervals
from individual submission latency.

### CPU clocks and memory bandwidth are part of the reference configuration

The reference runner specifies a big boot core, eight CPUs and CPU frequency
control, as well as copy workers, caches and display arguments. Gauguin already
uses eight CPUs; that alone does not qualify actual CPU/DDR clocks, bandwidth,
core placement or thermal behavior. The searched tracked gauguin driver/docs
contain no equivalent qualified CPU-frequency acceptance. Do not infer that
clocks are wrong merely from that missing evidence, and do not copy SM7325
register addresses to SM7225.
See [runner defaults and portability fallback](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L66)
and [the board-specific CPU-frequency review](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/driver-review/adsp-battery-cpufreq.md#L226).

Measure these after a correct desktop trace identifies CPU/copy bottlenecks.
They are not a reason to add unqualified clock writes before the pending
shared-output test.

## Connections already identified, still awaiting phone qualification

| Connection | Source/software status | Phone evidence still needed |
| --- | --- | --- |
| System plugin discovery, mobile admission and framework checks | Separate 0244 desktop profile; 0246 publication and finite first-open wait | Actual backboardd discovers that device and submits native jobs |
| Root-to-compositor ownership | 0245 explicit arm/clean close; 0247 single-process root router | Real bootstrap, clean release and compositor open in the same boot |
| Task files, launch cache, memory policy | 0247 local three-plist candidate; existing label policy preserved | Complete reviewed installation, using a fresh post-0240 capture |
| Decoded-image upload | 0244 bounded immediate-upload snapshot for an exact caller | Actual icons/widgets and lifetimes; generic compositor readonly surface gate remains closed |
| Shared output and display lifetime/cadence | Pending 0240 physical test; 0241/0242 source/native checks | Correct output, completion before consumption, buffer reuse and stable intervals |
| Asynchronous submit and independent-buffer overlap | Not implemented by those candidates | New lifecycle design and physical latency/throughput comparison |

See [0247 launch routing](gauguin-metal-launch-router-20261111.md),
[0246 discovery](gauguin-metal-discovery-20261111.md) and
[0245 ownership](gauguin-metal-bootstrap-owner-20261111.md).
These are candidate implementation milestones, not completed desktop bring-up.

## Which success claims are transferable

The reference reports roughly 100-104 fps swipes and 89-91 fps Settings scrolling
at 1125x2436 on A642L. Its 118-120 fps Settings test uses 750x1624 rendering,
a frozen wallpaper and synthetic input. Real-finger dragging is reported at
75-80 fps. Early metal2vulkan figures were faster while the picture was wrong
because less was drawn. Preserve complete pictures as part of performance
acceptance; missing icons/effects must not count as an optimization.
See [the author's conditions, wrong-picture results and remaining stalls](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md).

Its default GLES result also reaches 107-114 fps under different kernel/core
conditions, so API selection alone is not a controlled explanation. Separately,
CA's own animation request rate, its selected frame clock, the software
presenter beat and the physical panel mode must agree; forcing a 120 value
does not establish any of the other layers.

A repository/issue claiming success is insufficient. In issue 46 an MT6833
port claimed stable 60 fps and working peripherals; the maintainer subsequently
identified its submitted log as QEMU and its all-ones hardware reads as no
response. It is excluded as a successful physical case in this review.
See [the maintainer's review](https://github.com/oosexgang/hakios-xnu-kernel/issues/46).
The redwood device status itself still lists unfinished charging, no Bluetooth
and no cellular registration. Its UI result does not establish daily-phone
readiness. See [device status](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/devices/redwood.md).

## Execution order

1. Preserve the existing 0240 proposal. Only a genuine write reply permits its
   installation, followed first by its exact paired 0239 image.
2. Finish one complete desktop package: compositor readonly inputs, actual
   shared output/completion/presentation, and the coordinated 0244-0247 startup.
   Verify populated icons/widgets, colors/effects, repeated transitions,
   lock/unlock and native backboardd jobs together.
3. Obtain an end-to-end latency trace and use it to prioritize asynchronous
   transport, per-surface ownership and reduced global-lock scope, working
   toward sustained correct 60 Hz. Distinguish CPU recording from GPU execution
   and copy.
4. Run controlled cold/warm cache, CPU/core/DDR, copy-worker, scale and wallpaper
   comparisons. Record visual compromises rather than include them silently.
5. Qualify the actual panel's 90/120 Hz mode, scan timing, tearing and long-session
   thermals. The broader RAM/storage/peripheral/daily-phone goal remains open.

Private source proof: research/tmp/hakios-recheck-20261111-v5/source-proof.json,
SHA256 88955e12c10cc0bfecc1e21d08d58bf4c10d32f2f4656e2f114cf4cf4f88dc5f.
Local source pins/static review: pipeline-review.json, SHA256
6fb39b9f6219e0cffa19b731c55b1b618de4c00a32f13a6d43a6263a594f6741.
No new test or hardware performance result is claimed. No device command,
userdata write, reboot, CI run or push occurred.
