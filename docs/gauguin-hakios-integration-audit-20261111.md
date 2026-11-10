# HakiOS desktop integration audit, 2026-11-11

The [subsequent pipeline recheck](gauguin-hakios-pipeline-review-20261111.md)
adds the synchronous-submit/global-lock difference and current candidate status.
The integration requirements below remain physical acceptance work.

The main gap is the connection from the real iOS compositor to the driver.
Native GPU jobs and root CoreAnimation pixel tests do not establish that the
desktop discovers, selects and uses that device. Keep the working A619 hardware
baseline and prioritize a complete desktop candidate over additional unrelated
offscreen feature suites.

GitHub main was checked again and remains
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438`. This audit adds actual 20H392 cache
inspection to the [previous source comparison](gauguin-hakios-desktop-recheck-20261110.md).
It changes no phone state. The evidence below distinguishes source inspection,
host/native checks and physical results.

## Newly confirmed connections

### System discovery includes a filesystem installation

HakiOS publishes `MetalPluginName` and `MetalPluginClassName` on its
`IOAcceleratorES` service, and its build installs a link at
`/System/Library/Extensions/HakiosMetal.bundle`. Its bundle names
`HakiosMetalDevice` as its principal class. These are parts of one integration;
putting a library in a private directory and opening it from a probe is different.
See [the accelerator publication](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L2014),
[the system bundle link](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/build.sh#L731)
and [the bundle metadata](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetal.plist).

The actual 20H392 Metal cache now confirms this route rather than relying on
another iOS version's behavior. The function at `0x181a3c7c8` references both
plugin properties, builds a path under `/System/Library/Extensions` with the
`.bundle` suffix, calls `bundleWithPath:`, and obtains the named or principal
class. These are static call sites, not evidence of loading on this phone.

Our builder produces `GauguinMetal.bundle`; the installed diagnostic opens its
private path explicitly. The tracked frontend admits only the named root probe,
the diagnostic environment and checked 20H392 ABI. A desktop candidate needs
coordinated service publication, bundle installation, backboardd admission,
GPU-owner handoff and usable process cache. Publishing a property alone will
not accomplish these steps.

### Framework capability checks are part of admission

The current diagnostic returns false for every public family and feature set.
That was a deliberate limit on an offscreen test, not a ready desktop policy.
HakiOS documents its previous MPS startup failure when its device did not
advertise a family MPS accepted, and the limits-profile change it used. See
[its explanation](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L2372).

The actual 20H392 cache confirms that `MPSDevice::GetMPSDevice` directly queries
`supportsFamily:` through values including 1008 and 1002. `MTLAddDevice` also
checks protocols and invokes `initLimits` and `initFeatureQueries`. Device
creation from a manually loaded bundle bypasses some discovery work and is
insufficient acceptance. A compositor profile must qualify its actual framework
checks and required rendering operations; blindly restoring a family claim
would overstate support.

### Actual decoded-image upload uses two additional APIs

The fresh system cache contains these QuartzCore calls:

| Call site | API | Statically observed continuation |
| --- | --- | --- |
| `0x188483ffc` | `newTextureWithBytesNoCopy:length:descriptor:deallocator:` | Texture creation/upload path also includes `replaceRegion:...` |
| `0x18848438c` | `newBufferWithBytesNoCopy:length:options:deallocator:` | Derives cache/storage modes and calls `newLinearTextureWithDescriptor:offset:bytesPerRow:bytesPerImage:` |

Our diagnostic explicitly refuses the buffer API. Actual 0239's immutable
task-surface import and the five synthetic CA scenes test different contracts.
They do not qualify every image-service/desktop upload path. The existing
compositor's generic task-input import gate is also still closed.

HakiOS's buffer workaround copies initial bytes and keeps the deallocator.
Its comment explicitly excludes sharing later writes between caller and GPU.
See [the implementation](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L2612).
That can inform a bounded immediate-upload implementation, with layout,
ownership, updates and pixel checks. It is not a general no-copy contract.
The static call sites do not prove they caused the old EAGL desktop's missing
icons; our diagnostic Metal frontend was not serving that desktop.

## Presentation and performance details that remain necessary

| Detail | What the reference establishes | Gauguin acceptance still needed |
| --- | --- | --- |
| Surface identity and reuse | Retain through consumption, then retire promptly; waiting an extra beat starved CA's next buffer | Held candidate 0241 passes host/native checks only; qualify real replacement, exit, repeated transitions and retirement |
| GPU completion | The presenter coordinates completion before consuming output | Shared-output 0240 has not run; table references and a global GPU lock are not a complete deferred-producer handoff |
| Cadence | Deliver frames on a beat rather than accumulating work time | Phase candidate 0242 passes host/native checks only; measure delivered phone intervals, copy work and missed beats |
| Animation requests | HakiOS found 24 fps requests despite only 0.3 ms of GPU work and added a SpringBoard range hook | Trace requested versus delivered rate and use the measured gauguin mode, not a copied 80..120 range |
| Cache/process boundaries | Persistent shader caching is part of its measured runner | Our root-owned 0700 diagnostic cache does not qualify a usable backboardd cache; compare cold/warm/reboot |
| Panel scan and tearing | HakiOS describes writing behind its measured scan line using `INTF_LINE_COUNT` | Our software clock does not qualify physical scan timing, tear avoidance or 90/120 Hz; use this board's actual resources |

Sources: [prompt surface retirement](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp#L1380),
[animation hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1941),
[runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L18)
and [scan/tearing observations](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md#tearing).

One important correction to the performance framing: the author also reports
107–114 fps Settings scrolling on the default OpenGL ES path, under a different
kernel/core-count configuration. That is not a controlled comparison with Metal
and does not predict A619 performance. It does show why replacing the API alone
is not a sufficient explanation or acceptance criterion for our persistent
latency. See [the comparison's explicit conditions](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md#opengl-es-for-comparison).

HakiOS's reported full-resolution Metal swipes are about 100–104 fps and
Settings scrolling 89–91 fps on A642L. The 118–120 fps Settings result uses
750x1624 rendering, frozen wallpaper and synthetic gestures. Its counters are
not an independent optical panel measurement; real-finger results and main
thread stalls are separately documented. Neither those numbers nor this audit
establish gauguin's physical refresh or daily usability. Its device status still
lists charging unfinished, Bluetooth unavailable and cellular unregistered.
See [measurement conditions](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal-measurements.md)
and [device status](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/devices/redwood.md).

## Execution order and evidence

1. Preserve the pending 0240 proposal and its exact paired 0239 kernel; run it
   only after the genuine write reply. No other boot should stale that delta.
2. Qualify held 0241 and phase 0242 against the same installed userland. Both
   are compiled candidates, not proven UI or physical-refresh fixes.
3. Build one separate compositor profile covering discovery, actual capability
   checks, backboardd cache/admission/ownership, image input and shared output.
   Qualify populated icons/widgets, correct color/effects, repeated lock/unlock
   and app transitions, and native submissions from the actual compositor.
4. Measure touch-to-commit-to-GPU-to-copy latency and sustained usable 60 Hz.
   Then qualify physical high-refresh timing, tear behavior and thermals.

Private evidence stays outside git at
`research/tmp/dsh-desktop-0243-contracts`. It reads the verified 16 GiB backup
whose SHA256 is `2b8fab2f297533bfe08b6a3b9e8813d59a8b9f3e0c36ee6a61aad5ea8ad3d1a9`.
The first inventory attempt failed with an index-variable collision; that
failure and partial output remain preserved. DSH inventory v2 PID 77811 exited
0 with 12 unchanged pins; contract v3 PID 78843 exited 0 with 15 unchanged pins.
Codex independently rehashed both sets of inputs and logs and inspected the
relevant disassembly. Three freshly fetched upstream files match their Git
blobs. `review243-v1.json` SHA256:
`d3b11c2bd3afaabeec1cd6dcb58dc94b40775e758ed9fe3ba4590cde5b20225a`.
These results are static software evidence, not phone runtime results. No
device command, userdata write, reboot, CI build or push was performed.
