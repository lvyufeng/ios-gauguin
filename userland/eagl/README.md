# EAGL compositor admission

The accepted A619 Mesa185 renderer passes standalone shader, texture and
IOSurface checks. Desktop acceleration is a separate stage. The original
HakiOS bridge is pinned at `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`;
`upstream.json` lists the six source files needed in an offline cache.
Its 457 named GL dispatch entries (409 offsets, 62 marked for QuartzCore)
were compared with this root's iOS16.7.16/20H392 public GL stubs. All offsets
match. This does not qualify arbitrary argument semantics or UI rendering.

```sh
python3 tools/build-ios-eagl.py \
  --upstream-cache /absolute/path/pinned-hakios-files \
  --mesa-build /absolute/path/accepted-Mesa185-build \
  --registry /absolute/path/mesa-25.0.7/src/mapi/glapi/registry/gl.xml \
  --out /absolute/path/fresh-EAGL-build
```

The builder leaves the accepted Mesa library unchanged and produces two
signed arm64 iOS16 libraries. `libGauguinEAGLAdmission.dylib` reads the eight
EAGL method encodings, the calling compositor's GET8 memory limits and VM
footprint, and whether the GPU service is registered. It has no Mesa
dependency, GPU-open API or method-replacement API. It reports only when
loaded into `backboardd` as uid/euid501. No memory policy is changed.

`libGauguinEAGL.dylib` compiles the primary bridge against the accepted Mesa,
with a bounded uint32-to-GLsizei adaptation for the actual method's width
and height parameters. The diagnostic gate always returns zero, so the
compiled bridge cannot install renderer hooks. An environment variable or
boot argument cannot enable it. This product is for compilation review and
must not be described as an enabled compositor GPU driver.

The 0190 and 0191 device trials verified diagnostic injection into the real
UID 501 backboardd job. The existing backboardd plist and its cached job
remain byte-for-byte unchanged when staging the pilot libraries.

Build the separate 0192 compositor GPU probe and its admission launcher:

```sh
python3 tools/build-ios-eagl.py --compositor-pilot \
  --mesa-build /absolute/path/accepted-Mesa185-build \
  --out /absolute/path/fresh-compositor-pilot-build
```

On a kernel built with scoped compositor GPU authorization, the launcher
starts its worker only in the UID 501 backboardd process with a single
`sweeteagl=2` boot argument and the existing admission environment. The
worker runs off the startup thread. It waits for a successful GPU client
open and close before loading the probe from the root-owned library path.
The kernel holds that open until the root client releases the GPU cleanly
after six native fences. The probe reads back a 32×32 shader result and a
sampled IOSurface using the accepted Mesa. The built libraries leave renderer
methods unchanged. The 0192 device trial passed this probe inside UID 501
backboardd, with native fences 7–9 after six root fences, both complete pixel
checks and the ten-minute GPU health service.

The experimental desktop bridge builds with the same pinned bridge inputs:

```sh
python3 tools/build-ios-eagl.py --compositor-bridge \
  --upstream-cache /absolute/path/pinned-hakios-files \
  --mesa-build /absolute/path/accepted-Mesa185-build \
  --registry /absolute/path/mesa-25.0.7/src/mapi/glapi/registry/gl.xml \
  --out /absolute/path/fresh-desktop-bridge-build
```

This launcher runs the successful GPU probe first, then retains the desktop
bridge image for the compositor lifetime. The bridge verifies all eight
method encodings and the explicit mode-2 gate. It registers a same-sized
EAGL subclass with the Mesa methods, then publishes the base initializer
hook. New Mesa contexts adopt that subclass. Existing native instances and
other subclasses keep their native method dispatch. A recursive lock
protects the context registry. The first desktop trial still needs actual
CoreAnimation draws, full-resolution IOSurface output and stability checks.

```sh
python3 tests/test_eagl_bridge.py
python3 tests/test_eagl_admission.py --render-pilot --out /absolute/path/fresh-render-gate-check
```

The complete diagnostic C function also runs under typed OS boundaries and
real host Objective-C metadata in fourteen scenarios, including rejected
process identity, missing or changed method metadata, failed memory queries,
and a requested `render` mode. Every original IMP remains unchanged and every
call returns zero in the default build. Run it with a fresh output directory:

```sh
python3 tests/test_eagl_admission.py --out /absolute/path/fresh-host-check
```

The strict GNU C build removes the primary source's unsafe nonzero-depth
return-address diagnostics and unused extension counter. It preserves
`-Wall -Wextra -Werror`. Both Mach-O products have one constructor, verified
through this toolchain's `S_INIT_FUNC_OFFSETS` entry and local symbol table.
The default build retains these same diagnostics and disabled bridge.

The compositor build also requires the 20H392 QuartzCore `function_uniform`
observer before it publishes its EAGL subclass. The observer validates the
QuartzCore UUID, unslid image base, the single GLESContext virtual slot and
64 bytes of the actual method entry. It changes a private COW data page,
restores its original protection, and rolls the slot back if protection
restoration fails. All calls, including native contexts and rejected uniform
arguments, forward unchanged to the original method exactly once.

Effect uniforms belong to each registered EAGL context, rather than the
upstream global CA pointer and arrays. Bounded self-task reads validate the
live CA vptr and its dispatch-table association before collecting uniforms or
selecting a draw function. Invalid updates clear the affected uniform count;
unreadable or mismatched contexts yield an unknown function. Draw snapshots
and observer updates use the registry lock. EAGL's usual requirement that a
context be used by one thread at a time still applies. Native contexts never
receive the custom state. The host observer tests use the production code,
actual Mach VM/COW pages and ASAN/UBSAN; device visual correctness remains a
separate requirement.
