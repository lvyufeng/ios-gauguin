# Full kernel and three inherited scan timing images, 0259

The gauguin scan worker from 0217 now has a full ARM64 DEVELOPMENT kernel
and three temporary Android boot images. The scan modes are intended for
separate hardware trials of GCC, DISP_CC and INTF1. Access to the downstream
registers and the iOS scan frequency still require phone measurements.

[GitHub Actions run 42916745065](https://github.com/lvyufeng/ios-gauguin/actions/runs/42916745065)
built commit `1cefd98ea95fc09cfc33385d976021f7c7f4b095` on branch
`codex/gauguin-scan-timing-20261111`. Job 130181035584 ran from 22:46:01 to
22:54:26 UTC on 2026-11-10 and succeeded. DSH ran the six focused host checks
locally before dispatch. The cloud run repeated those checks, including
the 16 actual scan sampler scenarios, then linked the complete kernel
with the pinned 13.5 dependency profile.

The kernel is 17,882,976 bytes. SHA256
`949e10f9ba7fb2dd2e1d4134f4abcb8c11744f8c033969dd8afbf4f41c641a54`.
Its build identity is `xnu-182cecd683034be3bce5215a65380edc`.
The 5,338-file postbuild archive matches the captured build source,
SHA256 `b47fb04f0f40c2afa77648c9fd91b616f8c4995320758ddc1902fc58d0d86909`.
Compared with qualified local 0258, only the same four dxb build
adaptations differ. Qualification confirms 282 retained definitions
in their prior sections, the two new scan text definitions, zero undefined
symbols and the retained 64-bit physical cache address path. The CI SDK
and external libraries are recorded in the build manifest.

## Images

All three files are 19,955,712 bytes. The output directory is
`research/tmp/gauguin-build255-worktree-20261111/research/tmp/dsh-scan-build-0259/images`.

| File | Stage | SHA256 |
| --- | --- | --- |
| `gauguin-0259-scan1-gcc.img` | GCC display branches | `db3cd1de935f84c6c07aa9f2fb5c48ef26dd108f236e32b955b3b2e9304e7ca7` |
| `gauguin-0259-scan2-dispcc.img` | Adds DISP_CC branches | `8637533dc3148f4ed4e8edaf9ff4e33898d8fdf020cf8180568e5bcd004b7b01` |
| `gauguin-0259-scan3-intf.img` | Adds INTF1 frame and line sampling | `2c0178833183cb638ba64774d6e4795abd99d6e7843c24dbbbba1c0ab6c713a4` |

Independent readback checks every file-backed byte of the ten kernel
segments, the five firmware assets and padding, the Android v2 header,
shim and DTB, the original managed RAM range and the zeroed 2 MiB PAS
tail. The only difference across the three complete images is the scan
selector digit. Each 595-byte command replaces `sweettrace=2` with one
scan selector. The other desktop profile tokens and order are preserved.
The selected scan stage measures boot-time counters, separately from the
0255 gesture trace.

DSH dispatch PID 54546 exited 0 in 21.444 seconds. DSH artifact stage
PID 57165 exited 0 in 47.846 seconds after downloading 94 files
(102,027,101 bytes), qualifying the kernel and building all three images.
The CI watcher and both DSH launchers are terminal. The independent
`review.json` SHA256 is
`8c134a1ec12a853a257bbe033b7f21de5dd58d59a905960e4a78254e8cef107b`.

Physical acceptance still starts with the pending 0240 trial on paired
0239 and the subsequent scoped desktop installation and 0250 desktop
check. The 0255 gesture trace remains available. When the scan images
are tested, use the separate GCC and DISP_CC trials to establish register
access before attempting INTF1. An observed inherited cadence is a
prerequisite for display mode and presentation work. This milestone
performed no phone command, flash, root write or boot.
