# A619 core configuration contract

The pure `ggc` engine in patch0150 prepares native core configuration and the
powerup register list. Board/coordinator activation is subsequent work; merely
linking this module starts no hardware operation. The separate149 SQE cold-stage
and148 physical MMU/OOB baseline remain prerequisites for that integration.

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
Board integration must reuse existing core/MISC/CSR/AO aliases and map only the
six missing pages after OOB. These pages do not overlap the SMMU03d40000+10000
or TCM03d6c000+c000 aliases. The typed whitelist rejects CP doorbells/SQE start,
unowned GMU HOST controls and arbitrary register addresses.

Callbacks must enforce live same-boot SQE, firmware, context, route, owner, fault,
IRQ, clock and CPU/watchdog budgets. BUS must reject stale GPU ACK before its
first store. The pure engine is one-shot, preserves public output on failure and
never retries or performs rollback. Board failures must quarantine shared owners
before logging private cached diagnostics. Guards cannot cancel a hung MMIO.

Host validation uses exact unmodified native function bodies and actual target
tables, with typed OS/MMIO seams and the explicit runtime-preemption-disabled
scope. Four initial-register patterns exercise HWCG skip, both RMW paths and
live restore capture, including opaque all-ones values. Port/native ordered
register operations and restore-list bytes must agree. Host tests also cover
MMIO/map/parent/barrier/memory/phase failures and output/once-state invariants.
The native reference uses its pinned KBUILD base warnings plus Werror; the new
driver stays under Wall/Wextra/Werror. These proofs do not qualify hardware.

SQE halt release, ringbuffer programming, native ME_INIT plus WHERE_AM_I,
fenced doorbell/completion, secure ZAP loading and unsecured-mode transition,
interrupt-driven command scheduling and the iOS graphics/Metal ABI still follow.
