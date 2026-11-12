# C4 desktop Metal one-boot device trial

This trial is prepared and **has not run**. It would test the ordered desktop
frontend with the privately installed ownership core. Its log acceptance means
the new backend loaded and completed GPU work. Displayed pixels, physical FPS,
90/120 Hz and smooth daily use require separate evidence.

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

## Proposed one-shot actions

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

The runner refuses absent individual approval before an execution claim or
device IO. A backend result requires a new backboardd attestation of the
private core path, the ordered frontend path, positive completed command
buffers, a clean retained root bootstrap and completed GPU service work.
Return to TWRP and original-bundle restoration are checked independently.
Physical pixels and refresh cadence remain open. The two earlier boot
approvals were consumed; this distinct write/boot scope requires a new
explicit decision.
