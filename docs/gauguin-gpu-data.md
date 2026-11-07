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

The next execution capability is native indirect command-buffer fetching,
followed by shader/render work and the iOS acceleration interface. New work
must retain this proven mode3 path and its raw evidence, preserve signed and
unsecured prerequisites, and obtain separate physical evidence for each new
capability.
