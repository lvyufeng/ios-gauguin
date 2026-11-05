# gauguin: iOS on Snapdragon 750G — where it stands

Written 2026-11-03 after the iOS system was brought up on real hardware and the
display was characterised end to end. Everything below is either **measured on
the phone** or explicitly marked as unknown. Where an earlier claim was wrong,
it is listed as wrong rather than quietly dropped.

---

## 1. One-line status

**iOS boots and runs on gauguin. The screen shows no iOS content, and there is
a measured reason: userland submits a fully black surface to the compositor and
never anything else.**

Not a crash, not a deadlock, not a broken copy path. Nothing renders because
nothing is drawn.

---

## 2. What works, with evidence

| Layer | State | Evidence |
| --- | --- | --- |
| Kernel | works | `Darwin Kernel Version 22.6.0 … DEVELOPMENT_ARM64_GAUGUIN` |
| UFS driver | works | `SWEET UFS: init complete` |
| HFS+ root on `userdata` | works | `hfs: mounted iOSRoot on device b(1, 0)` |
| launchd | works | `exec launchd` → `ignition sequence complete` |
| Process bring-up | works | 245 `exec` calls, 116 distinct processes |
| SpringBoard | runs | `exec SpringBoard`; 10 threads; block ring shows 319,295 blocks with no deadlock |
| backboardd | runs | `exec backboardd`, opens 6 IOKit services |
| Display path | works | surface → swap → present → panel, verified end to end (below) |
| AGX service | opens | `open AGXAccelerator type 1 -> 0x0` |

Reported on real hardware: `<device-id-redacted>`, TWRP recovery, no UART. Console goes to
the ABL framebuffer and a 4 MiB ring at the end of `userdata`, read back with
`tools/sweet-log-pull.sh`.

---

## 3. The display path, measured

One banner-checked boot (`research/tmp/observe-nook.txt`), honest build, no
`sweetgpuok`:

```
vsync=2     nonblack=949  distinct=2  presents=0    ← ABL splash, not ours
vsync=1800  nonblack=485  distinct=1  presents=0    ← wiped
vsync=3000  nonblack=47   distinct=4  presents=1    ← first present
vsync=3600  nonblack=60   distinct=5  presents=17
vsync=4200  nonblack=67   distinct=5  presents=36
```

Reading:

- before any swap the panel already holds the bootloader's image
- `nonblack` *moves* as `presents` climbs → **the copy really does write the
  panel**; the path is not broken
- `distinct` saturates at 5 → what lands is a few flat colours, not a picture

And the source surface itself:

```
SWEET FB: src id=2 swap=2   nonblack=10 distinct=1 px0=0xff000000
SWEET FB: src id=3 swap=41  nonblack=13 distinct=2 px0=0xff000000
SWEET FB: src id=2 swap=92  nonblack=13 distinct=2 px0=0xff000000
SWEET FB: src id=3 swap=141 nonblack=13 distinct=2 px0=0xff000000
```

backboardd creates exactly two surfaces (`id 2`, `id 3`, 1125×2436 BGRA) and
re-submits them unchanged. **The compositor is honest; its input is empty.**

---

## 4. The GPU, and what it is not

The service exists and opens:

```
IOK backboardd: matching1 … IOProviderClass=AGXAccelerator -> AGXAccelerator
SWEET GPU: user client opened
IOK backboardd: open AGXAccelerator type 1 -> 0x0
```

**The class name matters.** backboardd asks for `AGXAccelerator`. An earlier
investigation published `IOAcceleratorES`, which is matched 218 times and
opened **zero** times — no consumer wants that name. Renaming (see
`class AGXAccelerator : public IOAcceleratorES` in `SweetFramebuffer.cpp` plus
a `KernelConfigTables.cpp` entry) made the service reachable.

**Selector 2 is a gate.** Answering it with `kIOReturnUnsupported` makes
backboardd close the connection after one call. Answering it `ok` unlocks 0, 4
and 22 calls of 33.

