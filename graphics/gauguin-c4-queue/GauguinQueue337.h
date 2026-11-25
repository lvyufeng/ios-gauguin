/* CPU metadata only. Include after GauguinC4QueueTrace.h. */
#ifndef GAUGUIN_QUEUE337_H
#define GAUGUIN_QUEUE337_H
#define GQ337_LIMIT 32768u
#define GQ337_LINE_MAX 192u
static unsigned gq337_records;
static void gauguin_queue337(unsigned stage,uintptr_t object,double made,
                             uint64_t queue,uint64_t ticket,uint64_t retired,double tick)
{
    if(stage>2||!object||!queue||!ticket||!(made>=220.0&&made<270.0)||
       !(tick>=made&&tick<900.0)||__atomic_load_n(&gcq_scope,__ATOMIC_ACQUIRE)!=1)return;
    unsigned n=__atomic_load_n(&gq337_records,__ATOMIC_RELAXED);
    do {
        if(n>GQ337_LIMIT)return;
    } while(!__atomic_compare_exchange_n(&gq337_records,&n,n+1,1,
                                         __ATOMIC_RELAXED,__ATOMIC_RELAXED));
    if(n==GQ337_LIMIT) {
        fprintf(stderr,"GAUGUIN Q337: limit=32768 coverage=incomplete\n");return;
    }
    fprintf(stderr,"GAUGUIN Q337: stage=%u object=%p made_us=%.0f queue=%llu ticket=%llu retired=%llu tick_us=%.0f\n",
            stage,(void *)object,made*1e6,(unsigned long long)queue,
            (unsigned long long)ticket,(unsigned long long)retired,tick*1e6);
}
#endif
