# gauguin port: current state (2026-11-03, latest)

> **Completion criterion (agreed with the user, 2026-11-04): a usable iOS
> interface is visible on the panel - lock screen, home screen or system UI -
> verifiable by screenshot. Not "SpringBoard renders something"; not "the GPU
> works". The interface, or the goal is not done.**
>
> **Status at handoff: iOS boots and runs; it does not reach a usable
> interface.** The blocking question is why SpringBoard stops after 33 platform
> calls, and the two cheap experiments that would narrow it are written and
> never run because the phone went off USB at round 218. Read "What is not
> known" before doing anything else - it is one paragraph and it is the
> shortest path into the remaining work.

Successor to `HANDOFF.md` (which describes the port before any kernel existed
and is now historical), `HANDOFF-2026-11-03.md` and
`HANDOFF-2026-11-03-FINAL.md`. This file is the state as of the long offline
stretch at the end of the 2026-11-03 session.

## Where this actually stands

**iOS boots and runs on the phone.** Kernel, UFS, HFS+ mount, launchd and
~140 userland processes all come up on a real Redmi Note 9 Pro 5G
(`gauguin`, SM7225 / snapdragon 750G, DT compatible `qcom,lagoon`).

**It does not reach a usable interface.** SpringBoard starts, lives for 20 s
and more, and stops before it makes a single graphics call. The panel shows the
centred shape described in NOTES (72) plus black - not a home screen.

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