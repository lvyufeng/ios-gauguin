# A619 ordinary memory execution

The165 temporary device trial completed the same-boot chain from native CP
initialization through signed ZAP loading, unsecured mode and ordinary GPU
memory writes. The strict physical verifier returned0. This is command
processor memory execution and CPU readback evidence; shader execution,
rendering, general scheduling and Metal remain unqualified.

The cold DATA19 profile maps19 GPU pages while preserving131 GMU pages and
performing171 ATOS checks. Its extra GPU page starts at IOVA`0xfc018000`, backed
by owner offset`0xb8000`. The CPU reservation is16KiB; only its first4KiB is GPU
mapped, with user read/write, non-cacheable and no-execute attributes. The
other three4KiB slots remain holes. Live guards check all16KiB of actual page
tables, the sole unmanaged non-cacheable CPU aliases, routes and faults.
ATOS results alone are not a permission proof.

CP initialization completed at device shadow15. Signed ZAP INIT/MEM/AUTH
returned the required full64-bit zeros, with all1984 code bytes copied and
compared. Native SET_SECURE_MODE0 and WHERE_AM_I then completed at shadow20.
The write stage appended exactly two native CP_MEM_WRITE packets and one
WHERE_AM_I packet,11 words total, taking the device shadow to31. Its first
fence check succeeded, AO busy bit23 was clear, and decoded GPU faults and the
final guard reason were zero.

Before submission, all1024 data words were zero. After completion, the CPU
read`0x47504431` at the first word and`0x47504432` at the last. All1022 middle
words remained zero, and all31 submitted ring words matched. The production
callbacks allow no CPU data store after cold preparation: the new data values
come from GPU execution. The raw records include the actual cached CPU
samples, full comparison counts, command words and guard observations.

The trial used the qualified local kernel`gauguin.of4pxl` and unique token
`gwrt-0165-a1`, then automatically returned to TWRP after131 seconds. Raw text
matches the immutable binary decode. The runtime verifier, complete input
catalog and separate independent reviews are under`research/tmp/dsh-0165/`;
these device artifacts stay outside Git. The build qualifier retains its
hardware flags as false because it qualifies build/source inputs; the separate
physical report establishes this bounded execution result.

The165 cached-record change kept the existing watchdog policy. ZAP entry was
observed12.6979 seconds after the watchdog arm, compared with13.1299 seconds
in164. The ordinary write diagnostic, including full page-table/alias checks
around callbacks and full page comparisons, took3.1987 seconds. These are
single-run bring-up timings, not GPU throughput or UI benchmarks. Service and
framebuffer logs provide no human observation of touch, smoothness or refresh
rate during this unattended test.

The166 diagnostic below adds native indirect command-buffer fetching.
Further work needs GPU completion fences, shader/render execution and the
iOS acceleration interface, each with separate physical evidence. The proven
mode3 path and its signed/unsecured prerequisites remain preserved.

## Fixed indirect-buffer execution (166 verified)

Mode4 adds a separate continuation at native shadow20, replacing mode3's
ordinary write stage for this trial. The exact mode is frozen when DATA19 is
created, so changing3 to4 later cannot acquire the new continuation. Mode3's
engine/provider, earlier modes, cold mappings and watchdog policy are retained.

The IB occupies32 bytes at offset`0x4000` of the existing32KiB user read-only,
non-executable ring mapping, at IOVA`0xfc00c000`. It contains two MEM_WRITE
packets, targeting the same first/last ordinary data words with distinct
values`0x47494231`/`0x47494232`. The direct ring appends seven words: the native
four-word CP_INDIRECT_BUFFER_PFE packet, with size8 and IB_PRIV clear, followed
by WHERE_AM_I. The final expected device shadow is27. CPU callbacks can write
only those eight indirect and seven direct words. Before submission, the IB
is copied, compared and ordered; after completion, all1024 data words,
27 submitted ring words and eight IB words must match. Failure quarantines
shared ownership before cached diagnostics; no retry or cleanup is performed.

The host oracle executes42 unchanged functions from the pinned gauguin Android
kernel plus the exact normal-user three-statement IB builder block in a typed
wrapper. This does not execute the entire KGSL user submission function. Five
packet/fence/idle traces match the port exactly. The actual board fixture also
runs signed/unsecured prerequisites while the secure CPU page is inaccessible.
These checks and ARM64 object compilation are source/model evidence.

The166 local kernel`gauguin.MVqkS8` completed one temporary physical trial
with token`gwrt-0166-a1`. The separate strict physical verifier returned0.
Signed loading and native shadow20 preceded the IB stage. All eight indirect
words and seven direct words matched; device shadow27 and idle status were
observed. CPU reads before submission were zero, and after submission the
actual first/last values were`0x47494231`/`0x47494232`. All1022 middle words
remained zero. Decoded GPU faults and the final guard reason were zero.
The full DATA19/171 ATOS, page-table and sole NC-alias checks remained active.