**Selector 33 is a command-buffer submission:**

```
method 33 (2 in, 0 out) in0=1104320000 in1=320000
method 33 (2 in, 0 out) in0=1104640000 in1=320000
…
```

`in1` is 320000 (0x4E200, 320 KiB) on every call; `in0` is a low user-space
address climbing monotonically. Userland hands the driver a command buffer.

**Nothing executes those buffers**, and here is the measured consequence
(`sweetgpuok` A/B, both runs banner-checked):

| | GPU methods | presents | distinct |
| --- | --- | --- | --- |
| no `sweetgpuok` | `2` → unsupported, connection closed | 36 | 5 |
| `sweetgpuok=1` | 2, 0, 4 ok, 33 ×22 | 88 | 5 |

`sweetgpuok=1` makes every method silently succeed. Submissions more than
double. **Not one pixel changes.** It is a probe, not a fix, and it must never
be the default.

---

## 5. What is needed next, and its size

To show a picture, iOS must put pixels into backboardd's surface. Exactly two
routes exist:

1. **Execute AGX command streams.** Parse the 320 KiB buffers, decode the
   command encoding, rasterise. This is a real GPU driver — weeks of work, no
   shortcut found in this session.
2. **Force CoreAnimation onto its CPU renderer.** The surface mapping is
   writable (`createMappingInTask(fTask, 0, kIOMapAnywhere | s->mapCache)` —
   the data mapping is *not* `kIOMapReadOnly`), so the mechanism exists. What is
   unknown is how userland decides between GPU and CPU rendering, and no switch
   was found; `unentitled_ios_sim_launch=1` is about sandbox entitlements
   (`kern_exec.c`), not rendering.

Route 2 is far cheaper if it exists. **It has not been shown to exist.**

---

## 5a. What rounds 53-96 added, and what it ruled out

The investigation after entry (52) narrowed the problem from the display stack
to SpringBoard's own startup, and ruled out several plausible causes **with
measurements**, not reasoning.

**SpringBoard never touches graphics at all.** Not once:

```
grep 'IOK SpringBoard' | grep -ciE 'acceler|gpu|framebuff|surface|clcd|metal'  ->  0
```

It opens exactly two IOKit services, `AppleKeyStore` and `IOPMrootDomain`, makes
33 IOKit calls in total, and after line 7664 of the log makes none for the
remaining 7,600 lines. It is not failing to render; **it never reaches rendering**.

**It is not waiting on anything external.** The `sweetmsgwait` tracer (fixed in
this session - it could never fire, see section 7) shows 40 blocking receives
across 8 ports, and every one of those ports is **owned by SpringBoard itself**.
They are its own libdispatch queues, idle. No external dependency is missing.

**It does not crash.** The iOS root holds 127 crash reports in
`/private/var/mobile/Library/Logs/CrashReporter/`; SpringBoard is not among them.
It is alive, quiet, and scheduling normally.

**Ruled out one by one:**

| Hypothesis | How it was tested | Result |
| --- | --- | --- |
| SpringBoard waits for a GPU node under `/arm-io` | added one to the ADT | **no change**: 33 IOKit calls, 13 `/arm-io` queries, same stop |
| A missing device tree node | ADT compare | `arm-io` only had gic/wdt/disp0, but adding gpu changed nothing |
| SpringBoard restarted / is in a degraded state | process presence records | `backboardd` shows the same `gone (t=1)` - it is a log-start artefact, not a crash |
| Permission denial | searched the log | no EACCES/EPERM for SpringBoard |
| Stop caused by the GPU service | timestamps | `driverkitd` crashes at line 7152, the GPU service opens at 9796 |
| The image is incomplete | `find frontboardd` | **retracted**: the real path is a `.framework`, and 32 board frameworks are present |

**The single fact that survives all of it:** SpringBoard completes its early
init, then stops, *before* any graphics initialisation. Everything downstream
(black surface, empty compositor, unattempted GPU command buffers) follows from
that, not the other way round.

