# Gauguin dynamic-refresh timing catalog

The recovery query now captures every complete advertised timing and the
active CRTC timing. Two snapshots 43 ms apart agreed on the route, active
mode and all 12 advertised modes. The phone was in Gauguin TWRP. A separate
vblank sample again measured 60.2444 Hz on the active nominal 60 Hz mode.
The uploaded static probe ran from `/tmp` tmpfs and was removed afterward.

## Mode construction

The handset selects the J17 36-02-0A video-mode DSC panel. Its base timing
is 1080×2400 at nominal 120 Hz with horizontal front/sync/back porches
50/12/40 and vertical porches 33/2/30. The four-lane link has two declared
lane bit clocks, 819,957,600 and 835,930,800 Hz. The source format uses
24 bits/pixel. DSC uses 8 bits/pixel in two 540-pixel slices, giving
360 transport pixel clocks per active line.

The vendor constructs each mode in three steps. First it computes VFP for
each DFPS rate. It then expands the two bit-clock families and adjusts HFP
to preserve the requested rate. Finally it applies Xiaomi's per-mode porch
reductions. These reductions trim VFP by 20 lines on the first family's
120 and 60 Hz modes and HFP by four clocks on the second family's 120 and
60 Hz modes. [DFPS calculation](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/dsi/dsi_display.c#L4443),
[clock adjustment and mode generation](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/dsi/dsi_display.c#L6086),
[DSC timing macros](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/dsi/dsi_defs.h#L17).

`tools/gauguin-display-profile.py --refresh-catalog CAPTURE.dtb` computes
those stages from the captured tree. All horizontal/vertical porches and
totals match the 12 real DRM mode records. The six entries for 60/90/120 Hz are
shown below. The estimated scan rate uses the declared link clock and DSC
transport total. The higher-refresh modes still need a physical scan test.

| Nominal Hz | DRM clock kHz | HFP | VFP | Logical H total | V total | Modeled transport Hz |
| --- | --- | --- | --- | --- | --- | --- |
| 60 | 136659 | 50 | 2478 | 1182 | 4910 | 60.2444 |
| 90 | 136659 | 50 | 854 | 1182 | 3286 | 90.0183 |
| 120 | 136659 | 50 | 13 | 1182 | 2445 | 120.9816 |
| 60 | 139321 | 55 | 2498 | 1187 | 4930 | 60.5139 |
| 90 | 139321 | 59 | 854 | 1191 | 3286 | 90.0183 |
| 120 | 139321 | 55 | 33 | 1187 | 2465 | 121.0278 |

The active recovery mode is the first row. Its modeled 60.244399 Hz agrees
with measured vblank within 0.001 Hz. Computing a scan rate from the logical
1080-pixel horizontal total and the reported compressed clock gives the wrong
result for this panel. The DSC transport total is 462 clocks in the active
mode.

## Tools and qualification

`tools/gauguin-drm-timing --modes` prints the stable active and advertised
timings. `python3 tools/gauguin-drm-timing.py --modes LOG` validates the
stream and reports full geometry plus an exact active-mode match when one
exists. The probe uses read-only mode queries with nonzero GETCONNECTOR
capacity. Its existing vblank and plane entry points passed in the same
recovery run. The profile tool's original CLI output also matches its prior
version when the new flag is absent.

DSH 88112 exited zero with 12 pinned inputs in 2.532 seconds. It built and
ran the 11,040-byte static ARM64 probe, captured all three query modes, and
confirmed tmpfs cleanup. DSH 89751 exited zero with 13 pins in 1.258 seconds
for the model comparison, ten malformed-log rejections, eight unsupported
profile rejections and six runs of the actual vendor front-porch function
under ASan/UBSan. The first host attempt stopped at the vendor's unsigned
`abs` warning under Werror. The second keeps that warning visible while
executing the original function on supported inputs. The captured source
matches its pinned Git blob. Codex independently verified receipts, all
current input/log hashes, raw records and the active timing calculation.
The final 90427 stage also checks DSC packet grouping, rejects a ninth
unsupported profile, and passes with 14 pins in 1.456 seconds. Its model
output matches the earlier catalog exactly.

Private evidence is in `research/tmp/dsh-display-modes-0272`.
Probe SHA256 `3f3477cf5b1b019b67fe8775268808a73d9dda8b7f9bebb67e2cccfd20f698c5`.
Mode-log SHA256 `722b541417410fe436ad6e86623df69436446d3ffadcd3ac794f0b84df245f34`.

## XNU handoff and switching

First qualify the inherited XNU display access, scan route and latch through
the prepared 0261/0263 sequence. Compare the inherited hardware state with
the recovery timing family. An initial mode-switch candidate can then target
the same clock family, with full absolute timing tuples and a saved-state
restore path. The first family preserves HFP 50 across 60/90/120 Hz.
Programming requires coordinated DSI and SDE timing updates, DSC preservation,
latch verification and bounded recovery. The catalog supplies concrete
targets. XNU mode switching, resulting panel cadence, optical output and
application cadence remain open. The paired 0239/0240 and correct 60 Hz
desktop acceptance retain their recorded order.
