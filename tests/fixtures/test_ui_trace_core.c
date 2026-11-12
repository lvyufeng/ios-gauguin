#include "gauguin_ui_trace.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint64_t ticks;
static uint64_t clock_now(void *p){(void)p;return __atomic_fetch_add(&ticks,1,__ATOMIC_RELAXED);}
static struct gut_event store[4096];
static void configured(struct gut_core *c,uint32_t cap,uint32_t which,uint64_t window)
{memset(c,0,sizeof(*c));ticks=100;assert(gut_init(c,store,cap,which,window,clock_now,NULL));}
static uint64_t report(struct gut_core *c,uint32_t mask)
{uint64_t n=__atomic_load_n(&ticks,__ATOMIC_RELAXED);return gut_report(c,n-2,n-1,0,mask);}
static void no_publish(void)
{
 struct gut_core c={0};struct gut_event e={.seq=99};struct gut_meta m={.count=99};uint32_t n=99;
 assert(!gut_enabled(NULL)&&!gut_enabled(&c));gut_record(&c,10,1,2,3,4,5,6);gut_stop(&c,4);
 assert(!gut_read(&c,&e,1,&n,&m)&&n==99&&m.count==99&&e.seq==99);
 assert(!gut_init(&c,NULL,1,1,10,clock_now,NULL));assert(!gut_init(&c,store,1,1,10,clock_now,NULL));
 for(unsigned bad=0;bad<6;bad++) {
  memset(&c,0,sizeof(c));assert(!gut_init(&c,store,bad==0?0:bad==1?4097:16,
       bad==2?0:bad==3?17:1,bad==4?0:10,bad==5?NULL:clock_now,NULL));assert(!gut_enabled(&c));
 }
 configured(&c,16,2,1000);assert(!gut_init(&c,store,1,1,1,clock_now,NULL));
 assert(!gut_report(&c,100,99,0,1));assert(!gut_report(&c,1,2,1,1));assert(!gut_report(&c,1,2,0,1024));
 assert(c.gestures==0);assert(!report(&c,1));assert(!report(&c,1));assert(!report(&c,0));
 assert(report(&c,1)==1&&c.gestures==2&&c.count==1);
 assert(store[0].id==1&&store[0].kind==GUT_REPORT&&store[0].c==1&&store[0].reserved==0);
 assert(!gut_read(&c,&e,1,&n,&m)&&n==99&&m.count==99&&e.seq==99);
}
static void boundaries(void)
{
 struct gut_core c;struct gut_event out[16];struct gut_meta m;uint32_t n=777;
 configured(&c,3,1,100);assert(report(&c,1)==1);
 gut_record(&c,GUT_API_BEGIN,99,7,0,1,2,3);gut_record(&c,GUT_API_END,99,7,0,4,5,6);
 assert(!gut_enabled(&c));uint64_t snapshot=ticks;
 gut_record(&c,10,8,0,0,0,0,0);assert(ticks==snapshot&&c.count==3);
 assert(gut_read(&c,out,2,&n,&m)&&n==2&&m.reason==GUT_CAPACITY&&m.cursor==2&&m.state==GUT_FROZEN);
 assert(out[0].seq==1&&out[1].id==99);
 __atomic_fetch_add(&c.lost,100,__ATOMIC_RELAXED); // after closure cannot alter frozen loss
 assert(gut_read(&c,out,16,&n,&m)&&n==1&&m.lost==0&&m.state==GUT_DRAINED&&out[0].seq==3);
 assert(gut_read(&c,out,16,&n,&m)&&!n&&m.lost==0);
 configured(&c,16,1,10);report(&c,1);ticks=c.end;
 assert(gut_read(&c,out,16,&n,&m)&&m.reason==GUT_DEADLINE&&n==1);
 configured(&c,16,1,10);report(&c,1);ticks=c.start-1;gut_record(&c,10,1,0,0,0,0,0);
 assert(gut_read(&c,out,16,&n,&m)&&m.reason==GUT_CLOCK&&n==1);
 configured(&c,16,1,10);ticks=UINT64_MAX-5;assert(!report(&c,1));
 assert(gut_read(&c,out,16,&n,&m)&&m.reason==GUT_CLOCK&&!n);
 configured(&c,16,1,100);gut_stop(&c,GUT_GPU_STOP);
 assert(gut_read(&c,out,16,&n,&m)&&m.reason==GUT_GPU_STOP&&!n);
 configured(&c,16,1,100);report(&c,1);gut_stop(&c,GUT_GPU_STOP);gut_stop(&c,GUT_DEADLINE);
 assert(gut_read(&c,out,16,&n,&m)&&m.reason==GUT_GPU_STOP&&n==1);
}
static struct gut_core *reenter;
static bool nested_emit;
static uint64_t nested_clock(void *p)
{(void)p;if(nested_emit){nested_emit=false;gut_record(reenter,10,8,0,0,0,0,0);}return ticks++;}
static void contention(void)
{
 struct gut_core c={0};struct gut_event out[2];struct gut_meta m;uint32_t n;
 ticks=100;reenter=&c;assert(gut_init(&c,store,16,1,100,nested_clock,NULL));report(&c,1);
 nested_emit=true;gut_record(&c,10,8,0,0,0,0,0);gut_stop(&c,4);
 assert(gut_read(&c,out,2,&n,&m)&&m.lost==1&&n==2);
 configured(&c,16,1,100);report(&c,1);c.busy=1;n=777;m.count=777;
 assert(!gut_read(&c,out,1,&n,&m)&&n==777&&m.count==777);c.busy=0;
 assert((c.lost&~(UINT64_C(1)<<63))==0);gut_stop(&c,4);
 assert(gut_read(&c,out,1,&n,&m)&&m.lost==0);
}
static struct gut_core concurrent;
static void *writer(void *p)
{uint64_t id=(uintptr_t)p;for(unsigned i=0;i<10000;i++)gut_record(&concurrent,10,id,1,0,i,0,0);return NULL;}
static void threads(void)
{
 configured(&concurrent,4096,1,UINT64_C(1000000000));report(&concurrent,1);
 pthread_t t[8];for(uintptr_t i=0;i<8;i++)assert(!pthread_create(&t[i],NULL,writer,(void *)(i+1)));
 for(unsigned i=0;i<8;i++)assert(!pthread_join(t[i],NULL));
 /* The amount of contention is scheduler dependent. Finish the bounded
  * prefix serially if the competing writers did not fill it. */
 for(unsigned i=0;i<4096&&gut_enabled(&concurrent);i++)gut_record(&concurrent,10,9,1,0,i,0,0);
 struct gut_event out[17];struct gut_meta m;uint32_t n,total=0;uint64_t last=0;
 do {assert(gut_read(&concurrent,out,17,&n,&m));for(unsigned i=0;i<n;i++){
  assert(out[i].seq==++total&&out[i].tick>=last);last=out[i].tick;
 }}while(m.state!=GUT_DRAINED);
 assert(total==4096&&m.reason==GUT_CAPACITY);
}
int main(void){no_publish();boundaries();contention();threads();puts("actual UI trace core: boundaries, immutable prefix, reentry and eight writers passed");}
