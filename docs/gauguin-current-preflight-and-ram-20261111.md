# Current recovery preflight and remaining RAM ownership, 0251

The phone is currently reachable in TWRP. A new read-only check matches every
old block of the pending 0240 proposal. A separate fresh memory capture agrees
with the earlier 0191 inventory and identifies the next concrete obstacle to
using more lower RAM. Neither action writes userdata, boots a kernel or grants
write permission. The completed [0250 image](gauguin-desktop-boot-profile-20261111.md)
and its memory configuration remain unchanged.

## Current proposal readiness

DSH runs a fixed read-only wrapper around the previously reviewed RecoveryIO.
Its command allowlist contains only device/property/partition/mount/holder/help
queries and raw reads. Device write, sync/flush and reboot operations are
unavailable in the wrapper. Each query has a bounded timeout and the reader a
finite overall deadline.

Observed: one recovery device, product gauguin, userdata partition
114,919,714,816 bytes, unmounted, with no holders. The current header matches
the reviewed backup header. All 33 ranges / 194 old blocks / 794,624 bytes
match plan SHA256:
9d943e79086c990652000ccbd1088411e6d51f2a1b8d83cc5d7319facffdbb3d.
The header is identical before and after the check. There are 42 allowed
queries including 35 raw reads, 802,816 raw block bytes including repeated
header reads. This checks the proposal's old ranges; it is not a fresh hash
of the whole 16 GiB volume.

The original proposal, ready receipt and historical preflight remain untouched.
The new receipt is separate. There is still no genuine 0240 reply or approval,
apply or trial state. A future authorized writer must recheck its preconditions
again immediately before writing; this observation is not permission or a
replacement for that check.

## Fresh RAM evidence

A second DSH stage reads /proc/iomem, /proc/meminfo and /sys/firmware/fdt,
with the userdata header read before and after. It makes 12 allowed queries
and reads another 8,192 raw userdata bytes. The root header stays identical.
Raw captures remain private because FDT/device data can contain identifiers.

Memory banks, fixed reservations, FDT reservation header and Linux System RAM
ranges equal the prior 0191 inventory. Current recovery MemTotal is
7,742,423,040 bytes (about 7.21 GiB). That is Linux's reported total, not proof
that the iOS VM manages the same pages.

The 0250 image still describes [0x100000000,0x27ff00000), 6,441,402,368 bytes,
with the top 1 MiB retained for the panic log. This range remains inside
Linux System RAM and does not overlap any fixed/FDT-header reservation or
declared dynamic allocation range. This source/range result is not a new
physical pressure or DMA test.

Intersecting Linux System RAM below that base, excluding every fixed
reservation, then aligning inward to 16 KiB leaves seven address candidates:

| Half-open physical interval | Status |
| --- | --- |
| [0x80880000,0x808fc000) | Requires runtime ownership reconciliation |
| [0x82900000,0x86000000) | Requires runtime ownership reconciliation |
| [0x8b718000,0x8b800000) | Requires runtime ownership reconciliation |
| [0x9b000000,0xa0000000) | Requires runtime ownership reconciliation |
| [0xa2400000,0xac000000) | Requires runtime ownership reconciliation |
| [0xad000000,0xbbb00000) | Requires runtime ownership reconciliation |
| [0xc7b00000,0x100000000) | Requires runtime ownership reconciliation |

Total: 91,417 pages / 1,497,776,128 bytes, about 1.395 GiB. These are address-map
candidates, not an added-memory whitelist or measured allocatable capacity.

Six dynamic pools have declared allocation ranges overlapping those candidates:
qseecom, qseecom_ta, secure_display, mem_dump, adsp and linux,cma. Their
declared individual sizes are 20, 16, 140, 40, 8 and 32 MiB. These sizes do
not establish current placement, permanent ownership or a reclaimable amount.
The broad allocation ranges collectively cover every candidate page. Thus
these static inputs alone qualify **zero additional lower pages**. This does
not mean no lower RAM can be recovered; the missing evidence is which actual
pages are owned at the iOS boot handoff and when those owners release them.

