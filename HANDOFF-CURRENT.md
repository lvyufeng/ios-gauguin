# gauguin port: current state (2026-11-04, updated round 480)

> **Completion criterion (agreed with the user): a usable iOS interface is
> visible on the panel - lock screen, home screen or system UI - verifiable by
> screenshot.** Not "SpringBoard renders something"; not "the GPU works".
>
> **Status: iOS boots fully - 433 userland execs, SpringBoard and backboardd
> both alive - and no interface appears. On gauguin it never has.** The Setup
> "Hello" and home-screen milestones in NOTES are from **Sweet (D22AP)**, a
> different board; gauguin's port began 2026-10-19, so there is nothing to
> bisect.
>
> **Everything observable is correct.** SpringBoard makes exactly 33 IOKit
> calls (the same 33 at 1 core and at 8), states `TH_RUN` or waits on an empty
> queue (`msgs=0/0`), and never calls the GPU. It then does nothing at all that
> reaches any log we can read.
>
> **What is needed next is a userspace view of SpringBoard.** The XNU tree used
> here has no `saved_state` in `struct thread` and contains no
> `arm64/saved_state.h`, so the thread dump cannot print a userspace PC; `log
> show` refuses the device's `.tracev3` directory as an archive. Both routes to
> "where is it stuck" are closed in this port.

## Current boot recipe (use this, it is the best measured configuration)

```text
debug=0x8 serial=3 cpus=8 keepsyms=1 -noprogress rd=ufsroot0
unentitled_ios_sim_launch=1 ignition_level=1 ufsrw=1 rootrw=1
launchd_unsecure_cache=1 sweetlog=1 sweetlogms=500
sweetfb_noconsole=1 sweetufsquiet=1
```

`cpus=8` matters: 268 execs / 1591 lines / 109 presents at `cpus=1` became
**433 execs / 1782-2677 lines / 198-225 presents**. Do not add
`-enable_kprintf_spam` or `debug=0xc` at 8 cores; the console flood costs more
than it shows.

Build: `bash deps/build-macos.sh gauguin`, then `cp
xnu/out-gauguin-macos/System/Library/Kernels/kernel.development.gauguin
research/k-proven`, `python3 tools/mkpayload.py research/k-proven
shim/out/sweet-gauguin-new.adt OUT.bin --cmdline "$CMD"`, `bash
deps/shim-macos.sh OUT.bin`.

**Always check the log ring advanced.** A boot that dies before
`sweet_log_start()` leaves the *previous* boot in the ring and the pull returns
it looking healthy - this silently invalidated a whole experiment once. Compare
`flush #` between runs.

## Writing to the iOS root (works, and is reusable)

The HFS+ volume occupies only the front of `sda35`: 17.18 GB of a 114.9 GB
partition, 4,194,304 blocks of 4096.

```sh
adb exec-out "dd if=/dev/block/sda35 bs=4096 count=4194304" > iosroot.img  # ~9 min
hdiutil attach -readwrite -noverify -mountpoint /mnt iosroot.img
# ...edit...
hdiutil detach /mnt
adb exec-in "dd of=/dev/block/sda35 bs=4096 count=4194304" < iosroot.img     # ~9 min
```

Ownership survives as `501:20`, so edited files are accepted by iOS.

## Where this actually stands

**iOS boots and runs on the phone.** Kernel, UFS, HFS+ mount, launchd and
**268 userland execs** come up on a real Redmi Note 9 Pro 5G (`gauguin`,
SM7225 / Snapdragon 750G, DT compatible `qcom,lagoon`). That is more than the
236 in the older log that was treated as healthy, so the boot is complete, not
truncated.

**It does not reach a usable interface.** SpringBoard starts, stays `present`
through t=20, builds **nine threads**, and all nine sit with empty queues
(`msgs=0/0`). It makes **0 GPU calls**. Setup/`buddy` never executes at all
(confirmed in three logs including a 36,093-line one). The panel shows the
centred shape described in NOTES (72) plus black - not a home screen.

**SpringBoard is idle, not wedged.** An earlier reading said it "stops after 33
platform calls"; the thread samples show a process that finished initialising
and is waiting for input.

That is the whole state. Everything below is evidence for it, and the list of
things already ruled out.

## The proven part

Verified on hardware unless marked:

