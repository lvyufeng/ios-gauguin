/*
 * Milestone 3: EL1 stage-1 MMU with the 16K granule XNU uses.
 *
 * Identity map (VA == PA):
 *   - L1: one 1GB block per entry. Cover the low 64GB (SoC MMIO + low DDR
 *     bank: sweet 0x80000000, gauguin 0x80000000/0xc0000000) with an L2
 *     table. Every other RAM block (the 32MB-granule limit makes a 1GB block
 *     legal) is mapped Device, whoever the board is: on gauguin phys_base is
 *     0x180000000, on sweet 0x100000000.
 *   - L2: 2048 x 32MB blocks.
 *
 * Qualcomm XPUs fault on speculative reads of protected carve-outs (TZ,
 * hyp, modem...), so nothing is mapped cacheable except our own image:
 *   - default: Device-nGnRnE, execute-never (same as MMU off)
 *   - the 32MB block(s) holding the image get an L3 table: image pages are
 *     Normal write-back, the rest of the block stays Device
 *   - the splash framebuffer block is Normal non-cacheable (write-combining)
 */
#include <stdint.h>
#include "mmu.h"
#include "console.h"

#define PG_SHIFT	14
#define PG_SIZE		(1UL << PG_SHIFT)		/* 16K */
#define BLK_SHIFT	25
#define BLK_SIZE	(1UL << BLK_SHIFT)		/* 32MB level-2 block */
#define L1_SHIFT	30
#define L1_SIZE		(1UL << L1_SHIFT)		/* 1GB level-1 block */
#define NENT		2048

#define ATTR_DEV	0	/* MAIR attr0 = 0x00 Device-nGnRnE */
#define ATTR_WB		1	/* MAIR attr1 = 0xff Normal WB RW-alloc */
#define ATTR_NC		2	/* MAIR attr2 = 0x44 Normal non-cacheable */
#define MAIR_VAL	0x44ff00UL

#define D_BLOCK		1UL
#define D_TABLE		3UL
#define D_PAGE		3UL
#define D_ATTR(i)	((uint64_t)(i) << 2)
#define D_SH_OUTER	(2UL << 8)
#define D_SH_INNER	(3UL << 8)
#define D_AF		(1UL << 10)
#define D_PXN		(1UL << 53)
#define D_UXN		(1UL << 54)

#define DEV_FLAGS	(D_ATTR(ATTR_DEV) | D_AF | D_PXN | D_UXN)
#define WB_FLAGS	(D_ATTR(ATTR_WB) | D_SH_INNER | D_AF | D_UXN)
#define NC_FLAGS	(D_ATTR(ATTR_NC) | D_SH_OUTER | D_AF | D_PXN | D_UXN)

/* TCR: T0SZ=28, IRGN0/ORGN0=WBWA, SH0=inner, TG0=16K, EPD1, TG1=16K, IPS=36 bit */
#define TCR_VAL		(28UL | (1UL << 8) | (1UL << 10) | (3UL << 12) | (2UL << 14) | \
			 (28UL << 16) | (1UL << 23) | (1UL << 30) | (1UL << 32))

#define SCTLR_M		(1UL << 0)
#define SCTLR_A		(1UL << 1)
#define SCTLR_C		(1UL << 2)
#define SCTLR_I		(1UL << 12)
#define SCTLR_WXN	(1UL << 19)

#define rsr(r) ({ uint64_t _v; __asm__ volatile("mrs %0, " r : "=r"(_v)); _v; })
#define wsr(r, v) __asm__ volatile("msr " r ", %0" : : "r"((uint64_t)(v)))

extern char _head[], _end[];

static void dcache_inval_range(uintptr_t start, uintptr_t end)
{
	uint64_t line = 4UL << ((rsr("ctr_el0") >> 16) & 0xf);

	if (start >= end)
		return;
	for (uintptr_t a = start & ~(line - 1); a < end; a += line)
		__asm__ volatile("dc ivac, %0" : : "r"(a) : "memory");
	__asm__ volatile("dsb sy" ::: "memory");
}

/*
 * Page tables (the image has no BSS: they must be in .data). Addresses come
 * from shim.ld: one L1 (512 x 1GB), two L2 (2048 x 32MB each: low 64 GB that
 * holds all SoC MMIO and the low DDR bank) and two L3 tables for the 32MB
 * blocks holding the image. Every other 1GB block is a Device L1 block, so
 * the iOS kernel's phys_base (0x100000000 on sweet, 0x180000000 on gauguin)
 * is covered without more tables.
 */
extern uint64_t pt_l1[], pt_l2lo[], pt_l2hi[], pt_l3[];

