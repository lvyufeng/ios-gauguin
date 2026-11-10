# Desktop boot command and temporary image, 0250

The 638-byte desktop command is replaced by a complete 607-byte profile that
fits the unchanged payload/shim ABI. A fully linked kernel and temporary
Android boot image now exist and pass offline qualification. No phone was
booted and no root volume was written. Desktop rendering and latency remain
unqualified on hardware.

Active worktree: research/tmp/gauguin-boot250-worktree-20261111, branch
codex/gauguin-desktop-boot-profile-20261111. Critical source d4dba773471b0fd6d5bd05f04fde9199f39be925;
fixture corrections 1fe2a7e and 5cc15ed; package binding and full-build clean
head d0409f25c40a764b0914089a57212b3e6bb01cce.
The [previous review](gauguin-hakios-success-recheck-20261111.md) describes the
confirmed truncation; its old package receipts are preserved.

## Complete command without changing the loader ABI

Payload v1 and boot_args both have a 608-byte command field, including NUL.
The segment table still starts at 0x2a8. mkpayload now validates UTF-8 byte
length and embedded NUL before opening kernel/ADT inputs. Invalid commands
raise an error rather than silently becoming a prefix; CLI failure preserves
an existing output.

Patch 0215 changes only SweetFramebuffer.cpp. The existing exact desktop
predicate, sweet_dyld_probe=1/sweeteagl=2/gmt=2, supplies defaults for held
presentation and the phase clock. Explicit sweetfb_hold/sweetfb_phase values
retain their prior meaning, including opt-outs and invalid-value rejection.
Other modes retain the previous defaults. The predicate uses early TUNABLE
initialization; no new late userland configuration dependency is added.

The package therefore needs four overrides, not six: the three desktop
selectors and sweetfb_hz=60. Every other board/GPU/UFS/health token is preserved.
The complete profile is 607 bytes with one terminating NUL. The software copy
target is still separate from physical refresh; this does not configure or
qualify 90/120 Hz.

Schema250 binds the package to the 207-patch kernel's exact source digest and
desktop default policy, so an older kernel that still requires redundant flags
cannot pass package validation.

## Source, host and native evidence

The source is an independent clone of the verified 206-patch source, with
identical old staging inputs and only strict zero-fuzz patch0215 added.
Exactly one of 5,332 files changes. The software/native-TU tree and separate
full-build tree have identical entries and content digest:
79a03b79d0de8d9753e1952333d79a7b6ca75461e32764b41b1bc2a04620bfef.
The original 0249 source remains unchanged.

Checks exercise actual implementation bodies, not a second policy model:
four boot-command groups cover byte boundaries, UTF-8, embedded NUL,
pre-input rejection, CLI output preservation and actual physical-board
arguments. The old real packer demonstrates the lost suffix. Seventeen
firmware payload regressions pass; the old 800-byte golden input is now
represented by its identical valid 607-byte prefix, with overflow refusal
checked separately.

Actual desktop predicate and framebuffer setup pass 5,400 selector/override
cases, 22,038 assertions, under ASan/UBSan. Kernel argument and clock operations
are typed host seams. Prior held-surface lifetime checks pass 3,236 assertions;
phase-clock checks pass 7,264 assertions, including their functional old-source
failures. These are host scheduling/lifetime checks, not GPU or panel results.

Native framebuffer TU: 427,064 bytes, SHA256
f7f208c5e96e97463fadc2578cf419f77854bbfeaf31f15a39a2d9aa79b6f9e9.
Its 5,334 source/context pins and 2,130 header/config checks verify unchanged.
All 372 undefined symbols match the actual 0249 framebuffer object.

## Complete kernel and image

DSH builds fresh objects with cloned dependencies from the clean head above,
then runs the retained archive, SDK, provenance, symbol and native checks.
SKIP_TESTS=1 avoids rerunning the whole unrelated host suite; the focused
checks above are the test evidence. Existing compiler and resource warnings
remain recorded.

For this host build, the capacity preflight uses 1,667,612,672 bytes of
reference outputs, 512 MiB overhead and a 2 GiB reserve against about 5.31 GB
free. This explicitly differs from 0249's 4 GiB reserve. No old artifact is
deleted. Free space after the package/image stage is about 2.97 GiB.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Full kernel | 17,331,000 | dc220b5b24c38f0bd641c2a41693ba664447d18a0735e8c342df6b2fbfd8cae8 |
| Temporary boot image | 20,021,248 | 18d3196f5827e7105c7b598c2951596f25f56449330223cbc9530ff3d4f1f72f |

