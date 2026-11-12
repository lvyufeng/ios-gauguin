# Isolated Metal ownership hardware trial

The requested real-device check is prepared for the qualified ownership core.
Preparation performed read-only recovery access and local builds/image edits.
No phone partition write or boot has occurred at this proposal milestone.

The phone is in TWRP with the 16 GiB iOS HFSX root prefix of userdata unmounted.
All 16,384 one-MiB device chunk hashes and the complete device SHA-256 match a
fresh independent backup. Backup SHA-256:
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

The pending explicit write confirmation is required by the project's
`AGENTS.md` instruction to confirm each destructive step before running it.
Successful future probe logs will qualify this finite core test and owner
handoff only; CoreAnimation frontend ordering and physical desktop frame rate
remain separate work.
