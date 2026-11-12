# Display notification and touch diagnostic: device result

The separately authorized 0300 image booted once, reached SpringBoard and
backboardd, and returned to TWRP after 746 seconds. The user first observed
the lock screen, then confirmed the desktop was reached and **still very
laggy**. The chronological feedback receipt is
`research/tmp/gpu-notify-hid-20261112/user-feedback300.json`, SHA-256
`ab146879b5081cf1123afddfbfe87fb5f9da9c9ca7e9b1cbb4bd750b5e475e63`.
It records no exact time for any screen observation.

The exact authorization was bound to question item
`["request_user_input_async","call_4d4c37f7216c49fbb7e629e22c0b467d",0]`,
install-plan SHA-256
`7f53afce0661307ae6d084b88f69484c193f035df78c70094f607377069ada39`,
trial-plan SHA-256
`9b9470515f404751030ebc5f07c5e80ff75d572ea372f8ec0f4ad5c23cb52491`,
and image SHA-256
`9d4bbee3cb0c0653bb157b6b989c47c9f82382a0ab16f91bc5aea8c742575d49`.
Approval receipt SHA-256 is
`971e0a58ca3ac7c68bcc70d67b6d0f0788f2b339e3b81031d28e0bc21e218701`.
This one-shot authorization is consumed; no retry is allowed under it.

The approved 434,176-byte desktop install, 13-byte misc marker and 434,176-byte
dynamic restore all passed write/readback checks. No rollback or boot retry
occurred. The restored original desktop executable is 428,400 bytes, SHA-256
`0a1b55bb20a29661de40099e58e45ec695ffb0bf78e132a9d10985450e868550`.
The postboot volume header SHA-256 is
`6e272d2e11ae716993301df334c35eeb5498b0a77adbccd965f924e28a5e77e4`.
Four captures checked 116 file records and five directory records per
capture; all three prior log prefixes were retained. The executor and
observer have exited, and `adb get-state` reports recovery. The independent
terminal review rechecked all 72 ready pins and the restoration; SHA-256
`e638aa12bb803bd671c430064cc6242b1fd8d211d2fd0be83d930dd5bb5501c0`.
The execution result SHA-256 is
`443a312ee25e25dbcb21e00ff1b5aa19c90d7b78f0fdd5c16d59ed70c074c23e`.

## What the current-only logs show

Kernel log SHA-256
`22e786c12d9b05ef3edbe8b3d05b18450770bc3733c20dc82da5a18a5bbe21e5`;
backboardd current-only log SHA-256
`e363a18f9c7671e8dff7d78e5593d84d9261e215a647917ac3d2307936341209`.
The 128 sampled notification summaries cover two framebuffer clients. Every
sample has **no port registration, no callback, and zero sends** for types 3
and 5. This confirms that this driver's async notification path was unused
throughout the sampled boot. It does not prove that missing notifications
caused the slow desktop: the locally reviewed HakiOS framebuffer source
explicitly says CoreAnimation can run its own frame clock without requesting
driver refresh notifications.

The physical NVT worker accepted 63,920 packets with zero malformed-frame
rejects in its latest summary. The touch service had one opened HID client.
Power-of-two trace records establish at least **512 changed HID frames**,
including at least 482 frames with a position bit and 67 with a touch/range
edge bit. The largest measured kernel dispatch interval was 4,337 clock
ticks. This proves the driver formed changing touch events and entered its
client callback path. It does not show whether the userland event queue
dropped any, whether backboardd processed them promptly, or the time to a
visible pixel change.

The GPU service completed 51/51 submissions. The software display clock
reached 42,000 callbacks with 613 skipped beats, yet selected only **33 held
frames**. Held-frame counters ended at 36 submitted, one replaced, 33
consumed/retired, two canceled and zero rejected. The latest sampled copy
prefix has 29 successful full-frame copies among 32 attempts, totaling
300,672,000 bytes; three attempts had zero copied bytes. In 58 regular
600-beat intervals, held retirement rose by at most three and was zero in
41. Five such intervals contained 38 contact-mask changes and had at most
three retired frames each. One wider 100-second sampling gap contained 60
contact changes and five retired frames. These are frame ownership and copy
counters, not optical FPS; the user's direct report confirms poor smoothness.

The separate framebuffer `presents` counter reached 300, but it increments
when `fDirty` is true **before** checking whether a held frame can be taken.
After a display-on request with no pending frame, it can count an empty copy
slot repeatedly. It is therefore not a count of distinct submitted, copied
or visible frames. The earlier 0299 report now uses held retirement instead.

The C4 Metal frontend logged 39 bounded command-buffer timeline records:
median GPU time 15.03 ms, maximum 59.25 ms, and 15/39 above a 16.667 ms
budget. Median time from buffer creation to the logged commit point was
12.7 ms, with a maximum 2,346.9 ms. These samples show some per-buffer
stalls and expensive GPU work. The much larger gap is that only 43 command
buffers were recorded across 28 FPS windows in the 600-second service, while
33 held frames reached retirement. Workloads differed from prior trials;
these numbers do not measure physical scanout or prove which stage first
stopped producing frames. Parsed counters are saved in
`research/tmp/gpu-notify-hid-20261112/pipeline300.json` and
`research/tmp/gpu-notify-hid-20261112/held-cadence300.json`.

## Next implementation target

The current framebuffer source publishes none of `TimingElements`,
`ColorElements` or `IOMFBDisplayRefresh`; the locally reviewed HakiOS
implementation publishes a 60 Hz timing/color mode and refresh interval for
CoreAnimation. That is a concrete source-level difference and a candidate
explanation for the sparse desktop frame producer, not yet a device-proven
cause. Prepare a bounded mode/refresh metadata patch, verify its exact
serialization and ARM64 build offline, then compare one separately approved
device boot with the 0300 control. Also count HID queue enqueue/drop and
touch-to-SwapEnd time before claiming touch latency has been fixed. No 60 Hz
or high-refresh success is qualified by the current trial.
