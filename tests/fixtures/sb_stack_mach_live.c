/* Native Mach adapter test; pauses only this disposable test process's main thread. */
#include "SBStackMach.h"
#include <assert.h>
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>

static _Atomic uint64_t watch;
static _Atomic bool waiting;
static dispatch_semaphore_t gate;
static struct sb_registered_thread target;
static struct sb_stack_result snapshot;
static bool found_test_frame;

__attribute__((noinline)) void sb_live_blocked_main(void)
{
    atomic_store_explicit(&waiting,true,memory_order_release);
    assert(dispatch_semaphore_wait(gate,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC))==0);
    __asm__ volatile("" ::: "memory");
}
static void *sample(void *unused)
{
    (void)unused;
    struct sb_mach_context context;
    assert(sb_mach_open(&context,&target,&watch));
    while(!atomic_load_explicit(&waiting,memory_order_acquire))usleep(1000);
    usleep(20000);
    uint64_t expected=atomic_load_explicit(&watch,memory_order_acquire);
    sb_stack_capture(&sb_mach_ops,&context,&context.target,expected,&snapshot);
    assert(snapshot.suspend_result==0 && snapshot.resume_result==0);
    assert(snapshot.state_result==0 && snapshot.registers_valid && snapshot.frames>0);
    /* Symbol lookup is deliberately after resume. Saved return addresses on
     * an arm64e Mac may carry PAC bits; this host's test image is below39bits.
     * Production logs preserve raw addresses and make no such normalization. */
    const uintptr_t mask=UINT64_C(0x0000007fffffffff);
    assert((uintptr_t)sb_live_blocked_main<=mask);
    for(unsigned i=0;i<snapshot.frames;++i) {
        Dl_info info={0}; uintptr_t address=(uintptr_t)snapshot.frame_lr[i]&mask;
        if(dladdr((void *)address,&info) && info.dli_sname && strcmp(info.dli_sname,"sb_live_blocked_main")==0)
            found_test_frame=true;
    }
    sb_mach_close(&context);
    dispatch_semaphore_signal(gate);
    return NULL;
}
int main(void)
{
    assert(pthread_main_np() && sb_register_current_thread(&target));
    mach_timebase_info_data_t timebase; assert(mach_timebase_info(&timebase)==0 && timebase.denom);
    uint64_t now=(uint64_t)(((__uint128_t)mach_absolute_time()*timebase.numer)/timebase.denom/1000);
    assert(now>1000000 && now<(UINT64_MAX>>2));
    atomic_store(&watch,((now-1000000)<<2)|2);
    gate=dispatch_semaphore_create(0); pthread_t worker;
    assert(pthread_create(&worker,NULL,sample,NULL)==0);
    sb_live_blocked_main(); assert(pthread_join(worker,NULL)==0);
    assert(found_test_frame && snapshot.stopped_watch==snapshot.expected_watch);
    printf("PASS native Mach snapshot frames=%u stop=%u elapsed_us=%llu resumed=1 known_test_frame=1\n",
           snapshot.frames,snapshot.stop,(unsigned long long)(snapshot.resumed_us-snapshot.us));
    mach_port_deallocate(mach_task_self(),target.port); dispatch_release(gate);
    return 0;
}
