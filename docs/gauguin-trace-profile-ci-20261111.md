# Trace boot profile and complete-kernel CI, 0255

The 0254 kernel trace has selected-TU qualification. This follow-up makes its
boot profile fit the real payload ABI. CI built the complete ARM64 kernel,
and DSH assembled and checked a temporary image offline. It has not run
on the phone.

Active branch `codex/gauguin-trace-build-20261111`, worktree
`research/tmp/gauguin-build255-worktree-20261111`, parent `8437753`.
Profile/test/CI-lane source `427f8f93f215bbf53c5c7ab80d23474da1eb5036`;
runner correction and current pushed build commit
`d6d9ed4f9b57fe4a9330a64cd42686da6ac3010a`.

## A complete 596-byte command

The accepted 0250 command already occupies 607 UTF-8 bytes. Appending
` sweettrace=2` creates 620 bytes and is rejected by the actual packer.
`tools/prepare-ui-trace-profile.py` instead replaces the existing
`sweettrial=gwrt-0175-a1` metadata slot with `sweettrace=2`. The result is
596 bytes, or 597 for a two-digit selector. Every other token and its order
remain byte-identical, including all board, GPU, UFS and health options.

The former trial key has no direct literal consumer in the exact qualified
208-patch XNU tree. The profile tool verifies that full source snapshot, the
actual 0250 image, and all nine 0254 native objects/inputs before creating
its JSON plan. A source consumer in a later revision makes this replacement
fail. Separate inspection also finds no direct key in the retained shim,
graphics/userland sources or the five qualified desktop binaries. This is a
revision-specific replacement, not a general rule for dropping boot keys.

The real payload builder tests all sixteen selectors, the 608-byte field's
complete NUL padding, unchanged segment table and identical bytes outside
the command field. Invalid selector types/ranges, wrong desktop modes,
duplicate keys, noncanonical spacing and embedded NUL are refused. The test
with the oversized append uses the real packer's failure before opening its
nonexistent input files.

The produced plan remains `reviewed-trace-command-not-kernel-or-image`.
The final image below supersedes this command-only receipt. It preserves
the pending 0240 / exact paired0239 prerequisite and the existing 0250
desktop-correctness-first acceptance. It performs no device access.

## Focused clean-tree CI lane

`tools/run-ui-kernel-checks.py` supplies a reproducible staged-source lane:
actual trace core/board/reader, real command ABI, actual HID methods, NVT
coordinator/protocol/SHA, and GPU ownership plus positive trace hooks. It
records input hashes, actual subprocess exits and logs. These five groups
pass locally through DSH; this is a focused regression suite, not every
repository test or a hardware result.

The existing workflow gains a manual `host_checks=ui-trace` choice restricted
to gauguin. Its default and push-trigger behavior still use `all`. The focused
lane runs before the existing complete build with strict patch replay and
fresh build identity. Its logs/receipt are retained with the CI artifacts.
Workflow YAML and all eight shell blocks pass syntax validation.

## Runner failure and correction

