# gauguin port: handoff after the 2026-10-20 session (network-limited)

Read `PORT-gauguin.md` for the hardware facts and `NOTES.md` for the sweet
history. This file is the state at the end of the session that started the
gauguin port.

## What is done and committed (main)

| Commit | What |
| --- | --- |
| `fe32fc4` | shim reads `/memory`, `cont_splash_region`, `/chosen framebuffer` and `ufshc` from the live FDT; 16K page tables cover the low 64 GB + the kernel bank as a 1 GB block; `mkadt.py --device=gauguin` (DRAM `0x180000000` + 4 GiB, `qcom,sm7125`); `tools/mkbootimg2.py`; `unpack_bootv2.py` dtb field fix; `PORT-gauguin.md` |
| `71eb706` `404638a` | `0082-gauguin-board.patch`: `GAUGUIN` machine config (`-DGAUGUIN`), Focaltech FT5452 on SE8 (`0x988000`), PM6350 keys (SID 0, PPID `0x4c0`), RPMh `ldoa6` 1.8 V, `xiaomi,gauguin` IOKit matches; vendor DTS reference copy in `dts/gauguin/` |
| `6b9f5b2` | touch probe continues when the RPMh ACTIVE vote fails, dumps unknown IC registers |
| `dcb4ed0` | 0054 reverted to the sweet original; `.deps-cache/`/`osxcross/` ignored |

Local-only (not committed, `.deps-cache/`, ~1.4 GB): patched xnu tree,
osxcross toolchain (`osxcross/`), the warp cache for CI.

Backups on this machine: `backup/{boot,dtbo,vbmeta}.img`,
`backup/partitions/{persist,modemst1,modemst2,fsg,fsc}.img` + `SHA256SUMS`
(all read from the phone in TWRP, read-only).

## What is NOT done

**No gauguin kernel has been built and the phone has not booted it.** The
gate is the kernel build, not the hardware code.

## The kernel build problem (read this first)

1. **GitHub Actions is the only workable builder right now.** dxb
   (blacktop/darwin-xnu-build) stages everything as before, except
   dxb's own bootstrap (`build_bootstrap_cmds` ... ) ends with `build_xnu`
   of a **VMAPPLE** bootstrap kernel. The SWEET patch series does not link
   for VMAPPLE: `sweet_sample.c` (added to `bsd/conf/files` as
   `standard`) references `sweet_sample_task`, which `0054` only puts into
   `osfmk/kern/exception.c` **inside `#if defined(ARM64_BOARD_CONFIG_SWEET)`**.
   Both the original 0054 and the "fix" (guarding the whole file) were tried;
   the file-guard version produced "unterminated conditional directive" and the
   original still fails the VMAPPLE link. dxb has no flag to skip the VMAPPLE
   bootstrap build.
2. **The workflow currently does** (`0749578`..`47ac490`, `dcb4ed0`): dxb
   bootstrap without dxb's `patches` step, then the series, then per-config
   `xnu_headers ... build_xnu` with `MACHINE_CONFIG=<mc>`. The bootstrap still
   compiles VMAPPLE and fails as above.
3. **Options, in order of promise:**
   - a `xnu` fork on GitHub owned by the user: fork apple-oss xnu, add commit
     `xnu-8796.141.3-patched` that puts `#if defined(ARM64_BOARD_CONFIG_SWEET)`
     around the body of `bsd/dev/sweet_sample.c`, push to the fork's `main`;
     `deps/build-local.sh` already clones the tree by URL and rev
     (`deps/versions.env`). CI then builds only `GAUGUIN` (VMAPPLE no longer
     breaks);
   - or patch the dxb clone from the workflow before sourcing it (replace
     its `build_xnu` with a no-op during the bootstrap);
   - or run dxb once with `MACHINE_CONFIG=GAUGUIN` (`bash build.sh` from the
     gauguin branch of the fork) so even its bootstrap builds gauguin.
4. **This host's network** to GitHub download hosts is ~4 KB/s (Apple CDN,
   npm and PyPI via Tsinghua are fine). CI log artefact downloads also time
   out often; the workflow now uploads `/tmp/dxb-*.log` as `dxb-logs` and
   prints the first errors itself.
5. **sudo does not work here** (`no new privileges`), so no apt; use a
   prefix (`pip --target`, tarballs) for tools.

## Local build progress (xnu-port/, untracked/WIP)

I started a CMake + host-tool port that needs no dxb and no TAPI:

- `xnu-port/CMakeLists.txt`: clang (macOS or osxcross) + **`ld64.lld` from
  LLVM 17 links against the macOS SDK `.tbd` stubs successfully** (tested:
  a Mach-O arm64 executable linked on this Linux host).
- `xnu-port/doconf.py`: Python port of the csh `SETUP/config/doconf`;
  **works**: it produces `config.DEVELOPMENT_ARM64` with 368 options and 36
  pseudo-devices from the real `MASTER*` files (the config attribute
  selector resolution needed a fix and is now in place).
- `xnu-port/host/xconfig.c` + `getword.c`: native (Linux) driver for xnu's
  generated makefiles (`mkmakefile.c`/`mkheaders.c`/`mkioconf.c` linked with
  `-fcommon` against a stub `parser.h`). **Works** (`b780d64`): run as
  `xconfig -c <tree>/<comp>/conf <objdir>/config.<KERNEL>_<ARCH>`; it writes
  `Makefile`, `ioconf.c` and the option headers (39 files for osfmk).
  Next: the other components, genassym, then the compile.
- The macOS SDK is at `research/tmp/sdkpkg/.../MacOSX11.3.sdk` (from the
  Apple CLT package, fetched from Apple's CDN, unpacked with `research/tmp/
  sdkpkg/xarpack.py` + `pbzx.py`); the in-repo `xnu-cache/blobs` branch has
  the same SDK + BearSSL/hfs/libpthread for CI.

## Plan A state (fork)

The user chose plan A: a fork of apple-oss xnu under `lvyufeng/xnu` with a
branch CI can build. `deps/make-branch.sh WORKDIR` prepares it from a clone
of the fork (real `xnu/patches` + `deps/mirror`, commit made as the user).
Every SWEET-only source in the series carries `#if defined(
ARM64_BOARD_CONFIG_SWEET)` (`sweet_sample.c` via 0054, the rest already), so
a VMAPPLE bootstrap build links. The workflow must then clone
`--branch gauguin https://github.com/lvyufeng/xnu dxb/xnu` before dxb runs.

## Next concrete actions

1. Fix the `xconfig` segfault (or fall back to the Darwin config tool inside
   CI, where the whole Makefile build works anyway).
2. Get one `GAUGUIN` kernel: either the xnu-fork route for CI, or finish
   `xnu-port` locally (genassym → compile → link with ld64.lld).
3. Package: `tools/mkpayload.py KERNEL ADT PAYLOAD` with
   `python3 tools/mkadt.py adt --highmem --device=gauguin`, then
   `shim/build.sh PAYLOAD` → `shim/out/shim-boot.img`; boot with
   `fastboot boot shim/out/shim-boot.img` from the fastbootd/fastboot of the
   phone (it is now in TWRP).
4. The iOS root (v15, `userdata` = `sda35`) has not been touched; the user
   allowed clearing `userdata` later (`backup/` has the calibration
   partitions).