/* Darwin <mach/mach.h> for the host tools: only the port-size helpers the
 * cctools libmacho/mach-o code touches (no Mach IPC on Linux). */
#pragma once
#include <mach/machine.h>
#include <mach/vm_types.h>
#include <mach/vm_prot.h>
typedef unsigned long mach_vm_size_t_x;
/* Minimal Mach host_info: the host tools only ask for the CPU type, which on
 * a Linux build host is the machine this build runs on (x86_64 or arm64). */
#include <signal.h>
typedef int kern_return_t;
typedef unsigned int mach_port_t;
typedef int *host_info_t;
#define HOST_BASIC_INFO 1
#define HOST_BASIC_INFO_COUNT 8
struct host_basic_info {
	int max_cpus;
	int avail_cpus;
	vm_size_t memory_size;
	cpu_type_t cpu_type;
	cpu_subtype_t cpu_subtype;
	unsigned int logical_cpus;
	unsigned int phys_cpu;
	int reserved[2];  /* keep it a multiple of 8 ints */
};
static inline mach_port_t mach_host_self(void) { return 1; }
static inline mach_port_t mach_task_self(void) { return 2; }
static inline int mach_port_deallocate(mach_port_t p, mach_port_t q) { (void)p; (void)q; return 0; }
static inline int host_info(mach_port_t p, int flavor, host_info_t out, unsigned int *count)
{
	struct host_basic_info *hi = (struct host_basic_info *)out;
	(void)p; (void)flavor;
#if defined(__x86_64__)
	hi->cpu_type = CPU_TYPE_X86_64;
	hi->cpu_subtype = CPU_SUBTYPE_X86_64_ALL;
#else
	hi->cpu_type = CPU_TYPE_ARM64;
	hi->cpu_subtype = CPU_SUBTYPE_ARM64_ALL;
#endif
	*count = HOST_BASIC_INFO_COUNT;
	return 0;
}
