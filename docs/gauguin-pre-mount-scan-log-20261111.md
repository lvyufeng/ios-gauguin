# Pre-mount scan evidence in one reserved block, 0260

The 0259 desktop scan images share the writable HFS startup profile. Their
ordinary console logger also depends on enabling ordinary UFS writes.
The new diagnostic path can collect a scan result before mounting any
filesystem and store it in one existing reserved diagnostic slot. It does
not depend on installing or running the pending desktop root changes.

DSH read the partition geometry from the connected gauguin in recovery.
The userdata partition begins at LBA 2,887,680 and spans 28,056,571 blocks,
using 4096-byte UFS sectors. The diagnostic record uses the last existing
mark slot at absolute LBA 30,943,225, partition-relative bytes
114,915,512,320 through 114,915,516,415. The normal console ring starts
at the next block. The 0240 HFS plan covers the first 16 GiB and its 33
write runs end by byte 15,673,884,672. The diagnostic slot is outside the
volume and every run.

Patch `0218-gauguin-pre-mount-scan-log.patch` adds a default-off
`sweetscanlog=1` branch before root mount. A diagnostic profile supplies
one `sweetscan=1..3` selector and a nonzero `sweetscanid`, with
`ufsrw=0` and `rootrw=0`. It rejects an alternate partition, existing UFS
ownership, conflicting write flags or unexpected partition geometry.
The diagnostic UFS initialization exits before registering a BSD disk,
starting the normal logger, or initializing the peripherals attached to
the ordinary root path. Its writer submits a single WRITE(10) to the
fixed mark slot and flushes the device cache after a successful write.
DMA ownership and timeout poisoning remain in the existing transport.
The diagnostic returns via the quick reboot path with filesystem sync
disabled, including on an error. Platform reboot is still untested in
this path.

The scan worker publishes an immutable snapshot. The pre-mount caller
waits up to 80 sleeps of 25 ms for it. The versioned, zero-padded record
contains the run ID at both ends, diagnostic stage, status, clock words
and raw scan statistics. A timed-out worker is recorded as incomplete.
The ordinary persistent console ring and root storage startup use their
existing paths.

## Qualification

Code commit `c95d2ca671f999cfcbb77dbf4fa3df106e9981f2` on
`codex/gauguin-scan-log-tail-20261111` in
`research/tmp/gauguin-build255-worktree-20261111`.
Private evidence is in `research/tmp/dsh-scanlog-0260` in that tree.

DSH verified the actual unmounted recovery partition geometry, then replayed
0218 strictly onto the qualified 0258 source. The four edited integration
inputs match the 0259 CI archive. Source SHA256
`7941d50f5cb60e807caf4b2998651d2f2ee53540a0d56c2ae3a1b046919d61a9`,
5,339 files and five changed paths. The actual writer test checked the
single CDB, byte range, format, zero padding, ownership and timeout path.
The scan and four UFS/mark regressions passed. UFS, scan board and BSD init
compiled with the native gauguin ARM64 recipe. The original patch context
blank lines were preserved. The added source was checked separately for
trailing whitespace.

DSH dispatchers 58347 and 59348 exited 0 with 4 and 21 unchanged pins.
The second stage ran in 12.392 seconds. The independent geometry, archive
and pending-delta audit SHA256 is
`2e8438ff12ebc8d7cffcf2256cb8bfde3ebf14c8a54ef9a9bde622f864173416`.

Next build and qualify a concrete temporary image and inspect the original
mark block before any overwrite. Obtain the separate write confirmation
for that exact 4 KiB diagnostic block, then check the recovered record and
read back the pending 0240 old blocks. The 0240 installation itself still
needs its own approval and paired 0239 trial. This milestone ran no boot
and wrote no phone storage.
