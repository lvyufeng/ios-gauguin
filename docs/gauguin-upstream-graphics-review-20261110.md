# gauguin graphics: renewed HakiOS / UniXNU source review

Reviewed 2026-11-10 Asia/Shanghai, after trial 0214. This is a source and
published-evidence review, not a new gauguin hardware qualification. No image
was installed or booted for this review. The phone last returned to TWRP.

## Decision

Keep gauguin's working A619 firmware, power, SMMU, storage and touch baseline.
Use HakiOS's **complete iOS 16 graphics integration** as the closest reference,
with its direct Metal path as the first Metal candidate. Use UniXNU's Metal
frontend/resource/presentation work as a second reference; its HakiOS iOS 16
metal2vulkan adaptation is the alternate frontend path. A whole UEFI/XNU/OS
migration is not justified by the graphics evidence collected here.

The immediate change is to fix the missing IOSurface memory semantics before
another channel-order experiment. Then evaluate real Metal rendering rather
than continuing indefinitely with approximated CoreAnimation GLES effects.
Metal availability alone will not establish correct icons, responsive input,
physical high refresh or daily usability.

Follow-up: the complete pinned Metal core now has a local
[261-test host and ARM64 archive baseline](gauguin-metal-core-baseline-20261110.md).
That report records the original build failures, unchanged-source retry, concrete
gen4/gen1 differences and missing AIR/compiler integration. It is software
preparation, not a hardware Metal result.

## Pinned primary sources

