# 0310 result: display-on scripted input, sparse frame production

The approved 0310 trial completed its single temporary boot and restored the
original frontend. It returned to TWRP automatically after 745 seconds; the
kernel banner matched the fixed image. Installation and restoration each
wrote/read back 434,176 userdata bytes. The 13-byte recovery marker was
verified before boot, and independent final readback found the original misc
contents. No boot retry or recovery fallback occurred.

The performance diagnostic did **not** qualify repeated presentation in its
selected four-second window. This time the requested display state was on
throughout the scripted workload, so the previous display-off precondition
is no longer the explanation for that window. Input reached the HID queue,
but command-buffer production remained sparse. This does not yet establish
whether SpringBoard accepted the gestures, unlocked or scheduled animations.

## Authorization and restoration

The direct user message was: “允许本轮 0310 写入、唤醒测试和回退，继续无人值守验证。”
It was bound to the already-reviewed plan, install plan and image. No async
questionItemId was supplied with that direct message; the receipt explicitly
labels its direct-message provenance rather than inventing a platform ID.
Approval receipt SHA-256:
`9aaf055218d4e4aa97de00e382c13306550df1bf7b7729b1e19b9956078b6326`.

The unchanged executor rehashed all 93 inputs, admitted its fresh 512 MiB
reserve at 499,458,293,760 bytes accounted, captured/compared the 29 files and
checked current HFS catalog/data/misc preimages before writing. After boot,
it captured the logs, restored the frontend and compared the final 29-file
capture to the original, allowing only expected log growth.

The executor's terminal `trial-incomplete-or-failed` refers to the diagnostic
condition `scripted capture has no repeated frame production/presentation`.
It records `restored=true`, `partition_write_phase=desktop-restored`, one boot,
observer exit 0 and zero recovery fallbacks. Result SHA-256:
`f1272013e2b83d2613646f28af7287e3e90d96660c64a3083471193aef231abf`.

Independent verification then read 139,911,168 bytes through an allowlisted
read-only interface, with no write or reboot calls. It matched the original
frontend data, live HFS file/CNID/fork/logical length, the postboot root header
and original 4 KiB misc preimage. It independently resolved the current
catalog leaf, which remains block 44123, byte offset 2010. Receipt SHA-256:
`a98667e4e1c4098e66a785cc4c5251c5a399a114659057e4556b13dac8f4fac7`.
The new current root-header SHA-256 is
`492c57e711dcb89e40330f8c4ffce88fc63ceec09edb519ad3e24dc75740c8c0`.
Future trials must use this restored capture and fresh preimages, not rerun
the consumed 0310 executor against its preboot header.

## Observations

| Evidence | Observed result | Limit |
| --- | --- | --- |
| Display gate | Already on; one-second settle and on confirmation; no off request during the workload | Software requested state; no physical screen observation |
| Wake button | Zero button pairs | The off-to-on button branch was not exercised |
| Script | All 13 strokes / 442 reports completed, from 226.205162 to 258.973606 seconds | Kernel callback success does not prove application acceptance |
| Selected UI254 window | 657 records over four seconds; zero lost; deadline stop, no capacity truncation | Covers strokes 1 and 2, not the entire 32.768-second script |
| HID queue | 68 successful enqueues, including releases; 66 down/movement contacts | No SpringBoard receipt or gesture-recognizer acknowledgement |
| C4 in selected window | One buffer created; zero commits and completions within the window | It was created near the end and committed just after the window closed |
| Display in selected window | Zero SwapEnd and present-end events | No repeated-frame workload for a frame-rate claim |
| Whole-boot GPU | 40 submitted / 40 completed; eight root jobs and 32 desktop command buffers | Successful sparse work, not sustained animation |
| C4 during the whole script | Nine buffers created during 32.768 seconds | Temporal overlap, not proof that each buffer was caused by a gesture |
| Last intact copy-stat prefix | 16 attempts, 10 copies, six zero-byte attempts, five GPU-read refusals | Sampled prefix, not final totals or physical FPS |

The full C4 timeline contains 32 command buffers. Seventeen of the gaps
between successive creations fall between 4.9 and 5.3 seconds. In the scripted interval,
examples are 231.455734, 236.461884, 241.469140 and 246.477292 seconds.
The buffer created at 236.461884 committed at 236.573765 and completed at
236.596226; the trace window ends at 236.573533. Thus the four-second result
is not an empty or lost log, nor evidence that a queue enqueue produced a
display frame. It contains input and the start of one sparsely produced buffer.

The frontend-reported GPU duration has a median of 13.533 ms and a maximum
of 57.389 ms. These are that frontend's duration reports, not independent
physical GPU occupancy or input-to-panel latency. Some work exceeds a
16.667 ms frame budget, but those durations alone do not explain the repeated
five-second gaps before the next buffer is created.

Framebuffer notification snapshots still show zero ports, registrations and
sent callbacks. The earlier HakiOS review explains why that fact alone does
not prove a missing display-notification mechanism: its reference says CA
can use a built-in frame clock without requesting driver notifications. The
five-second production pattern now needs direct input/CA scheduling evidence.
The legacy `presents` counter also counts attempted flushes, so its larger
value is not a count of successful copies or visible frames.

## Next action

Investigate the gap between HID queue acceptance, SpringBoard input handling
and CA frame scheduling before attributing the lag to a panel refresh rate
or raising GPU settings. The prepared 0311 pending-frame fix remains relevant
to the separately observed GPU-read refusals, but it cannot create command
buffers absent from the selected window. Do not treat another boot of that
image alone as a fix for the five-second producer cadence.

One measurement caveat was also confirmed against the exact C4 source pinned
by its native build: `waitUntilCompleted` starts its `hm_fps_waited` timer
**after** waiting on `_stateCondition`. Its reported wait duration omits that
frontend wait and cannot establish that the caller did not block. The full
made/committed/done timeline remains usable for the observations above.

0310 authorization is consumed. No 0311 boot is authorized by it. The original
backups, restored frontend, all trial inputs, raw logs and candidate images
remain intact. Smooth 60 Hz, physical touch response, general GPU coverage
and physical high refresh remain unqualified.

Private evidence is in
`research/tmp/gpu-display-wake310-20261114/execution/` in this worktree:

| File | SHA-256 |
| --- | --- |
| `kernel.log` | `78e7903f140792a41b76683c187b224604d70d9d3f39ac4aab3c06f109e40014` |
| `backboardd.log.current` | `50c7df48dde248f4ac4f18081ce93aa6150411b76f0e9bd444099c1e86ce3f1b` |
| `timeline-analysis.json` | `1b804fec88d584b3b0813fd3da941ca96dd72442ca73f27c073e8128a96f4ee1` |
| `diagnostic-summary.json` | `40ded4d1f924e8c1a6b9f17d3fe7fe9956ade525598866842889a79663766c03` |
