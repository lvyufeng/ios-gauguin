# HakiOS Metal core on gauguin

This directory pins public upstream source and carries the A619 adaptation.
The complete upstream checkout stays in a local cache. The patch changes the
Metal core, not gauguin's firmware, SMMU, kernel or installed GLES library.

`upstream.json` pins 227 Metal files at HakiOS commit
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438`. `air-upstream.json` pins its AIR
frontend, eight Mesa patches and Darwin shim, plus the Mesa 25.0.7 archive.
Upstream Metal/AIR sources and their notices are MIT licensed; preparation
preserves those files. Shader fixtures used here are the upstream authors'
own kernels, not Apple shader files.

Prepare fresh directories from already fetched, Git-blob-verified caches:

```sh
python3 tools/prepare-hakios-metal.py --cache /path/to/hakios-cache --out /work/metal
python3 tools/prepare-hakios-air.py --archive /path/to/mesa-25.0.7.tar.xz --cache /path/to/air-cache --out /work/air
```

Both cache roots contain the repository-relative directories named by their
manifest (`hakios-metal/` and `tools/mesa/`, respectively). Existing output
directories are rejected. Patches apply without fuzz; source and input hashes
are recorded. No downloads or device operations occur in these tools.

Build the prepared Mesa compiler archives for the host and iOS separately.
Use OSMesa disabled, LLVM disabled, Vulkan drivers empty and the Darwin
freedreno configuration. The exact thirteen archive targets are `ARCHIVES` in
`tools/build-hakios-metal.py`. The iOS cross file must select arm64, Darwin/iOS,
an explicit SDK and deployment target 16.0. Do not use the installed GLES
build as a writable workspace. The recorded local build and AIR smoke evidence
are described in [the qualification report](../../docs/gauguin-metal-a619-20261110.md).

Link the native core against that matching Mesa source/build pair:

```sh
python3 tools/build-hakios-metal.py --prepared /work/metal --mesa-source /work/air/mesa-25.0.7 --mesa-build /work/air/build-ios --out /work/native-metal --jobs 4
```

The builder selects `HAKIOS_METAL_TARGET_A619`, links AIR/NIR/IR3, validates the
Mach-O platform/deployment target, signs the dylib and checks its exported
entry points. The prepared core without that define retains the upstream
A635 profile for regression checks. A619 refuses an absent or different chip
identity, requires its GMEM size, and uses pipe `0x10` for query and submit.

`libGauguinMetalCore.dylib` is a local core artifact. It does not register an
MTLDevice, supply the Metal plug-in, install CoreAnimation shaders or implement
display presentation. Hardware execution and pixel correctness remain separate
requirements before connecting this core to the desktop.
