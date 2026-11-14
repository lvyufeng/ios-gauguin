/* SPDX-License-Identifier: MIT
 * Mach adapters used verbatim by the iOS probe and the live Darwin host test.
 */
#ifndef GAUGUIN_SB_STACK_MACH_H
#define GAUGUIN_SB_STACK_MACH_H
#include "SBStackSampler.h"
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/arm/thread_status.h>
#include <pthread.h>
#include <stdatomic.h>

_Static_assert(ATOMIC_LLONG_LOCK_FREE==2,"watch load must not acquire a library lock");
_Static_assert(sizeof(vm_address_t)==8 && sizeof(vm_size_t)==8,"this probe requires the LP64 VM API");
struct sb_registered_thread { thread_t port; uint64_t low, high; };
struct sb_mach_context {
    struct sb_stack_target target;
    task_t task;
    mach_timebase_info_data_t timebase;
    _Atomic uint64_t *watch;
    arm_thread_state64_t machine_state;
};

/* Caller decides that the current thread is the permitted main thread. */
static bool
sb_register_current_thread(struct sb_registered_thread *out)
{
    uint64_t high=(uintptr_t)pthread_get_stackaddr_np(pthread_self());
    uint64_t size=pthread_get_stacksize_np(pthread_self());
    if (size<16384 || size>UINT64_C(134217728) || high<size+4096) return false;
    thread_t port=mach_thread_self();
    if (port==MACH_PORT_NULL) return false;
    out->port=port; out->low=high-size; out->high=high;
    return true;
}

static uint64_t sb_mach_clock(void *pointer)
{
    struct sb_mach_context *context=pointer;
    return (uint64_t)(((__uint128_t)mach_absolute_time()*context->timebase.numer)/context->timebase.denom/1000);
}
static uint64_t sb_mach_watch(void *pointer)
{
    struct sb_mach_context *context=pointer;
    return atomic_load_explicit(context->watch,memory_order_acquire);
}
static int32_t sb_mach_suspend(void *pointer)
{
    return thread_suspend((thread_t)((struct sb_mach_context *)pointer)->target.thread);
}
static int32_t sb_mach_resume(void *pointer)
{
    return thread_resume((thread_t)((struct sb_mach_context *)pointer)->target.thread);
}
static int32_t sb_mach_state(void *pointer, struct sb_stack_registers *out)
{
    struct sb_mach_context *context=pointer;
    mach_msg_type_number_t count=ARM_THREAD_STATE64_COUNT;
    kern_return_t result=thread_get_state((thread_t)context->target.thread,ARM_THREAD_STATE64,
                                         (thread_state_t)&context->machine_state,&count);
    if (result!=KERN_SUCCESS) return result;
    if (count!=ARM_THREAD_STATE64_COUNT) return -10001;
    out->pc=arm_thread_state64_get_pc(context->machine_state);
    out->lr=arm_thread_state64_get_lr(context->machine_state);
    out->sp=arm_thread_state64_get_sp(context->machine_state);
    out->fp=arm_thread_state64_get_fp(context->machine_state);
    return KERN_SUCCESS;
}
static int32_t sb_mach_read_frame(void *pointer, uint64_t address, uint64_t *next, uint64_t *lr)
{
    struct sb_mach_context *context=pointer;
    uint64_t pair[2]={0,0}; vm_size_t copied=0;
    kern_return_t result=vm_read_overwrite(context->task,(vm_address_t)address,sizeof(pair),
                                         (vm_address_t)(uintptr_t)pair,&copied);
    if (result!=KERN_SUCCESS) return result;
    if (copied!=sizeof(pair)) return -10002;
    *next=pair[0]; *lr=pair[1]; return KERN_SUCCESS;
}
static const struct sb_stack_ops sb_mach_ops={sb_mach_clock,sb_mach_watch,sb_mach_suspend,
                                            sb_mach_state,sb_mach_read_frame,sb_mach_resume};

static void sb_mach_close(struct sb_mach_context *context)
{
    if (context->target.sampler) {
        mach_port_deallocate(context->task,(mach_port_t)context->target.sampler);
        context->target.sampler=0;
    }
}
static bool
sb_mach_open(struct sb_mach_context *context, const struct sb_registered_thread *target,
             _Atomic uint64_t *watch)
{
    memset(context,0,sizeof(*context));
    context->task=mach_task_self(); context->watch=watch;
    context->target.thread=target->port;
    context->target.sampler=mach_thread_self();
    context->target.low=target->low; context->target.high=target->high;
    if (!watch || !sb_stack_target_valid(&context->target) ||
        mach_timebase_info(&context->timebase)!=KERN_SUCCESS || !context->timebase.numer || !context->timebase.denom) {
        sb_mach_close(context); return false;
    }
    /* Resolve wrappers and populate this sampler thread's MIG reply-port state
     * before ever pausing the target. Null ports cannot pause/resume anyone. */
    struct sb_mach_context warm=*context;
    struct sb_stack_registers registers={0};
    warm.target.thread=warm.target.sampler;
    (void)sb_mach_state(&warm,&registers);
    warm.target.thread=MACH_PORT_NULL;
    int32_t suspend=sb_mach_suspend(&warm), resume=sb_mach_resume(&warm);
    uint64_t original[2]={UINT64_C(0x12345678),UINT64_C(0x87654321)}, next=0, lr=0;
    int32_t read=sb_mach_read_frame(&warm,(uintptr_t)original,&next,&lr);
    if (suspend==0 || resume==0 || read!=0 || next!=original[0] || lr!=original[1]) {
        sb_mach_close(context); return false;
    }
    return true;
}
#endif
