#include <assert.h>
#include <limits.h>
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
static int gcq_scope=1; /* unchanged C4 scope checker publishes this word */
#include "GauguinQueue337.h"
static void *worker(void *unused)
{
    (void)unused;
    for(unsigned i=0;i<5000;++i)
        gauguin_queue337(i%3,UINTPTR_MAX,269.999999999,UINT64_MAX,UINT64_MAX,UINT64_MAX,899.999999999);
    return NULL;
}
int main(void)
{
    const double bad[]={-INFINITY,0,219.99,270,INFINITY,NAN};
    for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);++i)gauguin_queue337(0,1,bad[i],1,1,0,300);
    for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);++i)gauguin_queue337(0,1,220,1,1,0,bad[i]<220?bad[i]:900+bad[i]);
    gauguin_queue337(3,1,220,1,1,0,221);gauguin_queue337(0,0,220,1,1,0,221);
    gauguin_queue337(0,1,220,0,1,0,221);gauguin_queue337(0,1,220,1,0,0,221);
    gcq_scope=0;gauguin_queue337(0,1,220,1,1,0,221);gcq_scope=1;
    assert(!gq337_records);
    pthread_t ts[8];for(unsigned i=0;i<8;++i)assert(!pthread_create(ts+i,NULL,worker,NULL));
    for(unsigned i=0;i<8;++i)assert(!pthread_join(ts[i],NULL));
    assert(gq337_records==GQ337_LIMIT+1);worker(NULL);assert(gq337_records==GQ337_LIMIT+1);
    gq337_records=UINT_MAX;worker(NULL);assert(gq337_records==UINT_MAX);
    puts("Q337 production logger: bounds, scope, 32768 concurrent rows, one marker, no counter wrap passed");
}