Run: .deps-cache/p0-20261105/build250-desktop/runs/gauguin.P5wxh4.
Manifest SHA256:
ac4e0db77dfaa611f10f8b6632b7d27fd2e6f930d9a5fb225002cf126723413a.
Banner: Darwin Kernel Version 22.6.0, Wed Nov 11 03:27:26 CST 2026,
xnu-679496ada27f4d6d8c1ec8bcdf87de1c.

Image: shim/out/shim-p3-kernel-0250-metal-desktop-600-20261111.img in the active
worktree. Its geometry, shim and DTB equal physical239; the complete command
is read back from its actual payload. Managed RAM stays at base0x100000000,
size0x17ff00000 (6,441,402,368 bytes). The five pinned Novatek/ZAP/GMU/SQE/ZAP
code assets retain the physical baseline's identities, raw sizes and reserved
sizes; ADT addresses, alignment, padding, segment extents and kernel_end agree.

The userland package retains seven files totaling 9,125,479 bytes, their
signatures/dependencies and target owner/mode declarations. No new frontend,
GPU core or probe binary is claimed. Three launch/cache files remain templates
outside the root payload and require fresh post240 regeneration. The checker
rejects 24 mismatched contracts, including the old desktop default policy.

## Execution record and independent review

All execution stages below are launched by DSH using the fixed pinned executor;
there is no provider fallback in this run. Outer DSH launch exits do not prove
inner success.

| Stage | PID | Exit | Result |
| --- | ---: | ---: | --- |
| Software v1 | 66217 | 1 | Source extension passes; fixture incorrectly assumes page-aligned file offsets |
| Software v2 | 66558 | 1 | Command and 17 asset checks pass; policy fixture hits unused header helpers under Werror |
| Software v3 | 66863 | 1 | Policy/lifetime pass; clock extractor uses raw-ID239 instead of held241 reference |
| Software v4 | 67099 | 0 | Remaining clock and native framebuffer checks pass, 741 pins, 6.726 s |
| Full kernel | 67634 | 0 | Build and qualification pass, 1,185 pins, 133.513 s |
| Package/image | 4756 | 0 | Complete assets, 24 rejection controls and image pass, 3,262 pins, 1.756 s |

Failed stages and their original logs/receipts are retained. Resume stages run
only unfinished checks. The framebuffer patch does not change across those
fixture/reference corrections. Later schema250/package bindings intentionally
change two earlier software-stage inputs; independent review records those
specific post-stage source changes rather than claiming every historical pin
is still current. Final kernel/package pins remain unchanged.

Codex independently rehashes stage profiles/logs, source entries, native object,
kernel, all packaged files, image and their inputs, and independently compares
the actual command, geometry/shim/DTB and retained board tokens. An initial
review comparison included the independent clone paths; the completed review
compares their entries/digests instead. Private evidence is under
research/tmp/dsh-boot-0250-profile in the active worktree.
review250-v1.json SHA256:
fa1945949be44fc515f91d1d1b29605adaeda30ce10c107438efb1f594636c28.

## Physical acceptance still required

The pending 0240 plan9d943e79 is unchanged and its genuine write reply remains
absent. Its installation and exact paired239 trial must precede later desktop
trials. No other boot may stale that proposal. The 0250 package/image does not
authorize a root write and is not a ready HFS delta.

After that prerequisite, capture the fresh root, regenerate launch templates,
prepare/review a complete desktop delta and obtain its own individual consent.
Then validate root bootstrap/clean handoff, backboardd discovery/native jobs,
icons/widgets/effects, shared output, safe reuse and repeated transitions.
Measure real touch -> HID -> CA commit -> encode -> issue -> complete -> copy
-> panel before prioritizing asynchronous transport and physical high refresh.
Synchronous GPU submission and the global copy lock are unchanged. The full
RAM/storage/peripheral/high-refresh/daily-phone goal remains active.

No device command, root write, boot, CI run or push occurs. The existing
physical baseline, pending proposal, backups and unrelated MAIN mkadt.py edit
are preserved.
