#pragma once
#include <stdint.h>

/* Identity map target: every block below this is Device (or fb Normal-NC). */
#define MAP_LIMIT	(8UL << 30)

struct mmu_info {
	uint64_t img_lo, img_hi, ttbr;
	uint64_t ram_lo, ram_hi;	/* first RAM block found in the live FDT */
	uint64_t sctlr_before, sctlr_after;
	int n_l3;
};

int mmu_enable(struct mmu_info *info);
uint64_t mmu_probe(uintptr_t va);
