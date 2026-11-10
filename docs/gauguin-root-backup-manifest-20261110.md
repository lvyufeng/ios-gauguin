# Complete root backups with device-side chunk verification

The 0240 raw-stream backup reached its 900-second transfer deadline and left
an unqualified partial clone. Its failed result and partial file are retained.
The replacement reads every byte of the 16 GiB root prefix on the phone and
returns per-MiB and whole-prefix SHA-256 digests. The Mac checks all 16,384 local
chunks, fetches only mismatches and reconstructs a separate complete clone.
Python's independent whole-file SHA must match the complete device digest.
Matching baseline bytes are verified rather than presumed unchanged.

`tools/root-backup-scan.c` is a static ARM64 recovery program with a fixed
userdata path, fixed 114,919,714,816-byte partition identity and maximum
17,179,869,184-byte prefix. It opens the device read-only, checks BLKGETSIZE64,
uses bounded pread64 calls, and writes only the digest protocol to stdout.
There is no block-writing syscall. Its syscall/ioctl definitions were checked
against the primary Linux [arm64 syscall table](https://github.com/torvalds/linux/blob/v4.19/include/uapi/asm-generic/unistd.h)
and [block ioctl definitions](https://github.com/torvalds/linux/blob/v4.19/include/uapi/linux/fs.h).
The native helper requires the SHA2 CPU extension, verified on this phone.
An optional `--selftest` reads only the first 8 MiB.

The helper is deployed only to a verified recovery RAM filesystem and its exact
binary hash is checked before execution. It has no dynamic linker/library.
Its 4,312-byte ELF SHA-256 is
`cb30d65fff67e4d427c62c309d987272afb6ed0b98ff930dd2748b8ac130e460`.
DSH ran 83 host SHA vectors, bounded reconstruction and corruption/budget
controls under sanitizers, then compared the native recovery helper's 8 MiB
result against independent fresh raw reads. No userdata write or reboot is
part of this process.

`tools/root_backup_manifest.py` rejects missing/extra protocol bytes, incorrect
geometry, changed device chunks, short reads and excessive local changes.
Each fetched group is verified completely before any of its bytes are written
to the local clone. A 1 GiB COW change budget and 4 GiB free-space reserve bound
local storage use. The clone is not qualified until every chunk and the final
whole-file digest pass. Root header, unmounted state, partition identity and
the current 22 captured files are also checked. A previous unqualified partial
file may serve as a clone seed because every resulting chunk and the final
digest are verified; the seed itself gains no qualification.

Actual 0240 backup-v2 completes in 276.047960 seconds. The helper reads the
entire 16 GiB prefix; 447 MiB in 249 changed groups crosses USB. Every one of
16,384 chunks and the whole volume match. The resulting separate backup is
read-only and has SHA-256
`2b8fab2f297533bfe08b6a3b9e8813d59a8b9f3e0c36ee6a61aad5ea8ad3d1a9`.
The seed is unchanged; userdata writes and reboots are zero. This is a complete
current root-prefix backup, not a backup of all 114 GiB of userdata or of the
other phone partitions. Their existing backups remain separate.

Private build/test, RAM selftest, raw-failure and full reconstruction receipts
are under the 0240 worktree's `research/tmp/dsh-shared-0240-ca-output/` directory.
Device contents, serial numbers, digest manifests and backup images stay out
of git. The host test accepts a locally built host scanner executable as its
argument; its synthetic data is not phone evidence.
