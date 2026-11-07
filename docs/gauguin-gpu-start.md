# A619 native MMU start and GPU access

147 physically verified the separate GPU SID0 context, retained GMU contexts,
168 ATOS checks and the native four-scalar CP aperture transport. Its full
firmware INIT/VERSION/PERF/BW/TEST/DCVS startup and autonomous runtime reset
were verified in the same trial. This establishes a baseline for starting the
GPU; it does not establish GPU commands, rendering or Metal.

Patch0148 adds a separate, default-off `sweetgpustart=1` stage after the existing
coherent147 transaction succeeds. The complete147 flag chain is required before
watchdog ownership. Existing firmware/public receipts and cold board function
bodies remain unchanged. It reuses the sole private SMMU/CSR mappings.

The order follows pinned native
[`kgsl_iommu_start` and `kgsl_iommu_set_pt`](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/kgsl_iommu.c#L1657):
HUM=2, DORA=1, barrier, same owned default TTBR0 and CONTEXTIDR=0, barrier/read
TTBR0, owned-bank TLBIALL=1, barrier, TLBSYNC=0 and bounded TLBSTATUS polling.
HUM/DORA observations retain raw values without requiring an invented equality.
The existing nonstall/HUPCF policy, GMU routes and unrelated contexts survive;
there is no cold global HALT/CR0/reset/implementation replay on running firmware.

The native [A619 legacy OOB path](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/blob/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/gpu/msm/adreno_a6xx_gmu.c#L591)
uses GPU HOST SET16 and ACK24. A stale ACK is refused before writes. Only an
accepted ACK24 is cleared; the HOST GPU request and earlier boot-slumber request
remain held for subsequent CP startup. There is no additional HFI_START message
for this HFI_USE_REG target and no IRQ enable/blanket clear.

Only after accepted OOB does the board create a disjoint16KiB Device mapping at
03d00000. It reads RBBM_STATUS and STATUS3 at byte offsets840/84c, rejecting failed
accesses/all-ones and recording other raw values without claiming GPU idleness
or execution. No core write is issued. Entry requires8s watchdog budget, every
stateful operation checks3s remaining, the CPU window is4s, TLB polling has a2s
CPU bound and OOB a100ms bound. None can cancel a nonreturning MMIO access.

Started failures quarantine all shared owners before cached diagnostics, preserve
output/mappings and issue no retry, rollback or HOST release. Successful output
requires final retained-context, firmware, fault, clock, IRQ, owner and deadline
checks. Native functions and the real engine produce the same48 writes across
six dynamic banks under host seams. Host tests and native compilation do not
qualify this stage on hardware. SQE loading, live powerup register lists, CP/RB
initialization, command completion and the iOS graphics ABI remain subsequent work.
