/* Real old/new guard bodies; function seams record every hardware predicate. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uintptr_t vm_offset_t;
enum { GMB_READY=1, GMB_PAGE=0x4000, GGP_TABLE_OFFSET=0x4000, GMB_MIN=3 };
static unsigned checks, calls, fail_at, data_case;
static char trace[64];
static uint64_t root_memory[4],ggrb_end,ggrb_root;
static vm_offset_t gmb_ram,gmb_reset=0x10000;
static unsigned ggrb_started;
static struct { uint64_t pa; } gmb_stage;
#define CHECK(x) do { ++checks; assert(x); } while(0)
static bool event(char id) { assert(calls<sizeof(trace)); trace[calls++]=id; return calls!=fail_at; }
static bool gmb_thread(void) { return event('C'); }
static uint64_t mach_absolute_time(void) { return event('T')?0:ggrb_end; }
static bool sweet_gpu_runtime_requested(void) { return event('O'); }
static unsigned sweet_gmu_board_state(void) { return event('S')?GMB_READY:0; }
static bool sweet_pas_zap_owner_authenticated(uint64_t pa) { assert(pa==gmb_stage.pa); return event('A'); }
static bool gauguin_wdt_lease_check_budget(unsigned n) { assert(n==GMB_MIN); return event('B'); }
static bool ggwb_unsecured(void) { return event('U'); }
static bool sweet_gmu_clock_live(bool live,uint32_t *gx) {
    assert(live); *gx=data_case==2?0:0x80000000; return event('G');
}
static bool sweet_gmu_irq_quiet(uint32_t irq[3]) {
    irq[0]=0x11111111;irq[1]=data_case==3?0x1000:0;irq[2]=0x33333333;return event('I');
}
static bool gfw_faults(bool probe) { assert(!probe); return event('F'); }
static uint32_t gfw_load32(vm_offset_t address) { assert(address==gmb_reset+0x2000); return !event('R')||data_case==4; }

@HELPERS@
@BASELINE@
@LIVE@

static void setup(unsigned fail,unsigned kind) {
    calls=0;memset(trace,0,sizeof(trace));fail_at=fail;data_case=kind;
    ggrb_started=kind!=1;ggrb_end=1000;ggrb_root=0x200003;gmb_stage.pa=0x100000;
    gmb_ram=(vm_offset_t)root_memory;root_memory[1]=kind==5?0:ggrb_root;
    root_memory[3]=kind==6?0:((gmb_stage.pa+GGP_TABLE_OFFSET+0x1000)|3u);
}
static unsigned compare(unsigned fail,unsigned kind) {
    setup(fail,kind);bool before=baseline_live(NULL);unsigned count=calls;
    char previous[sizeof(trace)];memcpy(previous,trace,sizeof(trace));
    setup(fail,kind);memset(&ggrb_live_sample,0,sizeof(ggrb_live_sample));
    CHECK(ggrb_live(NULL)==before);CHECK(calls==count);CHECK(!memcmp(previous,trace,sizeof(trace)));
    CHECK((ggrb_live_sample.reason==0)==before);
    if(!before){
        struct ggrb_live_sample first=ggrb_live_sample;
        setup(0,0);CHECK(ggrb_live(NULL));CHECK(!memcmp(&first,&ggrb_live_sample,sizeof(first)));
    } else CHECK(ggrb_live_sample.valid==63);
    return count;
}
int main(void) {
    unsigned count=compare(0,0);CHECK(count==12);
    const unsigned reason[]={2,3,4,5,6,7,8,9,11,13,14,17};
    for(unsigned i=1;i<=count;++i){compare(i,0);CHECK(ggrb_live_sample.reason==reason[i-1]);}
    const unsigned data_reason[]={0,1,10,12,14,15,16};
    for(unsigned kind=1;kind<=6;++kind){compare(0,kind);CHECK(ggrb_live_sample.reason==data_reason[kind]);}
    setup(0,0);memset(&ggrb_live_sample,0,sizeof(ggrb_live_sample));CHECK(ggrb_live(NULL));
    CHECK(ggrb_note(1,0,0x23b13,1,true));CHECK(ggrb_last_op==1&&ggrb_last_offset==0x23b13&&ggrb_last_value==1&&ggrb_last_ok);
    setup(10,0);CHECK(!ggrb_live(NULL));CHECK(ggrb_live_sample.reason==13&&ggrb_live_sample.valid==3);
    CHECK(!ggrb_note(2,7,123,456,false));CHECK(ggrb_last_op==1&&ggrb_last_space==0&&ggrb_last_offset==0x23b13&&ggrb_last_value==1&&ggrb_last_ok);
    printf("runtime diagnostics: %u assertions; old/new predicate traces and sticky cached failure passed\n",checks);
}
