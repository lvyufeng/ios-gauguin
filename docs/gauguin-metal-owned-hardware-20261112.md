# Isolated Metal ownership hardware trial

The isolated ownership-core check **passed twice on the real Adreno 619**.
Each run completed eight GPU command buffers, passed two callback-release
checks and all 20,480 byte/pixel comparisons, and closed its root owner cleanly.
The original launch entry was restored byte-for-byte after each run.

Preparation used read-only recovery access and local builds/image edits. The
user then explicitly authorized the exact writes, one temporary boot and
restoration described below. This qualifies the finite new-core test; desktop
asynchronous CoreAnimation composition and physical frame rate remain open.

Before the first installation, the phone was in TWRP with the 16 GiB iOS HFSX
root prefix of userdata unmounted. All 16,384 one-MiB device chunk hashes and
the complete device SHA-256 matched a fresh independent backup. That preserved
pre-installation backup has SHA-256:
`a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608`.

The first reconstruction stopped before transferring changed chunks because
792 MiB exceeded its conservative 384 MiB transfer cap. The original complete
device scan and unchanged local clone were retained. Reconstruction resumed
within the already admitted reservation for two full 16 GiB images; it created
no further clone and repeated no scanner execution. It verified all chunks and
the complete digest. The temporary read-only scanner was removed from recovery
RAM. No partition mutation was used for backup.

## Probe and launch scope

The new executable uses the public C API and the exact new ownership library:

- `/usr/libexec/gauguin-metal-owned-test`, 74,864 bytes, SHA-256
  `cb8e5c1a1b6f6e1a43f268144ede7abf0b264127e4ad747b3cc27aee457b854c`;
  build `1cb92917c87718fe918f9cdb`.
- `/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib`, 8,407,792 bytes,
  SHA-256 `c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674`.

The probe verifies its loaded library path and hash, the old router hash, exact
boot command, OS build 20H392, root role and existing 128 MiB fatal memory limits.
It waits at most 180 seconds for the real GPU, then has a 30-second work alarm.
It checks synchronous and deferred fill/copy readback, deferred RGBA8 clears,
cross-queue append, callback owner release/own wait, ordinary API error
completion, fixed queue mode, early queue-wrapper release and zero remaining
GPU allocation. Expected totals are eight successful GPU command buffers, two
release callbacks and 20,480 byte/pixel comparisons. Normal API refusal is an
expected non-submitted error; no old fault demonstration or forced GPU fault
is run.

After clean completion the process uses the existing SETEXEC/memory-policy
contract to become the unchanged old router. That router starts the unchanged
old bootstrap and desktop components with their old core. The test's root
connection does not arm compositor readiness. Kernel evidence must show its
clean eight-job close, followed by the old bootstrap's clean armed eight-job
close in the next epoch. Desktop deferred recording is not enabled.

Only the root job's executable/argument strings change in its standalone plist
and the launch cache. Equal-length strings preserve both file lengths. All
531 job entries remain, with 530 unrelated entries unchanged. The 25 other
previously captured files and four directory owner/mode records remain exact.
The old installed GPU core, router, bootstrap and desktop bundle are retained.

## Concrete proposed writes

Private preparation and immutable range data are in
`research/tmp/metal-hardware-20261112/` (`W`).

- Install delta: 2,439 four-KiB blocks, **9,990,144 bytes in 40 ranges** within
  the existing userdata root prefix. It adds the probe, private library and
  directory, changes the two launch files, and includes required HFS metadata.
- Native local HFS maintenance retires 57 unlinked `HFS+ Private Data/tempCNID`
  entries and rotates two filesystem event records. These exact changes are
  listed in `W/candidate/install-plan.json`; the full original data remains in
  the fresh backup. Event UUID content/ownership and unrelated BSD metadata
  are preserved. No GPT, recovery, modem, persist or bootloader change exists.
- Recovery return marker: exactly **13 bytes** (`boot-recovery`) at misc offset
  zero, with full-block preimage/readback validation and marker-failure rollback.
- Boot: exactly one temporary boot of the existing qualified 0298 image, SHA
  `64596164315fc496ff30037bb1fdf982d1322069eee788e28554f38d6f43cc7e`, with
  the same 600-second GPU service and 780-second observer window. No retry.
