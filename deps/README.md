# Network plan for the gauguin build (host network is the bottleneck)

Status 2026-10-20: GitHub download hosts (`codeload.github.com`, release
assets, Actions artifacts) deliver ~4 KB/s from this host, every mirror
tried is no faster or slower, and uploads to `github.com` are fast. Every
failed CI run died while re-downloading Apple's trees (a shared libpthread,
Libsystem or xnu checkout). Conclusion: **download each source once, locally,
and cache it**; CI is no longer on the critical path.

## Where each piece comes from

| Piece | Size | One-time source | Why |
| --- | --- | --- | --- |
| macOS SDK headers (11.3, from the CLT package, Apple CDN) | ~35 MB | done: `blobs-1..4.tgz` in the repo's `blobs` branch → `xnu-cache/blobs/` | Apple CDN is fast; CI/another host pulls them from the repo (fast upload/large files OK) |
| BearSSL, hfs, libpthread (used by the SWEET patches) | ~3 MB | `deps/mirror/` (small file set, pinned commits) → `blobs` branch | same commits as `xnu/patches/0*stage-*.sh`, no `apple-oss-distributions`/`bearssl.org` fetch |
| xnu-8796.141.3, dtrace-397, Libsystem, libplatform, libdispatch, AvailabilityVersions | ~150 MB | `deps/build-local.sh` (pinned revisions in `deps/versions.env`) | fetched once into `.deps-cache/`, reused by every later build |

Already on this host (from earlier in the session):

- `research/xnu-8796/` – xnu-8796.141.3 + the whole SWEET patch series
  applied and committed (the patched tree the build needs).
- `research/sdkpkg/root/Library/Developer/CommandLineTools/SDKs/MacOSX11.3.sdk`
  – the Apple SDK, repacked as `research/tmp/blobs-1..4.tgz`.
- `research/tmp/dxb.sh` – the darwin-xnu-build script at `DXB_SHA`.

So only four downloads remain for a full local build:

1. xnu, dtrace, Libsystem, libplatform, libdispatch, AvailabilityVersions at
   their pinned revisions (`deps/build-local.sh`; can also be fetched on
   another machine and copied in, the cache is plain git checkouts).
2. cctools-port + ld64 (the linker and tools in `ld64-*.tar.xz`/`cctools`).
3. clang for the host (system clang 17 is enough to compile cctools; the
   codegen clang can be any LLVM with the Darwin target and macOS SDK).
4. Bootstrap tools (`mig`, `ctfmerge`) built with the host compiler –
   see `deps/README.md`; this is the remaining technical work item for the
   osxcross route.

## Things that make the slow link hurt less

- `deps/build-local.sh` keeps the patched tree in `.deps-cache/` and only
  re-applies patches when `xnu/patches/` changes (`PATCH_SET` in
  `deps/versions.env`), so an iteration costs no network at all.
- The blobs branch is fetched with `--depth 1` from the same host that
  already pushes fast.
- A CI run is only started on request; with `xnu-cache/` in the tree the
  workflow can stage everything without touching Apple's hosts (the KDK and
  Xcode are preinstalled on the macOS runners).