/* Darwin <mach/machine.h>: CPU type constants and the cctools typedefs. */
#pragma once
#include <stdint.h>
#include <mach/machine/vm_types.h>
typedef int cpu_type_t;
typedef int cpu_subtype_t;
typedef int cpu_threadtype_t;
#define CPU_ARCH_ABI64 0x01000000
#define CPU_TYPE_ANY ((cpu_type_t) -1)
#define CPU_TYPE_X86_64 (7 | CPU_ARCH_ABI64)
#define CPU_TYPE_ARM64 (12 | CPU_ARCH_ABI64)
#define CPU_SUBTYPE_MASK 0xff000000
#define CPU_SUBTYPE_LIB64 0x80000000
