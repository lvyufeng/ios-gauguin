/* Actual board heartbeat/ready/flag functions plus actual runtime core.
 * Register/power/route/lease endpoints are typed seams, never real hardware. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_gpu_runtime.h"
#include "gauguin_wdt_lease.h"
static struct ggr_context ggrb_context;
static bool ggrb_service;
static uint32_t ggrb_refreshes;
static unsigned checks;
#define CHECK(x) do{++checks;assert(x);}while(0)
static struct {
    int service,mode;
    bool live,routes,lease,busy,bad_eop,bad_shadow,bad_wptr;
    unsigned fault,health_calls,fail_health,ready_calls,fail_ready;
    unsigned lease_calls,quarantines,records;
    uint32_t sequence;
    uint64_t ns;
} model;
bool PE_parse_boot_argn(const char *key,void *out,size_t bytes)
{assert(!strcmp(key,"sweetgpuservice")&&bytes==sizeof(int));*(int *)out=model.service;return true;}
bool sweet_gpu_runtime_requested(void){return model.mode==12;}
static bool ggrb_live(void *unused)
{(void)unused;++model.ready_calls;return model.live&&model.ready_calls!=model.fail_ready;}
static bool ggrb_routes(void){return model.routes;}
static bool healthy(void *unused)
{(void)unused;++model.health_calls;return model.live&&model.health_calls!=model.fail_health;}
static uint64_t ns(void *unused){(void)unused;return ++model.ns;}
static bool read_reg(void *unused,uint32_t reg,uint32_t *v)
{
    (void)unused;assert(model.live);
    if(reg==0x201)*v=model.fault==1?1u<<1:0;
    else if(reg==0x823)*v=model.fault==2?1:0;
    else if(reg==0x807)*v=ggrb_context.wptr+(model.bad_wptr?1:0);
    else {assert(reg==0x23b0c);*v=model.busy?1u<<23:0;}
    return true;
}
static bool memory(void *unused,enum ggr_memory kind,uint32_t off,uint32_t *v)
{
    (void)unused;assert(model.live&&!off);
    if(kind==GGR_SHADOW)*v=ggrb_context.wptr+(model.bad_shadow?1:0);
    else {assert(kind==GGR_COMPLETION);*v=ggrb_context.completed+(model.bad_eop?1:0);}
    return true;
}
static void quarantine(void *unused)
{(void)unused;assert(!model.quarantines);++model.quarantines;model.live=false;}
bool gauguin_wdt_lease_refresh(struct gauguin_wdt_refresh_record *out)
{
    assert(ggrb_service&&model.live&&model.routes&&ggrb_context.state==GGR_READY);
    assert(!model.fault&&!model.busy&&!model.bad_eop&&!model.bad_shadow&&!model.bad_wptr);
    ++model.lease_calls;if(!model.lease)return false;
    *out=(struct gauguin_wdt_refresh_record){model.ns,++model.sequence,32780,10};return true;
}
static void gmb_record(const char *line)
{assert(strstr(line,"SWEET GPU SERVICE: renew=")&&strstr(line,"completed=3 shadow=56"));++model.records;}

@READY@
@REQUESTED@
@HEARTBEAT@

static void setup(void)
{
    memset(&model,0,sizeof(model));memset(&ggrb_context,0,sizeof(ggrb_context));
    model.service=1;model.mode=12;model.live=model.routes=model.lease=true;ggrb_service=true;
    ggrb_context.state=GGR_READY;ggrb_context.wptr=56;ggrb_context.submitted=ggrb_context.completed=3;
    ggrb_context.ops=(struct ggr_ops){.healthy=healthy,.nanoseconds=ns,.read_reg=read_reg,
        .read_memory=memory,.quarantine=quarantine};
}
int main(void)
{
    for(int flag=-1;flag<=2;flag++)for(int mode=0;mode<=13;mode++) {
        setup();model.service=flag;model.mode=mode;
        CHECK(sweet_gpu_service_requested()==(flag==1&&mode==12));
    }
    setup();ggrb_service=false;CHECK(!sweet_gpu_runtime_heartbeat()&&!model.lease_calls&&!model.ready_calls);
    setup();for(unsigned i=0;i<65;i++)CHECK(sweet_gpu_runtime_heartbeat());
    CHECK(model.lease_calls==65&&model.records==3&&!model.quarantines&&ggrb_refreshes==65);
    unsigned health_boundaries=model.health_calls/65;
    for(unsigned i=1;i<=health_boundaries;i++) {
        setup();model.fail_health=i;
        CHECK(!sweet_gpu_runtime_heartbeat()&&!model.lease_calls&&model.quarantines==1);
        CHECK(!sweet_gpu_runtime_heartbeat()&&!model.lease_calls&&model.quarantines==1);
    }
    for(unsigned i=1;i<=2;i++) {
        setup();model.fail_ready=i;
        CHECK(!sweet_gpu_runtime_heartbeat()&&!model.lease_calls&&model.quarantines==1);
    }
    for(unsigned fault=0;fault<7;fault++) {
        setup();
        if(fault<2)model.fault=fault+1;
        else if(fault==2)model.busy=true;
        else if(fault==3)model.bad_eop=true;
        else if(fault==4)model.bad_shadow=true;
        else if(fault==5)model.bad_wptr=true;
        else model.routes=false;
        CHECK(!sweet_gpu_runtime_heartbeat()&&!model.lease_calls&&model.quarantines==1);
    }
    setup();model.lease=false;
    CHECK(!sweet_gpu_runtime_heartbeat()&&model.lease_calls==1&&model.quarantines==1);
    CHECK(!sweet_gpu_runtime_heartbeat()&&model.lease_calls==1&&model.quarantines==1);
    printf("PASS: %u actual board heartbeat/ready/core assertions; no refresh after GPU/route/lease failure, host-only\n",checks);
    return 0;
}
