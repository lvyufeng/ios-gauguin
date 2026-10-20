/* Linux stand-in for <mach/mach_init.h>: kextsymboltool's KXLD path only. */
#pragma once
#include <stdint.h>
typedef struct mach_port_x { uint32_t x; } *mach_port_name_t;
typedef struct mach_port_x *task_port_t;
static inline uint32_t mach_task_self_(void) { return 0; }
#define mach_task_self() mach_task_self_()
