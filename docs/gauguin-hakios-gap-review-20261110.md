# HakiOS success path: gaps remaining in gauguin

This follow-up supersedes the current-status portions of the earlier graphics
review. It follows actual0230's first-frame failure, not a new successful UI
trial. The complete phone, RAM, storage, peripherals and high-refresh objective
remains open.

## Sources revalidated

The GitHub connector fetched current-main sources and documentation again;
`gh api` independently resolved main to
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438`. The six fetched files, including
`HakiosMetalCA.m`, `inject.c`, `ca-metallib.py`, `metal-run.sh` and the two Metal
reference pages, are byte-identical to the earlier retained source snapshots.
There is no newly discovered upstream commit that fixes our failure.

Primary sources:

- [Metal integration](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal.md)
- [Measurements and limitations](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md)
- [Complete frontend](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m)
- [Library construction](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/ca-metallib.py)
- [Measured-run defaults](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh)

## Concrete integration gaps

| Gap | Actual evidence | Required work |
| --- | --- | --- |
| Desktop client admission | HakiOS admits backboardd by default and publishes its Metal plugin. Gauguin's frontend admits only the named root diagnostic; the qualified219 accelerator publishes no Metal plugin properties. Actual230's backboardd log explicitly has `hooks=0 gpu_opens=0 rendering=disabled`. Earlier interactive modes exercised the EAGL/GLES bridge. | Qualify and connect the complete Metal compositor path. A successful root probe cannot establish that the visible desktop uses Metal. Retain single-owner coordination during the transition. |
| Runtime function creation | Actual20H392 QuartzCore constructs a `MTLFunctionDescriptor`, sets its name and constants, then calls `newFunctionWithDescriptor:error:`. HakiOS's stand-in hooks cover the name and name/constants overloads; the removed hooks never instrumented this descriptor entry. Our shader census calls the A619 compiler directly. | Capture the exact failed function and NSError at the actual descriptor entry, then implement the required specialization using that image's own AIR and constants. Offline shader links do not exercise this Metal.framework contract. |
| Caller-backed IOSurfaces | Physical219 observed read-only caller-backed 180x180 surfaces reaching EAGL through a copy fallback. The qualified219 GPU importer rejects `readOnly` surfaces and memory that is not an `IOBufferMemoryDescriptor`. HakiOS's complete integration includes surface imports and a caller-page import interface. | Support owned, correctly wired read-only caller backing, offsets, lifetime and CPU/GPU cache visibility. Check exact source and destination pixels. Current refusals are a concrete integration gap; they do not alone establish the cause of every missing icon. |
| Encoding, completion and display | HakiOS records deferred encoding, fences, copying and scan-line timing. Gauguin's current trial uses a 30Hz software-copy display path, with no measured physical high-refresh acceptance. | Measure touch, HID, CA commit, submit, fence, copy/flip and panel latch together. Then adapt the actual gauguin display hardware and retire surfaces only when safe. |
| Framework feature negotiation | HakiOS restricts which processes see its device and documents MPS capability checks. Gauguin's root profile intentionally certifies no public GPU family and does not admit app/framework clients. | Qualify the capabilities required by actual system clients before wider publication. Root Metal execution does not prove MPS, general applications or games. |

## The new call-path finding

0230 aborted with SIG6 and `Metal failed to specialize fragment function`, after
one poison-clear submission and before any CA scene pixel result. The memory
limit and CA runtime-ABI checks had passed.

An independent offline read of the actual20H392 cache decoded the crash's nine
QuartzCore frames, its library/descriptor method encodings and the relevant
Objective-C call stubs. The specialization helper calls, in order:

1. `functionDescriptor`
2. `setName:`
3. `setConstantValues:` when values exist
4. `newFunctionWithDescriptor:error:`

This identifies the interface our diagnostics missed. It does **not** identify
the failed function or prove why Metal returned nil. Candidate explanations
such as missing metadata, an unsatisfied constant or a compiler entry point
remain hypotheses until the original NSError is captured. Replacing a shader
with a nearby variant would conceal that distinction.

The new opt-in `gauguin-ca-trace` preparation profile adds only a descriptor
observer to the exact profile. It checks five actual20H392 method encodings,
requires the method to belong to `_MTLLibrary`, and observes only libraries
whose device is `HakiosMetalDevice` in the already admitted root process.
Other devices delegate immediately. The observer passes the original descriptor,
selector and error pointer unchanged, calls the original implementation once,
and returns the original function with its ownership unchanged. It logs the
requested name, whether constants/name exist, and the original failure reason.
It performs no shader substitution, retry or success fabrication.

DSH built and signed the native frontend and its paired CA probe. Preparing the
existing exact profile still yields all three original source files unchanged.
Fresh actual20H392 resolution covers all680 native imports, including the two
new libobjc imports used to check method ownership. The installed core remains
the qualified8a826583 baseline. No new bundle, root delta or boot was installed.
Runtime tracing and specialization are still unqualified.

## What the successful measurements actually establish

HakiOS's authors report full-resolution1125x2436 page swipes around100-104fps and
Settings scrolling around89-91fps on an A642L. At750x1624, stretched to the panel,
Settings reaches118-120fps and page swipes107-118fps. Those runs include a frozen
wallpaper and deferred command encoding. They do not show every operation
holding120fps at full resolution. These are another GPU and another system
build, so they are reference conditions, not a gauguin performance forecast.

The same report records75-80fps while a real finger drags,8-14ms GPU fence waits,
and100-300ms SpringBoard main-thread turns at gesture startup. Its touch fix
reduced missed/lift delays; our Novatek driver already polls every8ms without
waiting for a low interrupt line, so copying their Goodix workaround is not
automatically appropriate. We still lack a comparable touch-to-panel trace.

The successful frontend also uses nearest shader variants, substitutes some
effects, and normally skips refused work unless strict mode is enabled. These
choices explain how a measured usable UI can coexist with incomplete semantics.
Our exact diagnostic deliberately rejects omitted work. Keep that distinction
visible when borrowing the integration: complete appearance, correct pixels,
frame pacing and long-session behavior each need their own evidence.

## Execution order

First obtain the actual descriptor error using the prepared trace candidate,
then repair the matched specialization path and pass the existing CA scene pixel
checks. Next qualify caller-backed surface sharing and the remaining real image
operations, connect backboardd to the complete Metal path, and verify icons,
widgets, effects and repeated application transitions together. Finally measure
end-to-end latency and sustained60Hz before qualifying physical90/120Hz.

Every new userdata delta still requires a fresh full backup and current-state
review, followed by its individual write consent. The last0230 approval is
consumed. This source review performed no device IO, root write or reboot.
