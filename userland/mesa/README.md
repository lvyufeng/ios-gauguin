# A619 GLES userland

This builds the actual Mesa 25.0.7 freedreno/IR3 driver for arm64 iOS 16 and a
standalone GLSL/IOSurface probe. It does not modify XNU, install files on the
phone, replace EAGL, or integrate Metal/CoreAnimation. The frozen 175 kernel and
its pending root delta remain separate.

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
Cross-compilation, signing and ABI checks do not prove that any shader has run.

The 175 prototype is insufficient for this full driver. Before device use:

1. Finish its separately approved physical BO/map/submit/fence/IOSurface trial.
2. Implement persistent watchdog/power/DMA ownership beyond the 20-second
   diagnostic window and recovery that preserves live mappings until DMA stops.
3. Supply the actual GMEM-base parameter 6. The probe refuses an unsupported
   query rather than guessing an address.
4. Support multiple independent queue IDs on the serialized hardware ring.
   Mesa creates a screen pipe and another pipe for each context; 175 permits
   only one queue. Numeric fences must retain the correct queue identity.
5. Physically verify this GLSL/texture/surface probe, then add the EAGL and
   compositor integration. Multi-client address-space/lifetime isolation is
   required before ordinary UI processes may open the driver.

Direct HakiOS Metal remains a later frontend. Its pinned `gpu.hpp` uses pipe
`1` and its compiler uses a fixed A642L chip ID, unlike this Mesa path. Those
and the backend's device parameters require an explicit A619 port; changing
the GPU's display name is insufficient. None of this build qualifies Metal,
UI FPS, display refresh, suspend/resume or daily use.
