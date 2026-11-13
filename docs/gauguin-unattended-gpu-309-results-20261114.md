# 0309 result: async GPU ran, scripted input arrived with display off

The separately approved one-shot 0309 boot returned to TWRP automatically
after 745 seconds. Its kernel banner matched the reviewed image. The original
frontend was restored and independently read back; misc also matches its
original 4 KiB preimage. No boot retry or recovery fallback was used.

The diagnostic did **not** establish smooth 60 Hz. All 13 generated strokes
completed, and the selected four-second trace contains 68 accepted HID queue
events, but no Metal command buffer or framebuffer presentation in that
window. The log shows the display was turned off before the first generated
stroke and never requested on afterward. This is a concrete missing
precondition for the unattended animation workload, not evidence that a busy
GPU stalled those touches. It does not prove that display power is the only
remaining downstream issue.

## Safe completion

The actual user reply `允许本轮 0309 写入、自动测试和回退` was bound to the
reviewed plan and image. Approval receipt SHA-256:
`91da1249bf449238732cee39da83f88e9a8aa72bc340a688d91cae1a2233d6ee`.
The executor rehashed 87 inputs and admitted its 512 MiB reserve at
499,330,142,208 bytes accounted. A fresh 29-file capture, catalog identity,
data ranges and misc preimages matched before the 434,176-byte install and
13-byte marker write. Both writes were read back. `fastboot boot` accepted
the exact image once. Following log collection, 434,176 userdata bytes were
restored/read back and the final 29-file comparison passed, allowing log growth.

The independent verifier read 139,911,168 bytes without any write or reboot.
It matched the original desktop data, HFSX file identity/fork and original
logical-size field, the dynamic postboot root header, and original misc bytes.
Receipt SHA-256:
`d4fbecf0c9eea627ea24d27a3a3540d5ca474ac0f9af3a39c0a16e53938d5534`.
The executor's final `trial-incomplete-or-failed` state refers to its diagnostic
gate: `scripted capture has no repeated frame production/presentation`.
It records `restored=true`, `boot_attempts=1`, `observer_exit=0`, and
`recovery_fallbacks=0`. Result SHA-256:
`91e290ca814afe7ddf0a3da29d2f0cf77c30c5a7653348df0ca66f422ef7812c`.

## Observed work

| Evidence | Result | Scope |
| --- | --- | --- |
| Script | 13 strokes, 442 reports, no script abort | Generated input, not physical fingers |
| UI254 | 416 records, four seconds, zero lost, deadline stop; 68 reports and 68 successful queue enqueues | Input reached the HID user-client queue; no SpringBoard receipt is recorded |
| During capture | Zero C4 buffers, SwapEnd events or presentation events | No animation workload for an FPS measurement |
| GPU service | Async compositor opt-in logged; 14 submitted / 14 completed, 598 watchdog renewals | Eight root jobs plus six desktop startup jobs; no sustained animation |
| GPU API | 14 submit calls, mean held time 6.659 ms, maximum 8.271 ms | Issued-fence return, not end-to-end GPU completion |
| Wait API | 14 calls, 20.585 ms total held plus 4.437 ms total unlocked waiting | Confirms the new unlocked wait path executed |
| C4 reports | Six command buffers, reported GPU duration median 9.526 ms, maximum 20.993 ms | Frontend-reported timing; one above 16.667 ms, not panel frames |
| Latest copy prefix | Four attempts, two successful copies, one GPU-read refusal | Prefix logged at powers of two; not a final presentation total |

The last C4 buffer completed at 155.425945 seconds on its CPU-clock timeline.
The first scripted stroke began at 225.225914 seconds, about 69.8 seconds later.
Kernel log power records are `on`, `off`, `on`, `off`; the last `off` precedes
the first generated stroke, with no later `on`. The framebuffer selector 12
records that requested state and its vsync path suppresses normal presentation
while off. Private power-order receipt SHA-256:
`c93eb4175deb9028b5b047e2e61f0d87b84514b5311c9f299e9ddc26e7281459`.

The source also consumes and retires a held frame even if a pending GPU
surface causes its read guard to refuse it. The one observed refusal makes
that path relevant for the async candidate, but it does not explain the
later display-off/no-command-buffer interval. It needs its own completion
and retirement correction/validation rather than a physical FPS claim.

## Next action

Make the unattended workload observe the requested display state. If off,
send one bounded power-button press/release through the existing HID button
service, wait for a recorded display-on transition, then start the strokes.
Refuse unknown state or failed wake, and stop if the display turns off again.
This makes wake success observable instead of assuming an injected swipe
will wake the system. It should precede another animation-rate comparison.

The 0309 approval is consumed. A new image requires its own exact-scope trial
confirmation after it is built and reviewed. Physical finger response, smooth
60 Hz and panel high refresh remain unqualified. Raw logs and dumps remain
private. Kernel-log SHA-256:
`e52ae509954ea29c7a891c88b1ec45a511a2552e31f2a959b2fab1b85803b84c`;
analysis SHA-256:
`0d2db0b4c6e50eee77fd448538c5bfd6d4291eaddf10177ddfb247ee7e26959d`.