- After recovery and evidence capture: restore **8,192 bytes in two ranges**
  containing only the original two launch-file data strings. Their current
  fork mappings and full range preimages must match. No pre-boot filesystem
  metadata is replayed over runtime log changes. The two new test files remain
  present but inactive.

Before any boot, failed installation/capture/marker preparation has an exact
pre-boot rollback plan. After boot, only the narrow launch-data restoration is
used. Any incomplete rollback or recovery uncertainty is reported explicitly;
the original execution is observed rather than relaunched.

## Completed preparation checks

- Actual whole core plus the new probe's FakeGpu adapter: eight successful
  modeled jobs, two callbacks, all 20,480 comparisons and zero remaining GPU
  allocation pass under ASan/UBSan. This is host evidence only.
- Signed ARM64 iOS 16 native probe builds successfully. Its imports contain
  the real GPU-open entry, not the FakeGpu-open entry.
- All **295 probe/core imports** resolve against the actual 20H392 shared cache;
  no unresolved strong or weak import remains.
- Full local allocated-block scope audit and read-only `fsck_hfs -f -n` pass.
  Candidate SHA-256:
  `9c3902e393b0488fb477d0599fb97f04b10e8840c6109ca23f100b5be042fc3c`.
- **52 writer controls** pass, including partial failure at each install and
  restoration range, exact rollback, stale preimages and missing approval.
- **10 log-parser controls** pass. Host output, wrong hashes/counts/order,
  missing cleanup, failed kernel closes and wrong epochs are rejected.
- The actual 29-file capture reader passes against the local candidate, and
  all 40 current old device ranges plus misc match their read-only preflight.
- Calling the execution entry without a real approval receipt fails before
  creating an execution directory or opening device IO.

The complete 33 GiB batch was admitted under the 500 GB project cap. No kernel
build, CI run, flash or device trial was performed while preparing this plan.
The final plan/hash and input pins are in `W/trial-plan.json` and `W/ready.json`.

The project-required write confirmation was received as the exact answer
`允许本轮写入、临时启动及回退` to question item
`["request_user_input_async","call_2cfc4a42d88b4a39b79a638e83abe767",0]`.
It binds plan
`e80817f02bde654b43c9a6c278b832c00c4becdf9500d3c2f4905e4e07966d4d`.
This one-shot authorization is now consumed.

## Observed real-device result

Source was committed as `b8a4b07`. Original execution PID 65017 and observer
PID/process group 66203 are terminal, with no surviving observer children.
The retained execution exits 0. All 173 reviewed input pins still match.

All 40 install ranges read back correctly, followed by the complete installed
29-file/five-directory check. The 13-byte recovery marker also read back
correctly. Fastboot accepted the image once (send and boot both OKAY; 0.601 s
reported total). The observer found TWRP after 747 s and verified the exact
0298 kernel banner. No retry or failure rollback occurred. Claim-to-result time
was 826.551773 s; initial input rehashing precedes that claim timestamp.

Current-only stdout identifies probe `1cb92917c87718fe918f9cdb`, the new
`c9da25aa…` core, Adreno 619/chip `06010900`, and seed `1481645600`:

- Synchronous and deferred GPU fill/copy, both RGBA8 clears and cross-queue
  append produced the exact independently recomputed readback hashes.
- The deferred success and expected API-error callbacks both returned from
  their own waits and released their command-buffer owners. FIFO sentinels
  completed afterward.
- Queue-mode freezing and early queue-wrapper release passed. All seven
  cleanup observations reported zero remaining GPU allocation.
- The complete result reported eight successful GPU jobs, two callbacks and
  20,480 readback comparisons. This count mixes byte and pixel comparisons; it
  is not a count of displayed pixels or frames.

Kernel close records independently bind the two owner epochs:

| Owner | Ready | Jobs | Native fence | Epoch | Clean |
| --- | ---: | ---: | ---: | ---: | ---: |
| New isolated core probe | 0 | 8 | 8 | 1 | 1 |
| Retained old bootstrap | 1 | 8 | 16 | 2 | 1 |

The old router executed the unchanged bootstrap/core. Its eight offscreen
stages reported success, with queue-local fences 1–8 and native arm fence 16.
The overall finite service ended with 598 renewals and 35 submitted/completed
jobs. Only the first eight belong to the new ownership probe; the remainder
must not be attributed to it. These counters do not measure desktop FPS.

