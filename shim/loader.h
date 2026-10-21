#pragma once
#include <stdint.h>

/* Boot the SWEETXNU payload found in the ABL ramdisk; returns only on error. */
const char *loader_boot(uintptr_t dtb);

/* Append " <label><hex>" to the command line of the payload about to boot,
 * so the kernel's boot-args line (and the persistent log) carries it. */
void loader_announce(uintptr_t dtb, const char *label, uint32_t value);
