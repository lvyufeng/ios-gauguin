# Complete local desktop candidate and private pipeline cache, 0249

The candidate now contains a fully linked native kernel, seven userland files,
target ownership/mode declarations and a checked desktop command line.
A real root-versus-mobile pipeline-cache conflict was found while assembling
it and corrected in the desktop frontend. This is an offline asset package,
not an installed root volume, boot image or working-phone result.

Source commit: 4e622627c776e6d4b1b9ad11c98920d4251b001f, branch
codex/gauguin-metal-desktop-package-20261111. Follow-up abd1408 adds the Git
attribute for unified-patch context prefixes; source/binary inputs remain
unchanged. The kernel was built earlier from clean parent
001965c94e3da70676db411df072f22618e3dc9a. Later changes are userland/package
sources; the kernel's 206-patch source stays byte-identical.

## Concrete startup correction

The verified pre-0240 backup contains
/private/var/tmp/hakios-pipelinelib owned by root, mode 0755, with seven
descendant entries from the earlier root diagnostic. The desktop runs as
mobile, UID 501. Those POSIX permissions prevent creating missing cache
entries there. This does not establish that an observed phone UI failure was
caused by this path; the new desktop has not run.

The frontend's pipeline-library fallback still used that shared temporary
root. Its existing shader-stage cache was already private, but that does not
redirect this separate pipeline-directory mirror. Desktop-only patch 0008 now
uses /private/var/mobile/Library/Caches/gauguin-metal244/pipelinelib.
The cache base is shared as a constant with the existing admission check.
Other six frontend profiles and the old root diagnostic paths stay unchanged.

The test executes the actual pipeline-library method's filesystem operations.
The old method fails when its shared directory is unwritable; the new method
passes 23 assertions covering private and warm caches, denied writes, original
library success, nil input and an unchanged old-cache sentinel. Storage roots
are rebased into private host fixtures, and Metal's cache class/format is
modeled. This proves neither the iOS cache ABI nor GPU rendering.

The new signed frontend is 428,400 bytes, SHA256
b7fcc72fc69a0ed429effecdf1b6b1ef071bc17a582832a32c3f95b52ea56acc.
It adds no native import and removes only NSTemporaryDirectory. The remaining
import/binding and dylib dependency tables match 0246, so the prior actual
20H392 symbol-resolution evidence is retained. Runtime private ABI checks and
five disabled optional M2V hooks remain unchanged.

## Kernel and asset package

DSH builds with fresh objects and cloned dependencies, preserving a 4 GiB free
space reserve. The source is a separate clone of the qualified 0248 pristine
replay; staging inputs and all 5,332 source files are verified. Its SHA256 is
2e62225c17d0886bdd018a13fd1e958f9def5c8dabc7f888e07a79f7da6ca80f.
The build and retained generic qualification both exit 0. The archive,
installation, provenance, SDK, old required symbols, held-frame/phase-clock
entry points and new desktop entry points are checked. Existing compiler
diagnostics are retained; the prior focused host checks are reused rather
than described as another complete host-suite run.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Complete kernel | 17,331,000 | 50ca42ff49dab0fef6802a0fc149b57270da3707a8d6dc29c9bb760c1d03dac0 |
| Desktop frontend | 428,400 | b7fcc72fc69a0ed429effecdf1b6b1ef071bc17a582832a32c3f95b52ea56acc |
| Retained 0240 probe | 139,376 | 26d09095687544b44af83232fd850c8d8c0d2149a7c17b87b7a0500b697bca3b |
| Root bootstrap | 115,968 | 2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c |
| SETEXEC router | 69,536 | a32f77cbbac5583fb681c037ab77cb2f16e304dc85006e5762bf3da1ab96c101 |
| A619 core | 8,369,632 | 8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1 |

The kernel banner is Darwin 22.6.0, Wed Nov 11 02:23:43 CST 2026,
xnu-538af7e14895401d81b773e520ae23f5. Run directory:
.deps-cache/p0-20261105/build249-desktop/runs/gauguin.l4qOcU.
Its manifest SHA256 is
0d411ea973bef99836beceb9a84783d6bd9f74964e0e0d7beb2a6537262b0c90.

