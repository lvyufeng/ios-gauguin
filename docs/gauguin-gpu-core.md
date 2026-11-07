# A619 core configuration contract

The pure `ggc` engine in patch0150 prepares native core configuration and the
powerup register list. Patch0151 supplies its live board adapter and coordinator
entry behind the existing default-off `sweetgpustart=1` flag. The coherent149
SQE cold-stage and148 physical MMU/OOB baseline remain prerequisites. Linking
the module alone starts no hardware operation.

Target policy is pinned to native commit
`19b63c8192b1c9b7c4d931d7d3be92024bc2d778` and the retained actual FDT:
chip06010900,512KiB GMEM, highest-bank-bit14, minimum access32 and UBWC2.
The selected quirk properties are HFI_USE_REG and SECVID_SET_ONCE; no SOC HW
revision child overrides them. A619 supports preemption and lacks APRIV/LM.
This initial mode deliberately leaves native runtime preemption disabled,
pending proper normal/secure preemption allocation. Target capability is retained.

The engine first deasserts GBIF at native DWORD offset3c45, then asks its board
adapter to run the existing MMU/GPU OOB stage exactly once. It validates the
returned context identity, TLB busy bit, accepted/cleared ACK and retained HOST
request. Only afterward may the adapter expose the additional register pages.
The subsequent order is native64-bit mode, GMU/core HWCG, target VBIF/UCHE/ROQ/
mempool/NC/busy-counter configuration,32 protection spans and live register capture.
No secure-mode bypass or extra HOST release is introduced.

HWCG always programs the four GMU clock controls before reading the current
RBBM clock control. The native already-enabled case skips63 HWCG table writes
and the SP/top-level clock changes. Otherwise SP clock updates preserve unrelated
bits through actual reads. Counter selectors also use native read/modify/write
semantics. Fixed core register writes do not gain invented equality checks.
Opaque live register values, including all-ones, are preserved in the restore list.

The restore list captures66 actual current registers, with a16-byte lock header,
132 data DWORDs and dynamic-list offset72 DWORDs. A private, zeroed4KiB NC region
is required. The engine publishes the132 captured register/value words, completes
a barrier, publishes the length/offset header last, completes another barrier and
checks the complete4KiB region. The544-byte used list and unused zero tail must
match. This stages data; it does not start CP execution.

Native register arguments are DWORD offsets. The exact union of required16KiB
physical-page offsets from03d00000 is:
`0,c000,20000,24000,28000,2c000,3c000,68000,7c000,8c000`.
The board adapter reuses existing core/MISC/CSR/AO aliases and maps only the
six missing pages after OOB. These pages do not overlap the SMMU03d40000+10000
or TCM03d6c000+c000 aliases. The typed whitelist rejects CP doorbells/SQE start,
unowned GMU HOST controls and arbitrary register addresses.

Callbacks must enforce live same-boot SQE, firmware, context, route, owner, fault,
IRQ, clock and CPU/watchdog budgets. BUS must reject stale GPU ACK before its
first store. The pure engine is one-shot, preserves public output on failure and
never retries or performs rollback. Board failures must quarantine shared owners
before logging private cached diagnostics. Guards cannot cancel a hung MMIO.

The151 adapter checks13 seconds of watchdog budget at entry, sets an8-second
total CPU deadline and a4-second deadline per phase, and retains the existing
GGX4-second total/2-second TLB/100ms OOB bounds. It authenticates the same SQE
view again before the first store. Each guard verifies the accepted firmware
transactions, clocks/IRQs/reset, GPU/GMU contexts and routes, owner and complete
16KiB NC register-list page attributes/physical endpoints. Before GBIF, the old
GGX stage must be idle with no stale GPU ACK. After its callback, it must be
ready with the same bank/ASID/root, cleared ACK, live GX and zero CONTEXTIDR.
This uses a separate live guard; the old GGX guard requires RUNNING and is not
reused after its success.

Mapping verifies Device attributes, alignment, bounds and physical endpoints;
partial diagnostics count mapping attempts, including failed returns. Every
alias stays retained. Register callbacks translate DWORD offsets exactly once,
use the whitelist and existing load/store/barrier helpers, and restrict the
register-list alias to4KiB. Started failures quarantine the core, GGX, firmware,
board and shared lease before cached diagnostics. A child failure that already
quarantined the lease does not trigger a duplicate quarantine. Successful logs
include all66 cached register/value pairs after final guards.

Host validation uses exact unmodified native function bodies and actual target
tables, with typed OS/MMIO seams and the explicit runtime-preemption-disabled
scope. Four initial-register patterns exercise HWCG skip, both RMW paths and
live restore capture, including opaque all-ones values. Port/native ordered
register operations and restore-list bytes must agree. Host tests also cover
MMIO/map/parent/barrier/memory/phase failures and output/once-state invariants.
The native reference uses its pinned KBUILD base warnings plus Werror; the new
driver stays under Wall/Wextra/Werror. These proofs do not qualify hardware.

The151 integration additionally passes160 new actual board/core/MMU cases,
retains the earlier board cases, checks406 coordinator cases and passes all69
host test files. It covers both HWCG paths, six missing mappings and invalid
aliases/attributes, live fault/route/root/IRQ/clock/SQE changes in each phase,
CPU deadlines, failed child startup, corrupted restore data and once-state.
These remain host/source/native-TU results until a full kernel and physical
trial establish the hardware stage.

SQE halt release, ringbuffer programming, native ME_INIT plus WHERE_AM_I,
fenced doorbell/completion, secure ZAP loading and unsecured-mode transition,
interrupt-driven command scheduling and the iOS graphics/Metal ABI still follow.

Patch0152 keeps the same total8s/per-phase4s/entry13s/min3s budgets and all
peripheral access guards. Only the private4KiB NC memory passes use batches
of at most64 words, with full live guards before and after each batch. Every
word is still read/compared or written with errors propagated immediately:
1024 zero checks,132 data writes, barriers and header-last publication, then
1024 final comparisons. No CP can concurrently own this retained private page.
A private zero-scan progress counter does not change the public receipt.

The board caches the first guard refusal and CPU ticks before quarantine.
Reasons1..21 identify phase, lifecycle, thread, total time, phase time, WDT,
owner, firmware, SQE, aperture, clock, IRQ, reset, fault, context, stale ACK,
NC page, parent, live GPU context, entry WDT and SQE asset, respectively.
Failure records consume cached state only after shared-owner quarantine.
No fresh MMIO is performed to format the reason/progress/time records.

The152 host model exercises every restore-phase guard and30 additional live
batch-boundary clock/deadline failures. Its190 board cases and all69 host
files pass; the four complete native R/W/list trace hashes remain identical.
Host operation profiling reduces restore-phase SMMU reads197912 ->9152 and
WDT checks8996 ->416, retaining2048 NC reads. These are operation counts,
not real-device latency measurements or proof of the151 guard failure cause.
Both changed C translation units compile under the current151 ARM64 recipe.
A full152 kernel and physical result remain required for hardware qualification.

The next CP submission must retain the native GMU keepalive vote around its
fenced WPTR write. Native code checks WRITEDROPPED0 with a posted barrier and
bounded10us retries (short100/long200), then drops that vote. For one selected
RB0 without runtime preemption, actual completion requires its shadow RPTR
at scratch offset0 to equal software WPTR, plus GMU AO busy bit23 clear.
The native initialization submits12 ME_INIT words plus3 WHERE_AM_I words
before loading ZAP; source-level ordering permits this diagnostic first step,
but the current core-only path does not release SQE or submit those commands.
