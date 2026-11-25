#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_ui_trace.h"

struct rate_row { uint64_t id,check,payload[18]; };
#include "SBTraceQueue.h"
static struct sb_trace_queue q=SB_TRACE_QUEUE_INIT;
static struct gut_core core;
static struct gut_event events[4096];
static _Atomic uint64_t ticks;
static _Atomic bool done,paused,release_writer,pause_next;
static uint64_t clock_now(void *unused)
{(void)unused;return atomic_fetch_add(&ticks,1);}
static uint64_t paused_clock(void *unused)
{
    uint64_t now=clock_now(unused);
    if(atomic_exchange(&pause_next,false)) {
        atomic_store(&paused,true);
        while(!atomic_load(&release_writer))sched_yield();
    }
    return now;
}
static void configure(unsigned capacity,uint64_t window)
{
    memset(&core,0,sizeof(core));memset(events,0,sizeof(events));atomic_store(&ticks,100);
    assert(gut_init(&core,events,capacity,1,window,clock_now,NULL));
    assert(gut_report(&core,98,99,0,1)==1);
}
static void *writer(void *p)
{
    uintptr_t id=(uintptr_t)p;
    for(unsigned i=0;i<200;++i)gut_record(&core,GUT_API_BEGIN,id,7,0,i,id^i,0);
    return NULL;
}
static void *poller(void *unused)
{
    (void)unused;struct gut_event out[16];struct gut_meta m;uint32_t n;
    while(!atomic_load(&done))assert(!gut_read(&core,out,16,&n,&m));
    return NULL;
}
static void kernel_parallel(void)
{
    configure(4096,UINT64_C(1000000000000));
    pthread_t writers[8],reader;
    assert(!pthread_create(&reader,NULL,poller,NULL));
    for(uintptr_t i=0;i<8;++i)assert(!pthread_create(writers+i,NULL,writer,(void *)(i+1)));
    for(unsigned i=0;i<8;++i)assert(!pthread_join(writers[i],NULL));
    atomic_store(&done,true);assert(!pthread_join(reader,NULL));
    gut_stop(&core,GUT_GPU_STOP);
    struct gut_event out[31];struct gut_meta m;uint32_t n,total=0;unsigned seen[8][200]={{0}};
    do {
        assert(gut_read(&core,out,31,&n,&m)&&!m.lost);
        for(unsigned i=0;i<n;++i) {
            assert(out[i].seq==++total);
            if(out[i].kind==GUT_REPORT)assert(out[i].id==1);
            else {
                assert(out[i].id>=1&&out[i].id<=8&&out[i].a<200);
                assert(out[i].b==(out[i].id^out[i].a));
                assert(!seen[out[i].id-1][out[i].a]++);
            }
        }
    } while(m.state!=GUT_DRAINED);
    assert(total==1601&&m.reason==GUT_GPU_STOP);
    for(unsigned i=0;i<8;++i)for(unsigned j=0;j<200;++j)assert(seen[i][j]==1);
}
static void *one_paused_writer(void *unused)
{(void)unused;gut_record(&core,GUT_API_BEGIN,9,7,0,1,2,3);return NULL;}
static struct gut_core *nested;
static bool emit_nested;
static uint64_t nested_clock(void *p)
{
    uint64_t now=clock_now(p);
    if(emit_nested){emit_nested=false;gut_record(nested,GUT_API_END,10,7,0,4,5,6);}
    return now;
}
static void kernel_boundaries(void)
{
    struct gut_event out[4096];struct gut_meta m;uint32_t n=999;
    configure(3,1000);writer((void *)1);
    assert(!gut_enabled(&core)&&gut_read(&core,out,4096,&n,&m));
    assert(n==3&&!m.lost&&m.reason==GUT_CAPACITY);
    configure(16,100);atomic_store(&ticks,core.end);
    assert(gut_read(&core,out,16,&n,&m)&&n==1&&m.reason==GUT_DEADLINE);
    configure(16,100);atomic_store(&ticks,core.start-1);
    assert(gut_read(&core,out,16,&n,&m)&&n==1&&m.reason==GUT_CLOCK);
    configure(16,100);core.busy=1;gut_record(&core,GUT_API_BEGIN,9,7,0,1,2,3);core.busy=0;
    gut_stop(&core,GUT_GPU_STOP);assert(gut_read(&core,out,16,&n,&m)&&n==2&&!m.lost);
    configure(16,100);core.busy=1;(void)gut_report(&core,98,99,0,0);core.busy=0;
    gut_stop(&core,GUT_GPU_STOP);assert(gut_read(&core,out,16,&n,&m)&&n==1&&m.lost==1);
    configure(16,100);nested=&core;core.clock=nested_clock;emit_nested=true;
    gut_record(&core,GUT_API_BEGIN,10,7,0,1,2,3);gut_stop(&core,GUT_GPU_STOP);
    assert(gut_read(&core,out,16,&n,&m)&&n==3&&!m.lost);
    assert(out[1].tick>out[2].tick); /* reservation order is not CPU clock order */
    configure(16,100);core.clock=paused_clock;pthread_t t;atomic_store(&pause_next,true);
    assert(!pthread_create(&t,NULL,one_paused_writer,NULL));
    while(!atomic_load(&paused))sched_yield();
    gut_stop(&core,GUT_GPU_STOP);n=999;m.count=999;out[0].seq=999;
    assert(!gut_read(&core,out,16,&n,&m)&&n==999&&m.count==999&&out[0].seq==999);
    atomic_store(&release_writer,true);assert(!pthread_join(t,NULL));
    assert(gut_read(&core,out,16,&n,&m)&&n==1&&!m.lost&&m.reason==GUT_GPU_STOP);
    /* A deadline closer must not hide a late pre-close writer filling the
     * final slot, or a clock fault that writer observed before suspension. */
    for(unsigned fault=0;fault<2;++fault) {
        configure(fault?16:2,100);core.clock=paused_clock;
        atomic_store(&paused,false);atomic_store(&release_writer,false);atomic_store(&pause_next,true);
        if(fault)atomic_store(&ticks,core.start-1);
        assert(!pthread_create(&t,NULL,one_paused_writer,NULL));
        while(!atomic_load(&paused))sched_yield();
        atomic_store(&ticks,core.end);
        assert(!gut_read(&core,out,16,&n,&m));
        atomic_store(&release_writer,true);assert(!pthread_join(t,NULL));
        assert(gut_read(&core,out,16,&n,&m)&&!m.lost);
        assert(m.reason==(fault?GUT_CLOCK:GUT_CAPACITY)&&n==(fault?1u:2u));
    }
}
static _Atomic unsigned sb_finished;
static unsigned sb_each;
static void *sb_writer(void *p)
{
    uint64_t base=(uintptr_t)p*100000;
    for(unsigned i=0;i<sb_each;++i) {
        struct rate_row row={.id=base+i,.check=(base+i)^UINT64_C(0xa55aa55a)};
        for(unsigned j=0;j<18;++j)row.payload[j]=row.id+j;
        while(!sb_trace_push(&q,&row))sched_yield(); /* test caller retries full; hook does not */
    }
    atomic_fetch_add(&sb_finished,1);return NULL;
}
static void sb_stream(unsigned each,bool concurrent_drain)
{
    sb_each=each;atomic_store(&sb_finished,0);pthread_t ts[8];
    for(uintptr_t i=0;i<8;++i)assert(!pthread_create(ts+i,NULL,sb_writer,(void *)(i+1)));
    if(!concurrent_drain)for(unsigned i=0;i<8;++i)assert(!pthread_join(ts[i],NULL));
    unsigned seen[8]={0},total=0;struct rate_row rows[17];
    do {
        unsigned n=sb_trace_take(&q,rows,17);
        for(unsigned i=0;i<n;++i) {
            struct rate_row *r=rows+i;unsigned producer=(unsigned)(r->id/100000)-1;
            assert(producer<8&&r->id%100000==seen[producer]++);
            assert(r->check==(r->id^UINT64_C(0xa55aa55a)));
            for(unsigned j=0;j<18;++j)assert(r->payload[j]==r->id+j);
            ++total;
        }
        if(!n)sched_yield();
    } while(total<8*each);
    if(concurrent_drain)for(unsigned i=0;i<8;++i)assert(!pthread_join(ts[i],NULL));
    assert(atomic_load(&sb_finished)==8&&atomic_load(&q.occupied)==0);
    for(unsigned i=0;i<8;++i)assert(seen[i]==each);
}
static void sb_boundaries(void)
{
    struct rate_row row={.id=123},out[SB_TRACE_ROWS];
    for(unsigned i=0;i<SB_TRACE_ROWS;++i)assert(sb_trace_push(&q,&row));
    assert(!sb_trace_push(&q,&row)&&atomic_load(&q.lost)==1);
    assert(sb_trace_take(&q,out,SB_TRACE_ROWS)==SB_TRACE_ROWS);
    assert(!sb_trace_take(&q,out,1)&&atomic_load(&q.occupied)==0);
    /* An interrupted head does not expose a partial row or release its slot. */
    uint64_t ticket=atomic_load(&q.head);atomic_store(&q.head,ticket+1);atomic_fetch_add(&q.occupied,1);
    assert(sb_trace_push(&q,&row)&&!sb_trace_take(&q,out,1));
    q.rows[ticket%SB_TRACE_ROWS]=row;atomic_store(&q.published[ticket%SB_TRACE_ROWS],ticket+1);
    assert(sb_trace_take(&q,out,2)==2&&atomic_load(&q.occupied)==0);
    atomic_store(&q.lost,0);
}
int main(void)
{
    kernel_parallel();kernel_boundaries();sb_boundaries();sb_stream(100,false);
    assert(!atomic_load(&q.lost));sb_stream(10000,true);
    atomic_store(&q.head,UINT64_MAX-SB_TRACE_ROWS);
    struct rate_row row={0};assert(!sb_trace_push(&q,&row)&&atomic_load(&q.exhausted));
    assert(!sb_trace_push(&q,&row));
    puts("337 actual kernel and SB queues: no-contention-loss, concurrent payload/order, full, reentry, interrupted publication, immutable freeze and counter exhaustion passed");
}
