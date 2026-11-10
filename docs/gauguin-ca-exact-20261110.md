# Exact CoreAnimation offscreen bring-up

The GPU can already execute the project's Metal shaders and return checked
pixels. That does not establish that CoreAnimation draws icons, widgets or its
effects correctly. The next gate runs the actual system `CARenderer` against an
explicit A619 texture and queue, before changing desktop device discovery.

`prepare-hakios-metal-ca.py --profile gauguin-ca-exact` applies the diagnostic
profile and a second patch to the pinned MIT HakiOS frontend. It removes EDR and
luma function substitutions, nearest variant matching, and the omitted luma draw.
Exact precompiled variants remain available from the image's own pipeline
library; otherwise the function's own AIR and specialization constants must
compile successfully. A requested debug draw omission fails the command buffer.
The earlier `gauguin-diagnostic` profile still selects only its original patch.

The root-only `--metal230` probe requires the exact profile, actual 20H392
CARenderer method encodings, and the image's original full default Metal library
hash. It supplies its own texture and command queue. There are five 64×64 scenes:

- Opaque gray bands, including midtones.
- A decoded, owned BGRA image with nearest filtering.
- A premultiplied half-alpha image over black.
- The image clipped by a layer mask.
- Changed image contents on the same layers and renderer, after the masked frame.

All 20,480 pixels are compared with a CPU oracle in linear sRGB. Opaque/image
channels allow one code point of rounding; half-alpha allows two. Every scene
must encode an actual driver draw. Queue-ordered GPU readback waits for CA work;
the ten explicit poison/readback jobs do not count as the CA draws. The existing
128 MiB fatal process limits, sole GPU owner and finite deadline remain in force.
Mode2 still follows the qualified SETEXEC handoff to the retained GLES probe.

The scene oracle has passed on a Mac Apple GPU with zero pixel error. The
derived host fixture explicitly omits iOS admission, image pins and driver
counters. This validates the chosen oracle; it is not an A619 or iOS result.
Native compile/link and actual-image import resolution likewise are software
checks, not physical rendering evidence.

After physical offscreen scenes pass, the remaining work includes CA effects,
MRT/framebuffer fetch and graphics image stores, compositor ownership and Metal
publication, then desktop pixel correctness and latency. Full safe RAM, storage,
phone peripherals, power management, 90/120 Hz and daily use still require their
own physical acceptance. A new userdata delta needs fresh backup, minimal block
audit, filesystem/writer checks and separate user authorization.
