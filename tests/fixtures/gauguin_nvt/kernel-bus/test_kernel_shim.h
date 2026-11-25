#ifndef NVT_TEST_KERNEL_SHIM_H
#define NVT_TEST_KERNEL_SHIM_H
/* Host boundary only; the separate real ARM64 TU never includes this file. */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef uintptr_t thread_t;
#define THREAD_NULL 0
struct test_mutex { thread_t owner; const void *group; };
#define LCK_GRP_DECLARE(n, label) const char n[] = label
#define LCK_MTX_DECLARE(n, grp) struct test_mutex n = {0, grp}
#define bzero(p, n) memset(p, 0, n)
bool lck_mtx_try_lock(struct test_mutex *);
void lck_mtx_unlock(struct test_mutex *);
thread_t current_thread(void);
bool ml_get_interrupts_enabled(void);
bool ml_at_interrupt_context(void);
int get_preemption_level(void);
bool PE_parse_boot_argn(const char *, void *, int);
vm_offset_t ml_io_map(vm_offset_t, vm_size_t);
uint64_t mach_absolute_time(void);
void absolutetime_to_nanoseconds(uint64_t, uint64_t *);
void delay(int);
void sweet_log_mark_sync(const char *);
uint32_t test_mmio_read(vm_offset_t, uint32_t);
void test_mmio_write(vm_offset_t, uint32_t, uint32_t);
void test_barrier(void);
#endif
