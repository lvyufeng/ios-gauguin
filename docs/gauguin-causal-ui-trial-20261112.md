# 0301 causal UI trace: reviewed one-shot plan

**Prepared only. No 0301 partition write or boot has occurred.** The user
reported that the 0300 C4 desktop reached SpringBoard but still lagged. The
prior one-shot consent was consumed. This candidate requires a new exact-scope
reply before its executor can open device IO.

## Why this trace follows the HakiOS reference

The published [HakiOS SpringBoard hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L1783-L1852)
found animations requesting no preferred frame range and advancing at 24 fps
with about 0.3 ms of GPU work. Its opt-in `anim_max=1` then copied those
animations and requested 80–120 fps on its 120 Hz Redmi. Its
[runner](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/metal-run.sh#L66)
also uses deferred Metal recording, asynchronous GPU submission, copy workers
and touch timing. See the [source comparison](gauguin-hakios-60hz-causal-review-20261112.md).
Gauguin's 0300 evidence cannot tell whether the HID queue accepted the
touches or whether SpringBoard/CA asked for frames. A 60 Hz clock callback
alone did not yield a smooth desktop. This trial measures the kernel half of
that missing path and C4 command-buffer times on the same `mach_absolute_time`
domain. It does not change animation requests, GPU serialization, display
copy or panel timing. The source still lacks a read-only SpringBoard
animation-request hook, so even a successful trace cannot by itself certify
the HakiOS 24 fps explanation or physical 60 fps.

## Candidate and offline evidence

Patch `xnu/patches/0224-gauguin-causal-ui-trace.patch` SHA-256
`fcc58b98074cfd159e23c87252c6c8ed113e08a4283173129acbf60576c6ae15`
ports the bounded 0254 four-second ring to the current C4 tree. It adds an
absolute-timestamp link from the digitizer event to the HID user-client queue
and records enqueue success, queue refusal, GPU API/submission spans, SwapEnd,
held-frame presentation and copy spans. Producers do no console or UFS IO.
The trace is opt-in with `sweettrace=2` and has a 4,096-record bound; its
parser reports lost records and refuses incomplete captures. Queue success
means a user-space queue accepted a kernel event. It is not a SpringBoard
receipt or a panel latch.

The patch applies without fuzz to the 0300 source. Ten affected ARM64
translation units passed native single-file compilation; the actual trace
core/board and strict log parser passed host checks. Full local
`make install` exited 0 with `SKIP_TESTS=1` after the focused checks.
The isolated tree lacks older source202 fixtures for the broad host suite.
Kernel SHA-256 is
`8f8ddd92b49d08e166692da2e89c2ab271609d04bd1dbe2fd2f378215ffdaa42`,
build identity `xnu-6d388b8ecea741f6a453c82b2e752c69`.

Offline image `research/tmp/ui301-image.img` is 20,021,248 bytes,
SHA-256 `6f02f0ebe258a754dc915b7b786244e59e656989d7732ffa9af6a9148983653a`.
An independent byte review SHA-256
`830bf5e7eeb0bd7c1af763f9d253641545b7376a29c8ab942d44dab51f4e34be`
checks its Android wrapper, shim, DTB, ADT, segment VM layout, firmware
physical addresses, content and padding against the booted 0300 image. The
new kernel file segment grows 744 bytes; asset payload offsets move 736
bytes. The 601-byte command preserves `sweetfb_hz=60`, the 600-second GPU
service and `metal_fps=timeline`, replaces the unused `sweettrial` metadata
token with `sweettrace=2`, and adds `touch_lat=1` for C4 command-buffer
timestamps. `sweettrial` has no direct consumer in this staged XNU source.

## Current phone and exact proposed scope

A fresh read-only capture checked 29 files and five directories in TWRP,
with `userdata` unmounted and no block holders. Root header SHA-256 is
`6e272d2e11ae716993301df334c35eeb5498b0a77adbccd965f924e28a5e77e4`;
the original desktop executable is 428,400 bytes, SHA-256
`0a1b55bb20a29661de40099e58e45ec695ffb0bf78e132a9d10985450e868550`.
The existing 16 GiB root backup rehashed as
`a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608`.
The current misc 4 KiB preimage is zero, SHA-256
`ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7`.

With a separate approval, the one-shot runner would:

1. Rehash all 70 pinned inputs and recheck the 1 GiB storage reserve before
   claiming the trial once, recapture the current
   29 files, check the exact root header, HFSX catalog location, full data
   preimages and misc preimage before writing.
2. Write/read back 105 existing desktop blocks starting at root block
   **3,817,791** (430,080 bytes), then the existing catalog block **44,123**
   (4,096 bytes). In the catalog leaf only the eight-byte logical length at
   offset **2010** changes from 428,400 to 428,720. A partial write or bad
   readback rolls touched ranges back in reverse order.
3. Write/read back the 13-byte `boot-recovery` misc marker and `fastboot boot`
   the exact image **once**, without a boot retry. The observer waits up to
   780 seconds for TWRP and checks the exact kernel banner. If recovery is
   needed for rollback and unavailable, at most one bounded
   `fastboot reboot recovery` is permitted. If `fastboot boot` is refused
   before temporary launch, restore the original desktop and then write/read
   back the original 13 misc bytes. A failed helper launch also follows this
   preboot restoration path.
4. Capture only new kernel and C4 logs, parse the selected second gesture's
   four-second ring and C4 command-buffer times, then read the **postboot**
   catalog leaf. Restore the original 430,080 desktop data bytes and only the
   current leaf's eight-byte logical length, sync/read back and repeat the
   29-file capture. If the first restore write fails and its rollback is
   verified, exactly one fresh restore retry is allowed. An incomplete
   rollback stops the runner. If restore preflight refuses before any write,
   the bounded fallback can re-read the live catalog and try restoration.
   If both restores fail, the installed C4
   executable may remain and further repair requires a new scoped decision.

Normal explicit writes are **868,352 bytes to userdata** and **13 bytes to
misc**. Two failed restore writes with verified reverse-order rollbacks can
raise the bounded total to **2,170,880 userdata bytes**; restoring a preboot
misc marker can add one 13-byte misc write. No new file, allocation, GPT,
bootloader, recovery, modem or persist write is planned. The fresh 1 GiB trial
storage reserve was admitted at 498,808,119,296 accounted bytes under the
500 GB cap.

The installation plan SHA-256 is
`abab7f0f432f7ffe5f94234b5245be337bfe5d054a3887916338f2a465d81365`;
whole trial plan SHA-256
`5ef6e2f1bdd2240d233830f2754f7d517dc6066a938677e6b0cc8614e3d41d03`.
The 70-pin ready receipt SHA-256 is
`4ce5196d6cd8eb271b98708deeffa6586808ebc5368de2928c1480df1a4d9a12`;
independent read-only review SHA-256
`9a7fe6ff1e762f5970410e68ebbe62f194ffa871ef05482bf46adae4d0f13009`.
The revised executor SHA-256 is
`0fc4cf326e4d51ba761a7a0b725351fd96a201f024beacc1bc29e160fe5b2dbb`.
The previous ready/review/admission receipts were archived with private
cleanup manifest SHA-256
`ce97593690f223494176f38d298e2bd0ab3696710c30849f5682ad8b8a27a3d8`;
the intermediate ready/review pair was archived with manifest SHA-256
`673c2e27bda7c925e6f6f10ff03cba20b911ec0ab483ec6db8969750d5b576b1`.
The image, install plan and whole trial plan hashes did not change.
The actual-range writer model passed 24 installation and rollback controls.
Running the executor without this round's reply was verified to stop before
device IO and before creating an execution claim. A separate fake-IO
`fastboot boot` code-5 fault test verified original desktop restoration and
13-byte misc marker readback, without a device command.

For a useful capture, start repeated swipes promptly after reaching the
desktop; the second finger-down starts the bounded four-second trace. An
original-cadence screen recording would be needed to estimate visible FPS.
The resulting trace will distinguish a queue failure or slow kernel/GPU/copy
span from a gap before frames are made. If the queue is healthy and frames
remain sparse, add a read-only SpringBoard animation-request hook before
trying a HakiOS-style 60 fps animation policy on Gauguin.
