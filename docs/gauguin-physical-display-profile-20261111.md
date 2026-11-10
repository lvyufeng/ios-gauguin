# Gauguin panel and display interface, 0256

The connected phone's TWRP kernel exposed 12 modes for the built-in DSI
connector. Each is 1080×2400 video mode. The rates are 30, 48, 50, 60, 90
and 120 Hz, each with two reported DRM clock values, 136659 and 139321 kHz.
The capture read connector status and modes. Both debugfs state and vblank
files were missing, as indicated by the command bodies despite a successful
ADB transport exit. The current physical scan frequency remains unmeasured.

The earlier FDT captured from this handset selects the J17 36-02-0A panel.
The boot selector agrees with the primary panel phandle. DSI controller 0
and PHY 0 also agree with the primary display phandles. Its single base timing
is 1080×2400 at 120 Hz with DSC. It declares the same six rates as recovery,
with dynamic refresh via the vertical front porch. The base timing and the
DRM mode list do not identify the mode inherited by XNU. The stock driver
calculates its front porch from the current and requested modes.
[Xiaomi DSI driver](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/dsi/dsi_display.c#L4440)

The 0255 image's Android v2 DTB matches the retained boot DTB byte for byte.
It describes an inherited 1080×2400 framebuffer, stride 4320, and has its
display subsystem disabled. The payload sets the framebuffer software target
to 60 Hz. The panel mode still depends on the display configuration at
handoff.

## Register evidence for an iOS scan timing probe

The recovery FDT locates `mdp_phys` at `0x0ae00000` with length
`0x84208`. The Xiaomi driver maps that named region. The SDE catalog
assigns interface indices in property order and DSI controller IDs within
the DSI entries. The DSI 0 interface is therefore INTF1 at offset `0x6b800`,
length `0x2c0`. The vendor register definitions place frame count at
`0x0ae6b8ac` and line count at `0x0ae6b8b0`. The status path depends on
interface features. These addresses are derived from the handset's DT and
source. Their accessibility and values in XNU remain untested.
[SDE mapping](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_kms.c#L3416)
· [Interface catalog](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_catalog.c#L1966)
· [Counter definitions](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_intf.c#L39)

The first iOS measurement needs evidence that the display domain is accessible
and that inherited counters are running. Take a bounded series of CPU-clock
timestamps and paired frame/line counts. Reject a sample that crosses a frame
boundary during the reads. Require several consistent periods and report
stopped counters or unstable timing as unavailable. Add physical observation
before treating frame delivery and tearing as qualified. Panel programming,
scanout ownership, modeset and rollback are separate implementation work.

## Reproduction and verification

`tools/gauguin-display-profile.py` parses a captured recovery DTB with
`fdtget`. Optional boot DTB and recovery connector files add comparisons
with the inherited framebuffer and the advertised modes. It prints a JSON
profile and does not access the phone or registers. It requires agreement
among the selected panel, controller and PHY and validates the counter
offsets against the DT region. Raw capture files stay private.

DSH performed the capture and qualifications in
`research/tmp/dsh-display-0256`. Dispatcher 48913 exited 0. Codex verified
all four downloaded vendor source blob IDs against GitHub at pinned commit
`e601e14af391539e0fd67fe0506bcbe55bfcd997`.
Qualification v1 failed on the timing property's prefix. V2 stopped before
execution because the private output directory already existed. V3 used a
fresh output and passed the handset DTB, 0255 embedded DTB and all 12 modes.
It rejected an inconsistent panel phandle, an undeclared rate and a disconnected
connector. V3 dispatcher 49750 exited 0 with 20 unchanged pins. Profile SHA256
`502715bf2c5ab08339cb05eee149bc1b29ddd554d6ee9e87898c76c0bb03d1fc`.

The 0250 desktop and 0255 trace trials remain behind the pending 0240
installation and paired 0239 trial. This milestone collected read-only
recovery evidence, with no device write, reboot, modeset or MMIO access.
The pre-commit SpringBoard boundary still requires separate instrumentation.
