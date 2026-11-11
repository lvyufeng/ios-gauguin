# Recovery DRM configuration checks

`gauguin-drm-timing --test-modes` can ask the recovery driver to validate
the advertised 60/90/120 Hz modes in the active clock family. It uses
temporary mode blobs and the exact flags `TEST_ONLY | ALLOW_MODESET`
(`0x500`). The vendor atomic ioctl directs this flag to
`drm_atomic_check_only`. The mode-change commit path is separate.
[Vendor atomic ioctl](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/gpu/drm/drm_atomic.c#L2529).

The probe first resolves the active route and advertised modes, enables
atomic capability on its own fd, and requests DRM master ownership. It
checks the CRTC's current `MODE_ID` property before forming any test. Each
test blob is destroyed after the ioctl, including a rejected check. The
fd closes on exit. The active route, mode and catalog are checked afterward.
The matching Python `--test-modes` reader reports the per-rate kernel
statuses and rejects incomplete or inconsistent streams.

The real Gauguin run stopped at `SET_MASTER` with `EINVAL` (`-22`). It
executed no mode checks. Recovery still had an open card0 descriptor.
The matching vendor kernel returns `EINVAL` when another master exists,
which explains this observation. The acquisition failure prevents this
path from validating high-refresh modes while recovery owns the display.
[Master acquisition](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/gpu/drm/drm_auth.c#L169).

Both full mode snapshots agree and the measured vblank rate was 60.2446 Hz
before and after. The executable and its tmpfs directory were removed. The
phone remained in TWRP. The attempted check adds an observed ownership
constraint to the existing timing catalog. Hardware mode switching and XNU
scanout acceptance still need their own trials.

The static ARM64 executable is 13,312 bytes, with no undefined symbols.
Its request flags also appear as `0x500` in native disassembly. Host
ASan/UBSan checks exercise the actual request constructor, argument pointers,
create failure, rejected check and blob-release failure. Seven malformed
test logs are rejected. The first host fixture omitted Darwin header types
and was corrected before hardware execution.

Private evidence is in `research/tmp/dsh-drm-test-0273`. DSH 91517 passed
the host checks in 1.024 seconds with 16 pins. Physical dispatcher 91679
finished with exit 1 after acquiring the observations and completing
cleanup because its initial error classification expected different master
failure codes. A separate review of that retained run, dispatcher 91897,
passed in 7.159 seconds with 26 pins. It verified the unavailable state,
mode and vblank observations, cleanup and recovery's open descriptor. The
physical test was attempted once. The result remains unavailable.

Executable SHA256
`c8d3b0dc7bac6ae78ffec619317f8f05623eee53a4c48f52d06bb300199afcbf`.
Review SHA256
`9be28e93cee85d2117e55957b97d1245283fc20b621c59c4f4367427db52a928`.
The existing 0240 and 0261 physical trials still await their individual
write confirmations. Their proposals and authorized scope are separate
from this recovery test.
