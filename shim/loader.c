/*
 * Milestone 4: act as iBoot for xnu.
 *
 * mkpayload.py already resolved the kernel's chained fixups and built the
 * ADT, so this only has to: find the payload in the ABL ramdisk, copy the
 * segments to phys_base + (vmaddr - virt_base), place the ADT and
 * boot_args behind the kernel, and jump to the entry point with the MMU
 * and caches off, x0 = boot_args (physical).
 */
#include <stdint.h>
#include "console.h"
#include "fdt.h"
#include "loader.h"
#include "pas_reservation.h"

extern const uint8_t _head[], _end[];

#define BOOT_LINE_LENGTH	608
#define PAGE_16K		0x4000UL

struct payload_seg {
	uint64_t vmaddr, vmsize, file_off, file_size;
};

struct payload {
	char magic[8];
	uint32_t version, nsegs;
	uint64_t virt_base, entry_va, adt_off, adt_size, kernel_end;
	uint64_t phys_base, mem_size;
	char cmdline[BOOT_LINE_LENGTH];
	struct payload_seg segs[];
};

/* pexpert/pexpert/arm64/boot.h, Revision/Version 2 */
struct boot_video {
	uint64_t v_baseAddr, v_display, v_rowBytes, v_width, v_height, v_depth;
};

struct boot_args {
	uint16_t Revision, Version;
	uint64_t virtBase, physBase, memSize, topOfKernelData;
	struct boot_video Video;
	uint32_t machineType;
	uint64_t deviceTreeP;
	uint32_t deviceTreeLength;
	char CommandLine[BOOT_LINE_LENGTH];
	uint64_t bootFlags, memSizeActual;
};

_Static_assert(__builtin_offsetof(struct payload, segs) == 0x2a8, "payload header layout");
_Static_assert(__builtin_offsetof(struct boot_args, Video) == 40, "boot_args layout");
_Static_assert(__builtin_offsetof(struct boot_args, CommandLine) == 108, "boot_args layout");
_Static_assert(sizeof(struct boot_args) == 736, "boot_args layout");

/* MMU off: everything is Device memory, so copy in aligned 8-byte words. */
static void copy64(uintptr_t dst, uintptr_t src, uint64_t n)
{
	volatile uint64_t *d = (volatile uint64_t *)dst;
	volatile const uint64_t *s = (volatile const uint64_t *)src;
	for (uint64_t i = 0; i < (n + 7) / 8; i++)
		d[i] = s[i];
}

static void zero64(uintptr_t dst, uint64_t n)
{
	volatile uint64_t *d = (volatile uint64_t *)dst;
	for (uint64_t i = 0; i < n / 8; i++)
		d[i] = 0;
}

static int magic_ok(const char *m)
{
	static const char want[] = "SWEETXNU";
	for (int i = 0; i < 8; i++)
		if (m[i] != want[i])
			return 0;
	return 1;
}

/* Returning would enter shim_main's old UFS diagnostic path. Invalid supplied
 * input (including non-XNU cpio) therefore stops here before any load/copy. */
static __attribute__((noreturn)) void loader_stop(const char *reason, int status)
{
    con_str("LOAD STOP", reason);
    con_hex("STATUS", (uint64_t)(int64_t)status);
    for (;;) __asm__ volatile("wfe" ::: "memory");
}

typedef void (*xnu_entry_t)(uint64_t boot_args_pa);

