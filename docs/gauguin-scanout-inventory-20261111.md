# Gauguin scanout inventory, 0262

The TWRP DRM query returned one active primary plane on the connected
DSI-1 route in both snapshots. Connector 29, encoder 28 and CRTC 103
agreed before and after the 43 ms sampling interval. Plane 57 and the
CRTC both reported framebuffer object 176. The active mode remained
1080×2400 at nominal 60 Hz. A separate timing run took 25 observations,
with 62 vblank advances over 1.029139323 seconds, giving 60.2445 Hz.
The DRM IDs identify objects in that recovery session. The active XNU
pipe, control path, fetch address and actual latch time remain unknown.

The compiled `gauguin-drm-timing --planes` probe opens the DRM device
read-only and uses a file-local universal-plane capability to enumerate the primary plane.
It checks the immutable plane type and compares two snapshots of the
connector, encoder, mode, CRTC, framebuffer and active planes. It issues
no modeset, flip, property update or MMIO access. The original no-argument
vblank mode also ran successfully. The matching Python reader rejects
partial, duplicate and inconsistent plane records.

## Hardware register candidates

`tools/gauguin-display-profile.py --scanout-catalog` reads the captured
Gauguin DTB. The device describes four source pipes and four control
paths. All candidate registers fit their declared, nonoverlapping
ranges within the MDP aperture. The selected DSI path uses INTF1, which
corresponds to mask `0x2` in Lagoon's `CTL_INTF_ACTIVE`. That register
can help resolve the active control path after display access is qualified.
The source address, stride, size, format and operation mode are needed to
associate a pipe with the inherited framebuffer.
[Xiaomi catalog](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_catalog.c#L1511),
[source pipe registers](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_sspp.c#L19),
[control path registers](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_hw_ctl.c#L14).

| Register | Physical address candidates |
| --- | --- |
| `SSPP_SRC0_ADDR` | `0x0ae05014`, `0x0ae25014`, `0x0ae27014`, `0x0ae29014` |
| `CTL_INTF_ACTIVE` | `0x0ae020f4`, `0x0ae022f4`, `0x0ae024f4`, `0x0ae026f4` |

The recovery FDT declares a 35 MiB continuous splash reservation starting
at `0xa0000000`. The exact 0255 embedded boot DTB describes its first
`0x9e3400` bytes as the inherited 1080×2400 framebuffer. Another
16 KiB-aligned frame would fit geometrically at `0xa09e4000` in an
`0x9e4000`-byte mapping. This is a size-and-alignment calculation. The
runtime handoff, actual fetch address and address translation, exclusive
ownership and DMA/cache visibility must be verified before mapping or
writing the candidate range.

## Verification and next step

DSH dispatcher 65438 ran the catalog and recovery jobs in 2.370 s with
18 pinned inputs. The AArch64 executable was static, uploaded to an
executable TWRP `/tmp` tmpfs and verified by SHA256. The temporary
executable and directory were removed. Dispatcher 66193 ran the updated
offline inventory in 2.009 s with 19 pinned inputs. It verified the exact
embedded boot DTB, rejected six malformed catalog cases, checked the
exact-fit and short splash cases, and rejected five malformed plane logs.
Both DSH launchers exited 0. The recovery probe and reader were identical
between the two stages. Evidence is under `research/tmp/dsh-display-0262`.

Plane log SHA256 `8ac2b52f347d75ca2c1e63c2026323a4b908882b38d81c7eb31767abd2c8774b`.
Catalog with boot data SHA256 `5104e56f9630893c1de8eed2ad25964e528898c817bee37b439e34439da72e22`.

Next qualify the existing XNU clock and INTF access. Then take bounded,
read-only samples of the source pipes and control paths, require a stable
and unique route, and correlate it with the live handoff framebuffer.
A hardware flip needs its own latch, buffer ownership and failure
qualification. This milestone performed no reboot, display mode change,
partition write or XNU build. The existing desktop and scan receipts remain
separate from the TWRP observation.
