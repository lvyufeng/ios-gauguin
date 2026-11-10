# Inherited scanout route in XNU, 0263

The Gauguin XNU route diagnostic extends the inherited display sampler
with `sweetscan=4`. It runs after the existing GCC, DISP_CC and INTF1
checks and a successful one-second scan cadence measurement. Other scan
selectors still stop at their existing stages. The diagnostic is off
unless selected in the boot arguments.

The worker first validates the live PE console geometry and that its
page-aligned framebuffer address and full extent fit below 4 GiB. Then it
maps four 16 KiB pages for the CTL, VIG0, DMA0/DMA1 and DMA2 registers as
read-only device memory and verifies both ends of each translation. It
rechecks display clocks and INTF1 timing before each register sample.
It takes three identical snapshots on different scan frames, dropping
samples that cross a frame boundary. The route stage is bounded to 16
attempts and checks a 150 ms deadline. It releases each mapping before
publishing the result. A translation check cannot rule out an external
abort or an MMIO fabric stall. The staged GCC, DISP_CC and INTF1 trials
still need physical qualification.

The route match requires one source address equal to the inherited
framebuffer address, one CTL for INTF1, and that same source assigned to
one of its two layer mixers with no other catalog pipe or second rectangle
staged. The pipe must show the expected size and stride, linear packed
four-byte pixels and unrotated source coordinates. The CTL must report
video mode and no pending flush. This establishes matching programmed
state when measured on the phone. It provides no hardware latch event
or permission to write a new scanout address.
[Xiaomi CTL layer fields](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_ctl.c#L145),
[Xiaomi SSPP layout](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_sspp.c#L333),
[Gauguin inventory](gauguin-scanout-inventory-20261111.md).

The pre-mount writer emits a `GAUGUIN_SCAN2` receipt for mode 4 and
preserves the `GAUGUIN_SCAN1` representation for modes 1–3. The new
reader accepts one saved 4 KiB mode-4 block and its exact run ID. It
checks record shape, padding, cadence and the unique route association.
The writer is behind the explicit `sweetscanlog=1` pre-mount diagnostic.
Any physical run of that diagnostic must use its own confirmed write
scope and fresh device preflight.

## Verification

Source commit `7a58414f485d0745957505d4c88e949befeabda2` in branch
`codex/gauguin-scanout-route-20261111`. Reader commit `d00baab`.
The worktree is `research/tmp/gauguin-build255-worktree-20261111`, with
evidence under its `research/tmp/dsh-scanroute-0263`.

- DSH PID 68163 replayed patch 0219 without fuzz or offset. The 5,339-file
  source snapshot changes exactly five files. Six host groups and three
  native ARM64 translation units passed. The actual sampler passed 16
  cadence and 17 route cases, including multiple sources, mismatched
  layers, clock loss and partial mapping cleanup.
- DSH PID 69012 parsed a block emitted by the actual writer against the
  mock UFS controller. It rejected eight stale or corrupted variants.
- DSH PID 69413 prepared two offline pre-mount images from the qualified
  0261 kernel for DISP_CC and INTF1. Independent byte comparison confirms
  that only the selector digit and diagnostic run ID digit differ from
  the reviewed GCC image.
- DSH PID 68484 passed all 11 local host groups, pushed the exact source
  commit and dispatched the full kernel build. [GitHub Actions run 42925740306](https://github.com/lvyufeng/ios-gauguin/actions/runs/42925740306).

Native source snapshot SHA256
`5c29e6c442eb1bcec973b3e8573a4ad0a9047a65fbb07f90fd8f12db4dcfe01f`.
Patch SHA256
`c1a97ce3938e97f2e3646cf257e5cad8ed8649b937851335202f54ad39211793`.

| Offline image | SHA256 |
| --- | --- |
| `gauguin-0261-scan2-premount-261002.img` | `cecc1804c50dccbc7acb3a421da1170890f99e29e97a95138ff9fe160bb8493c` |
| `gauguin-0261-scan3-premount-261003.img` | `47938bd4f92e4c5a5cd7812309f18ad897f1dba667f438d799e1b70c745b6fb9` |

This turn performed no phone command, boot or partition write. The next
physical step remains the existing 0261 GCC trial after its exact
approval. Later hardware validation must prove the active route and
exclusive second-buffer ownership before testing a latch or modeset.