Linux recovery's runtime allocator is not the allocator state of a later
bootloader handoff. A fixed-carveout-only subtraction, or subtracting the six
pool sizes from a total, cannot produce a safe iOS allocation map.

### Recovery allocation follow-up, 0264

Two read-only DSH captures measured TWRP `CmaTotal` at 262,144 KiB and
`CmaFree` at 173,796 KiB. The 14 `/proc/iomem` reserved ranges remained
available without per-pool names. The current `dmesg` buffer returned no
matching early allocation records, and the existing CMA and memblock
debug paths returned exit 1. The Xiaomi source emits dynamic placement at
debug log level. The observed aggregate CMA total supplies no base address
for any of the six dynamic pools. The original ABL handoff consumer is
still needed to advance the lower-memory qualification.
[Xiaomi reserved-memory allocator](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/of/of_reserved_mem.c#L94).

Evidence is under `research/tmp/dsh-memory-0264-recovery-pools`. DSH
dispatchers 70503 and 70634 completed with exit 0 and four unchanged pins
each. The launcher sessions were reaped. No raw dmesg dump was saved and
the capture used no device write, reboot or mount change.

The saved recovery FDT also identifies explicit Linux consumers for five
of the six dynamic pools. QSEECom and ION heap 27 reference `qseecom_region`.
ION heaps 19 and 10 reference `qseecom_ta_region` and
`secure_display_region`, respectively. The memory-dump node references
`mem_dump_region`, and the ADSP RPC memory node references `adsp_region`.
The sixth pool, `linux,cma`, carries the default CMA marker. All six are
declared reusable `shared-dma-pool` regions. These references identify
the subsystems to audit when checking live ownership and release.
DSH PID 78376 verified the six pool nodes and named references from the
saved DTB under six pinned inputs. This captures the recovery FDT's
declarations. Actual ABL handoff addresses remain to be measured.

## Implementation implications and order

The current loader passes one physBase/memSize interval, and the selected
XNU phystokv helpers check against gPhysBase and real_phys_size. Increasing
memSize only extends the upper end; it does not admit these lower pages.
Changing physBase also affects translation and bootstrap placement. Keep the
working six-GiB image as the control.

After the existing 0240 paired trial and correct desktop acceptance:

1. Capture a versioned loader-handoff owner map: actual firmware allocations,
   FDT reservations and live splash/PAS/GMU/loader/initrd/DTB/panic ownership,
   with source, bounds and release conditions.
2. Teach bootstrap mappings and VM admission to preserve those holes and
   owned pages at 16 KiB granularity. This needs an explicit memory model;
   changing a displayed size or the single interval is insufficient.
3. Compare native boot/VM/max/actual/sane counters with that map, then test
   allocated-page integrity, pressure and DMA in admitted ranges on the phone.
4. Qualify the recoverable lower ranges and long-session behavior while
   retaining GPU, storage and peripheral regressions.

This is a concrete remaining RAM task, not an expansion implemented here.
Physical 90/120 Hz, power, radios/storage and daily-phone acceptance remain
part of the full active objective.

## Execution and review

Both stages are executed by DSH with full access using the pinned dispatcher.

| Stage | PID | Exit | Inputs | Elapsed |
| --- | ---: | ---: | ---: | ---: |
| Current 0240 old-range check | 7281 | 0 | 40 unchanged pins | 2.570 s |
| Fresh memory capture/analysis | 17322 | 0 | 12 unchanged pins | 0.965 s |

The memory analysis reuses the prior primary-DTB/Linux parser. Codex verifies
the stage profiles, input and log hashes, capture hashes, proposal bytes and
0250 image, then independently enumerates the candidate pages rather than
reusing the interval-subtraction algorithm. All 91,417 pages and seven ranges
agree, and every candidate intersects an unresolved dynamic allocation range.

Private evidence: research/tmp/dsh-preflight-0251-device in the active0250
worktree. review251-v1.json SHA256:
cf6d06a175f2e05abff140c63b2898acbbb650aafc68372628abf4400ece63ef.

No new kernel/frontend/build/image, root write, mount/unmount, sync/flush,
reboot, CI run or push occurred. The user's original mkadt.py diff is
preserved. No raw dump or identifier is committed.