| what | evidence |
| --- | --- |
| kernel boots, banner-checked | every run via `tools/sweet-observe.sh` |
| UFS, HFS+ mount, `vfs_mountroot ok` | NOTES (1)-(20) |
| launchd reaches `ignition sequence complete` | 292 exec calls, 140 distinct processes |
| SpringBoard starts and stays alive | `SWEET PROC: SpringBoard present (t=20)` |
| SpringBoard makes exactly **33** IOKit calls | identical in **19** boots - hard constant |
| SpringBoard opens **2** services, both platform basics | `AppleKeyStore`, `IOPMrootDomain` only |
| SpringBoard makes **0** GPU matches | never asks for one |
| backboardd finds the GPU **213** times | all succeed, 0 MISS |
| backboardd's GPU chain stops at `method 2 -> unsupported` | one call, then closes |
| `method 2`'s failure is a **switch, not a bug** | `SweetFramebuffer.cpp:240` |
| turning that switch on does **not** help | presents 177 vs 132, content identical |
| display controller is healthy end to end | `AppleCLCD` opens, matches, 16 submissions |
| what it submits is blank | 99.7 % black, first pixel 0xff000000 |
| the centred shape is ~180x168 px, centred | measured from the ASCII map, NOTES (74) |
| an injected HID touch does **not** wake SpringBoard | five-condition-clean experiment, NOTES (70) |
| SpringBoard parks on **its own** message queues | `sweetmsgwait=SpringBoard`: 40 records, 7 ports, every one `owner=SpringBoard`, `WQT_PORT` |
| it parks *before* the 33 calls, not after | waits occupy log lines 620-777, calls 1002-1041, no overlap; vsync monotonic so line order is time order |
| its 33 calls de-duplicate to 10 kinds, none graphic | 13 `/arm-io`, 12 `/product`, one keystore match, two opens |
| every thread ends in an ordinary state, process idle | state 1 (TH_WAIT) x4, one at 41 (TH_WAIT+TH_UNINT+TH_TERMINATE2, exiting) - not a deadlock |

**The single most useful measurement of the session** is the `sweetmsgwait` one:
SpringBoard is not blocked on a service somebody else should provide. It sits on
queues it owns, which rules out the whole "a daemon it needs never started"
family that earlier rounds spent a long time on.

## The chain, settled

```text
SpringBoard    2 opens, 33 IOKit calls, 0 GPU matches  -> produces nothing
     |
backboardd     finds the GPU 213x, method 2 refused   -> composites blanks
     |
AppleCLCD      healthy, 16 submissions                -> passes them on
     |
panel          centred 180x168 shape + black
```

**Nothing below SpringBoard is broken.** The missing piece is a produced frame,
which needs the GPU command path executed - a driver to write, not a flag.

## What is explicitly ruled out

Each of these was a hypothesis that got tested and failed:

- GPU discovery or class-name mismatch - 213 matches, all succeed
- permission / entitlement on the GPU path
- the framebuffer, swap chain or panel
- ADT contents (a GPU node under `arm-io` changed nothing)
- missing daemons - `frontboardd` is a SpringBoard-provided Mach service
- SpringBoard crashing - 127 crash reports, none is SpringBoard
- SpringBoard waiting on another process - its 8 ports are all its own queues
- input as the trigger - injected touch is delivered and ignored
- "SpringBoard only runs briefly" - it lives past t=20; the log looked short
  because of ring overwrite, not a short boot
- "distinct=5 means something is drawn" - it does, but `nonblack` was
  understating it; use the ASCII map, not the counter

Checked again while the phone was offline, all ruled out against existing logs:

- display size wrong - the `disp0` ADT node supplies 1125x2436 and the kernel
  presents at that size over a 1080x2400 panel, which is the intended design
- touch coordinate mapping inverted - `fOffX = (1125-1080)/2 = 22` and the tap
  maps `(x + 22) / 1125`, i.e. centred, correct
- surface/panel size mismatch - surface is 1125x2436 bpr 4608 for 11,239,424
  bytes, exactly 1125*2436*4; internally consistent
- SpringBoard crashed or deadlocked - thread count runs 1 -> 11 -> 5 and stays
  at 5 across the last four of 21 samples: an orderly release, not a fault