DSH pushed source and dispatched
[run42905900210](https://github.com/lvyufeng/ios-gauguin/actions/runs/42905900210).
It was cancelled before any step, runner ID0; its job annotation states:
`The configuration 'macos-14-arm64-us-default' is not supported`.

The official runner support table states that GitHub Actions retired macOS14
on 2026-11-02 and lists macos-15 as an Arm64 runner. See the
[support table](https://github.com/actions/runner-images/blob/main/README.md)
and [retirement announcement](https://github.com/actions/runner-images/issues/15226).
Fetched README Git blob: `cbb0ec6433933cd83d6c749bffbb24a2513388be`.

The workflow now uses macos-15. This change affects the runner environment;
the pinned13.5 dependency profile, DEVELOPMENT/ARM64/gauguin target and kernel
patch series remain unchanged. Existing code/profile test pins remain valid;
the changed workflow is re-parsed and its shell blocks rechecked before push.

DSH pushed the correction and dispatched
[run42906506786](https://github.com/lvyufeng/ios-gauguin/actions/runs/42906506786),
exact head `d6d9ed4f9b57fe4a9330a64cd42686da6ac3010a`, job130145768388.
The combined prepare/test/build step ran 21:43:18–21:50:07 UTC on
2026-11-10, and the job completed successfully at 21:50:29 UTC. The final
watch was reaped with exit 0. Runner macOS 15 ARM64, Xcode 16.0,
Apple clang 16.0.0 (clang-1600.0.26.3). All five CI host groups passed.
The native manifest records make exit 0 and the unique build identity
`xnu-621f0290565c4274adcb241babfae972`.

## Local execution and review

DSH local-stage-v1 PID39972: exit0, 6,331 pins, 9.662s. Five host groups,
actual proof-bound 596-byte profile, YAML and shell syntax passed.
CI-stage-v1 PID40361: exit0, 6,335 pins, 29.802s; successful push/dispatch,
followed by GitHub's unsupported-runner cancellation, not a compiler result.
CI-stage-v2 PID41252: exit0, 6,337 pins, 13.428s; retained code-test pins,
workflow revalidation, fast-forward push and one corrected dispatch.
All DSH dispatchers, outer launchers and the CI watcher are terminal.
No provider fallback was used.

Codex independently checks the current focused test inputs/logs, profile
inputs, remote branch head, selected run head, and preserved anchors. Earlier
stage pins intentionally changed only for the runner YAML and expected-head
file after those stages had finished; the review records that distinction.
The final CI-stage-v2 pins were current before this handoff documentation.

Private evidence W255: `research/tmp/dsh-build-0255-trace` in the active tree.
Profile receipt SHA256:
`08f6dc425904e48ac3ebea8358814dae01767fc65803974e22de50c7fbbd9fbc`.
Focused host result SHA256:
`a28c98e96be3c6da8d84b94901ce272e1224ef67518aa4b936c9d33e02ed2992`.
Independent `review255-v1.json` SHA256:
`06a550bccdbfa4ee70d8e09a83318fc6dcc2538e5bf133fa31fe87e3c2f78977`.

## Completed artifacts and readback

DSH fetched 92 files (101,803,135 bytes), retaining more than 2 GiB free.
The complete kernel is 17,866,344 bytes, SHA256
`07dd709e916a986914d7f8ff4a3211ac76e05404e1f96a798bbfc2d0d7f4e1d5`.
The archived postbuild source matches the captured build source (5,335 files,
208 patches, SHA256
`31966c8cd2ada7d9f700ede6f9043be9b5aed117dcd23aa390398dcdb81b6558`).
Relative to local 0254, four dxb adaptations change build tool paths, includes
and linkage; driver bytes match. The differing toolchains preclude a strict
timing A/B against the locally built 0250. External SDK/archive metadata was
recorded in CI; their bytes were not independently reread here.

`kernel-qualification-v2.json` checks the native build identity, zero
undefined symbols, 269 retained definitions in the same sections as 0250,
13 new trace text definitions and the retained physical-cache address path.
The first verifier rejected a retained data constant as non-text; v2 compared
the actual baseline sections with no compiler or artifact change.
DSH fetch/qualification-v1/qualification-v2/package ran respectively in
50.107/1.310/1.659/0.649 seconds with exits 0/1/0/0.

Image: `shim/out/shim-p3-kernel-0255-ui-trace2-600-20261111.img` in R255,
19,939,328 bytes, SHA256
`8baab14d0fcf5e3cfb7f349a2b42f806e2f441fa88aea124d2d1c0bf7573ce88`.
Independent raw readback matches all ten Mach-O segments byte for byte,
five firmware assets and their zero padding, Android v2 header geometry,
shim and DTB against 0239/0250, the full 596-byte command plus 12 NULs, the
2 MiB PAS zero tail, and unchanged default-off handoff capture. It rehashes
19 package inputs and verifies the 0240 plan and 0239/0250 anchors.
`review255-v2.json` SHA256
`5a28a640fd06a58b2c4a552b0549f024a25b62d866605537c93f56c4f6901616`.

## Next action

Physical baseline remains kernel 0239 / root 0237. Genuine 0240 consent
is still pending. With that consent, apply its exact 9d943e79 delta using
fresh preconditions and run its exact paired 0239 image first. Obtain a
fresh root capture, regenerate the scoped desktop installation and launch
cache, and obtain individual consent for that write. Run existing 0250
to qualify the whole desktop before 0255 real-gesture tracing. No device
command, root write or boot was performed by this milestone.

0255 captures kernel touch, GPU and display-copy spans. It cannot measure
the CA pre-commit wait, physical panel latch or causal touch-to-photon time.
It is an offline diagnostic image; no speedup or higher refresh is claimed.
Safe RAM, storage, peripheral and daily-phone milestones remain active.
