# A619 GLES userland

This builds the actual Mesa 25.0.7 freedreno/IR3 driver for arm64 iOS 16 and a
standalone GLSL/IOSurface probe. It does not modify XNU, install files on the
phone, replace EAGL, or integrate Metal/CoreAnimation. Kernel and root-volume
installation remain separate, reviewed stages.

`upstream.json` pins the primary Mesa archive and four original HakiOS source
blobs at `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`. Put those four files at their
repository paths beneath a local cache directory. No Apple binary or firmware
is downloaded by either tool.

```sh
python3 tools/prepare-ios-gles.py \
  --archive /absolute/path/mesa-25.0.7.tar.xz \
  --upstream-cache /absolute/path/hakios-cache \
  --out /absolute/path/fresh-prepared
python3 tools/build-ios-gles.py \
  --prepared /absolute/path/fresh-prepared \
  --venv /absolute/path/existing-meson-venv \
  --out /absolute/path/fresh-build --jobs 8
```

Both output directories must be new. The builder uses the installed iPhoneOS
SDK, an existing Meson/Mako/PyYAML/packaging environment, Ninja, Bison and Flex.
It cross-builds and ad-hoc signs `libGauguinOSMesa.8.dylib` and
`gauguin-gles-probe`. The probe expects the library through
`@rpath/libGauguinOSMesa.8.dylib`, with `/usr/local/lib/gauguin` as its runtime
search path. Software rendering drivers and LLVM are disabled. Mesa's Darwin
build links its GL dispatch statically into this library even though GLES
configuration requires `shared-glapi=enabled`.

The source preparation retains HakiOS's OSMesa ES-context and IOSurface winsys
changes. The gauguin-specific changes use the real Linux pipe `0x10`, require
actual GPU/chip/GMEM identity `619/0x06010900/512 KiB`, clear otherwise-unused
submission fields, set absent fence descriptors to `-1`, discard only the
Linux BO-dump hint, and disable advertising native fence descriptors. The
shim checks returned struct/mapping sizes. Mesa uses its own A619 hardware
table; no A642L/A660 compiler or bank/UBWC literals are substituted.

`queue-local-fences.patch` keeps each pending syncobj receipt as an exact
queue/fence pair, including transfers and waits. Verified synchronous
completions are cached before queue close. A failed wait on full pending
storage cannot advance the timeline. Empty command submissions are refused,
matching the kernel ABI; a global fence from another queue is never borrowed.
This GLES profile does not advertise syncobj capabilities or build Turnip.
The typed-boundary regression compiles the actual old/new transport source:

```sh
python3 tests/test_mesa_queue_fences.py \
  --old-source /absolute/path/old-prepared/mesa-25.0.7 \
  --source /absolute/path/fresh-prepared/mesa-25.0.7 \
  --out /absolute/path/fresh-host-results
```

The old source must compile and functionally fail; the new source must pass.

The A6xx USER32 event-source selection is carried from the retained A619
170–174 trials into Mesa25's equivalent emitter. Only RB_DONE/ALWAYSON writes
timestamps. This is a device-specific port profile; it is not an upstream fix
or physical qualification of the new complete driver. Screen creation fails
if the hardware service cannot create an actual A619 screen.

`tools/gpu-mesa-abi-check.c` compares the actual kernel runtime header against
Mesa's independent Linux UAPI and HakiOS's surface struct. Compile it natively
and for `arm64-apple-ios16.0`, including the kernel `bsd/dev`, prepared Mesa
`include`, and `src/hakios-drm` directories.

The probe requires root and real kernel parameters before creating a context.
It rejects CPU renderers, compiles ES3 vertex/fragment shaders, draws a seeded
checkerboard, verifies all 1,024 RGBA pixels, samples the texture into a BGRA
IOSurface with a nonzero 64-byte offset, and verifies all 1,024 BGRA pixels.
Success requires both complete comparisons and successful GL completion.
`--after-gpu-api` first spawns the separately installed signed GPU API probe,
requires its successful exit, waits at least 90 seconds on the monotonic clock,
then opens Mesa and performs the shader/texture/surface checks. One launchd job
orders the clients, so they cannot race for the privileged single-client slot.
This mode requires the 600-second service image, not a 60-second smoke image.
Cross-compilation, signing and ABI checks do not prove that any shader has run.