Seven root files total 9,125,479 bytes: the five userland binaries above,
plus the desktop bundle's Info.plist and resource seal. Signatures and native
dependency tables are checked. The two mobile cache directories declare
501:501/0700; bundle directories declare root ownership. Payload ownership on
the Mac is explicitly separate from installation ownership, and existing
parent-directory metadata must be preserved.

The 638-byte command line derives from the physically qualified 0239 profile.
Six keys are replaced once, with all other board tokens preserved: the three
desktop selectors, held-frame and phase-clock flags, and a 60 Hz software copy
target. It stays below the 1,023-byte consumer limit. These values do not
configure or qualify physical 90/120 Hz.

The system contract is read from the verified immutable 16 GiB 0240 backup.
It confirms the image's existing 20H392 default.metallib and pipeline assets,
the writable mobile cache parent and the system Extensions directory.
No other system's Apple shader library is added.

Three qualified 0247 task/cache files are stored separately as templates,
outside the root payload. They must be regenerated from a fresh post-0240
capture. The package is explicitly not a ready volume delta; no stale cache
template should be copied directly onto the phone. An independent checker
verifies actual file hashes, native load tables, target metadata, kernel and
template separation, and rejects 23 mismatched contracts.

## Execution record

| Stage | Dispatcher | Exit | Evidence |
| --- | ---: | ---: | --- |
| Full kernel | 4825 | 0 | DSH, 122.123274 s, 723 unchanged pins; build and qualification 0 |
| System contract | 43062 | 0 | Local pinned fallback, 8.524421 s, 8 unchanged pins |
| Frontend v1 | 44694 | 1 | Six old profiles and new preparation pass; host seam name shadows a local variable |
| Frontend v2 | 45074 | 1 | Corrected old/new filesystem controls and native build pass; overly strict equality check rejects the removed import |
| Frontend v3 | 45397 | 0 | Audit only, 42 unchanged pins; confirms exactly one removed import, no rebuild |
| Package | 45780 | 0 | Local pinned fallback, 3,250 unchanged pins; assembly and 23 rejection controls pass |

After the kernel stage, two DSH provider sessions terminate with TRANSPORT
errors before launching any system-capture stage. The original logs are
retained. Codex then starts the same pinned local executor for readonly
capture, frontend build/checks and package assembly. Those steps are not
reported as DSH execution. Failed fixture/audit stages are retained; only
unfinished checks resume after their authoritative terminal results.

Codex independently rehashes final stage pins/logs, the complete source,
frontend inputs and binary, packaged files and kernel. Private evidence:
research/tmp/dsh-package-0249-desktop in the 0249 worktree.
review249-v1.json SHA256:
65fa9fbc1213c83d6454f55198e9fc1d63d79365e1acba98aff09780a2c9eaa6.
Readonly cache-parent observation SHA256:
141b0088d79270352e53750dcf9cb12b5991e456e4ee979a3e6f1d06e2eac567.

## Remaining acceptance

Next assemble and qualify a temporary boot image from this kernel and checked
board profile. No phone boot may stale the pending 0240 delta. The genuine
0240 write reply is still absent; its exact paired 0239 image, SHA256
7357a0abf1894969d1b67b2000fcf2e1e928adb2583bf02bb9850cfea6b99956,
must run first after that installation. A desktop root proposal then needs
a fresh capture/backup, regenerated task/cache files, scoped delta review and
its own individual write consent.

Actual acceptance must show root startup timing, clean owner handoff, real
backboardd discovery/native jobs, populated icons/widgets, correct effects,
shared output, repeated transitions and safe reuse. Synchronous GPU submission
and the global display-copy lock remain. Measure touch-to-panel latency and
sustained correct 60 Hz before prioritizing asynchronous overlap and physical
90/120 Hz. RAM, storage, peripherals and daily-phone readiness remain open.

No device command, userdata write, mounted-root modification, boot, CI run or
push occurred. The physical 0239 kernel, installed 0237 root, pending 0240 plan
and unrelated MAIN mkadt.py edit remain unchanged.
