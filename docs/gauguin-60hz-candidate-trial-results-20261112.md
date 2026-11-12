# 60 Hz submit-guard candidate: one-shot device result

The authorized candidate boot reached SpringBoard and backboardd, ran the
owned C4 GPU frontend, and returned to TWRP. The user directly reported during
this boot: **“还是很卡顿 触摸操作不跟手”**. This candidate has not established smooth
60 Hz or responsive touch. The feedback receipt is
`research/tmp/gpu-poll-guard-20261112/user-feedback299.json` (SHA-256
`e7f7570867d21b48f438a72b6568276203d25cfcf7cecf403040140686c8894e`).
Its creation time is not an exact touch-observation timestamp.

## One-shot and restoration

The actual authorization was bound to question item
`["request_user_input_async","call_5e6f2e8f95ce40bdac1791493b5f2015",0]`,
trial-plan SHA-256
`dfaad8e4db036aead3e3d83e5aba91194b21c00dbc9ca1ec61ee9202581b5c81`,
install-plan SHA-256
`a6d1c2a4810d1f1d551ded7cdecdebbc47b73a27b71c02cf9ed3b5346708e3ed`
and image SHA-256
`63c085a7bcbaacd494cc94b965b1386ffa8770f4e77cd4e415e7bf9389636f73`.
The approval file SHA-256 is
`e84b5b8449a3f9e00795f175f444e0324270123082a0b1636d32d24f78ed136e`.
The approval is consumed. Never rerun the executor or boot under it.

The executor made one `fastboot boot` attempt (send 0.454 s, boot 0.135 s),
matched the candidate kernel banner and observed TWRP return after 744 s.
It wrote and read back the approved 434,176-byte desktop install, 13-byte misc
recovery marker and 434,176-byte dynamic desktop restore. No rollback or boot
retry occurred. The postboot HFSX catalog was read live before restoring its
current leaf. The original 428,400-byte desktop executable is restored. Four
captures contain 29 files and five directories each, all 116 file records
rehashed, and all three old log prefixes retained. The final root-header
SHA-256 is
`2c9814834dbf66065e479f77b04f7139d5da723d6bf44a26e2ea051669fdd752`.
The phone is in TWRP; the executor and observer process group have exited.
The independent review checked all 67 ready pins, the exact approval, the
boot count, captures, restoration and device state. Its SHA-256 is
`b1b63686832dc1489c47f58669830be61a40dd2cd424218b4ced6e8d5ceee7f7`.
The terminal result SHA-256 is
`d1cf9c1207815a97c2b9390832fc520d75a90185e87ec555eed1affa57cb5772`.

## What the logs establish

The current-only kernel log SHA-256 is
`bafda83622b515ee687f39928c8e80273851ed2a771cadabb1f376e3a974287e`.
The native GPU service completed 49/49 submissions; its full health checks
totaled 2,107, or 43.0 per submission. The earlier C4 control completed
27/27 with 1,584 checks, or 58.7 per submission. Their interaction loads
differed, so neither the 26.7% lower checks per submission nor the 8.59 ms
versus 11.13 ms mean submit duration proves a user-visible speedup.

The 60 Hz software callback ran for 42,300 beats, skipped 145 and selected
104 held frames. The held-frame counters ended at 106 submitted, one replaced,
104 consumed/retired and one canceled. The latest sampled copy prefix has
63 successful 10,368,000-byte frame copies in the 2–4 ms bin, one zero-byte
attempt, and zero rejects. Its GPU read-guard histogram has 46 samples below
0.5 ms, but also one above 33.333 ms. The 16–33.333 ms bin cannot resolve
whether a guard exceeded the 16.667 ms frame budget.

The sampled **held-frame retirement** counter rose by at most **four** in any
of 67 regular 600-beat (nominal ten-second) intervals. It rose by zero in 27
of those intervals. Nine intervals contain 144 observed NVT contact-mask
changes (including a two-contact mask); each had at most three retired held
frames. These are software counter differences, not optical FPS or a measured
touch-to-pixel latency. The separate framebuffer `presents` counter is not a
distinct-frame count: the 0300 diagnostic showed it can increment for a dirty
copy slot before a held frame is actually taken. The sparse held retirement
aligns with the user's report that motion is very slow. The NVT
worker reported accepted physical packets and no malformed-frame rejects, but
the current log does not count changed HID events or prove their receipt by
backboardd. The cadence analysis is in
`research/tmp/gpu-poll-guard-20261112/held-cadence299.json`.

Backboardd's 37 logged FPS windows contain 41 completed command buffers and
zero `presentedDrawable` events. That counter does not cover the owned
IOSurface display path. Logged passes ran in sysmem with GMEM off, including
one about 40 ms; five shader specializations took roughly one second each.
Those spikes matter, but their total is insufficient to explain the sustained
near-absence of newly submitted display frames. The captured workload is not
matched to the C4 control and physical scanout was not measured.

## Next causal check

The current framebuffer implementation sends 60 Hz async notifications only
when a client has both a registered port and a nonzero callback for that
notification type. The candidate kernel log has no `notifications type`
registration line, but registration-port calls and send results were not
instrumented. It is therefore unknown whether the display producer received
usable vsync messages. The next kernel diagnostic should count port and
callback registrations, successful and failed notification sends, changed
HID frames/callback cost, and SwapEnd cadence. A bounded Metal timeline should
tie command-buffer completion and IOSurface IDs to the display swap. Resolve
that chain before claiming or enabling a smooth 60 Hz setting. Any new phone
write or temporary boot needs a new exact plan and user authorization.
