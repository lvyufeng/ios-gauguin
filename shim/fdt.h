#pragma once
#include <stdint.h>
#include <stddef.h>

/* Read a u32/u64 (cell-size agnostic) property of /chosen. Returns 0 if absent. */
int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out);

/* Find a node by path ("/memory", "/reserved-memory/cont_splash_region").
 * Returns its FDT_BEGIN_NODE token offset, 0 if absent. */
uintptr_t fdt_find(uintptr_t fdt, const char *path);

/* Property `prop` of `node`: up to max cells of big-endian ASCII hex,
 * decoded into out[0..n-1]. Returns the number of cells (0 if absent). */
int fdt_b32hex(uintptr_t fdt, uintptr_t node, const char *prop, uint64_t *out, int max);

/* Property `prop` of `node` as one decimal number ("width = <1080>;"). */
int fdt_dec3(uintptr_t fdt, uintptr_t node, const char *prop, uint32_t *out);

/* First reg pair, 2/2 cells (root and /soc address space). */
int fdt_reg2(uintptr_t fdt, uintptr_t node, uint64_t *base, uint64_t *size);

/* First reg pair, 1/1 cells (simple bus with ranges). */
int fdt_reg1(uintptr_t fdt, uintptr_t node, uint64_t *base, uint64_t *size);