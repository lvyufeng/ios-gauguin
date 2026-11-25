#ifndef NVT_RUNTIME_TEST_SHIM_H
#define NVT_RUNTIME_TEST_SHIM_H
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <libkern/crypto/sha2.h>
#define GAUGUIN 1
#define KERN_SUCCESS 0
#define kSuccess 0
#define kBootArgsVersion2 2
#ifndef EAUTH
#define EAUTH 80
#endif
typedef uintptr_t vm_offset_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);
typedef void *DTEntry;
typedef struct boot_args {
    unsigned Version;
    uint64_t physBase, memSize, topOfKernelData;
} boot_args;
extern struct test_pe_state {void *bootArgs;} PE_state;
bool PE_parse_boot_argn(const char *,void *,size_t);
kern_return_t kernel_thread_start(thread_continue_t,void *,thread_t *);
void thread_deallocate(thread_t);
void thread_terminate_self(void);
void IOSleep(unsigned);
uint64_t mach_absolute_time(void);
void absolutetime_to_nanoseconds(uint64_t,uint64_t *);
bool ml_get_interrupts_enabled(void);
bool ml_at_interrupt_context(void);
int get_preemption_level(void);
vm_offset_t ml_static_ptovirt(vm_offset_t);
int SecureDTLookupEntry(DTEntry,const char *,DTEntry *);
int SecureDTGetProperty(DTEntry,const char *,const void **,unsigned *);
void sweet_log_mark_sync(const char *);
void sweet_log_flush_now(void);
void sweet_log_append(const char *,int);
int nrt_test_printf(const char *,...);
#define printf nrt_test_printf
#endif
