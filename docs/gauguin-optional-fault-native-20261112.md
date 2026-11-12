# Optional GFW fault-profile kernel: native build evidence

2026-11-12 CST. Local full kernel build and native artifact qualification passed.
Runtime performance and all phone acceptance remain unqualified.

The source is local commit `8787ed352c8b6546fcc39e3434d6937e81045db5` on
`codex/gauguin-optional-fault-profile-20261112`, in
`research/tmp/gauguin-optional-fault-profile-worktree-20261112` (R below).
Its 214 active patches descend from the exact 213-patch 0298 source. The full
source SHA is `4e29d9db16724271641fb1c7c9f7a09ec2a24fef10e0f7be3d4fc4c282e1dfff` (5,333 files). Only
`bsd/dev/gauguin_gmu_board.c` differs from 0298; all other source entries match.

0222 makes only GFW subgroup diagnostic timing default-off; `sweetgfprof=1`
explicitly enables it. Live reads, predicates, barriers and deadlines remain
in the source. Disabled sites still execute an atomic policy load and branch;
other guard/runtime clocks remain. The sealed earlier 29-test suite includes
80 deterministic fault/settle/deadline cases across baseline/off/on, plus
actual macro/configure/dump tests. It is source/model evidence. The historical
6/12 suites and ARM64 TU are retained, without another test run in this build.

Dispatcher **55911** executed the pinned v2 profile once, finished exit 0 in
185.691 seconds, with all 49 input pins unchanged. The 12 external file
pins also remain current. The wrapper admitted the entire 8 GiB native batch
plus 256 MiB pending capture before its independent source/dependency clones,
fresh objects and native make-install. Make and qualifier both exited 0.
No CI run or remote publication occurred.

- Local run: `gauguin.UV1bla`
- Identity: `xnu-74ec6106a08a44889ffee9668d76986e`
- Native installed kernel: `.deps-cache/p0-20261105/build-optional-fault-profile/runs/gauguin.UV1bla/install/System/Library/Kernels/kernel.development.gauguin` relative to R
- Kernel: 17347344 bytes, SHA `3079754f80e690b7576968e6d3679d1fc79f8659552600058b34d7314f5dcc92`
- Native link archive SHA: `7940a22b9494924e012e3e4a27d49c6f44dcbe4dffe09752a5818f96fa763427`
- Native kernel and the actual archive's unique `version.o` carry the same
  banner/build identity; the manifest carries that same banner and source.
- The installed file is a thin ARM64 Mach-O executable; 261 required symbols
  have definitions. Prior binary markers are retained, plus the new optional
  flag and both status literals. This proves native presence/provenance only.

The first prepared validator expected newline-ended new status strings.
Codex checked the accepted ARM64 object: `gmb_record` adds the newline
separately, and the literals are NUL-terminated. The v2 check uses those exact
constants; eight original v1 files remain in `review-v1-original/`. No kernel
build was launched from v1, and the v2 build was not retried.

Evidence under R's `research/tmp/optional-fault-native/`:

- `build-stage-profile-v2.json`, `build-stage-run/result.json`
- `kernel-source-result.json`, `kernel-result.json`, `kernel-qualification.json`
- `kernel-build.log`, `kernel-qualification.log`
- `codex-review-v2.json`, `codex-artifact-audit.json`
- `storage-preparation.log`, `storage-build.log`, `storage-post.log`

Post-build accounting is **450792763392 B** of the
500,000,000,000 B cap; whole-turn accounted growth is 3548626944 B, within the
8 GiB native reservation. APFS clones are counted conservatively. Backups and
all 82 original 0298 ready pins and 12 preserved 0297 evidence files match.
The original MAIN `tools/mkadt.py` edit remains uncommitted and unchanged.

The kernel is not packaged or booted. The reviewed 0298 image/605-byte command
are still separate and unapproved; no approval or trial output was fabricated.
0298 remains the next individually scoped device test, using its existing
fresh-preflight/one-shot/post-capture helpers after the real answer. Do not
substitute this new kernel into that plan.

For a later same-kernel timing comparison, a command budget still needs review.
Omitting `sweetfb_hz=60` is not equivalent: its source default is 10, changing
`fFlushTicks` from 1 to 6. Copy cadence is not physical panel refresh or FPS.

No device commands, partition writes or boots occurred. This increment does
not qualify physical MMIO/fault behavior, watchdog reset, GPU/Metal rendering,
desktop correctness, latency, 90/120 Hz, all safe RAM, storage reliability,
peripherals or daily use. The full phone objective remains active.
