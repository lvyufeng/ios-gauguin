# Inherited display scan timing in XNU, 0258

Patch `0217-gauguin-inherited-scan-timing.patch` adds one diagnostic worker to
the gauguin XNU kernel. It uses the panel route identified from the handset
FDT and can measure the cadence inherited at boot. The switch defaults to
off. A diagnostic boot must explicitly select a stage.

| Selector | Reads |
| --- | --- |
| `sweetscan=1` | GCC display AHB, AXI and DISP_CC XO branches |
| `sweetscan=2` | The same GCC checks, then DISP_CC AHB, MDP, pixel and VSYNC branches |
| `sweetscan=3` | Both clock checks, then INTF1 timing enable, counter enable, frame and line counts |

The board maps only the required 16 KiB pages as read-only device memory
and checks the physical translation at both ends before access. It closes
the mappings after the worker returns. Each scan sample rechecks all clock
branches and requires the timing engine and both counters already enabled.
The probe changes no votes, clock rates, counter settings or display modes.
An enabled branch and a correct translation do not independently establish
safe downstream MMIO. The separately selectable GCC and DISP_CC stages let
the first hardware tests establish access one region at a time. External
abort or fabric-stall recovery is outside this implementation.

The scan worker sleeps 8 ms between observations, with a 1.25-second
window and 160-attempt ceiling. It reads frame/line/frame and discards a
sample when the frame changes during the reads. At least a second of
accepted samples, varying line counts and consistent frame progress across
both halves are required. The result reports frame progress, elapsed
monotonic nanoseconds, estimated millihertz and the matching 60/90/120
nominal rate when applicable. It does not measure when a particular
Core Animation frame reaches the panel. The recovery vblank result of
60.244 Hz is available as a comparison for this handset.

Clock addresses come from the handset FDT and pinned Xiaomi Lagoon GCC,
DISP_CC and SDE sources. The GCC aperture is already used by the gauguin
driver stack. The two downstream regions require separate XNU evidence.
[Xiaomi GCC](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/clk/qcom/gcc-lagoon.c#L1296)
· [SDE counters](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_intf.c#L39)

## Qualification

Source branch `codex/gauguin-scan-timing-20261111` in
`research/tmp/gauguin-build255-worktree-20261111`. Code commit
`25dae0cafe50524e4ee998a0324007fb35dc6630`. Private evidence directory
`research/tmp/dsh-scan-0258` in that tree.

DSH strictly applied 0217 to a clone of the qualified 0254 source. The two
edited integration inputs match the 0255 CI archive byte for byte. The
result contains 5,338 files and changes five paths. DSH ran the actual
sampler with simulated hardware under ASan and UBSan. Sixteen scenarios
passed, including disabled mode, per-stage access guards, closed mappings,
stopped counters, boundary crossing, wrap and unstable cadence. It
compiled the sampler, board worker and BSD init with the existing native
gauguin ARM64 recipe. The new internal references match the definitions
in those objects. The referenced kernel APIs are defined by the 0255
kernel.

The first dispatcher, PID 53382, exited 1 before patching. The verifier
compared a path-bearing snapshot across two different directories. The
corrected verifier compares the file entries. PID 53590 exited 0 in 8.572
seconds with 15 unchanged pins. The second run did not change the patch.
The qualified source SHA256 is
`bfed80f0425e98377d200e7ec57af6d9129d5a0d9fba2deef8fce6d06a71b4c4`.
The independent review receipt SHA256 is
`53a3ee07a011ff0238f7bace24ba95ac6e79b5c6263c450bb03ab712226d3bb4`.

The actual packer accepts three 595-byte command profiles formed by
replacing the 0255 gesture switch with the corresponding scan switch.
Appending a scan switch to that profile exceeds the 607-byte limit.
This milestone has selected ARM64 objects. Full kernel link, image
assembly and phone qualification remain open. The pending 0240 delta and
existing 0250/0255 trial order stay in effect.
