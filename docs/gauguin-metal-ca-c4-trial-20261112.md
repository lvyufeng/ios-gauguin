# C4 desktop Metal one-boot device trial

The approved one-boot trial **ran and passed its backend/restoration checks**.
The ordered desktop frontend loaded the private ownership core and completed
GPU work; the original desktop bundle was restored. Displayed pixels, physical
FPS, 90/120 Hz and smooth daily use require separate evidence.

## Current device and payload

The latest read-only TWRP capture matches all 29 selected files, five directories
and the HFSX root header left by repeat2. Userdata is unmounted with no holders.
Root-header SHA-256:
`42ec2e54c3a7a0972786f70fc768e2c3e72f143353320dedf2e79ac78fdca388`.
The preserved full 16 GiB backup has SHA-256
`a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608`.

The installed desktop executable is 428,400 bytes; the signed candidate is
428,720 bytes, SHA-256
`560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5`.
Both fit the same 105 allocated four-KiB blocks. Info.plist and CodeResources
match byte-for-byte. The candidate refuses queue creation unless `dladdr`
identifies the private owned core at
`/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib`. All 563 native
core/frontend imports resolve against the preserved iOS 20H392 cache or that
exact core; runtime behavior is still untested.

## Executed one-shot scope

1. Re-read the 29-file baseline, volume header, misc preimage and both full
   write-range preimages. Require exactly one Gauguin recovery device, unmounted
   userdata and no block holders.
2. Write the new executable into 105 existing blocks starting at root block
   **3,817,791** (430,080 bytes). Then write one HFSX catalog leaf at block
   **44,139** (4,096 bytes); only the eight-byte logical length at byte offset
   **1,434** changes from 428,400 to 428,720. Sync and read back each run.
   Partial-write or readback failure triggers reverse-order preimage rollback.
3. Write and verify the 13-byte misc marker `boot-recovery`. Temporarily boot
   the already used 0298 image **once**, SHA-256
   `64596164315fc496ff30037bb1fdf982d1322069eee788e28554f38d6f43cc7e`.
   GPU service runs for 600 seconds; the observer waits up to 780 seconds for
   TWRP and checks the exact kernel banner. There is no boot retry. If a
   preboot failure leaves the verified phone in fastboot, one bounded
   `fastboot reboot recovery` may return it for rollback.
4. Capture this boot's stdout, stderr, backboardd and kernel evidence, retaining
   the old log prefixes. Re-read the **current** HFSX catalog and require the
   same file ID, data extents and signed binary. Restore the original 430,080
   data bytes, then one current catalog leaf whose only changed content is the
   eight-byte length back to 428,400. Preserve all other postboot catalog
   bytes. Sync, read back and capture the restored files. A restore-write
   failure rolls its touched ranges back to the verified postboot state and
   reports an incomplete trial; it does not replay stale metadata.

Normal userdata writes total **868,352 bytes**, plus 13 bytes in misc. A
restore failure and rollback can raise bounded userdata writes to 1,302,528
bytes. No GPT, bootloader, recovery, modem or persist write is in this plan.
The whole trial reserves one GiB: 486,109,007,872 accounted bytes plus
1,073,741,824 planned bytes is below the 500,000,000,000-byte cap.

## Review and acceptance

The read-only virtual overlay re-parsed all 325,681 HFSX catalog records and
found only this file's logical length changed. The actual-range writer passed
24 in-memory controls: wrong consent, stale preimages, partial writes, bad
readback, receipt failure and dynamic restore preserving unrelated catalog
bytes. A read-only virtual activation exercised current HFSX restoration and
rejected the still-inactive old file. Fixture consent cannot reach writable IO.
The log validator rejects the prior boot's old frontend output.

Private evidence is in `research/tmp/metal-ca-c4-20261112/`:

| Record | SHA-256 |
| --- | --- |
| Install plan | `886f11d68dbc05c071884431b706c23a83aaea061e3e79793cf1b2781e7a1fd6` |
| Whole trial plan | `f04d847fda3237907eced7804e45d3a754fc51286754c0e13f68d80394b89a79` |
| Ready receipt, 80 input pins | `6b293f422dfe9b387836316e6a10b3f81cabdfeef44c461f93eb3dcf9448f0d9` |
| Independent read-only review | `1103d82c2204fbe3784b300fff00c29f0d8ca99c567ccb5a4e8e6a354558b8d4` |

The runner refused absent individual approval before an execution claim or
device IO. The user then answered `允许本轮写入、临时启动及回退` to question item
`["request_user_input_async","call_d10c2bc40437497c883a39ae9977241f",0]`.
That approval binds the two plan hashes above; its receipt SHA-256 is
`8fa388c1415929d201d150406613c18d2e80af9e4add02e1058424f51e015faa`.
This authorization has now been consumed.

## Observed result

Original executor PID 49955 and observer PID/process group 50741 are terminal;
the retained execution exited 0 with one boot attempt and no surviving
observer children. Both userdata ranges, 434,176 bytes total, passed install
readback. The 13-byte misc marker also passed. Fastboot sent and booted the
same 0298 image once (both OKAY, 0.611 seconds). TWRP returned after 746
seconds and the kernel banner matched. Claim-to-result time was 818.052373
seconds. No boot retry or failure rollback occurred.

The fresh, installed, postboot and restored captures independently verify
116 file records and five directory records each. All three full old log
prefixes were retained. This run added 3,007 bytes of stdout, 135 bytes of
stderr and 55,061 bytes of backboardd log. Postboot restoration dynamically
re-read the catalog; the same 434,176 userdata bytes were restored with
readback. The original desktop executable hash and fork are intact, with
postboot metadata outside its eight-byte length field preserved. Phone state
is recovery. The current postboot/post-restoration root-header SHA-256 is
`8e81a422e334b7f484a17f9af7c6e85076319f41ac9a7dcca65b0301a45453fe`.
The pretrial `42ec2e54…` header above is historical.

Current-only backboardd output attests the exact private owned-core path and
the new frontend admission path once each. It has no `refused:` or `failed`
line. The retained root bootstrap closes cleanly (ready 1, jobs 8, fence 8,
epoch 1, clean 1). The finite GPU service records 598 renewals, 27 submitted
and 27 completed jobs, shadow 344. Seventeen frontend timing windows contain
19 completed command buffers. Their `presentedDrawable` total is **zero**.
The observer's final logical panel `presents` count is **21**, versus 97 and
228 in the two prior core trials. Those runs did not have matched physical
input or optical captures; these counts cannot establish an improvement or
assign a cause to the difference.

Read-only independent review rechecked all 80 ready pins, actual captures,
current-only validation, restoration bytes, fresh kernel log and empty process
group. Terminal result SHA-256:
`facf6f7d134a5d44b303bcd20862ed6d4582f6294ff6bf170be2256d7ed33043`;
independent review SHA-256:
`c3a493e0861942889199ffa6b13150aae39ce48ecc691fef1a98d0f41d73f443`.
The new kernel log SHA-256 is
`eed579df67a69d67dca06572ba268b57b4593d7ba101a7e68e56be76906ebf3d`.
Latest storage accounting is 485,787,680,768 bytes of the 500 GB cap.

This run proves that the new desktop backend can load the new core and finish
work without losing the original installation. It does not prove that GPU
results reach the physical screen or that iOS runs smoothly. The next device
test needs matched input, surface/scanout identifiers and physical frame
observation at a verified 60 Hz baseline. The prepared 90/120 Hz panel modes
and optical A/B probe follow that baseline; they have not run in iOS.