const char *loader_boot(uintptr_t dtb)
{
	uint64_t rd_start, rd_end;

	size_t fdt_bytes = pas_fdt_header_size((const uint8_t *)dtb);
	int handoff = pas_initrd((const uint8_t *)dtb, fdt_bytes, &rd_start, &rd_end);
	if (handoff || rd_end <= rd_start || rd_end - rd_start < sizeof(struct payload) || (rd_start & 7))
		loader_stop("invalid FDT/initrd", handoff);
	if ((rd_start < dtb + fdt_bytes && dtb < rd_end) ||
	    (rd_start < (uintptr_t)_end && (uintptr_t)_head < rd_end))
		loader_stop("initrd overlaps loader/FDT", PAS_OVERLAP);
	con_hex2("INITRD", "lo=", rd_start, "hi=", rd_end);

	const struct payload *p = (const struct payload *)rd_start;
	if (!magic_ok(p->magic))
		loader_stop("no SWEETXNU payload", PAS_BAD_PAYLOAD);
	if (p->version != 1 || (p->adt_off & 7) || (rd_start & 7))
		loader_stop("bad payload header", PAS_BAD_PAYLOAD);

	struct pas_context context = {
		.payload = (const uint8_t *)p, .fdt = (const uint8_t *)dtb,
		.payload_bytes = rd_end - rd_start, .fdt_bytes = fdt_bytes,
		.payload_pa = rd_start, .fdt_pa = dtb,
		.shim_pa = (uintptr_t)_head, .shim_bytes = (uintptr_t)_end - (uintptr_t)_head,
	};
	struct pas_plan reservation;
	int reservation_status = pas_prepare(&context, &reservation);
	if (reservation_status < 0)
		loader_stop("payload preflight", reservation_status);

	uint64_t pa_of_va_base = p->phys_base - p->virt_base;	/* pa = va + this */
	con_hex2("PHYS", "base=", p->phys_base, "size=", p->mem_size);
	con_hex("VIRT", p->virt_base);
	con_hex("ENTRY", p->entry_va);

	/* The payload must not overlap where the kernel goes. */
	if (rd_end > p->phys_base && rd_start < p->phys_base + p->mem_size)
		loader_stop("ramdisk overlaps kernel memory", PAS_OVERLAP);

	for (uint32_t i = 0; i < p->nsegs; i++) {
		const struct payload_seg *s = &p->segs[i];
		uintptr_t dst = s->vmaddr + pa_of_va_base;
		copy64(dst, rd_start + s->file_off, s->file_size);
		if (s->vmsize > s->file_size)
			zero64(dst + ((s->file_size + 7) & ~7UL), s->vmsize - ((s->file_size + 7) & ~7UL));
	}
	con_hex2("SEGS", "n=", p->nsegs, "end=", p->kernel_end + pa_of_va_base);

	/* ADT, then boot_args, behind the kernel; everything below topOfKernelData is ours. */
	uintptr_t adt_pa = p->kernel_end + pa_of_va_base;
	copy64(adt_pa, rd_start + p->adt_off, p->adt_size);
	if (reservation_status == PAS_READY) {
		int status = pas_commit((uint8_t *)adt_pa, p->adt_size, &reservation);
		if (status != PAS_READY)
			loader_stop("PAS metadata commit", status);
		con_hex2("PAS OWNED", "pa=", reservation.pa, "bytes=", reservation.bytes);
		/* No read, write, map, firmware load or SMC using this range. */
	}
	uintptr_t ba_pa = (adt_pa + p->adt_size + PAGE_16K - 1) & ~(PAGE_16K - 1);
	uintptr_t top = ba_pa + PAGE_16K;

	zero64(ba_pa, PAGE_16K);
	volatile struct boot_args *ba = (volatile struct boot_args *)ba_pa;
	ba->Revision = 2;
	ba->Version = 2;
	ba->virtBase = p->virt_base;
	ba->physBase = p->phys_base;
	ba->memSize = p->mem_size;
	ba->topOfKernelData = top;
	ba->Video.v_baseAddr = con_fb_base;
	ba->Video.v_display = 1;
	ba->Video.v_rowBytes = con_stride;
	ba->Video.v_width = con_w;
	ba->Video.v_height = con_h;
	ba->Video.v_depth = 32;
	ba->deviceTreeP = adt_pa - pa_of_va_base;	/* xnu reads it with the MMU on: a VA */
	ba->deviceTreeLength = (uint32_t)p->adt_size;
	for (int i = 0; i < BOOT_LINE_LENGTH; i++)
		ba->CommandLine[i] = p->cmdline[i];
	ba->memSizeActual = p->mem_size;
	con_hex2("BOOTARG", "pa=", ba_pa, "top=", top);

	uintptr_t entry_pa = p->entry_va + pa_of_va_base;
	con_hex("JUMP", entry_pa);
	con_str("XNU", "jumping (fbcon clears screen)");

	/* Everything was written with the MMU and caches off; drop any stale I-cache lines too. */
	__asm__ volatile("dsb sy; ic iallu; dsb sy; isb" ::: "memory");
	((xnu_entry_t)entry_pa)(ba_pa);
	loader_stop("xnu returned", PAS_BAD_INPUT);
}

/*
 * The reason the previous boot ended is known only here, in the shim, and the
 * kernel's console log is the one place that survives: append
 * " <label><hex>" to the payload's command line, which the kernel prints with
 * its first boot-args line, so the persistent log carries it.
 */
static void
announce_into(char *line, const char *label, uint32_t value)
{
	int n = 0;

	while (n < BOOT_LINE_LENGTH - 1 && line[n])
		n++;
	if (n + 12 >= BOOT_LINE_LENGTH)
		return;
	line[n++] = ' ';
	while (*label && n < BOOT_LINE_LENGTH - 12)
		line[n++] = *label++;
	static const char hex[] = "0123456789abcdef";
	for (int sh = 28; sh >= 0; sh -= 4)
		line[n++] = hex[(value >> sh) & 0xf];
	line[n] = 0;
}

void
loader_announce(uintptr_t dtb, const char *label, uint32_t value)
{
	uint64_t rd_start, rd_end;

	size_t fdt_bytes = pas_fdt_header_size((const uint8_t *)dtb);
	if (pas_initrd((const uint8_t *)dtb, fdt_bytes, &rd_start, &rd_end) ||
	    rd_end <= rd_start || rd_end - rd_start < sizeof(struct payload) ||
	    (rd_start & 7) || (rd_start < dtb + fdt_bytes && dtb < rd_end) ||
	    (rd_start < (uintptr_t)_end && (uintptr_t)_head < rd_end))
		return;
	struct payload *p = (struct payload *)rd_start;
	if (!magic_ok(p->magic) || p->version != 1)
		return;
	/* Diagnostics also write the input command line. Do not modify an input
	 * whose geometry/ownership check would later stop the actual boot. */
	struct pas_context context = {
		.payload = (const uint8_t *)p, .fdt = (const uint8_t *)dtb,
		.payload_bytes = rd_end - rd_start, .fdt_bytes = fdt_bytes,
		.payload_pa = rd_start, .fdt_pa = dtb,
		.shim_pa = (uintptr_t)_head, .shim_bytes = (uintptr_t)_end - (uintptr_t)_head,
	};
	struct pas_plan reservation;
	if (pas_prepare(&context, &reservation) < 0)
		return;
	announce_into(p->cmdline, label, value);
}
