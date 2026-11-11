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

At the source-only stage, this correction is not installed or phone-qualified. Installation requires a
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

## Installed trial 0282: router rejects the updated bootstrap

The user subsequently authorizes both 0281 writes and the paired temporary
0250 boot. The 31 root ranges read back successfully, the 13-byte misc marker
is verified, and the phone automatically returns to TWRP after 745 seconds.
The native service records 598 renewals but zero submissions during its
600-second window. This trial does not establish a working UI or GPU desktop.

The initial post-review stops because root stdout does not grow. All 27 files
were nevertheless captured. A separate offline review confirms 24 unchanged
static files, four directory ownership/mode records and all three complete old
log prefixes, without replacing the failed receipt. The new root stderr is
exactly `GAUGUIN ROUTER247 FAIL phase=target code=0`. There is no new root
bootstrap stdout. Backboardd times out after 180,001,053,593 ns and 1,777 attempts.

The installed router still embeds the former bootstrap's 115,968-byte size and
SHA256 `2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c`.
The updated bootstrap is 116,048 bytes with SHA256 `7b922e66fbeb862504ea8ac01fd73681382e4718b7b1325e405fbecc25f6b6e0`.
The router receipt, generated target header and captured installed router
agree. Its target check therefore rejects the new executable before SETEXEC;
the new root readiness wait never runs. Updating the bootstrap without its
hash-bound consumer was an integration omission in 0281.

DSH 38118 independently audits the actual authorization, successful writes,
single boot and failed evidence, then verifies the full capture and target
mismatch. Both review jobs pass in 0.452 seconds with 19 unchanged stage pins.
Private evidence remains under research/tmp/dsh-startup-execute-0282.

The next correction must rebuild the router for the installed bootstrap and
check the actual target tuple as part of package validation. Preserve the
0250 kernel, core, shaders and already-installed readiness executables. No new
write is authorized by the spent 0281 consent, and no frame-rate, high-refresh
or daily-use qualification follows from this failed trial.

## Router correction and minimal local candidate

Source [bf43185](https://github.com/lvyufeng/ios-gauguin/commit/bf43185afe998161902b0ac484be58c3d4fe6340)
rebuilds the router for the installed readiness bootstrap. It also adds a
reusable check of the router and both actual target tuples. Production router
code is exercised with the real 0282 target binaries: the former binding is
rejected before spawn, and the new binding reaches modeled SETEXEC. The original
29 router cases and four malformed package controls pass. Runtime C and the
native import/load listings remain unchanged. These are host tests, rather than
evidence of a running GPU desktop.

The new signed router is still 69,536 bytes, allowing its data fork to be
replaced in a local image without mounting HFS or changing filesystem metadata.
A fresh complete 16 GiB device snapshot verifies all 16,384 chunk digests and
all 27 captured files. The proposed final image changes four 4 KiB blocks
(16,384 bytes), all within the router's logical file. The catalog, allocation
map, volume headers, four retained directories, all 531 cached tasks and 26
other captured files remain intact. Actual candidate target compatibility and
read-only HFS fsck pass. The proposal is not an installation.

The existing rollback writer receives explicit root-header pre/post checks
because the volume header is absent from this data-only delta. Its 117 fake-IO
checks and partial-write failure controls at all four concrete runs pass.
There is no real approval file or new device write. DSH 41950 independently
reviews the full-byte scope, final target bindings and all four fresh device
old ranges in 77.573 seconds with 65 unchanged pins. Codex subsequently rehashes
all six current stage input/log sets and the 59 readiness pins.

The concrete proposal has plan SHA256
`369bbd2b791007d327e9b663de3fa59cd8347a855e44aa910a831b58ddac00b0`.
The fresh backup is `deb89f0f4b0a0d30dcefe13a3479d919dcdc8cdd25cf9d9fbe92000508b2c4aa`
and final candidate is `da1884b1dc98b4fb954bd9e408f582a771eec5f1dc72f4dffe3ce33ca91a11d6`.
The zero misc block is backed up separately; another 13-byte recovery marker
will be needed for the paired temporary boot. These new writes require their
own consent. Current project accounting is 425.8 GB, below the 500 GB cap.
