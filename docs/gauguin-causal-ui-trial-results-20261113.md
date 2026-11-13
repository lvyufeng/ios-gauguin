# 0301 one-boot causal UI trace: no physical contact recorded

The user approved the exact [0301 one-shot plan](gauguin-causal-ui-trial-20261112.md)
through this chat's `request_user_input_async` reply. Private approval SHA-256
`d50c63a9ba9a7db43df10165455adefd4a99362ab2b2a609f4de53607a0e42df`
binds that answer, its question item ID, the install/trial plan and image
hashes. The executor claimed this approval once. No asynchronous GPU
candidate was enabled.

## Boot and restoration

The prewrite 70-pin and 1 GiB storage checks passed. In recovery the runner
captured and compared 29 files, then wrote/read back the planned 105 desktop
data blocks and one catalog leaf: 434,176 bytes in userdata. It wrote the
13-byte misc recovery marker, launched the pinned image **once**, and its
observer verified the image's kernel banner. TWRP returned after 745 seconds,
within the 780-second observation limit. The observer exited 0. There was no
boot retry and no fastboot recovery fallback.

The runner captured postboot files, restored/read back 434,176 userdata bytes,
then compared the original 29-file set, allowing only the expected log growth.
An independent TWRP read confirmed the original desktop data bytes, the
original catalog logical length and file identity. The whole catalog leaf
was not required to revert: iOS had changed other HFSX metadata during boot.
The root header changed on boot but was identical in postboot and restored
captures. The misc 4 KiB preimage returned to its exact original bytes. The
phone is in recovery. Independent restore receipt SHA-256:
`9f319e541c18d41eb13acc3b0c42c50357c174866d1b64bbabf7d6c07bf10746`.
The first independent check incorrectly expected the preboot root-header
hash and stopped without writing; a corrected check used the documented
dynamic postboot-header rule and passed.

The final executor state is `trial-incomplete-or-failed`, with
`installed=true`, `restored=true`, `boot_attempts=1`,
`partition_write_phase=desktop-restored`, `observer_exit=0` and
`recovery_fallbacks=0`. Its failure is **diagnostic**, not a failed restore:
`selected gesture has no complete HID queue trace`. Private executor result
SHA-256 is `1db9a5813c723a731d60e8d19f972cfaec49cfd77ccdb9860461d5e5431d06bb`.

## What this boot measured

| Evidence | Observation | Limit |
| --- | --- | --- |
| Novatek input | Firmware bootstrap succeeded; final summary: 63,904 packets accepted, zero rejected, mask `0`. No contact-mask transition was logged. | This cannot tell whether a finger touched the panel; user observation is pending. |
| HID / bounded trace | Backboardd opened one SweetHIDTouch client. `UI254` stayed armed for gesture 2, then stopped with reason 4 (`GPU_STOP`): zero gestures, zero events, zero lost records and zero HID queue links. | No touch-to-HID or touch-to-frame latency can be computed. The ring did not overflow. |
| GPU service | Final service: 598 renewals, 14 submitted and 14 completed native jobs. | Completion establishes this boot's executed GPU work, not smooth animation or high refresh. |
| Submit CPU cost | The 14 native submits used 72,724,947 ns wall time; 374 full guard checks used 71,043,697 ns, 97.7% of that submit span. | Aggregate CPU wall time from mostly startup/idle work; it is not paired to a touch or visible frame. |
| C4 / framebuffer | Five C4 FPS windows contained six command buffers and zero C4 `presented` counts. Their frontend-reported GPU durations were 13.033–28.247 ms, three above 16.667 ms. Framebuffer logs recorded five CPU copies and a software 16,667 µs clock. | The C4 durations are frontend reports, the FPS windows have no touch, and neither counter measures physical panel frames. |

Private raw kernel log SHA-256 is
`805dbf6dfd51c5fa0c949281499e5c80044cebca51ed18198c301b1a06b494a3`;
the strict parsed trace SHA-256 is
`b393dfe430eaac3141bf75efd9c672a045fedad15acf2e41d277499aac8cdc51`.
The private no-contact analysis receipt SHA-256 is
`5136cc22e0cfee2addfd55c5ce1775e7e67a20e3d0158a8ced9426d248eedca3`.
Device dumps, raw logs and serials remain out of git.

## Decision from the missing gesture

Ask whether the user physically touched or swiped during this exact boot.
If not, this trial never exercised the intended causal path; a repeat would
require a new separately approved phone trial with confirmed interaction.
If the user did touch, the zero contact mask makes Novatek physical-report
delivery the first fault to investigate before changing GPU or animation
cadence. Neither interpretation is justified until that observation arrives.
The full smooth 60 Hz, GPU acceleration and high-refresh goal remains open.
