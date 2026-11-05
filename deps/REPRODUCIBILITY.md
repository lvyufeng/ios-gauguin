# Replaying and building the gauguin baseline

`xnu/patches/series` is the active patch order. It retains patches 0001–0082,
uses the consolidated 0083 baseline through the old 0089 work, then applies
0090 onward. The other historical 0083–0089 patch files are not replayed.
Any failed patch stops staging.

Start with a fresh XNU checkout at `XNU_REV` from `deps/versions.env`. Choose
separate absolute paths for source and writable build state:

```sh
P0_SOURCE="$PWD/.deps-cache/p0/source"
P0_BUILD="$PWD/.deps-cache/p0/build"
bash deps/apply-patches.sh "$P0_SOURCE" "$PWD/deps/mirror" gauguin \
  "$P0_BUILD/source-state"
python3 tools/xnu-source-state.py check "$P0_SOURCE" \
  --state-root "$P0_BUILD/source-state"
bash deps/build-macos.sh gauguin --xnu "$P0_SOURCE" --build-root "$P0_BUILD"
```

Staging uses the tracked libpthread, HFS and BearSSL mirror. TargetConditionals.h
is fetched from a fixed SDK mirror commit and checked by SHA-256. To use an
existing copy, set `XNU_TARGET_CONDITIONALS` to its absolute path; the same hash
check applies. The header and downloaded SDK files remain outside Git.

The default source remains `.deps-cache/xnu-patched-0082-2`. Its name and
`.patch-set` file do not establish freshness. A missing or stale input record
stops the build without replacing that tree. `apply-patches.sh` writes the
record only after staging succeeds. An existing tree can be adopted with
`tools/xnu-source-state.py record SOURCE --state-root BUILD_ROOT/source-state`
only after independently comparing it with a fresh replay. Records are named
`<source-directory>-<absolute-path-hash>.json` and live outside the source.
They detect changed staging inputs; they do not prove the source was never edited.

`--build-root` isolates dependencies, SDK copies, objects, symbols, logs and
installation staging. Its default output is `BUILD_ROOT/out-gauguin-macos`.
An explicit `--out` chooses another publication directory. Existing default
paths remain unchanged when `--build-root` is omitted. The Linux entry point
accepts the same source/build-root options and uses a writable copy of its host
tools and SDK; its installed osxcross compiler is still an external input.

Every invocation installs into a new `BUILD_ROOT/runs/gauguin.*/install`
directory. A nonzero kernel build exit, missing kernel, or wrong Mach-O
architecture fails without publishing an old output or copying an old object
kernel. Successful builds publish `build-manifest.json` beside the output.
The manifest records actual source hashes, patch/mirror inputs, tool versions,
SDK metadata, generated link inputs, build exit and kernel SHA-256. It is a
provenance record, not proof of bit-identical output or successful hardware boot.

CI uses only the 13.5 dependency profile and the pinned XNU revision. The pinned
dxb supplies bootstrap tools and six path adjustments; the project applies its
own strict series and runs the kernel make with explicit error propagation.
Host tests cover the build adapter with fixture tools. A real clean kernel
build, a GitHub Actions run and a device boot are separate qualification steps.
