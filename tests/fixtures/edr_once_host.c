/* Real dispatch_once completion plus an actually occupied initializer. */
#include "../../graphics/gauguin-edr-default/EDRDefault.c"
#include <assert.h>
#include <pthread.h>
static dispatch_once_t tokens[64], busy;
static unsigned initialized[64], busy_initialized;
static dispatch_semaphore_t entered, release_busy;
static void *occupy(void *unused)
{
    (void)unused;
    dispatch_once(&busy, ^{
        ++busy_initialized;
        dispatch_semaphore_signal(entered);
        assert(!dispatch_semaphore_wait(release_busy,
            dispatch_time(DISPATCH_TIME_NOW, 5*NSEC_PER_SEC)));
    });
    return NULL;
}
int main(void)
{
    assert(geq_once_available(0) && !geq_once_complete(0));
    assert(geq_once_available(UINTPTR_MAX) && geq_once_complete(UINTPTR_MAX));
    const uintptr_t completed[] = { 2, 6, 0x19f31e02, UINTPTR_MAX-1 };
    const uintptr_t occupied[] = { 4, 5, 3, 0x123400, 0x123401, UINTPTR_MAX-2 };
    for (size_t i=0;i<sizeof(completed)/sizeof(completed[0]);++i)
        assert(geq_once_available(completed[i]) && geq_once_complete(completed[i]));
    for (size_t i=0;i<sizeof(occupied)/sizeof(occupied[0]);++i)
        assert(!geq_once_available(occupied[i]) && !geq_once_complete(occupied[i]));
    unsigned generations = 0;
    for (unsigned i=0;i<64;++i) {
        assert(geq_initialize_once(&tokens[i], ^{++initialized[i];}));
        uintptr_t state = (uintptr_t)__atomic_load_n(&tokens[i],__ATOMIC_ACQUIRE);
        generations += state != UINTPTR_MAX && geq_once_complete(state);
        assert(initialized[i] == 1);
        assert(geq_initialize_once(&tokens[i], ^{++initialized[i];}));
        assert(initialized[i] == 1);
    }
    assert(generations > 0);
    entered=dispatch_semaphore_create(0);release_busy=dispatch_semaphore_create(0);
    assert(entered && release_busy);
    pthread_t thread;assert(!pthread_create(&thread,NULL,occupy,NULL));
    assert(!dispatch_semaphore_wait(entered,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC)));
    /* Refuse the observed owner without waiting or calling its initializer. */
    assert(!geq_initialize_once(&busy, ^{++busy_initialized;}));
    dispatch_semaphore_signal(release_busy);
    assert(!pthread_join(thread,NULL));
    assert(geq_initialize_once(&busy, ^{++busy_initialized;}) && busy_initialized==1);
    dispatch_release(entered);dispatch_release(release_busy);
    printf("{\"state\":\"passed-production-once-generation-and-real-busy-refusal\",\"completed_initializers\":64,\"generation_returns\":%u,\"each_block_executed_once\":true,\"occupied_initializer_refused\":true,\"completed_after_release_accepted\":true,\"device_commands\":0}\n",generations);
}