- thread samples unreliable - 21 samples across the whole boot, each labelled
  with the exec happening at that moment; the curve is clean
- locked screen holding it back - `SWEET AKS: AppleKeyStore registered (no
  passcode, unlocked)`; the system believes it is unlocked

Ruled out in rounds 464-480, on hardware:

- **the whole provisioning set.** Writing `com.apple.purplebuddy.plist`
  (`SetupDone`, `SetupFinishedAllSteps`, `SetupVersion` 11,
  `daemonizeNeedsToRun` false), both `.notbackedup` files, and
  `BKNoWatchdogs` + `FBLaunchWatchdogExceptions` +
  `MCForceShowCloudConfigurationUI` into `com.apple.springboard.plist` gives
  **433 execs and still no `exec Setup`, still 33 SpringBoard IOKit calls, still
  the same five-colour panel.** These are exactly what `sweet-root-tweaks.py`
  writes for the Sweet images: necessary there, **not sufficient here.**
- `EmbeddedHomeScreen` in the SpringBoard launchd job - removed, behaviour
  byte-for-byte identical (429 execs / 33 IOKit / 0 Setup). Restored.
- **backlight.** backboardd matches a *service* with `backlight-control=true`;
  `/backlight` was only a device-tree node, so it got `0 found` and stopped its
  display set-up. `SweetBacklight` (an `IOService` with the property, registered
  in `KernelConfigTables.cpp`) fixes the lookup - it now reports
  **`-> SweetBacklight`, `-> 1 found`** - and changes nothing else. The service
  is kept because iOS should have it; **it is not the blocker.**
- MobileGestalt - answers `sel 8` with `[0x465, 0x984]` = **1125x2436**, the
  panel's real geometry, then closes its client normally.
- `/product/region-info = "LL/A"` - the one identity property iOS references and
  nothing supplied. Added, booted, no change (and the first attempt at this was
  invalid: the ring it compared had not advanced).
- `/chosen/chip-revision = 0x10` - same, no change.
- the three `NEVER FOUND` classes - `ApplePearlSEPDriver` (Face ID) and
  `AppleM2ScalerCSCDriver` (a video scaler), i.e. hardware that does not exist
  here, plus one empty class-name string.
- `runningboardd` - starts normally and the boot continues 200+ execs past it.
- SpringBoard's `Info.plist` requirements - `UIRequiredDeviceCapabilities` is
  just `arm64`.

**Log noise examined and found harmless:** `not in trust cache` (43x, code
continues), `check_np ... vm_shared_region_start_address() failed` (exactly 2x
every boot, at the moment launchd forks its first child - a probe that falls
back), `GetMasterBlock: Error 16` (EBUSY on `ufsroot0`, expected while mounted),
`hfs_mark_inconsistent` (HFS+ metadata; every file read still has correct Mach-O
magic).

## What is not known

**Why SpringBoard stops.** Established: it parks on its own queues, is woken,
makes 33 platform calls, opens two services and then goes silent for at least
10 s while staying alive and idle (threads in TH_WAIT, none stuck). It does not
reach for a GPU at any point.

Two experiments would narrow this further, both one boot each and both written
but never run (the phone left USB at round 218):

1. `sweetmsgwait=SpringBoard` with the cap at 200 - the 40-record cap filled
   during the early burst, so whether it parks *again* after the 33 calls is
   still unseen
2. `sweetmsgsend=SpringBoard` - whether anything ever sends *to* those queues.
   If messages arrive, the stop is in what SpringBoard does next; if none
   arrive, it was never asked to do anything

`research/tmp/next-runs.sh` runs both. Beyond that, answering "why" needs a
debugger inside the process, which this setup does not have - no ptrace server,
no UART.

## Honest scale of what remains

Two paths, weeks of work each rather than sessions. **They are not
interchangeable, and they are not sequential - one is necessary and the other is
the root cause.**

**The root cause is SpringBoard.** Even with a perfect GPU driver, SpringBoard
makes zero GPU matches and never creates a surface - it would still produce
nothing for backboardd to composite. Settling *why it stops after its 33 calls*
is the only route that ends with frames. It needs a debugger inside the process:
a kernel debug stub or a userland backtrace hook, neither of which exists here.
The two experiments in `research/tmp/next-runs.sh` are the cheap next step and
should be run before building any of that.

