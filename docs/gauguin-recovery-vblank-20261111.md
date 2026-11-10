# Gauguin recovery vblank measurement, 0257

TWRP reports the active DSI mode as 1080×2400 at 60 Hz, with mode totals
1182×4910 and a reported DRM clock of 136659 kHz. The completed run gathered
25 fresh monotonic timestamp samples over 1.045739427 seconds of vblank
progress. The sequence advanced by 63, giving 60.244453 Hz. Per-interval
periods ranged from 16.598247 to 16.600026 ms, with median 16.599080 ms.
The DSI connector, encoder, CRTC and mode matched before and after sampling.
This is the recovery driver cadence for the mode active during the run.
The corresponding iOS handoff and optical panel output still need measurement.

## Probe

`tools/gauguin-drm-timing.c` opens card0 read-only, resolves the connected
DSI-1 route, and samples the CRTC sequence via the pinned vendor DRM UAPI.
A compatibility path uses a legacy vblank query and at most one synchronous
wait for a first timestamp. The kernel can briefly enable the vblank IRQ
to serve these ioctls. The probe contains no modeset, page flip or MMIO
operation. The vendor video encoder hooks its vblank callback to the
interface VSYNC IRQ.
[Xiaomi DRM vblank implementation](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/gpu/drm/drm_vblank.c#L1801)
· [SDE VSYNC hookup](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_encoder_phys_vid.c#L1328)

The freestanding static ARM64 Linux executable builds with Clang/lld and
the vendor DRM UAPI plus a minimal Linux type header. The private DSH
runner records the exact build and verifies the ELF, then revalidates
gauguin recovery and the executable `/tmp` tmpfs. It uploads into a unique
directory there, verifies the remote hash, runs under a five-second device
timeout and removes the probe and directory. No persistent storage files
are involved. `tools/gauguin-drm-timing.py` validates the saved log on the Mac.
It rejects stale or partial streams, counter resets, and unstable cadence.

The first attempt exited with an unavailable vblank result after reading the
60 Hz CRTC mode. The second collected 25 samples, and the parser rejected the
first timestamp, which was 67.78 seconds old. The remaining samples were
consistent with approximately 60.244 Hz. The final probe performs a warmup
query and waits a sample interval before gathering 25 observations.
The original timestamp freshness and cadence checks passed on that run.

## Display clock evidence for XNU

The captured handset FDT maps the Lagoon display clock controller at
`0x0af00000` with length `0x20000`. The clock phandles and bindings identify
its MDSS AHB, core MDP, and VSYNC branches. The matching vendor source
defines branch offsets 0x104c (AHB), 0x1010 (MDP), 0x100c (DSI pixel) and
0x1028 (VSYNC). Branch2 checks bit 31 for the clock-off indication. These
are candidates for a read-only hardware preflight, once the clock controller
itself is known to be accessible at XNU handoff. The TWRP debugfs clock
summary was absent, so clock state across the boot remains an open question.
[Clock controller](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/clk/qcom/dispcc-lagoon.c)
· [Clock status semantics](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/clk/qcom/clk-branch.c#L47)

## Execution evidence

DSH dispatchers 50604 (preflight), 51217, 51529 and 51759 exited 0, 1, 1
and 0, respectively. Probe process exits for the three measurement stages
were 1, 0 and 0. All three temporary directories were removed. Codex
independently checked the sample span, hashes and the 13 final unchanged
inputs. Private outputs are in `research/tmp/dsh-display-0257`.
Final binary SHA256
`ead344418577df6f67ca01aee7672ead9c51c16ae40c1d45cf420bcb11f6430f`.
Final raw observation SHA256
`288736b6cc109977a40fd21259b24c4e3293f3adf73f6f3e0d87b25fd233941c`.

Next, qualify access to the inherited display clock and read the XNU
frame/line counters under a bounded, opt-in profile. Use the recovery
cadence for comparison and measure the mode actually handed to iOS.
Physical 90/120 Hz still needs modeset and presentation qualification.
The pending 0240 consent, paired 0239 trial and desktop test order remain
as recorded in the handoff.