| Source | Reviewed revision | Meaning |
| --- | --- | --- |
| [HakiOS](https://github.com/oosexgang/hakios-xnu-kernel/tree/63fc2b4633bac3af8e57dadab9f5a8d4cb940438) | `63fc2b4633bac3af8e57dadab9f5a8d4cb940438` | Current main resolved by the GitHub connector; SAME revision as our earlier research, not a newly discovered upstream fix. |
| [UniXNU catalog](https://github.com/UniXNU/UniXNU/tree/95ad78129203442c3c14c02336303adbddf8d0a3) | `95ad78129203442c3c14c02336303adbddf8d0a3` | Current catalog/docs; Adreno740 submodule still `6fa7bae2a5b3b523e790eb3e0348af4d98969e4d`. |
| [AdrenoMetal](https://github.com/UniXNU/AdrenoMetal/tree/da7aedd827dfdb581eac041615c45cc1cd5e71db) | `da7aedd827dfdb581eac041615c45cc1cd5e71db` | Newer than the previously reviewed `6d7f7343`; current head caps the diagnostic frame trace at 64 MiB. |
| [sheng device](https://github.com/UniXNU/UniXNU-sheng/tree/a68ee4ee67cc71792fbf519de7e3e28072c717b5) | `a68ee4ee67cc71792fbf519de7e3e28072c717b5` | Board-owned evidence, including the iPadOS 27 GPU and touch/frame-gap reports. |

27 selected text files, 2,081,279 bytes, were fetched through the GitHub connector
and checked against their exact Git blob hashes. Private cache and complete
receipts: `research/tmp/upstream-review-20261110/source-receipts.json`, SHA-256
`738d5ad43740732a524af15e767a6898795587c4f24615adfc194330629ca109`.
This was not a whole-repository audit. One guessed main-repo device.conf path
returned 404; device-specific files live separately. The failed fetch is retained.
No Apple binaries, firmware, device dumps or downloaded upstream source enter git.

## What the successful cases actually demonstrate

### HakiOS / POCO X5 Pro (redwood)

The authors publish two real compositor paths: direct Metal through HakiosMetalCA
and their PM4 backend, and UniXNU's AdrenoMetal/metal2vulkan over Turnip. GLES is
also available. The [Metal guide](https://hackios-web.vercel.app/en/guide/metal)
and [measurement record](https://hackios-web.vercel.app/en/docs/reference/metal-measurements)
give conditions as well as results:

| Author-reported workload | Direct Metal | Metal over Vulkan |
| --- | --- | --- |
| Page swipes, 1125x2436 render size | 100–104 fps | 50–57 fps |
| Settings scrolling, same render size | about 90 fps | 41 fps |
| Lower 750x1624 render size, stretched to panel | Settings 118–120; page swipes 107–118 fps | No corresponding result claimed here |

These are the authors' device measurements, not ours. The device is reported as
Adreno 642L at 550 MHz with a 1080x2400 / 120 Hz panel. The benchmark fixes
wallpaper, changes copy workers and uses synthetic gestures. The direct path's
continuous finger drag is slower than the combined gesture average. The source
explicitly does not claim steady 120 fps or arbitrary Metal apps/games.
Panel scan counters and visual observations exist; final panel output was not
independently measured. Do not use these rates as A619 predictions.

The same record separates touch delays, SpringBoard main-thread stalls, GPU
fences and presentation. Its framebuffer uses scan position to schedule copies
behind the scan; changing a software refresh parameter does not change panel
mode. The [device status](https://hackios-web.vercel.app/en/docs/devices/redwood)
reports working display/input/GPU/audio/camera/Wi-Fi and persistent var, while
charging is unfinished, Bluetooth is at an initial probe and cellular has no
registration. This is not evidence of a complete daily phone.

### UniXNU / Xiaomi Pad 6S Pro (sheng)

[AdrenoMetal's README](https://github.com/UniXNU/AdrenoMetal/blob/da7aedd827dfdb581eac041615c45cc1cd5e71db/README.md)
states verified A740 GPU composition. Its path is Metal → AdrenoMetal →
metal2vulkan → Turnip → the matching A740 kernel interface. The current
[GPU report](https://github.com/UniXNU/UniXNU-sheng/blob/a68ee4ee67cc71792fbf519de7e3e28072c717b5/reports/ipados27-gpu.md)
separates implemented interfaces and host checks from still-pending device
qualification of current preemption/frame-pacing changes.

The [touch/frame-gap report](https://github.com/UniXNU/UniXNU-sheng/blob/a68ee4ee67cc71792fbf519de7e3e28072c717b5/reports/ipados27-touch-frame-gaps.md)
contains actual completed GPU work in iconservicesagent and cold-cache Settings
and App Store artwork matching references. It also records agent crashes/Jetsam,
multi-second synchronous icon-service waits, page-wiring stalls, input cadence
and remaining gesture faults. This is useful precisely because successful draws
and unresolved system behavior are recorded separately. A catalog entry marked
implemented is not equivalent to every feature being device-qualified.

Reusable lessons are texture swizzles, no-copy ownership, heap/resource lifetime,
failure propagation, shader-cache identity, input-to-display correlation and
fence-before-scanout. A740 CP/GMU initialization, board rails and firmware cannot
be substituted for A619. See the [GPU adaptation procedure](https://unixnu.com/porting/gpu).

## Concrete gaps in the current gauguin port

| Layer | Upstream evidence | gauguin finding / next action |
| --- | --- | --- |
| Create around existing pixels | HakiOS MiniIOSurface.cpp `surfaceCreate` reads IOSurfaceAddress and retains/maps the caller's descriptor. Its comment identifies icons and layer contents as users. | SweetSurface::create always allocates and zeroes new memory and never reads this key. Actual 0214 backboardd creates 180x180 format-0 surfaces 16/17/18/20/21/22; EAGL imports those SAME IDs. Missing address semantics is confirmed in source; whether those calls supplied the key remains unobserved. |
| Wrap versus create | HakiOS handles both through matching memory semantics. | Our selector-6 wrapping works, but 0214 sampled only successful format-0, 4-byte wraps. The icons above use create, so the census returned ZERO samples. No alpha-order inference is justified. |
| CA uniform lifetime | Upstream inject.c forwards native function_uniform data; eagl.c retains the cached function values. | Installed 0210 observer can discard all cached values during an unrelated unknown function selection. UI216 reproduces and fixes this on host; not installed and not proved to explain the device faults. |
| Metal compositor | HakiOS has HakiosMetalCA, shader-library assembly, pipeline variant selection and the matching kernel publication. | gauguin has real Mesa GLES execution but no installed Metal device/frontend. Copying only the shader compiler or naming a service Metal is insufficient. |
| GPU-specific state | HakiOS direct backend's a6xx.hpp selects chip 0x06030500, gen4 capabilities, two SP cores and its cache/GMEM constants; compiler.cpp consumes that chip ID. | gauguin is observed A619/0x06010900. Query actual capabilities and parameterize all consumed state from matching Mesa definitions; do not only rename/change the ID. Start with sysmem; qualify GMEM separately. |
| iOS version | HakiOS integration was measured on 20F66; its m2v recipe pins a complete iOS 16 patch stack. | Current cache is 20H392. Verify QuartzCore/Metal class layout, library contents, registration and return ABI for this image. Existing 20H392 CA slot validation must remain. |
| Present/input | HakiOS records GPU-complete, scanline and touch delivery; UniXNU correlates HID, commits, fences and display flips. | Current software framebuffer copies at 30 Hz; timer notifications are not a measured 90/120 Hz panel path. Measure continuous touch, not only the first 30 frames or aggregate submission time. |
| Resource pressure | UniXNU tracks imported owners, caches, reclamation and memory pressure; its reports retain failures. | 1024 live BO slots removed one observed 256-slot limit, but Mesa OOM recovery remains unfinished. Do not mask failed descriptor allocation and submit invalid work. |

Primary code for the first gap:
[MiniIOSurface.cpp](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOSurface.cpp#L489),
[direct Metal parameters](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/hakios-metal/include/hakios-metal/a6xx.hpp#L26),
[compiler](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/hakios-metal/src/compiler.cpp#L52).
The main local baseline is source211, not the isolated 0214 diagnostic tree.

## Execution order and acceptance

1. **Complete the existing surface contract.** Inspect create-property presence
   without logging raw addresses or image content. Add owned caller-memory
   backing using the existing validated wrap lifecycle; retain size/overflow,
   task ownership, read-only handling, cache policy and teardown rules. Prove
   caller changes remain visible and ordinary creates still allocate their own
   storage. Cover failures and lookup by the same surface ID. Then check icons,
   widgets, repeated lock/unlock and App Library on device. Do not introduce an
   unverified pixel swizzle as a substitute.
2. **Keep UI216 as a separate correctness candidate.** Software tests already
   pass; integrate only after the surface comparison is reviewable. It is not
   an FPS change. Any new root delta still needs its exact backup/old-block
   checks and the required individual destructive-write approval.
3. **Connect a real Metal frontend on the current backend.** First adapt
   HakiOS direct Metal's actual A619 parameters, IOKit matching, struct sizes,
   deadlines, BO flags and surface offset/lifetime. Begin with one clear,
   triangle, textured quad and blend plus exact pixel readback/fences, then
   multiple queued buffers and cleanup. Build the CA plug-in/library only after
   these pass. Reuse the user's local shader inputs; never commit Apple files.
4. **Require one complete compositor path.** Validate device discovery,
   shader-library loading, exact pipeline variants/constants, IOSurface views,
   completion, presentation, icons and widgets together on 20H392. If direct
   Metal's generation-specific encoder prevents reasonable reuse, use HakiOS's
   already-adapted iOS16 m2v/Turnip path on the SAME A619 transport; do not switch
   the entire kernel/boot chain. Its recipe pins AdrenoMetal `243d63cf43305a85c8119b66b49cb7df4b30b019`
   and metal2vulkan `624bab3918de5b978e1101517abca2b4fa426565` plus patches;
   latest AdrenoMetal is not a drop-in replacement for that stack.
5. **Measure responsiveness, then raise refresh.** On fixed scenes, correlate
   touch report → HID delivery → CA commit → submit → fence → copy/flip/latch.
   Record warm/cold P50/P95/P99 and complete images. Fix measured BO/sync/page
   costs and presentation stalls; then bring up actual DPU/DSI/panel timing,
   bandwidth and fence retirement for 60/90/120 Hz. A faster VSync timer is not
   the acceptance test.
6. **Continue the full phone goal.** Reconcile all safe RAM banks/reservations
   and pressure/DMA behavior, qualify reliable persistent storage, then power,
   charging/thermal, sleep/wake, network, audio/camera/modem and long sessions.
   Neither another project's feature list nor this graphics review completes
   those gauguin milestones.

Codex owns critical driver/design changes. DSH executes local builds, meaningful
tests, packaging and authorized temporary boots. Use focused checks for small
changes and integrated checks when ABI/MMU/lifetime/presentation changes justify
them. No new CI run, userdata write or device trial was performed in this review.

## Follow-up device evidence: 0219

The separately implemented caller-memory create path is now exercised on the
device. A finite diagnostic emits one synthetic unlock swipe; afterward six
180x180 surfaces (IDs 16/17/19/21/22/23) use `IOSurfaceAddress` with retained
read-only backing. All six reach the matching EAGL `texImageIOSurface` method.
The EAGL logs explicitly say they use a copy fallback, so this is not proof of
direct shared GPU import, correct source pixels or visually correct icons.
There are nine caller-backed creates in twenty backing records overall.

The original 0219 observer failed its strict banner check and remains failed:
a second printed kernel banner contains an interleaved Sandbox log line.
Separate offline v3 verifies the raw ring decodes exactly to the captured log,
the complete first banner matches the image, and removing that one exact
interleaved line from the second occurrence reconstructs the same full banner.
It changes only a derived file. Finite 600-second service records are consistent:
47 completed submissions, 598 verified renewals; one backboardd crash and two BO
allocation failures occur after the explicit planned stop. The phone returned
automatically to TWRP after about 746 seconds. No visual feedback was obtained.

Private `forensic-stage-v3/result.json` has exit 0 and unchanged inputs, while
the original trial remains exit 3. An intervening forensic v2 failed because
it wrongly assumed all address keys were absent from the first records; that
failure also remains intact. `review-EAGL-copy-meaning-v4.json` clarifies the
method-entry versus direct-import distinction without rewriting v3.
All fifteen files were captured, twelve static files and complete prior log
prefixes preserved; no userdata application was performed. This provides
caller-memory-path coverage, not a completed icon fix or Metal qualification.