**To go further needs something this session did not have**: userland debugging
(attach to SpringBoard and see its instruction pointer), or executing AGX
command streams (a real GPU driver). Neither is a parameter change.

---
## 6. Corrections to earlier claims

Kept because several were repeated across many rounds before being measured
again:

| Claim | Status |
| --- | --- |
| "293 processes" | **wrong**: 245 `exec` calls, 116 distinct names |
| "SpringBoard is stalled" | **wrong as stated**: it starts, creates 10 threads, then parks normally — the block ring shows no deadlock |
| "IOAcceleratorES needs a UserClient, that is the blocker" | **wrong**: a UserClient was added and nothing opened it; the name was wrong |
| "`sweetgpuok` reaching presents=185 is progress" | **wrong**: it inflates the counter and changes no pixels |
| "driverkitd crash is on the GPU path" | **not supported**: it crashes at line 7152, the GPU service opens at 9796 |
| "the panel's 5 colours are our debug marker" | **wrong**: disabling `sweetfb_mark` left the numbers identical |
| "a GPU node under /arm-io will let SpringBoard proceed" | **wrong**: added one; IOKit call count, `/arm-io` query count and stop point all unchanged |
| "driverkitd's crash is on the GPU path" | **wrong**: crash at line 7152, GPU service opens at 9796 |
| "the image is missing frontboardd / BackBoardServices" | **retracted**: those are `.framework` paths; 32 board frameworks are present. A bare-name search misses every framework |
| "prefer counters as progress" | **wrong twice**: `sweetgpuok` and the ADT node each moved `presents` without moving a pixel |

**The recurring failure mode across all of these:** treating a query that
returned nothing as proof that the thing was absent, and treating a counter that
moved as proof that something happened. Both need a second, independent check
before a conclusion is drawn from them.

---

## 7. Instrument defects that were fixed

These mattered more than they look — conclusions had been drawn from them.

- **`shim-proven.img` carried a kernel 40 minutes older than the tree.** The
  "proven" image was not built from the source being edited.
- **`tools/sweet-observe.sh` could report a previous boot as the current one.**
  The log pull ended in `|| true`, so a failed pull left the old log in place
  and every counter was computed from it, silently. It now removes the output
  first, exits 4 on failure/empty, and compares the log's kernel banner against
  the image's, exiting 3 on mismatch. `tests/test_observe.py` guards all of it.

**Rule for whoever picks this up: banner-check every log before believing a
number that comes from it.** Several results in `NOTES.md` predate that check
and should be re-measured before being built on.

---

## 8. Practical notes

- Build: `bash deps/build-macos.sh gauguin` (~4 min; host tests run first,
  `SKIP_TESTS=1` to skip)
- Observe: `bash tools/sweet-observe.sh IMAGE OUT.txt [SECONDS]` — the only
  script that waits long enough for userland
- Live images: `shim/out/shim-proven.img` (honest build, no `sweetgpuok`),
  `shim-bisect-on.img` (with the probe)
- Boot line that works:
  ```
  debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress
  rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 ufsrw=1 rootrw=1
  launchd_unsecure_cache=1 sweetlog=1 sweetlogms=200 sweetfb_noconsole=1
  ```
- The iOS root (16 GiB) lives in `userdata`; TWRP cannot mount HFS+, but
  `tools/hfs-read.py` lists and locates files (not `cat`; see its docstring).
- `.deps-cache/` is git-ignored and rebuilt from `xnu/patches`.

---

## 9. Honest bottom line

The port is a working iOS environment on a phone that Apple never shipped iOS
on: kernel, storage, filesystem, process model, SpringBoard, a functioning
display pipeline, and a GPU service that answers the calls it is asked.

It is not a phone you can use. Getting from here to a visible springboard is a
driver-sized piece of work, and this session established exactly where that
work starts — which is more than it had at round 1, and less than "iOS runs on
gauguin" would suggest to a casual reader.