# Desktop Metal startup ordering

The first physical 0250 kernel with the approved 0277 desktop root does not
reach the desktop. Both installation and capture checks pass: 44 delta runs
read back, 27 installed files and four directory permissions match, and all
three old log prefixes remain intact. The phone automatically returns to TWRP
after 745 seconds. The user reports continuous log output and no desktop.

The root bootstrap exits at its first GPU open because the HakiosGPU service
does not yet exist. Backboardd loads the desktop frontend and passes its
20H392 admission checks, but its first-device wait times out after
35,001,062,136 ns and 344 attempts. Only later does the kernel publish its
runtime GPU service. The service then completes its 600-second window with
598 renewals and zero submissions. No root arm, clean handoff or desktop GPU
work occurs. This is evidence of premature discovery, not a GPU rendering or
frame-rate result. The strict activity gate correctly leaves the trial failed.

The source correction gives both startup paths a bounded 180-second readiness
wait. They retry every 100 ms and return as soon as an open succeeds. The root
bootstrap's separate 30-second GPU-work alarm starts after that open. It is
not consumed while waiting for kernel publication. Clock failure/reversal,
sleep failure, frozen clocks and late acquired handles retain explicit failure
and cleanup behavior. Core shaders, the kernel, authorization and clean owner
handoff are unchanged. The old diagnostic profile and binaries are retained.

DSH 20697 builds and signs the frontend and bootstrap in 8.292 seconds with
30 unchanged stage pins. Production wait controls pass 2,913 assertions under
ASAN/UBSAN. The actual C++ startup callbacks and acquisition/alarm prefix pass
virtual-time checks, including service publication after 60 seconds and cleanup
after failed clocks or late acquisition. The old 35-second helper returns the
expected functional failure code 42 for the same delayed publication; the new
helper returns 0. These tests produce no hardware evidence.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Desktop frontend | 428,400 | 0a1b55bb20a29661de40099e58e45ec695ffb0bf78e132a9d10985450e868550 |
| Root bootstrap | 116,048 | 7b922e66fbeb862504ea8ac01fd73681382e4718b7b1325e405fbecc25f6b6e0 |

The frontend's 343 imports are unchanged. The bootstrap adds `___error` and
`_nanosleep`, both already imported with the same libSystem binding by the
previous frontend. The pair's combined import set is unchanged, retaining the
previous static 20H392 resolution evidence. Bundle Info.plist and CodeResources
are byte-identical to the installed desktop bundle. Codex independently
rehashes stage inputs/logs and native receipt pins and compares import sets.
The binaries were built from the pinned working source and reviewed before
the subsequent source commit. Private evidence is under this worktree's
research/tmp/dsh-startup-0279-wait.

This correction is not installed or phone-qualified. Installation requires a
fresh post-0277 backup and scoped delta, separate write authorization and one
temporary 0250 boot. Acceptance must first show root readiness, eight verified
jobs, clean owner release and subsequent compositor work. Desktop image
correctness, touch latency, sustained frame rate, high refresh and the full
daily-phone objective remain open.

Source correction: [ba679b0](https://github.com/lvyufeng/ios-gauguin/commit/ba679b0445b5f2cbe90eb02cc921ec70c0fa90ba), on `codex/gauguin-metal-startup-order-20261111`.

The fresh complete post-0277 backup has SHA256
`da5707648ddae41f56c5dee634b31c599e95a934d6490fc16c2a7ee9055b7c78`.
The new proposal updates only the two executables, preserving all 531 task/cache
entries, bundle Info/seal, directory ownership and complete logs. It comprises
276 blocks, 1,130,496 bytes in 31 runs, plan SHA256
`3c4719e0f581c1a3a1cee5061856b11aca8973f260b3c971a529a3ec6d19e41d`.
Local HFS fsck and 102 writer failure/rollback controls pass. Two final-record
attempts retain stale path errors; the corrected review preserves those records,
prechecks provenance paths and completes the full image diff and all current
old device-range checks. Its 80 input pins are independently rehashed. The
recovery misc block is zero again, so another separately approved 13-byte
recovery marker is required for the next automatic-return trial. No new root
write or boot is performed while preparing this proposal.