The three complete pre-test log prefixes were retained. New suffixes contain
4,959 bytes of root stdout, 135 bytes of root stderr and 53,070 bytes of
backboardd output. Installed/post/restored captures verify all 87 file records
and five directory records in each capture. The two launch files were restored
through exactly two data ranges (8,192 bytes), then independently compared
byte-for-byte with their originals. All 24 original static captured files are
retained. Logs did not change during restoration. The private test executable
and library remain installed but inactive; the default desktop core is still
`8a826583…`.

The first run ended in recovery. Its post-boot and post-restoration root
headers agreed at
`1c43ad66d5195271397bd23a13ed4f284df231e1ad67b7c3552a15dc423ba539`.
That header is historical after the second run below. Future work must use
fresh current preconditions, not replay the consumed 9.99 MB installation
metadata.

Evidence is in `W/execution/`: original install/marker/observer/restore receipts,
all three captures, current-only log tails, `validation.json`, and
`independent-review.json`. No raw phone evidence was committed. No screen
attestation was received in this run; launching SpringBoard and backboardd is
not a substitute for a physical UI observation. CoreAnimation admission/wait
ordering, full desktop GPU composition and physical FPS still require their
own work.

## User-requested second temporary boot

The user then explicitly requested `再刷机一次`. This authorized one repeat of
the same temporary image and probe, with capture and launch-entry restoration;
it was not a screen observation or reuse of the first consumed approval.
Private repeat evidence is in `research/tmp/metal-hardware-repeat2-20261112/`
(`R`). The new plan is
`14ddfd2fac19bcbc6250461dce0a363eade1cd40052449015dfbeea919a53dc2`.

A fresh 29-file/five-directory capture matched the first restored state. The
existing probe and private core were reused. Activation and restoration each
changed only two launch-file data blocks, **8,192 bytes**, with verified
preimages and readback. No binary installation, filesystem metadata write,
new image or clone was needed. The narrowed writer passed 14 range controls.
The complete repeat batch reserved 1 GiB within the 500 GB cap. The 13-byte
recovery marker also passed readback.

Original execution PID 3532 and observer PID/process group 3973 are terminal;
the retained execution exited 0 and the observer group is empty. Fastboot
accepted the same 0298 image once, reporting 0.598 s total. Recovery was
detected after **746 s** and the exact kernel banner matched. Claim-to-result
time was 808.155601 s. No retry or failure rollback occurred.

The new log suffix identifies seed **1734417142**, the same native probe and
the same private `c9da25aa…` core. All eight ordered jobs, two callback checks,
20,480 readback comparisons and seven zero-allocation observations passed
again. Independent CPU hash reconstruction matched every fill/copy and RGBA8
clear. Kernel closes again showed the new probe at ready 0/jobs 8/fence 8/
epoch 1/clean 1, then the retained bootstrap at ready 1/jobs 8/fence 16/epoch 2/
clean 1. The retained bootstrap also completed its eight stages.

The whole service ended at 598 renewals, **80 submitted and 80 completed** jobs,
and shadow count 980. Only its first eight jobs belong to the new probe.
The difference from the first run's 35 total jobs does not establish desktop
FPS or explain physical screen behavior.

Independent review rechecked all 161 ready pins, all 101 preserved first-run
evidence pins, and 116 actual file records across fresh/installed/post/restored
captures. All 26 static files match the inactive repeat baseline, including
the two original launch files. Each capture retains five directory records.
All three complete old log prefixes remain; new stdout/stderr/backboardd
suffixes contain 4,957/135/102,456 bytes. Those logs did not change during
restoration. The new kernel-log hash is
`8d85a10ba23d9dcf3150cb424ac084a3d4ad5b47cca0dd0260e7171f9964a6bb`,
distinct from the first run's preserved capture.

The device is back in recovery with the private test inactive and the original
desktop core/router/bootstrap retained. The current post-boot and
post-restoration root headers agree at
`42ec2e54c3a7a0972786f70fc768e2c3e72f143353320dedf2e79ac78fdca388`.
The new request has been fulfilled; its one-boot scope is consumed.
`R/execution/result.json`, `validation.json`, `independent-review.json` and
`R/final-review.log` retain the terminal result and read-only audit. No new
kernel build or CI run was needed. No physical screen attestation was received;
CoreAnimation admission/wait ordering and desktop GPU performance remain open.
