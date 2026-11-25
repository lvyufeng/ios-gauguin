/* Execute the production first-device wait with a virtual clock/transport. MIT. */
#include "../graphics/hakios-metal-ca/desktop-overlay/userland/src/GauguinMetalBootstrapWait.h"
#include <stdio.h>
#include <string.h>
struct model {uint64_t now,cost;unsigned ready,opens,clocks,sleeps,closes,failclock,backclock;bool freeze,failsleep;int token;};
static bool clock_model(void *p,uint64_t *out){struct model *m=p;m->clocks++;if(m->clocks==m->failclock)return false;*out=m->now;if(m->clocks==m->backclock)*out-=2;return true;}
static bool sleep_model(void *p,uint64_t ns){struct model *m=p;m->sleeps++;if(m->failsleep)return false;if(!m->freeze)m->now+=ns;return true;}
static void *open_model(void *p){struct model *m=p;m->opens++;m->now+=m->cost;return m->opens==m->ready?&m->token:NULL;}
static void close_model(void *p,void *v){struct model *m=p;if(v!=&m->token)__builtin_trap();m->closes++;}
static unsigned checks;
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"line%d failed\n",__LINE__);return 1;}}while(0)
int main(void)
{
    struct model m={0};struct gauguin_metal_wait_result r;
    struct gauguin_metal_wait_ops ops={&m,clock_model,sleep_model,open_model,close_model};
    CHECK(!gauguin_metal_wait_open(NULL,&r)&&r.reason==GMW_ARGUMENT);
    CHECK(!gauguin_metal_wait_open(&ops,NULL));
    m=(struct model){.ready=1,.cost=1};CHECK(gauguin_metal_wait_open(&ops,&r)==&m.token&&r.reason==GMW_READY&&r.attempts==1&&r.elapsed_ns==1&&!m.sleeps&&!m.closes);
    m=(struct model){.ready=5,.cost=1};CHECK(gauguin_metal_wait_open(&ops,&r)==&m.token&&r.attempts==5&&r.elapsed_ns==400000005&&!m.closes);
    m=(struct model){.ready=GAUGUIN_METAL_OPEN_ATTEMPTS};CHECK(gauguin_metal_wait_open(&ops,&r)==&m.token&&r.elapsed_ns==GAUGUIN_METAL_OPEN_BUDGET_NS&&m.sleeps==GAUGUIN_METAL_OPEN_ATTEMPTS-1);
    m=(struct model){0};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_TIMEOUT&&m.opens==GAUGUIN_METAL_OPEN_ATTEMPTS&&m.sleeps==GAUGUIN_METAL_OPEN_ATTEMPTS-1);
    m=(struct model){.ready=1,.cost=GAUGUIN_METAL_OPEN_BUDGET_NS+1};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_TIMEOUT&&m.closes==1);
    m=(struct model){.failclock=1};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_CLOCK&&!m.opens);
    m=(struct model){.ready=1,.failclock=3};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_CLOCK&&m.closes==1);
    m=(struct model){.now=10,.ready=1,.cost=1,.backclock=3};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_CLOCK&&m.closes==1);
    m=(struct model){.freeze=true};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_ATTEMPTS&&m.opens==GAUGUIN_METAL_OPEN_ATTEMPTS&&m.sleeps==GAUGUIN_METAL_OPEN_ATTEMPTS-1);
    m=(struct model){.failsleep=true};CHECK(!gauguin_metal_wait_open(&ops,&r)&&r.reason==GMW_SLEEP&&m.opens==1);
    m=(struct model){.now=UINT64_MAX-2,.ready=1,.cost=1};CHECK(gauguin_metal_wait_open(&ops,&r)==&m.token&&r.elapsed_ns==1);
    for(unsigned n=1;n<=1000;n++) {
        unsigned ready=(n*193)%2000+1,cost=(n*79)%1000;
        m=(struct model){.ready=ready,.cost=cost};void *device=gauguin_metal_wait_open(&ops,&r);
        uint64_t completion=(uint64_t)(ready-1)*GAUGUIN_METAL_OPEN_STEP_NS+(uint64_t)ready*cost;
        bool expected=ready<=GAUGUIN_METAL_OPEN_ATTEMPTS&&completion<=GAUGUIN_METAL_OPEN_BUDGET_NS;
        CHECK((device!=NULL)==expected);CHECK(m.opens<=GAUGUIN_METAL_OPEN_ATTEMPTS&&m.sleeps<GAUGUIN_METAL_OPEN_ATTEMPTS);
        if(expected){CHECK(r.reason==GMW_READY&&r.elapsed_ns==completion&&!m.closes);}
    }
    printf("%u actual first-device wait checks passed; virtual clock, no GPU\n",checks);return 0;
}
