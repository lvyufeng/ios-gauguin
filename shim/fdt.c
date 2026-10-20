/*
 * Just enough flattened-device-tree parsing to find what ABL put in
 * /chosen (initrd location) and in the memory / reserved-memory nodes that
 * differ between boards. Big-endian, 4-byte aligned tokens.
 */
#include <stdint.h>
#include <stddef.h>
#include "fdt.h"

#define FDT_MAGIC	0xd00dfeed
#define FDT_BEGIN_NODE	1
#define FDT_END_NODE	2
#define FDT_PROP	3
#define FDT_NOP		4
#define FDT_END		9

static uint32_t be32(uintptr_t a)
{
	return __builtin_bswap32(*(volatile uint32_t *)a);
}

static int streq(const char *a, const char *b)
{
	while (*a && *a == *b)
		a++, b++;
	return *a == *b;
}

static uintptr_t align4(uintptr_t a)
{
	return (a + 3) & ~3UL;
}

static uintptr_t skip_str(uintptr_t p)
{
	/* byte loads are fine on Device memory as long as they are aligned to 1 */
	while (*(volatile char *)p)
		p++;
	return p + 1;
}

/* Property lookup in the block starting at BEGIN_NODE token `node`. */
static uintptr_t find_prop(uintptr_t fdt, uintptr_t node, const char *prop, uint32_t *lenp)
{
	uintptr_t strings = fdt + be32(fdt + 12);	/* off_dt_strings */
	uintptr_t p = align4(skip_str(node + 4));
	int depth = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE:
			depth++;
			p = align4(skip_str(p));
			break;
		case FDT_END_NODE:
			if (depth-- == 0)
				return 0;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			if (depth == 0 && streq((const char *)(strings + nameoff), prop)) {
				*lenp = len;
				return val;
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			return 0;
		}
	}
}

static uintptr_t find_child(uintptr_t parent, const char *name, size_t nlen)
{
	uintptr_t p = align4(skip_str(parent + 4));
	int depth = 0;

	for (;;) {
		uint32_t tok = be32(p);
		uintptr_t tokp = p;
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *nm = (const char *)p;
			if (depth == 0) {
				size_t i = 0;
				while (i < nlen && nm[i] == name[i])
					i++;
				if ((i == nlen && nm[i] == 0) || (nm[i] == '@' && i == nlen)) {
					/* match "name" or "name@unit" */
					if (i == nlen && (nm[i] == 0 || nm[i] == '@'))
						return tokp;
				}
			}
			depth++;
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			if (depth-- == 0)
				return 0;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p);
			p = align4(p + 8 + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			return 0;
		}
	}
}

uintptr_t fdt_find(uintptr_t fdt, const char *path)
{
	if (!fdt || be32(fdt) != FDT_MAGIC)
		return 0;
	uintptr_t node = fdt + be32(fdt + 8);	/* root BEGIN_NODE */
	if (!*path || streq(path, "/"))
		return node;
	while (*path == '/')
		path++;
	while (*path) {
		const char *e = path;
		while (*e && *e != '/')
			e++;
		node = find_child(node, path, (size_t)(e - path));
		if (!node)
			return 0;
		path = *e ? e + 1 : e;
	}
	return node;
}

int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out)
{
	uintptr_t chosen = fdt_find(fdt, "/chosen");
	uint32_t len = 0;

	if (!chosen)
		return 0;
	uintptr_t val = find_prop(fdt, chosen, prop, &len);
	if (!val)
		return 0;
	if (len == 4)
		*out = be32(val);
	else if (len == 8)
		*out = (uint64_t)be32(val) << 32 | be32(val + 4);
	else
		return 0;
	return 1;
}

static int hexval(uint8_t c)
{
	if (c >= '0' && c <= '9')
		return c - '0';
	if (c >= 'a' && c <= 'f')
		return c - 'a' + 10;
	if (c >= 'A' && c <= 'F')
		return c - 'A' + 10;
	return -1;
}

int fdt_b32hex(uintptr_t fdt, uintptr_t node, const char *prop, uint64_t *out, int max)
{
	uint32_t len = 0;
	int n = 0;

	if (!node)
		return 0;
	uintptr_t val = find_prop(fdt, node, prop, &len);
	if (!val)
		return 0;
	for (uint32_t i = 0; i + 4 <= len && n < max; i += 4) {
		uint64_t v = 0;
		for (int k = 0; k < 4; k++) {
			int h = hexval(*((volatile uint8_t *)val + i + k));
			if (h < 0)
				return n;
			v = v << 4 | (uint64_t)h;
		}
		out[n++] = v;
	}
	return n;
}

int fdt_u32(uintptr_t fdt, uintptr_t node, const char *prop, uint32_t *out)
{
	uint32_t len = 0;

	if (!node)
		return 0;
	uintptr_t val = find_prop(fdt, node, prop, &len);
	if (!val || len != 4)
		return 0;
	*out = be32(val);
	return 1;
}

int fdt_dec3(uintptr_t fdt, uintptr_t node, const char *prop, uint32_t *out)
{
	uint32_t len = 0;

	if (!node)
		return 0;
	uintptr_t val = find_prop(fdt, node, prop, &len);
	if (!val || !len)
		return 0;
	uint32_t v = 0;
	for (uint32_t i = 0; i < len; i++) {
		uint8_t c = *((volatile uint8_t *)val + i);
		if (c < '0' || c > '9')
			return 0;
		v = v * 10 + (c - '0');
	}
	*out = v;
	return 1;
}

static int reg_cells(uintptr_t fdt, uintptr_t node, uint64_t *base, uint64_t *size)
{
	uint32_t len = 0;
	uintptr_t val = find_prop(fdt, node, "reg", &len);

	if (!val)
		return 0;
	if (len >= 16) {		/* 2/2 cells */
		*base = (uint64_t)be32(val) << 32 | be32(val + 4);
		*size = (uint64_t)be32(val + 8) << 32 | be32(val + 12);
		return 1;
	}
	if (len >= 8) {			/* 1/1 cells */
		*base = be32(val);
		*size = be32(val + 4);
		return 1;
	}
	return 0;
}

int fdt_reg2(uintptr_t fdt, uintptr_t node, uint64_t *base, uint64_t *size)
{
	return reg_cells(fdt, node, base, size);
}

int fdt_reg1(uintptr_t fdt, uintptr_t node, uint64_t *base, uint64_t *size)
{
	return reg_cells(fdt, node, base, size);
}