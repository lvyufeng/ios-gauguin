/* Darwin <mach/machine/thread_status.h>: arm64 thread state for loader.h. */
#pragma once
#include <stdint.h>
#define ARM_THREAD_STATE64 6
#define ARM_THREAD_STATE64_COUNT 68
struct arm_thread_state64 {
	uint64_t __x[29];
	uint64_t __fp;
	uint64_t __lr;
	uint64_t __sp;
	uint64_t __pc;
	uint32_t __cpsr;
	uint32_t __pad;
};