The first physical trial reached the delayed hardware/GMEM query, then iOS
terminated the process with Jetsam `per-process-limit` before a renderer or new
GPU submission appeared. The device's daemon policy has a 6 MiB inactive hard
limit for jobs without an override. This is a failed GLES trial; the separate
startup API and 600-second idle GPU service passed.

`org.gauguin.gpu-probe.plist` requests finite 128 MiB active/inactive hard limits
only for this prototype. The second physical trial proved that these job
properties alone are insufficient: GET command8 still returned active 6 MiB
nonfatal and inactive 6 MiB fatal. The probe exited before context creation.

The actual iOS 16.7.16 launchd selects each key in this order:
`Daemon.Override[label]`, `Override.Global`, job properties,
`Default[label]`, `Default.Global`. The device's `Override.Global` supplies
active soft 6 MiB and inactive hard 6 MiB. When positive soft and hard limits
coexist, launchd keeps the smaller; equal values prefer the soft limit.
Adding only hard 128 MiB to the label therefore still leaves active soft 6 MiB.

`probe-jetsam-policy.fragment.plist` provides the intended probe-label override:
active soft `-1`, active hard `128`, inactive hard `128`. Merge only that label
entry into the existing `Version4.Daemon.Override` dictionaries of the target
D22/D221 policies. The negative soft entry suppresses the inherited 6 MiB soft
limit; launchd removes it during validation and retains the finite hard limit.
The fragment is incomplete policy data: it must never replace a target policy
file. Preserve every global and other-label entry, as well as the existing job
and launch cache. Both installed target policies currently have equal parsed
contents but different serialized bytes; preserve each file independently.

Fourteen host cases execute the original binary's ARM64 merge, job whitelist,
int32 validation and soft/hard resolution with typed XPC/map stubs. They
reproduce the failed 6 MiB result, verify the proposed 128 MiB hard result,
check all five precedence levels, and leave an unrelated label at 6 MiB.
This does not test physical launchd spawning or effective kernel policy.

The actual iOS16 launchd recognizes `ActiveHardMemoryLimit` and
`InactiveHardMemoryLimit`; its binary explicitly says the older
`JetsamMemoryLimit` key is ignored. The probe reads its own effective limits
through XNU GET command8 and its physical footprint through `TASK_VM_INFO`
before/during context creation, shader linking and both readbacks. It refuses
unlimited, soft, incorrect or unreadable limits. It never sets memory policy.
These changes need a new physical trial; they do not establish GLES success.

```sh
python3 tests/test_gles_probe_memory.py \
  --kernel-source /absolute/path/actual-patched-XNU \
  --out /absolute/path/fresh-memory-boundary-results
python3 tests/test_gles_probe_order.py
```

The memory test uses the actual kernel's independent struct and command
definitions, then exercises the production query function with typed syscall
seams. It cannot establish that launchd applied the installed policy.

Kernels 179/180 provide the source profile for this package: a health-gated watchdog
service, up to 32 logical queues over one synchronous serialized ring, and
GMEM queries derived from the driver's native UCHE aperture configuration
(base `0x100000`, size 512 KiB). These are configured GPU addresses, not a new
measurement of physical RAM. The main project retains the physical 178
600-second idle-service acceptance and the separate 179 compatibility results
in `NOTES.md`. Kernel source/build and host checks do not qualify this library.

Device installation requires a fresh root backup and an explicitly approved
concrete file/cache/HFS delta. Physical acceptance must verify the late start,
actual A619 renderer, native GPU completions and both full pixel comparisons.
EAGL/compositor integration and multi-client address-space/lifetime isolation
remain required before ordinary UI processes may open the driver.

Direct HakiOS Metal remains a later frontend. Its pinned `gpu.hpp` uses pipe
`1` and its compiler uses a fixed A642L chip ID, unlike this Mesa path. Those
and the backend's device parameters require an explicit A619 port; changing
the GPU's display name is insufficient. None of this build qualifies Metal,
UI FPS, display refresh, suspend/resume or daily use.
