# Gauguin refresh-rate A/B probe

The 20H392 audit identified separate CoreAnimation heartbeat and application
opt-in controls. This probe measures the app's response to each requested
rate and puts the callback sequence on the screen for independent capture.
[20H392 audit](gauguin-20h392-refresh-policy-20261111.md).

## Build and use

```sh
python3 tools/build-refresh-probe.py --out /tmp/gauguin-refresh-build
```

The builder compiles once for ARM64 iOS 16 and produces two ad-hoc signed
`GauguinRefresh.app` bundles, in `control` and `opt-in`. Both use the same
bundle ID and version for sequential A/B testing. The only Info.plist
difference is `CADisableMinimumFrameDurationOnPhone=true` in the opt-in.
The app uses public UIKit and QuartzCore APIs. Installation and launch on
the port still need device qualification.

For a qualified physical mode, select the same 60, 90 or 120 Hz request in
each build. After a one-second warmup, the app samples for five seconds. It
reports the screen maximum, callback rate and intervals, the median target
interval, late callbacks at entry, invalid targets, Mach ticks and the sampled
frame ID range. The begin log records power mode, thermal state and timebase.
The requested rate is a hint. An interrupted or capacity-limited run is
labeled in the result. [Apple display-link requirements](https://developer.apple.com/documentation/quartzcore/optimizing-iphone-and-ipad-apps-to-support-promotion-displays).

## Observe the displayed frames

The strip contains a white and black reference cell followed by 12 Gray-code
bits, least significant first. Each bit is paired with its complement. A
single callback advances the marker by one ID and updates two cells in one
transaction. Use a fixed crop and one continuous camera take per test. For
90/120 Hz, use a camera with a verified acquisition cadence above the panel
rate, preferably 240 fps or faster, and an exposure that resolves transitions.
Use original frame times at the acquisition speed. Slow-motion playback or
export can retime them.

Crop the strip's full interior width and a few interior rows. Use the camera
image coordinates for `W`, `H`, `X` and `Y`. The first and last IDs come from
the app's result. Commands below use FFmpeg and FFprobe with the same stream.

```sh
ffmpeg -i recording.mov -map 0:v:0 \
  -vf 'crop=W:H:X:Y,scale=26:1:flags=area,format=gray' \
  -fps_mode passthrough -f rawvideo marker.gray
ffprobe -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time \
  -of default=noprint_wrappers=1:nokey=1 recording.mov > camera-pts.txt
python3 tools/gauguin-refresh-optical.py marker.gray camera-pts.txt \
  --first-id FIRST --last-id LAST
```

The decoder reports observed advances, unobserved IDs, camera duplicates,
undecodable samples and the longest camera gap. Camera duplicates include
oversampling and time spent filming a held marker. An unobserved ID can come
from either presentation or camera sampling. Use the same boot's compositor
and scanout-latch data to attribute losses. The marker samples one part of
the display. Full-frame correctness and gesture latency use the separate
desktop tests.

## Qualification

The two ARM64 iOS bundles compiled, signed and passed strict verification.
The common binary was copied before signing. Independent inspection checked
identical executable text, the exact one-key plist difference, and 72 imports
resolved against the actual 20H392 shared cache. Host checks cover all 4,096
marker words, bad contrast/complements, repeated and missing IDs, malformed
timestamps and sequence regression.

On the iOS 26.5 simulator, a private smoke variant selected 90 Hz using the
same request method as the buttons. It reported 60 Hz maximum, 300 callbacks
at 60.0/s and IDs 60–359. Decoding the final screenshot returned ID 359. The
temporary simulator app was removed. A synthetic 240 fps video preserved
60 marker IDs and decoded to 119.919 observed advances/s through the complete
FFmpeg/FFprobe workflow. Handset measurements remain pending.

Private receipts and the native bundles are in
`research/tmp/dsh-refresh-probe-0271/native-v3`. Physical testing follows the
correct-desktop baseline and hardware mode qualification.
