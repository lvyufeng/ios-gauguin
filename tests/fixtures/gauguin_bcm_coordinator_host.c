/* Actual coordinator; typed CPU API seams only. Every wait uses a fake clock.
 * This exercises ordering/error propagation, not hardware/reset/PAS execution. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "gauguin_pas_stage.h"
#include "gauguin_bus_probe.h"
#include "gauguin_bcm_transport.h"
#include "gauguin_wdt_lease.h"
#define GAUGUIN 1
#define KERN_SUCCESS 0
#define NSEC_PER_SEC UINT64_C(1000000000)
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *,wait_result_t);
#define CHECK(c,why) do { if(!(c)) { fprintf(stderr,"FAIL line %d [%s]: %s\n",__LINE__,case_name,why);exit(1); } } while(0)
static const char *case_name="setup";
static unsigned cases;
static const char *const off_flags[]={"sweettouchmode","sweetwdtpet","sweetreboot",
    "sweetbusprobe","sweetgpuprobe","sweetscmprobe","sweetwdttest"};
static struct {
    int requested,off[7],probe,stage,context,late_context,after_plan_context,thread_error;
    unsigned starts,deallocations,terminations,before_sleeps,claim_sleeps,after_sleeps;
    unsigned claims,ready_after,claimed,plans,arms,transactions,quarantines,state_queries;
    unsigned plan_fail,arm_fail,frozen_wait_clock,markers,flushes,lines;
    uint64_t now;
    struct sweet_pas_cpu_stage ready;
    struct gbcm_plan plan;
    struct gbcmt_receipt receipt;
    enum gbcmt_rc tx_result;
    thread_continue_t worker;
    char order[8],log[32][224];unsigned order_count;
} mock;
static void order(char step)
{ CHECK(mock.order_count<sizeof(mock.order)-1,"bounded API sequence");mock.order[mock.order_count++]=step; }
static int test_printf(const char *fmt,...)
{
    va_list ap;int n;CHECK(mock.lines<32,"bounded logs");
    va_start(ap,fmt);n=vsnprintf(mock.log[mock.lines],sizeof(mock.log[0]),fmt,ap);va_end(ap);
    CHECK(n>0 && (size_t)n<sizeof(mock.log[0]) && mock.log[mock.lines][n-1]=='\n',"bounded newline record");++mock.lines;return n;
}
bool PE_parse_boot_argn(const char *key,void *out,size_t bytes)
{
    CHECK(bytes==sizeof(int),"integer argument");
    if(!strcmp(key,"sweetpasprobe")){*(int*)out=mock.probe;return true;}
    if(!strcmp(key,"sweetpasstage")){*(int*)out=mock.stage;return true;}
    for(unsigned i=0;i<7;++i)if(!strcmp(key,off_flags[i])){*(int*)out=mock.off[i];return true;}
    CHECK(false,"known flag");return false;
}
bool sweet_bcm_vote_requested(void){return mock.requested==1;}
kern_return_t kernel_thread_start(thread_continue_t fn,void *arg,thread_t *thread)
{
    CHECK(!arg,"null thread argument");++mock.starts;
    if(mock.thread_error)return mock.thread_error;
    mock.worker=fn;*thread=(thread_t)(uintptr_t)1;return KERN_SUCCESS;
}
void thread_deallocate(thread_t thread){CHECK(thread==(thread_t)(uintptr_t)1,"known thread");++mock.deallocations;}
void thread_terminate_self(void){++mock.terminations;}
int ml_get_interrupts_enabled(void){return mock.context!=1;}
int ml_at_interrupt_context(void){return mock.context==2;}
int get_preemption_level(void){return mock.context==3 ? 1:0;}
unsigned long long mach_absolute_time(void){return mock.now;}
void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *deadline)
{CHECK(n==5 && scale==NSEC_PER_SEC && mock.before_sleeps==45,"five-second ready wait after delay");*deadline=mock.now+5*NSEC_PER_SEC;}
void IOSleep(unsigned ms)
{
    if(mock.before_sleeps<45){
        CHECK(ms==1000 && !mock.claims && !mock.plans && !mock.arms && !mock.transactions,"45s before experiment");
        ++mock.before_sleeps;mock.now+=NSEC_PER_SEC;
        if(mock.before_sleeps==45)mock.context=mock.late_context;
    }else if(!mock.transactions){
        CHECK(ms==10 && !mock.claimed && !mock.plans && !mock.arms,"only unclaimed READY wait uses10ms");
        CHECK(mock.claim_sleeps<500,"bounded500 ready waits");++mock.claim_sleeps;
        if(!mock.frozen_wait_clock)mock.now+=10000000;
    }else{
        CHECK(ms==1000 && mock.tx_result==GBCMT_OK && !mock.quarantines,"only successful transfer waits for reset");
        CHECK(mock.after_sleeps<30,"bounded30 requested seconds");++mock.after_sleeps;mock.now+=NSEC_PER_SEC;
    }
}
void sweet_log_mark_sync(const char *line)
{
    CHECK(!mock.context && mock.lines && strstr(mock.log[mock.lines-1],line),"valid-context marker matches record");
    CHECK(mock.markers==mock.flushes,"previous marker flushed");++mock.markers;
}
void sweet_log_flush_now(void){CHECK(!mock.context && mock.markers==mock.flushes+1,"valid context one flush");++mock.flushes;}
bool sweet_pas_cpu_stage_claim(struct sweet_pas_cpu_stage *out)
{
    CHECK(out && mock.before_sleeps==45 && !mock.claimed && !mock.plans && !mock.arms && !mock.transactions,"READY first");
    ++mock.claims;
    if(mock.ready_after==0 || mock.claims<mock.ready_after)return false;
    *out=mock.ready;mock.claimed=1;order('R');return true;
}
bool sweet_bus_plan_prepare(struct gbcm_plan *out)
{
    CHECK(out && mock.claimed && !mock.plans && !mock.arms && !mock.transactions,"fresh plan after claim before WDT");
    ++mock.plans;order('P');if(mock.plan_fail)return false;
    *out=mock.plan;mock.context=mock.after_plan_context;return true;
}
bool gauguin_wdt_lease_arm(struct gauguin_wdt_lease_record *out)
{
    CHECK(out && !mock.context && mock.claimed && mock.plans==1 && !mock.arms && !mock.transactions,"arm only after stage/plan");
    ++mock.arms;order('W');if(mock.arm_fail)return false;
    *out=(struct gauguin_wdt_lease_record){mock.now,mock.now+NSEC_PER_SEC,32765,655300,753595,32765};return true;
}
enum gbcmt_rc sweet_bcm_submit_once(const struct gbcm_plan *input,struct gbcmt_receipt *out)
{
    CHECK(input && out && mock.arms==1 && !mock.arm_fail && !mock.transactions && !mock.quarantines,"TX only once after armed lease");
    CHECK(!memcmp(input,&mock.plan,sizeof(*input)),"exact prepared plan passed unchanged");
    ++mock.transactions;order('T');if(mock.tx_result==GBCMT_OK)*out=mock.receipt;return mock.tx_result;
}
void gauguin_wdt_lease_quarantine(void)
{
    CHECK(mock.transactions==1 && !mock.quarantines,"only after attempted transfer, no duplicate coordinator quarantine");
    CHECK(mock.tx_result!=GBCMT_OK || mock.after_sleeps==30,"success quarantine only after unqualified timeout");
    ++mock.quarantines;order('Q');
}
enum gbcmt_state sweet_bcm_transport_state(void)
{CHECK(mock.transactions==1 && mock.tx_result!=GBCMT_OK,"state queried for failed transfer");++mock.state_queries;return GBCMT_QUARANTINED;}
#define printf test_printf
@SOURCE@
#undef printf
static bool has(const char *needle){for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))return true;return false;}
static unsigned count(const char *needle){unsigned n=0;for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))++n;return n;}
static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock));case_name=name;++cases;bcm_started=0;
    mock.requested=mock.probe=mock.stage=1;mock.ready_after=1;mock.now=1;
    mock.ready=(struct sweet_pas_cpu_stage){UINT64_C(0x94000000),6860,16384};
    static const uint32_t addr[]={0x50000,0x50004,0x5002c,0x50044,0x5006c,0x50080};
    static const uint32_t data[]={0x6fffffff,0x6fffffff,0x2fffffff,0x6fffffff,0x6fffffff,0x60000008};
    mock.plan.wait_mask=0x3b;
    for(unsigned i=0;i<6;++i){mock.plan.cmd[i]=(struct gbcm_command){addr[i],data[i],(0x3bu>>i)&1};mock.receipt.cmd_status[i]=i==2 ? 0x100:0x10100;}
    mock.receipt.slot=1;mock.receipt.config=0x80008104;mock.receipt.irq_before=1;mock.receipt.irq_after=1;mock.receipt.irq_completed=2;
}
static void run_worker(void)
{
    sweet_bcm_vote_init();CHECK(mock.starts==1 && mock.worker && mock.deallocations==1,"one scheduled worker");
    CHECK(!mock.before_sleeps && !mock.claims,"no inline execution");sweet_bcm_vote_init();CHECK(mock.starts==1,"one start while pending");
    mock.worker(NULL,0);CHECK(mock.terminations==1,"thread terminates once");
    unsigned transactions=mock.transactions,arms=mock.arms,plans=mock.plans,claims=mock.claims;
    sweet_bcm_vote_init();CHECK(mock.starts==1 && mock.transactions==transactions && mock.arms==arms && mock.plans==plans && mock.claims==claims,"no retry after any result");
    CHECK(mock.markers==mock.flushes,"all marked logs flushed");
}
static void success(void)
{
    run_worker();CHECK(!strcmp(mock.order,"RPWTQ"),"READY -> fresh plan -> WDT -> TX -> terminal timeout");
    CHECK(mock.after_sleeps==30 && mock.quarantines==1,"bounded posttransfer wait");
    CHECK(count("SWEET BCM BOOT: cmd")==6,"six completion statuses logged");
    for(unsigned i=0;i<6;++i){char text[160];snprintf(text,sizeof(text),"cmd%u addr=%05x data=%08x wait=%u status=%08x",i,mock.plan.cmd[i].address,mock.plan.cmd[i].data,mock.plan.cmd[i].wait,mock.receipt.cmd_status[i]);CHECK(has(text),"exact command/status log");}
    CHECK(has("native batch complete slot=1 config=80008104 irq_before=00000001 irq_after=00000001 irq_completed=00000002"),"receipt log");
    CHECK(has("coordinator performed no PAS/SMC/GPU operation") && has("survived30 requested seconds after transfer; reset unqualified"),"no reset or PAS success claim");
}
int main(void)
{
    const int disabled[]={0,2,-1};
    for(unsigned i=0;i<3;++i){reset("default off");mock.requested=disabled[i];sweet_bcm_vote_init();sweet_bcm_vote_init();CHECK(!mock.starts && !mock.lines && !mock.claims,"off without effects");}
    reset("thread failure");mock.thread_error=5;sweet_bcm_vote_init();sweet_bcm_vote_init();CHECK(mock.starts==1 && !mock.worker && !mock.before_sleeps && !mock.claims,"no fallback/retry");
    for(int c=1;c<=3;++c){
        reset("initial context");mock.context=c;run_worker();CHECK(!mock.before_sleeps && !mock.claims,"early context stops");
        reset("context after delay");mock.late_context=c;run_worker();CHECK(mock.before_sleeps==45 && !mock.claims,"late context stops");
        reset("context after plan");mock.after_plan_context=c;run_worker();CHECK(!strcmp(mock.order,"RP") && !mock.arms && !mock.transactions,"invalid context cannot arm");
    }
    for(unsigned flag=0;flag<7;++flag)for(int v=-1;v<=1;v+=2){reset("conflicting flag");mock.off[flag]=v;run_worker();CHECK(!mock.before_sleeps && !mock.claims,"flags checked before wait");}
    for(unsigned flag=0;flag<2;++flag)for(unsigned i=0;i<3;++i){reset("stage prerequisite flags");if(flag)mock.stage=disabled[i];else mock.probe=disabled[i];run_worker();CHECK(!mock.before_sleeps && !mock.claims,"both stage flags exact1");}
    reset("normal ordered trial");success();
    reset("READY after two unsuccessful polls");mock.ready_after=3;success();CHECK(mock.claims==3 && mock.claim_sleeps==2,"bounded retry only for unclaimed stage");
    reset("last valid below4G PA");mock.ready.pa=UINT64_C(0xfff00000);success();
    for(unsigned freeze=0;freeze<=1;++freeze){reset("READY unavailable");mock.ready_after=0;mock.frozen_wait_clock=freeze;run_worker();CHECK(mock.claims==500 && mock.claim_sleeps==500 && !mock.plans && !mock.arms && !mock.transactions,"both count and five-second bounds");CHECK(has("READY unavailable/invalid"),"unavailable reason");}
    for(unsigned bad=0;bad<7;++bad){
        reset("invalid READY record");if(bad==0)mock.ready.pa=0;if(bad==1)mock.ready.pa++;
        if(bad==2)mock.ready.pa=UINT64_C(0x100000000);if(bad==3)mock.ready.metadata_bytes=6859;
        if(bad==4)mock.ready.metadata_bytes=6861;if(bad==5)mock.ready.reserved_bytes=16383;if(bad==6)mock.ready.reserved_bytes=16385;
        run_worker();CHECK(!strcmp(mock.order,"R") && !mock.plans && !mock.arms && !mock.transactions,"invalid record never reaches arm/plan");
    }
    reset("CMDDB prepare fails");mock.plan_fail=1;run_worker();CHECK(!strcmp(mock.order,"RP") && !mock.arms && !mock.transactions,"no arm after bad CMDDB");
    reset("lease arm fails");mock.arm_fail=1;run_worker();CHECK(!strcmp(mock.order,"RPW") && !mock.transactions && !mock.after_sleeps,"no TX after bad lease");
    for(unsigned rc=GBCMT_OFF;rc<=GBCMT_COMPLETION;++rc){reset("transport rejected");mock.tx_result=(enum gbcmt_rc)rc;run_worker();CHECK(!strcmp(mock.order,"RPWTQ") && mock.quarantines==1 && mock.state_queries==1 && !mock.after_sleeps,"failed TX quarantines, no retry/wait/PAS");CHECK(has("no PAS/GPU call, no retry"),"failure log");}
    printf("PASS: %u actual coordinator cases; serialized prerequisites and bounded simulated waits; no hardware/reset claim\n",cases);return 0;
}
