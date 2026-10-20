/* Pre-included for every host tool: the Darwin SDK declarations the xnu
 * SETUP sources expect (implemented in compat.c where possible). */
#ifndef XNU_HOST_DARWIN_COMPAT_H
#define XNU_HOST_DARWIN_COMPAT_H
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#include <mach/machine.h>
#include <architecture/byte_order.h>
#define MAXPATHLEN 1024
typedef int boolean_t;
#ifndef TRUE
#define TRUE 1
#define FALSE 0
#endif
#ifndef KERN_SUCCESS
#define KERN_SUCCESS 0
#endif
/* OSSwap* and NXByteOrder come from <architecture/byte_order.h> (below). */
const char *getprogname(void);
void *setmode(const char *mode_str);
mode_t getmode(const void *set, mode_t mode);
unsigned long mach_vm_round_page(unsigned long x);
int uuid_generate(void *out);           /* fills 16 random bytes */
#endif
/* ---- CPU constants used by cctools libmacho (Darwin <mach/machine.h>) ---- */
#define CPU_ARCH_ABI64 0x01000000
#define CPU_ARCH_ABI64_32 0x02000000
#ifndef CPU_TYPE_ANY
#define CPU_TYPE_ANY 0
#endif
#define CPU_TYPE_VEO 255
#define CPU_TYPE_HPPA 11
#define CPU_TYPE_I860 15
#define CPU_TYPE_I386 7
#define CPU_TYPE_X86_64 (7 | CPU_ARCH_ABI64)
#define CPU_TYPE_MC680 6
#define CPU_TYPE_MC88000 13
#define CPU_TYPE_SPARC 14
#define CPU_TYPE_ARM 12
#define CPU_TYPE_ARM64 (12 | CPU_ARCH_ABI64)
#define CPU_TYPE_ARM64_32 (12 | CPU_ARCH_ABI64_32)
#define CPU_TYPE_POWERPC 18
#define CPU_TYPE_POWERPC64 (18 | CPU_ARCH_ABI64)
#define CPU_SUBTYPE_MULTIPLE 0xffffffff
#define CPU_SUBTYPE_BIG_ENDIAN 1
#define CPU_SUBTYPE_LITTLE_ENDIAN 0
#define CPU_SUBTYPE_LIB64 0x80000000
#define CPU_SUBTYPE_INTEL_FAMILY(x) ((x) & 15)
#define CPU_SUBTYPE_INTEL_MODEL(x) ((x) >> 4)
#define CPU_SUBTYPE_INTEL_FAMILY_MAX 15
#define CPU_SUBTYPE_PENT 5
#define CPU_SUBTYPE_486 4
#define CPU_SUBTYPE_486SX 132
#define CPU_SUBTYPE_586 5
#define CPU_SUBTYPE_PENTII_M3 54
#define CPU_SUBTYPE_I386_ALL 3
#define CPU_SUBTYPE_X86_64_ALL 3
#define CPU_SUBTYPE_X86_64_H 8
#define CPU_SUBTYPE_HPPA_ALL 0
#define CPU_SUBTYPE_HPPA_7100LC 1
#define CPU_SUBTYPE_I860_ALL 0
#define CPU_SUBTYPE_I860_860 1
#define CPU_SUBTYPE_MC680 1
#define CPU_SUBTYPE_MC68030_ONLY 3
#define CPU_SUBTYPE_MC68040 2
#define CPU_SUBTYPE_MC88000_ALL 0
#define CPU_SUBTYPE_MC88110 1
#define CPU_SUBTYPE_SPARC_ALL 0
#define CPU_SUBTYPE_ARM_ALL 0
#define CPU_SUBTYPE_ARM_V4T 5
#define CPU_SUBTYPE_ARM_V5TEJ 7
#define CPU_SUBTYPE_ARM_XSCALE 8
#define CPU_SUBTYPE_ARM_V6 6
#define CPU_SUBTYPE_ARM_V6M 14
#define CPU_SUBTYPE_ARM_V7 9
#define CPU_SUBTYPE_ARM_V7F 10
#define CPU_SUBTYPE_ARM_V7S 11
#define CPU_SUBTYPE_ARM_V7K 12
#define CPU_SUBTYPE_ARM_V7M 15
#define CPU_SUBTYPE_ARM_V7EM 16
#define CPU_SUBTYPE_ARM_V8 13
#define CPU_SUBTYPE_ARM64_ALL 0
#define CPU_SUBTYPE_ARM64_V8 1
#define CPU_SUBTYPE_ARM64E 2
#define CPU_SUBTYPE_ARM64_32_V8 1
#define CPU_SUBTYPE_POWERPC_ALL 0
#define CPU_SUBTYPE_POWERPC_601 1
#define CPU_SUBTYPE_POWERPC_603 3
#define CPU_SUBTYPE_POWERPC_603e 4
#define CPU_SUBTYPE_POWERPC_604 5
#define CPU_SUBTYPE_POWERPC_604e 6
#define CPU_SUBTYPE_POWERPC_620 7
#define CPU_SUBTYPE_POWERPC_750 8
#define CPU_SUBTYPE_POWERPC_7400 10
#define CPU_SUBTYPE_POWERPC_7450 11
#define CPU_SUBTYPE_POWERPC_970 100
#define CPU_SUBTYPE_VEO_ALL 0
#define CPU_SUBTYPE_VEO_1 1
#define CPU_SUBTYPE_VEO_2 2
#define CPU_SUBTYPE_VEO_3 3
#define CPU_SUBTYPE_VEO_4 4
#define CPU_SUBTYPE_I386 0
#define CPU_SUBTYPE_MASK 0xff000000
#define CPU_SUBTYPE_MC680x0_ALL 1
#define CPU_SUBTYPE_PENTPRO 38
#define CPU_SUBTYPE_PENTII_M5 86
#define CPU_SUBTYPE_PENTIUM_4 10
#define CPU_SUBTYPE_POWERPC_603ev 12
#define CPU_TYPE_MC680x0 6
