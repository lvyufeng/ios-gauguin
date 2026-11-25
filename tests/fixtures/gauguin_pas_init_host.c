/* Actual PAS INIT helper with typed CPU API and SMC/DSB seams only.
 * There is no firmware, physical buffer, device access or real sleep here. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <pthread.h>
#include "gauguin_pas_init.h"
#include "gauguin_bcm_transport.h"
#include "gauguin_wdt_lease.h"
#define GAUGUIN 1
#define NSEC_PER_SEC UINT64_C(1000000000)
#define CHECK(c,why) do { if(!(c)){fprintf(stderr,"FAIL line%d [%s]: %s\n",__LINE__,case_name,why);exit(1);} } while(0)
static const char *case_name="setup";
static unsigned cases;
static const char *const required[]={"sweetbusvote","sweetpasprobe","sweetpasstage"};
static const char *const disabled[]={"sweettouchmode","sweetwdtpet","sweetreboot","sweetbusprobe","sweetgpuprobe","sweetscmprobe","sweetwdttest"};
static struct sweet_pas_cpu_stage stage;
static struct {
    int requested,required[3],off[7],context;
    int mem_requested; bool mem_phase;
    unsigned allow_quarantined_budget,allow_repeat_quarantine,inflight_mem;
    enum gbcmt_state bcm;
    unsigned budget_calls,budget_fail_call,budget_live,calls,barriers,sleeps,quarantines;
    unsigned count,replies,lines,markers,flushes,last_return_lines,last_return_sleeps;
    unsigned expire_pre,expire_raw,lose_pre_budget,lose_raw_budget,lose_context,lose_bcm,pre_bcm;
    unsigned concurrent,mutate_input;
    uint64_t now,deadline,original_pa;
    struct gpi_registers scripted[80],last;
    char event,log[256][224];
} mock;
static int test_printf(const char *fmt,...)
{
    CHECK(mock.lines<256,"bounded log capacity");va_list ap;va_start(ap,fmt);
    int n=vsnprintf(mock.log[mock.lines],sizeof(mock.log[0]),fmt,ap);va_end(ap);
    CHECK(n>0 && (size_t)n<sizeof(mock.log[0]) && mock.log[mock.lines][n-1]=='\n',"bounded complete record");
    ++mock.lines;mock.event='L';return n;
}
bool PE_parse_boot_argn(const char *key,void *out,size_t size)
{
    CHECK(size==sizeof(int),"integer boot flags");
    if(!strcmp(key,"sweetpasinit")){*(int*)out=mock.requested;return true;}
    if(!strcmp(key,"sweetpasmem")){*(int*)out=mock.mem_requested;return true;}
    for(unsigned i=0;i<3;++i)if(!strcmp(key,required[i])){*(int*)out=mock.required[i];return true;}
    for(unsigned i=0;i<7;++i)if(!strcmp(key,disabled[i])){*(int*)out=mock.off[i];return true;}
    CHECK(false,"known boot flag");return false;
}
int ml_get_interrupts_enabled(void){return mock.context!=1;}
int ml_at_interrupt_context(void){return mock.context==2;}
int get_preemption_level(void){return mock.context==3 ? 1:0;}
unsigned long long mach_absolute_time(void){return mock.now;}
void clock_interval_to_deadline(unsigned amount,uint64_t scale,uint64_t *out)
{CHECK(amount==5 && scale==NSEC_PER_SEC && !mock.deadline,"one shared five-second deadline");mock.deadline=mock.now+5*NSEC_PER_SEC;*out=mock.deadline;}
void IOSleep(unsigned ms)
{
    CHECK(ms==30 && mock.calls && (int32_t)mock.last.x[0]==-12,"only fresh BUSY retry may sleep30ms");
    CHECK(mock.last.x[0]!=1,"continuation never sleeps");++mock.sleeps;mock.now+=30000000;mock.event='S';
}
void sweet_log_mark_sync(const char *line)
{CHECK(!mock.context && mock.lines && strstr(mock.log[mock.lines-1],line),"persist only in valid context");CHECK(mock.markers==mock.flushes,"previous marker flushed");++mock.markers;}
void sweet_log_flush_now(void)
{
    CHECK(!mock.context && mock.markers==mock.flushes+1,"one valid-context flush");++mock.flushes;mock.event='L';
    const char *line=mock.log[mock.lines-1];
    if(strstr(line,"before fresh=")){
        if(mock.expire_pre)mock.now=mock.deadline;
        if(mock.lose_pre_budget)mock.budget_live=0;
        if(mock.pre_bcm)mock.bcm=GBCMT_QUARANTINED;
    }
    if(strstr(line,"raw calls=")){
        if(mock.expire_raw)mock.now=mock.deadline;
        if(mock.lose_raw_budget)mock.budget_live=0;
    }
}
enum gbcmt_state sweet_bcm_transport_state(void){return mock.bcm;}
bool gauguin_wdt_lease_check_budget(uint32_t minimum)
{
    CHECK(!mock.quarantines || mock.allow_quarantined_budget,"no lease checks after terminal quarantine except in-flight failure propagation");
    CHECK(minimum==(mock.calls==0 ? 327650u:98295u),"initial10s then3s fresh budget");
    ++mock.budget_calls;mock.event='B';return !mock.quarantines && mock.budget_live && mock.budget_calls!=mock.budget_fail_call;
}
void gauguin_wdt_lease_quarantine(void)
{CHECK(!mock.quarantines || mock.allow_repeat_quarantine,"quarantine is software-only and idempotent for nested failed prerequisites");++mock.quarantines;mock.budget_live=0;}
static void fake_dsb(void)
{CHECK(mock.event=='B' && mock.now<mock.deadline,"DSB after latest guard, no intervening log");++mock.barriers;mock.event='D';}
struct competing_result { enum gpi_rc rc; struct gpi_receipt out; };
static void *competing_caller(void *opaque)
{
    struct competing_result *r=opaque;memset(&r->out,0xa5,sizeof(r->out));const struct gpi_receipt saved=r->out;
    r->rc=sweet_pas_init_image_once(&stage,&r->out);
    CHECK(r->rc==GPI_ALREADY && !memcmp(&r->out,&saved,sizeof(saved)),"concurrent caller cannot consume running attempt or output");return NULL;
}
struct competing_mem_result { enum gpi_rc rc; struct gpm_receipt out; };
static void *competing_mem_caller(void *opaque)
{
    struct competing_mem_result *r=opaque;memset(&r->out,0xa5,sizeof(r->out));const struct gpm_receipt saved=r->out;
    r->rc=sweet_pas_mem_setup_once(&r->out);
    CHECK(r->rc==GPI_ALREADY && !memcmp(&r->out,&saved,sizeof(saved)),"concurrent MEM caller cannot claim running stage");return NULL;
}
static void fake_invoke(struct gpi_registers *regs)
{
    CHECK(mock.event=='D' && mock.barriers==mock.calls+1,"exactly one DSB immediately before SMC");
    CHECK((mock.mem_phase ? sweet_pas_init_state()==GPI_COMPLETE && sweet_pas_mem_state()==GPM_RUNNING : sweet_pas_init_state()==GPI_RUNNING) && mock.calls<mock.replies,"correct active stage and bounded script");
    if(mock.calls && mock.last.x[0]==1){
        CHECK(!memcmp(regs,&mock.last,sizeof(*regs)),"continuation preserves ALL64bit x0..x6");
        CHECK(mock.lines==mock.last_return_lines && mock.sleeps==mock.last_return_sleeps,"tight continuation has no log/UFS/sleep");
    }else{
        const struct gpi_registers expected={{mock.mem_phase ? 0x42000202u:0x42000201u,
            mock.mem_phase ? 3u:0x82u,13,mock.original_pa,mock.mem_phase ? 4096u:0u,0,0}};
        CHECK(!memcmp(regs,&expected,sizeof(*regs)),"exact INIT/MEM fresh frame; MEM x4=4096 and BUSY discards x6/context");
    }
    if(mock.concurrent && mock.calls==0){
        pthread_t thread;struct competing_result result;struct competing_mem_result mem;
        CHECK(!pthread_create(&thread,NULL,mock.mem_phase ? competing_mem_caller:competing_caller,
            mock.mem_phase ? (void *)&mem:(void *)&result),"concurrent host claimant");
        CHECK(!pthread_join(thread,NULL),"join concurrent caller");
    }
    if(mock.inflight_mem && !mock.calls){
        struct gpm_receipt out;memset(&out,0xa5,sizeof(out));
        CHECK(sweet_pas_mem_setup_once(&out)==GPI_PREREQUISITE,"MEM cannot enter during actual in-flight INIT");
        CHECK(out.stage_pa==0 && !out.has_returned && !out.smc_calls && sweet_pas_mem_state()==GPM_QUARANTINED && sweet_pas_init_state()==GPI_RUNNING,"in-flight INIT private PA is never exported/used");
    }
    *regs=mock.scripted[mock.calls++];mock.last=*regs;mock.last_return_lines=mock.lines;mock.last_return_sleeps=mock.sleeps;mock.event='R';
    if(mock.lose_context)mock.context=(int)mock.lose_context;
    if(mock.lose_bcm)mock.bcm=GBCMT_QUARANTINED;
    if(mock.mutate_input)stage.pa=0; /* helper must retain its CPU copy, never restage */
}
#define printf test_printf
@SOURCE@
#undef printf
static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock));case_name=name;++cases;gpi_lifecycle=GPI_IDLE;gpm_lifecycle=GPM_IDLE;gpi_success_pa=0;
    mock.requested=mock.budget_live=mock.replies=1;mock.now=1;mock.bcm=GBCMT_COMPLETE;
    for(unsigned i=0;i<3;++i)mock.required[i]=1;
    stage=(struct sweet_pas_cpu_stage){UINT64_C(0x94000000),6860,16384};mock.original_pa=stage.pa;
    for(unsigned i=0;i<80;++i)for(unsigned r=2;r<7;++r)mock.scripted[i].x[r]=UINT64_C(0x1234567800000000)+(i<<8)+r;
}
static struct gpi_receipt check_result(enum gpi_rc wanted,unsigned calls,unsigned fresh,unsigned continuations)
{
    struct gpi_receipt out;memset(&out,0xa5,sizeof(out));
    enum gpi_rc rc=sweet_pas_init_image_once(&stage,&out);
    if(rc!=wanted)fprintf(stderr,"actualrc=%u wanted=%u calls=%u\n",rc,wanted,mock.calls);
    CHECK(rc==wanted && mock.calls==calls && mock.barriers==calls,"result/call/barrier counts");
    CHECK(out.stage_pa==mock.original_pa && out.has_returned==(calls ? 1u:0u) && out.smc_calls==calls && out.fresh_attempts==fresh && out.continuations==continuations,"deterministic terminal receipt");
    struct gpi_registers zero={{0}};CHECK(!memcmp(&out.returned,calls ? &mock.last:&zero,sizeof(zero)),"full raw x0..x6, including nonzero upper bits");
    CHECK(sweet_pas_init_state()==(wanted==GPI_OK ? GPI_COMPLETE:GPI_QUARANTINED) && mock.quarantines==(wanted==GPI_OK ? 0u:(mock.inflight_mem ? 2u:1u)),"terminal state and software quarantine");
    const struct gpi_receipt saved=out;CHECK(sweet_pas_init_image_once(&stage,&out)==GPI_ALREADY && !memcmp(&saved,&out,sizeof(out)),"no retry after any terminal result");
    CHECK(mock.calls==calls,"no extra SMC after terminal result");return out;
}
static void mem_phase_reset(uint64_t saved_pa, bool failed_init)
{
    /* Only the platform-script phase resets here. Production lifecycle and
     * private publication remain exactly as the actual INIT call left them. */
    uint64_t now=mock.now;
    memset(&mock,0,sizeof(mock));mock.mem_phase=true;
    mock.requested=mock.mem_requested=mock.replies=1;mock.budget_live=!failed_init;
    mock.bcm=GBCMT_COMPLETE;mock.now=now;mock.original_pa=saved_pa;
    for(unsigned i=0;i<3;++i)mock.required[i]=1;
    if(failed_init){mock.quarantines=1;mock.allow_repeat_quarantine=1;}
    for(unsigned i=0;i<80;++i)for(unsigned r=2;r<7;++r)mock.scripted[i].x[r]=UINT64_C(0x9876543200000000)+(i<<8)+r;
}
static void mem_begin(const char *name,uint64_t pa)
{
    reset(name);stage.pa=mock.original_pa=pa;
    struct gpi_receipt init=check_result(GPI_OK,1,1,0);
    CHECK(sweet_pas_init_state()==GPI_COMPLETE && gpi_success_pa==pa,"actual INIT publishes private PA");
    init.stage_pa=UINT64_C(0x12300000); /* caller receipt is not MEM authority */
    stage=(struct sweet_pas_cpu_stage){0,0,0}; /* nor is the former input */
    CHECK(init.stage_pa!=pa,"caller receipt mutated deliberately");
    mem_phase_reset(pa,false);
}
static void mem_check(enum gpi_rc wanted,unsigned calls,unsigned fresh,unsigned cont,bool knows_pa)
{
    enum gpi_state prior=sweet_pas_init_state();unsigned quarantines=mock.quarantines;
    struct gpm_receipt out;memset(&out,0xa5,sizeof(out));
    enum gpi_rc rc=sweet_pas_mem_setup_once(&out);
    if(rc!=wanted)fprintf(stderr,"MEM rc=%u expected=%u calls=%u\n",rc,wanted,mock.calls);
    CHECK(rc==wanted && mock.calls==calls && mock.barriers==calls,"MEM result and call/barrier counts");
    CHECK(out.stage_pa==(knows_pa ? mock.original_pa:0) && out.region_bytes==4096 && out.has_returned==(calls ? 1u:0u) && out.smc_calls==calls && out.fresh_attempts==fresh && out.continuations==cont,"typed MEM receipt, no speculative PA");
    struct gpi_registers zero={{0}};CHECK(!memcmp(&out.returned,calls ? &mock.last:&zero,sizeof(zero)),"MEM full7register return or deterministic zero");
    CHECK(sweet_pas_init_state()==prior,"MEM never rewrites INIT historical state");
    CHECK(sweet_pas_mem_state()==(wanted==GPI_OK ? GPM_COMPLETE:GPM_QUARANTINED) && mock.quarantines==quarantines+(wanted==GPI_OK ? 0u:1u),"independent MEM/WDT terminal state");
    const struct gpm_receipt saved=out;CHECK(sweet_pas_mem_setup_once(&out)==GPI_ALREADY && !memcmp(&saved,&out,sizeof(out)) && mock.calls==calls,"MEM no retry/output overwrite");
    if(prior==GPI_COMPLETE){
        struct gpi_receipt old,saved_old;memset(&old,0xa5,sizeof(old));saved_old=old;
        CHECK(sweet_pas_init_image_once(&stage,&old)==(mock.requested==1 ? GPI_ALREADY:GPI_OFF) && !memcmp(&old,&saved_old,sizeof(old)),"MEM does not reopen INIT");
        CHECK(gpi_success_pa==mock.original_pa,"private INIT PA remains immutable");
    }
}
int main(void)
{
    const int off[]={0,2,-1};
    for(unsigned i=0;i<3;++i){reset("exact opt-in");mock.requested=off[i];struct gpi_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;CHECK(!sweet_pas_init_requested() && sweet_pas_init_image_once(&stage,&out)==GPI_OFF && !memcmp(&out,&saved,sizeof(out)),"OFF unchanged");CHECK(sweet_pas_init_state()==GPI_IDLE && !mock.calls && !mock.lines,"OFF no work");}
    reset("NULL pointers");struct gpi_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;CHECK(sweet_pas_init_image_once(NULL,&out)==GPI_ARGUMENT && !memcmp(&out,&saved,sizeof(out)) && sweet_pas_init_image_once(&stage,NULL)==GPI_ARGUMENT && sweet_pas_init_state()==GPI_IDLE,"NULL no consumed attempt");
    reset("strict successful INIT only");check_result(GPI_OK,1,1,0);
    reset("highest aligned below4G dynamic PA");stage.pa=mock.original_pa=UINT64_C(0xfff00000);check_result(GPI_OK,1,1,0);
    reset("concurrent attempt while SMC active");mock.concurrent=1;check_result(GPI_OK,1,1,0);
    for(int c=1;c<=3;++c){reset("invalid context");mock.context=c;check_result(GPI_CONTEXT,0,0,0);}
    for(unsigned flag=0;flag<3;++flag)for(unsigned i=0;i<3;++i){reset("missing required flag");mock.required[flag]=off[i];check_result(GPI_CONFIG,0,0,0);}
    for(unsigned flag=0;flag<7;++flag)for(int v=-1;v<=1;v+=2){reset("conflicting probe/writer");mock.off[flag]=v;check_result(GPI_CONFIG,0,0,0);}
    for(unsigned bad=0;bad<7;++bad){reset("invalid stage geometry");if(bad==0)stage.pa=0;if(bad==1)stage.pa++;if(bad==2)stage.pa=UINT64_C(0x100000000);if(bad==3)stage.metadata_bytes--;if(bad==4)stage.metadata_bytes++;if(bad==5)stage.reserved_bytes--;if(bad==6)stage.reserved_bytes++;mock.original_pa=stage.pa;check_result(GPI_PREREQUISITE,0,0,0);}
    for(unsigned s=GBCMT_IDLE;s<=GBCMT_QUARANTINED;++s)if(s!=GBCMT_COMPLETE){reset("BCM not COMPLETE");mock.bcm=(enum gbcmt_state)s;check_result(GPI_PREREQUISITE,0,0,0);}
    reset("BCM changes during prelog");mock.pre_bcm=1;check_result(GPI_PREREQUISITE,0,0,0);
    reset("initial10s budget fails");mock.budget_fail_call=1;check_result(GPI_BUDGET,0,0,0);
    reset("prelog consumes deadline");mock.expire_pre=1;check_result(GPI_TIMEOUT,0,0,0);
    reset("prelog consumes WDT budget");mock.lose_pre_budget=1;check_result(GPI_BUDGET,0,0,0);
    reset("raw terminal logs consume deadline");mock.expire_raw=1;check_result(GPI_TIMEOUT,1,1,0);
    reset("raw terminal logs consume WDT budget");mock.lose_raw_budget=1;check_result(GPI_BUDGET,1,1,0);
    for(unsigned c=1;c<=3;++c){reset("context lost during call");mock.lose_context=c;check_result(GPI_CONTEXT,1,1,0);}
    reset("BCM completion lost after call");mock.lose_bcm=1;check_result(GPI_PREREQUISITE,1,1,0);
    const uint64_t transport_errors[]={2,UINT64_MAX,UINT64_C(0x100000000),UINT64_C(0x100000001)};
    for(unsigned i=0;i<4;++i){reset("nonzero full64 transport");mock.scripted[0].x[0]=transport_errors[i];check_result(GPI_TRANSPORT,1,1,0);}
    const uint64_t service_errors[]={1,UINT64_MAX,UINT64_C(0x100000000)};
    for(unsigned i=0;i<3;++i){reset("nonzero full64 service");mock.scripted[0].x[1]=service_errors[i];check_result(GPI_SERVICE,1,1,0);}
    reset("eight tight continuations then success");mock.replies=9;for(unsigned i=0;i<8;++i)mock.scripted[i].x[0]=1;check_result(GPI_OK,9,1,8);CHECK(!mock.sleeps && mock.lines==4,"continuations have no intermediate UFS/log/sleep");
    reset("global continuation cap");mock.replies=9;for(unsigned i=0;i<9;++i)mock.scripted[i].x[0]=1;check_result(GPI_CONTINUATION_LIMIT,9,1,8);
    reset("continuation budget expires");mock.scripted[0].x[0]=1;mock.budget_fail_call=2;check_result(GPI_BUDGET,1,1,0);
    const uint64_t busy_codes[]={UINT64_C(0xfffffffffffffff4),UINT64_C(0x00000000fffffff4),UINT64_C(0x87654321fffffff4)};
    for(unsigned i=0;i<3;++i){reset("native int BUSY fresh reset");mock.replies=2;mock.scripted[0].x[0]=busy_codes[i];mock.scripted[0].x[1]=123;mock.mutate_input=1;check_result(GPI_OK,2,2,0);CHECK(mock.sleeps==1,"one native30ms fresh retry");}
    reset("68 total fresh BUSY attempts");mock.replies=68;for(unsigned i=0;i<68;++i)mock.scripted[i].x[0]=UINT64_C(0xfffffffffffffff4);check_result(GPI_BUSY_LIMIT,68,68,0);CHECK(mock.sleeps==67,"no needless sleep after terminal busy cap");
    reset("continuation cap shared across BUSY restarts");mock.replies=10;for(unsigned i=0;i<10;++i)mock.scripted[i].x[0]=1;mock.scripted[4].x[0]=UINT64_C(0xfffffffffffffff4);check_result(GPI_CONTINUATION_LIMIT,10,2,8);CHECK(mock.sleeps==1,"only BUSY causes sleep");
    unsigned old_cases=cases;CHECK(old_cases==69,"all69 original INIT cases retained");
    reset("MEM disabled before INIT");struct gpm_receipt mem,saved_mem;memset(&mem,0xa5,sizeof(mem));saved_mem=mem;
    CHECK(sweet_pas_mem_setup_once(&mem)==GPI_OFF && !memcmp(&mem,&saved_mem,sizeof(mem)) && sweet_pas_mem_state()==GPM_IDLE,"default MEM off has no effect");
    for(unsigned i=0;i<3;++i){mem_begin("MEM exact opt-in after actual INIT",UINT64_C(0x94000000));mock.mem_requested=off[i];memset(&mem,0xa5,sizeof(mem));saved_mem=mem;CHECK(!sweet_pas_mem_requested() && sweet_pas_mem_setup_once(&mem)==GPI_OFF && !memcmp(&mem,&saved_mem,sizeof(mem)) && !mock.calls && sweet_pas_mem_state()==GPM_IDLE,"off MEM preserves receipt/attempt and INIT");}
    mem_begin("MEM NULL does not claim",UINT64_C(0x94000000));CHECK(sweet_pas_mem_setup_once(NULL)==GPI_ARGUMENT && sweet_pas_mem_state()==GPM_IDLE,"NULL MEM unchanged");mem_check(GPI_OK,1,1,0,true);
    reset("MEM while INIT IDLE");mock.mem_requested=1;mock.mem_phase=true;mem_check(GPI_PREREQUISITE,0,0,0,false);CHECK(gpi_success_pa==0,"no INIT PA publication");
    reset("MEM during actual INIT SMC");mock.mem_requested=mock.inflight_mem=mock.allow_quarantined_budget=mock.allow_repeat_quarantine=1;
    check_result(GPI_BUDGET,1,1,0);CHECK(!gpi_success_pa && sweet_pas_mem_state()==GPM_QUARANTINED,"in-flight refusal and failed INIT never publish PA");
    memset(&mem,0xa5,sizeof(mem));saved_mem=mem;CHECK(sweet_pas_mem_setup_once(&mem)==GPI_ALREADY && !memcmp(&mem,&saved_mem,sizeof(mem)),"MEM cannot retry after premature call");
    reset("failed INIT never authorizes MEM");mock.scripted[0].x[1]=1;check_result(GPI_SERVICE,1,1,0);mem_phase_reset(0,true);mem_check(GPI_PREREQUISITE,0,0,0,false);CHECK(!gpi_success_pa,"failed INIT private PA stays zero");
    mem_begin("actual INIT then MEM immutable PA",UINT64_C(0x98200000));mem_check(GPI_OK,1,1,0,true);
    mem_begin("actual INIT last valid base then MEM",UINT64_C(0xfff00000));mem_check(GPI_OK,1,1,0,true);
    mem_begin("concurrent second MEM caller",UINT64_C(0x94000000));mock.concurrent=1;mem_check(GPI_OK,1,1,0,true);
    for(int c=1;c<=3;++c){mem_begin("MEM invalid context",UINT64_C(0x94000000));mock.context=c;mem_check(GPI_CONTEXT,0,0,0,false);}
    for(unsigned i=0;i<3;++i){mem_begin("MEM requires INIT flag1",UINT64_C(0x94000000));mock.requested=off[i];mem_check(GPI_CONFIG,0,0,0,false);}
    for(unsigned flag=0;flag<3;++flag)for(unsigned i=0;i<3;++i){mem_begin("MEM required flags",UINT64_C(0x94000000));mock.required[flag]=off[i];mem_check(GPI_CONFIG,0,0,0,false);}
    for(unsigned flag=0;flag<7;++flag)for(int v=-1;v<=1;v+=2){mem_begin("MEM conflicting diagnostic",UINT64_C(0x94000000));mock.off[flag]=v;mem_check(GPI_CONFIG,0,0,0,false);}
    for(unsigned state=GBCMT_IDLE;state<=GBCMT_QUARANTINED;++state)if(state!=GBCMT_COMPLETE){mem_begin("MEM requires BCM COMPLETE",UINT64_C(0x94000000));mock.bcm=(enum gbcmt_state)state;mem_check(GPI_PREREQUISITE,0,0,0,true);}
    mem_begin("MEM prelog deadline expiry",UINT64_C(0x94000000));mock.expire_pre=1;mem_check(GPI_TIMEOUT,0,0,0,true);
    mem_begin("MEM prelog lease expiry",UINT64_C(0x94000000));mock.lose_pre_budget=1;mem_check(GPI_BUDGET,0,0,0,true);
    mem_begin("MEM prelog BCM loss",UINT64_C(0x94000000));mock.pre_bcm=1;mem_check(GPI_PREREQUISITE,0,0,0,true);
    mem_begin("MEM rawlog deadline expiry",UINT64_C(0x94000000));mock.expire_raw=1;mem_check(GPI_TIMEOUT,1,1,0,true);
    mem_begin("MEM rawlog lease expiry",UINT64_C(0x94000000));mock.lose_raw_budget=1;mem_check(GPI_BUDGET,1,1,0,true);
    for(unsigned i=0;i<4;++i){mem_begin("MEM full64 transport error",UINT64_C(0x94000000));mock.scripted[0].x[0]=transport_errors[i];mem_check(GPI_TRANSPORT,1,1,0,true);}
    for(unsigned i=0;i<3;++i){mem_begin("MEM full64 service error",UINT64_C(0x94000000));mock.scripted[0].x[1]=service_errors[i];mem_check(GPI_SERVICE,1,1,0,true);}
    mem_begin("MEM eight tight continuations success",UINT64_C(0x94000000));mock.replies=9;for(unsigned i=0;i<8;++i)mock.scripted[i].x[0]=1;mem_check(GPI_OK,9,1,8,true);CHECK(!mock.sleeps && mock.lines==4,"MEM continuation no logs/sleep");
    mem_begin("MEM continuation cap",UINT64_C(0x94000000));mock.replies=9;for(unsigned i=0;i<9;++i)mock.scripted[i].x[0]=1;mem_check(GPI_CONTINUATION_LIMIT,9,1,8,true);
    mem_begin("MEM continuation budget loss",UINT64_C(0x94000000));mock.scripted[0].x[0]=1;mock.budget_fail_call=2;mem_check(GPI_BUDGET,1,1,0,true);
    for(unsigned i=0;i<3;++i){mem_begin("MEM BUSY fresh x4/x6 frame",UINT64_C(0x94000000));mock.replies=2;mock.scripted[0].x[0]=busy_codes[i];mock.scripted[0].x[1]=55;mem_check(GPI_OK,2,2,0,true);CHECK(mock.sleeps==1,"MEM fresh30ms retry");}
    mem_begin("MEM fresh BUSY cap",UINT64_C(0x94000000));mock.replies=68;for(unsigned i=0;i<68;++i)mock.scripted[i].x[0]=UINT64_C(0xfffffffffffffff4);mem_check(GPI_BUSY_LIMIT,68,68,0,true);CHECK(mock.sleeps==67,"MEM bounded BUSY");
    mem_begin("MEM total continuation cap across BUSY",UINT64_C(0x94000000));mock.replies=10;for(unsigned i=0;i<10;++i)mock.scripted[i].x[0]=1;mock.scripted[4].x[0]=UINT64_C(0xfffffffffffffff4);mem_check(GPI_CONTINUATION_LIMIT,10,2,8,true);
    printf("PASS: originalINIT=%u MEM_additions=%u; actualINITpublication feedsMEM, one shared bounded engine\n",old_cases,cases-old_cases);
    printf("PASS: %u actual PAS INIT host cases; fixed ABI, full returns, tight continuation and bounded fresh retry; no secure call executed\n",cases);return 0;
}
