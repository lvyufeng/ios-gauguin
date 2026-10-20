/* Darwin <crt_externs.h>: the host tools only query their own image header,
 * which is their ELF image on Linux: return NULL (no Mach-O header). */
#pragma once
#include <mach-o/loader.h>
static inline struct mach_header *_NSGetMachExecuteHeader(void)
{
	struct mach_header *h = 0;
	return h;
}
