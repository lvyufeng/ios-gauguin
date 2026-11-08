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

Runtime injection is still unproven. The existing backboardd plist and its
cached job differ only in the cache's two logging environment variables;
future staging must preserve those separately. The diagnostic library may
be added only after a new full backup, exact local HFS delta review and
explicit consent. A later rendering stage also needs compositor-scoped
GPU authorization and startup ordering. Ordinary applications must remain
denied while the driver has a single privileged owner and a global GPU page
table. Do not run backboardd as root to bypass that work.

The complete diagnostic C function also runs under typed OS boundaries and
real host Objective-C metadata in fourteen scenarios, including rejected
process identity, missing or changed method metadata, failed memory queries,
and a requested `render` mode. Every original IMP remains unchanged and every
call returns zero. Run it with a fresh output directory:

```sh
python3 tests/test_eagl_admission.py --out /absolute/path/fresh-host-check
```

The strict GNU C build removes the primary source's unsafe nonzero-depth
return-address diagnostics and unused extension counter. It preserves
`-Wall -Wextra -Werror`. Both Mach-O products have one constructor, verified
through this toolchain's `S_INIT_FUNC_OFFSETS` entry and local symbol table.
Physical injection and desktop rendering are still separate acceptance steps.