The phone returned to TWRP automatically after131 seconds. Raw text matches
the immutable binary decode with zero console framing recoveries. The full
physical report is`research/tmp/dsh-0166/hardware-full-verification.json`,
SHA256`13b8a9c50e350ad0e0c2e883645cc163784d331d61c8191826e677db1553d55c`.
An independent review rehashed all19 complete report inputs and15 wrapper
inputs, checked the actual values and independently decoded the binary log.
The source-only kernel qualification retains its hardware flags as false;
the physical execution evidence is a separate immutable report.

The guarded IB stage took3.3753 seconds, including full CPU guards and page
comparisons. It is not a throughput or UI benchmark. Service logs and five
framebuffer swaps provide no human observation of touch, smoothness or refresh
rate. This166 result establishes fixed reduced-privilege IB command fetching and
indirect ordinary memory writes. It provides no shader, EOP, rendering, general
scheduling, Metal or iOS acceleration proof; the separate167 result follows.

## No-IRQ completion event (167 verified)

Mode5 extends the fixed indirect command test with the native
CP_EVENT_WRITE/CACHE_FLUSH_TS completion protocol. The event follows the IB
and writes a distinct marker to ordinary DATA+4; WHERE_AM_I follows it. The
direct append is12 words, ending at device shadow32. The eight-word IB writes
`0x47455032`/`0x47455033` to the page edges, while the event writes`0x47455031`
to the completion word. Existing mappings and mode3/mode4 providers are retained.
The exact cold mode is frozen before DATA19 is created.

Ring progress and an idle GPU cannot substitute for observing the completion
word. The new engine separately polls its NC CPU alias, with at most1024
reads and the unchanged2-second phase/4-second total guards, then compares
all1024 data words,32 submitted ring words and eight indirect words. Only the
IB and direct command slots admit CPU stores. Failure quarantines shared
ownership before diagnostics. The event requests no interrupt and makes no
protected-mode override.

The event value4 is defined in the pinned kernel's
[a3xx_reg.h](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/a3xx_reg.h),
which its A6xx ring submission code includes. The host oracle executes43
unchanged native functions plus the exact EOP statement block; destination
macros and deferred event publication are typed model seams. Only the requested
NULL-context/noninternal/no-IRQ branch is qualified. An extra test of the
native IRQ branch exposed its signed`1 << 31` under UBSan; that failed result
is retained and that branch remains unqualified. Native bytes and sanitizer
settings were preserved.

The167 source has passed all81 host test files,495 new actual board cases,
five exact native packet/fence/idle/event-read traces and four ARM64 TU builds.
These establish source/model behavior. The complete local kernel and the
separate physical trial described below now provide bounded event-marker
evidence; shader/rendering work remains necessary.


The167 local kernel `gauguin.NQU6PL` passed its first complete build and strict
qualification, then one temporary physical boot with token `gwrt-0167-a1`.
After signed loading and native shadow20, the GPU fetched all eight indirect
words, executed both ordinary-page writes and the no-IRQ event, then reached
shadow32 with idle status and zero decoded faults. The CPU's separate EOP
poll succeeded on its first read with `0x47455031` at IOVA `0xfc018004`.

All1024 words were zero before submission. Afterward the first/last words
were `0x47455032`/`0x47455033`, the EOP word held `0x47455031`, and all1021
other words remained zero. All32 submitted ring words and eight IB words
matched. Actual cached sample mask `0x3f` covered all three before/after
values. The production callbacks permit no CPU DATA stores. The unchanged
DATA19/171 ATOS, complete page-table, sole NC-alias, monotonic deadline and
fault checks remained active; the final guard reason was zero.

The phone automatically returned to TWRP after131 seconds. The strict physical
reader returned0, and an independent review rehashed all19 complete report
inputs and15 wrapper inputs, checked actual commands/data/timestamp and
independently decoded the immutable binary log. There were zero console
framing recoveries. The physical report is
`research/tmp/dsh-0167/hardware-full-verification.json`, SHA256
`4b377a953fbff3d468acabb9fe1fa13a8204395c7a86e4ae422bc49c984e1397`.
The source-only kernel qualification keeps every hardware flag false; this
separate physical report establishes the bounded event execution result.

The guarded stage took3.4259 seconds, leaving0.5741 seconds of its4-second
budget. This includes CPU guards and full comparisons and is not a GPU
throughput or UI benchmark. The test establishes fixed native IB memory
execution plus actual no-IRQ CACHE_FLUSH_TS completion-word observation.
It does not establish shader execution, rendering, general scheduling, Metal,
high refresh or human-observed UI performance. The next step is to bind and
execute a minimal shader workload from a primary A6xx implementation before
working on rendering and the iOS acceleration interface.