**The GPU driver is necessary but not sufficient.** backboardd does ask for an
accelerator 213 times and is refused at `method 2`, so a real
`AGXAccelerator` implementation is genuinely needed for compositing to do work -
`shim/out/shim-proven.img` plus `sweetgpuok` shows the plumbing around it already
works, and the command interface is the hard part. But it does not by itself make
SpringBoard draw.

So: do the two experiments, then build the debugging path. Write GPU command
execution when there is a frame to composite, not before.

## Tooling worth knowing about

All in `NOTES.md` in more detail; sources preserved in `xnu/instrumentation/`.

- `tools/sweet-observe.sh IMAGE OUT [SECONDS]` - the only script that waits long
  enough for userland. Banner-checks and deletes OUT before pulling, so a failed
  pull cannot be mistaken for this run's log.
- `tools/hfs-read.py` - read-only HFS+ reader over adb. `list`/`find`/`cat`.
- `tools/sweet-log-pull.sh` - pulls the 4 MiB persistent ring from the end of
  userdata.
- Boot args that matter: `sweetlog=1 sweetlogms=200 sweetufsquiet=1
  sweetfb_noconsole=1`, plus `sweettap=1 sweettapdelay=N` for the injected tap
  and `sweetiolog=Name` for the per-process IOKit trace.

## Two kernels exist and they are not the same

| kernel | verified on hardware |
| --- | --- |
| `research/k-proven` | **yes** - the last one that booted |
| build tree (`xnu/out-gauguin-macos/...`) | no - carries an untested GPU caller-name change |

Same size, different hash. Boot `k-proven` first to reproduce the known state,
and test the caller-name change on its own.

## Device state

The phone has dropped off USB twice: after round 142 (back at 218) and again
after the round-218 test run, where it has stayed. Host side is fine each time -
`ioreg -p IOUSB` lists three `AppleT8142USBXHCI` controllers and nothing
attached. Not fixable from the host.

**Evidence on how it comes back is thin: one observation.** A forced power
restart succeeded at round 218 (the user reported doing it); the phone has been
off USB again since round 219 and has not returned. That is not enough to say a
restart is the fix - only that it worked once.

When it returns, in order:

1. `bash research/tmp/next-runs.sh` - the two written-but-unrun experiments:
   `sweetmsgwait=SpringBoard` with the cap at 200, and
   `sweetmsgsend=SpringBoard`. One boot each.
2. boot `k-proven` with no tracing and confirm the known panel state reproduces
3. run the colour-coded map (lost mid-flight at round 142) - it answers whether
   the centred shape is white, i.e. a boot logo, or coloured, i.e. something else
4. only then test the GPU caller-name build

## Traps worth knowing before editing anything

Things that cost rounds in this session, all recorded in `NOTES.md`:

- **`printf` inside a lock.** `ipc_mqueue_send_locked` holds the port lock;
  logging there takes `sweet_log_lock`, and that pairing can wedge a
  single-core boot. Buffer into a fixed array and print outside.
- **`IOSleep` is not a delay you can reason about** on a busy single core - it
  stretches far past its nominal value. `assert_wait_deadline` +
  `thread_block(THREAD_CONTINUE_NULL)` here never woke at all.
- **Bring-up timing matters.** `sweettouchdelay` below ~12 s puts I2C/RPMh work
  on the bus during `vfs_mountroot` and the boot stops at ~787 lines with
  `presents=0`, against 1586/177 at the default 45 s.
- **The log ring has no timestamps in order of time** unless you check. `vsync`
  monotonic means line order is time order; if it is not monotonic, the ring
  overwrote and earlier lines are gone.
- **`nonblack` understates the panel.** It samples at a 632-pixel stride; the
  ASCII map samples ~5x denser inside the region. Use the map.
- **`sweetiolog`/`sweetmsgwait` caps fill early.** A 40-record cap used itself up
  in the first third of a boot and made the rest invisible.
- **Map sizes need converting back through the sampling step.** A 600x250 px
  reading of a 4 px-per-column map was really 180x168 - counted twice wrong
  before it was counted right.
- **`grep SpringBoard` matches `IOK backboardd` lines** if the pattern is not
  anchored with `^IOK SpringBoard:`. It caused a wrong reading of which process
  queried what.