/* Clear them before first use: the Image (and the .data initialisers ABL
 * copied) must stay small, so the tables are not filled at link time. */
void zero_tables(void)
{
	uint64_t *t[] = { pt_l1, pt_l2lo, pt_l2hi, pt_l3 };
	unsigned n[] = { 512, 2 * NENT, 2 * NENT, 2 * NENT };

	for (unsigned i = 0; i < 4; i++)
		for (unsigned j = 0; j < n[i]; j++)
			t[i][j] = 0;
}

int mmu_enable(struct mmu_info *info)
{
	uintptr_t img_lo = (uintptr_t)_head & ~(PG_SIZE - 1);
	uintptr_t img_hi = ((uintptr_t)_end + PG_SIZE - 1) & ~(PG_SIZE - 1);
	uint64_t *l1 = pt_l1, *l2 = pt_l2lo, *l2_hi = pt_l2hi, *l3_first = pt_l3;
	int n_l3 = 0;

	info->img_lo = img_lo;
	info->img_hi = img_hi;
	info->ttbr = (uint64_t)l1;
	info->ram_lo = img_lo >> L1_SHIFT << L1_SHIFT;
	info->ram_hi = img_lo >> L1_SHIFT << L1_SHIFT;
	if (((img_hi - 1) >> BLK_SHIFT) - (img_lo >> BLK_SHIFT) > 1)
		return -1;	/* only room for two L3 tables */

	for (int i = 0; i < 512; i++)
		l1[i] = ((uint64_t)i << L1_SHIFT) | DEV_FLAGS | D_BLOCK;
	for (int i = 0; i < NENT; i++)
		l2[i] = ((uint64_t)i << BLK_SHIFT) | DEV_FLAGS | D_BLOCK;

	/* Low 64 GB: L1[0] and L1[1] -> L2. Each L2 covers 2048 x 32MB. */
	l1[0] = (uint64_t)l2 | D_TABLE;
	l1[1] = (uint64_t)l2_hi | D_TABLE;

	/* Framebuffer block: Normal non-cacheable (write-combining). */
	uint64_t fb = con_fb_base;
	if ((fb >> L1_SHIFT) <= 1) {
		uint64_t *tbl = (fb >> L1_SHIFT) ? l2_hi : l2;
		tbl[(fb >> BLK_SHIFT) & (NENT - 1)] = (fb & ~(BLK_SIZE - 1)) | NC_FLAGS | D_BLOCK;
	} else {
		l1[fb >> L1_SHIFT] = (fb & ~(L1_SIZE - 1)) | NC_FLAGS | D_BLOCK;
	}

	/* L3 tables for the block(s) that hold part of the image. */
	for (uint64_t blk = img_lo >> BLK_SHIFT; blk <= (img_hi - 1) >> BLK_SHIFT; blk++) {
		uint64_t *l3 = l3_first + n_l3 * NENT;
		uint64_t base = blk << BLK_SHIFT;
		uint64_t *tbl = (blk >> (L1_SHIFT - BLK_SHIFT)) ? l2_hi : l2;
		for (int i = 0; i < NENT; i++) {
			uint64_t pa = base + ((uint64_t)i << PG_SHIFT);
			int ours = pa >= img_lo && pa < img_hi;
			l3[i] = pa | (ours ? WB_FLAGS : DEV_FLAGS) | D_PAGE;
		}
		tbl[blk & (NENT - 1)] = (uintptr_t)l3 | D_TABLE;
		n_l3++;
	}
	info->n_l3 = n_l3;

	/* Image lines may be stale in the cache from ABL; we wrote memory directly. */
	dcache_inval_range(img_lo, img_hi);
	__asm__ volatile("ic iallu; dsb sy; isb" ::: "memory");

	wsr("mair_el1", MAIR_VAL);
	wsr("tcr_el1", TCR_VAL);
	wsr("ttbr0_el1", (uintptr_t)l1);
	__asm__ volatile("isb; tlbi vmalle1; dsb nsh; isb" ::: "memory");

	uint64_t sctlr = rsr("sctlr_el1");
	info->sctlr_before = sctlr;
	sctlr &= ~(SCTLR_A | SCTLR_WXN);
	sctlr |= SCTLR_M | SCTLR_C | SCTLR_I;
	wsr("sctlr_el1", sctlr);
	__asm__ volatile("isb" ::: "memory");
	info->sctlr_after = rsr("sctlr_el1");
	return 0;
}

/* Translate a VA with AT S1E1R; returns PAR_EL1. */
uint64_t mmu_probe(uintptr_t va)
{
	__asm__ volatile("at s1e1r, %0; isb" : : "r"(va) : "memory");
	return rsr("par_el1");
}