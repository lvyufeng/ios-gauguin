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
#include "gauguin_pas_init.h"
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
    int requested,off[7],probe,stage,pasinit,context,late_context,after_plan_context,after_tx_context,after_init_context,thread_error;
    unsigned starts,deallocations,terminations,before_sleeps,claim_sleeps,after_sleeps;
    unsigned claims,ready_after,claimed,plans,arms,transactions,quarantines,state_queries;
    unsigned plan_fail,arm_fail,frozen_wait_clock,markers,flushes,lines;
    unsigned init_requested_queries,init_calls,init_state_queries;
    enum gpi_rc init_result;
    enum gpi_state init_state;
    struct gpi_receipt init_receipt;
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
    if(!strcmp(key,"sweetpasinit")){*(int*)out=mock.pasinit;return true;}
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
        CHECK(mock.pasinit==0 || (mock.init_calls==1 && mock.init_result==GPI_OK),
            "enabled INIT must complete once before post-transfer reset wait");
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
    ++mock.transactions;order('T');if(mock.tx_result==GBCMT_OK)*out=mock.receipt;mock.context=mock.after_tx_context;return mock.tx_result;
}
void gauguin_wdt_lease_quarantine(void)
{
    CHECK(mock.transactions==1 && !mock.quarantines,"only after attempted transfer, no duplicate coordinator quarantine");
    CHECK(mock.tx_result!=GBCMT_OK || (mock.init_calls==1 && mock.init_result!=GPI_OK) ||
        mock.after_sleeps==30,"quarantine after TX/INIT failure or unqualified reset timeout only");
    ++mock.quarantines;order('Q');
}
enum gbcmt_state sweet_bcm_transport_state(void)
{CHECK(mock.transactions==1 && mock.tx_result!=GBCMT_OK,"state queried for failed transfer");++mock.state_queries;return GBCMT_QUARANTINED;}
bool sweet_pas_init_requested(void)
{
    CHECK(mock.transactions==1 && mock.tx_result==GBCMT_OK && !mock.quarantines,
        "optional INIT considered only after native BCM completion");
    ++mock.init_requested_queries;
    return mock.pasinit==1;
}
enum gpi_rc sweet_pas_init_image_once(const struct sweet_pas_cpu_stage *input,struct gpi_receipt *out)
{
    CHECK(input && out && mock.pasinit==1 && !mock.init_calls && !mock.quarantines,
        "one explicit enabled INIT call with valid typed pointers");
    CHECK(mock.claimed==1 && mock.plans==1 && !mock.plan_fail && mock.arms==1 && !mock.arm_fail &&
        mock.transactions==1 && mock.tx_result==GBCMT_OK,"INIT after all serialized prerequisites");
    CHECK(!strcmp(mock.order,"RPWT") && mock.init_requested_queries==1,"one path READY/plan/WDT/BCM/INIT");
    CHECK(input->pa==mock.ready.pa && input->metadata_bytes==mock.ready.metadata_bytes &&
        input->reserved_bytes==mock.ready.reserved_bytes,"exact current CPU-stage record passed to helper");
    unsigned receipt_lines=0;
    for(unsigned i=0;i<mock.lines;++i) if(strstr(mock.log[i],"SWEET BCM BOOT: cmd")) ++receipt_lines;
    CHECK(receipt_lines==6,"all six native completion statuses logged before INIT");
    if(mock.context) CHECK(mock.init_result==GPI_CONTEXT,"helper seam refuses invalid context");
    ++mock.init_calls;order('I');
    if(mock.init_result==GPI_OK) {
        mock.init_receipt.stage_pa=input->pa;
        mock.init_state=GPI_COMPLETE;
        *out=mock.init_receipt;
    } else {
        /* Failed helper output must not be consumed by the coordinator. */
        memset(out,0xa5,sizeof(*out));
    }
    mock.context=mock.after_init_context;
    return mock.init_result;
}
enum gpi_state sweet_pas_init_state(void)
{
    CHECK(mock.init_calls==1 && mock.init_result!=GPI_OK && mock.quarantines==1,"INIT state queried only after failed call and coordinator quarantine");
    ++mock.init_state_queries;return mock.init_state;
}
#define printf test_printf
@SOURCE@
#undef printf
static bool has(const char *needle){for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))return true;return false;}
static unsigned count(const char *needle){unsigned n=0;for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))++n;return n;}
static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock));case_name=name;++cases;bcm_started=0;
    mock.requested=mock.probe=mock.stage=1;mock.ready_after=1;mock.now=1;
    mock.init_result=GPI_OK;mock.init_state=GPI_QUARANTINED;
    mock.init_receipt.has_returned=1;mock.init_receipt.smc_calls=1;
    mock.init_receipt.fresh_attempts=1;
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
    unsigned transactions=mock.transactions,arms=mock.arms,plans=mock.plans,claims=mock.claims,inits=mock.init_calls,init_queries=mock.init_requested_queries,state_queries=mock.init_state_queries;
    sweet_bcm_vote_init();CHECK(mock.starts==1 && mock.transactions==transactions && mock.arms==arms && mock.plans==plans && mock.claims==claims && mock.init_calls==inits && mock.init_requested_queries==init_queries && mock.init_state_queries==state_queries,"no retry after any result");
    CHECK(mock.markers==mock.flushes,"all marked logs flushed");
    if(mock.pasinit==0) CHECK(mock.init_calls==0 && mock.init_state_queries==0,
        "off flag preserves 115 with no PAS helper/state access");
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
static void legacy_cases(void)
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
    CHECK(cases==58,"all 58 original coordinator cases preserved with INIT off");
    printf("PASS: retained %u original coordinator cases with INIT disabled\n",cases);
}

static void reset_init(const char *name)
{reset(name);mock.pasinit=1;}
static void no_init(void)
{CHECK(!mock.init_calls && !mock.init_state_queries,"no PAS operation or state query before successful prerequisites");}
static void init_success(void)
{
    run_worker();
    CHECK(!strcmp(mock.order,"RPWTIQ"),"READY -> current CMDDB -> WDT -> BCM COMPLETE -> one INIT -> reset timeout");
    CHECK(mock.init_calls==1 && mock.init_requested_queries==1 && !mock.init_state_queries,
        "successful helper called once; no redundant status query or retry");
    CHECK(mock.after_sleeps==30 && mock.quarantines==1,"success uses only original bounded reset wait afterward");
    CHECK(count("SWEET BCM BOOT: cmd")==6,"six native statuses still logged");
    char expected[192];
    snprintf(expected,sizeof(expected),"PAS INIT returned success pa=%016llx calls=%u; no MEM_SETUP/AUTH_RESET/GPU operation",mock.ready.pa,mock.init_receipt.smc_calls);
    CHECK(has(expected),"logs exact dynamic PA and helper call count without claiming authentication");
    CHECK(has("PAS INIT trial done; requests and shared buffer retained; awaiting watchdog reset"),"retains buffer and held votes");
    CHECK(has("survived30 requested seconds after transfer; reset unqualified"),"mock wait never becomes reset proof");
    CHECK(!has("coordinator performed no PAS/SMC/GPU operation") && !has("PAS INIT stopped"),
        "enabled success does not emit off-mode or failure claim");
}
static void init_cases(void)
{
    const int disabled[]={0,2,-1};
    for(unsigned i=0;i<3;++i){
        reset_init("INIT flag cannot enable the base coordinator");mock.requested=disabled[i];
        sweet_bcm_vote_init();sweet_bcm_vote_init();
        CHECK(!mock.starts && !mock.lines && !mock.claims && !mock.init_requested_queries,"no bypass when busvote not exact1");no_init();
    }
    const int invalid[]={-1,2,9};
    for(unsigned i=0;i<3;++i){
        reset("invalid optional INIT flag");mock.pasinit=invalid[i];run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.plans && !mock.arms && !mock.transactions && !mock.init_requested_queries,
            "INIT must be0or1 before any delay or resource acquisition");no_init();
    }
    reset("explicit INIT off preserves full115 path");success();
    CHECK(mock.init_requested_queries==1 && !has("PAS INIT returned success") && !has("PAS INIT stopped"),"off considered once, no helper state or operation");
    reset_init("thread creation failure with INIT requested");mock.thread_error=5;
    sweet_bcm_vote_init();sweet_bcm_vote_init();CHECK(mock.starts==1 && !mock.worker && !mock.before_sleeps,"no inline fallback for enabled INIT");no_init();
    reset_init("INIT initial context rejected");mock.context=1;run_worker();CHECK(!mock.before_sleeps && !mock.claims,"initial context precedes dependencies");no_init();
    reset_init("INIT context after delay rejected");mock.late_context=2;run_worker();CHECK(mock.before_sleeps==45 && !mock.claims,"late context precedes READY");no_init();
    reset_init("INIT context after plan rejected");mock.after_plan_context=3;run_worker();CHECK(!strcmp(mock.order,"RP") && !mock.arms && !mock.transactions,"late context prevents watchdog/INIT");no_init();
    reset_init("INIT does not bypass conflicting PET");mock.off[1]=1;run_worker();CHECK(!mock.before_sleeps && !mock.claims,"conflict stops before prerequisites");no_init();
    for(unsigned flag=0;flag<2;++flag){
        reset_init("INIT requires both CPU staging flags");if(flag)mock.stage=0;else mock.probe=0;run_worker();
        CHECK(!mock.before_sleeps && !mock.claims,"staging flags precede waiting");no_init();
    }
    reset_init("INIT never sees unavailable CPU stage");mock.ready_after=0;run_worker();
    CHECK(mock.claims==500 && mock.claim_sleeps==500 && !mock.plans && !mock.arms && !mock.transactions,"bounded unavailable READY");no_init();
    reset_init("INIT never sees unaligned claimed CPU stage");mock.ready.pa++;run_worker();
    CHECK(!strcmp(mock.order,"R") && !mock.plans && !mock.arms && !mock.transactions,"invalid record cannot reach later prerequisites");no_init();
    reset_init("INIT requires current CMDDB preparation");mock.plan_fail=1;run_worker();CHECK(!strcmp(mock.order,"RP") && !mock.arms && !mock.transactions,"failed plan prevents later operations");no_init();
    reset_init("INIT requires watchdog readiness");mock.arm_fail=1;run_worker();CHECK(!strcmp(mock.order,"RPW") && !mock.transactions,"failed watchdog prevents BCM/INIT");no_init();
    const enum gbcmt_rc tx_errors[]={GBCMT_OFF,GBCMT_COMPLETION};
    for(unsigned i=0;i<2;++i){
        reset_init("BCM early or uncertain-completion failure prevents INIT");mock.tx_result=tx_errors[i];run_worker();
        CHECK(!strcmp(mock.order,"RPWTQ") && !mock.after_sleeps && mock.state_queries==1 && !mock.init_requested_queries,
            "BCM success required before even checking INIT option");no_init();
    }
    reset_init("successful one-path INIT");init_success();
    reset_init("INIT receives asynchronously acquired stage");mock.ready_after=3;init_success();CHECK(mock.claims==3 && mock.claim_sleeps==2,"only preclaim polling repeats");
    reset_init("INIT uses different dynamic reservation");mock.ready.pa=UINT64_C(0x9ab00000);init_success();
    reset_init("INIT uses last aligned below4G reservation");mock.ready.pa=UINT64_C(0xfff00000);init_success();
    reset_init("helper continuation receipt remains one coordinator call");mock.init_receipt.smc_calls=3;mock.init_receipt.continuations=2;init_success();
    for(unsigned rc=GPI_OFF;rc<=GPI_SERVICE;++rc){
        reset_init("every helper failure is terminal for coordinator");mock.init_result=(enum gpi_rc)rc;run_worker();
        CHECK(!strcmp(mock.order,"RPWTIQ") && mock.init_calls==1 && mock.init_state_queries==1 &&
            mock.quarantines==1 && !mock.after_sleeps,"failed INIT quarantines and returns without retry/wait/later operation");
        char expected[160];snprintf(expected,sizeof(expected),"PAS INIT stopped rc=%u state=%u; no retry or later PAS/GPU operation",rc,(unsigned)mock.init_state);
        CHECK(has(expected) && !has("PAS INIT returned success") && !has("PAS INIT trial done") && !has("survived30") && !has("calls="),"failure logs rc/state only, never poisoned receipt");
    }
    const enum gpi_rc exceptional_rc[]={GPI_ALREADY,GPI_OFF};
    const enum gpi_state exceptional_state[]={GPI_COMPLETE,GPI_IDLE};
    for(unsigned i=0;i<2;++i){
        reset_init("helper state alone never overrides failed return");mock.init_result=exceptional_rc[i];mock.init_state=exceptional_state[i];run_worker();
        CHECK(mock.init_calls==1 && mock.init_state_queries==1 && !mock.after_sleeps && mock.quarantines==1 && !has("PAS INIT returned success"),"COMPLETE/IDLE state with failed return remains terminal");
    }
    for(int c=1;c<=3;++c){
        reset_init("helper context failure after BCM completion");mock.after_tx_context=c;mock.after_init_context=c;mock.init_result=GPI_CONTEXT;run_worker();
        CHECK(!strcmp(mock.order,"RPWTIQ") && !mock.after_sleeps && mock.init_calls==1,"typed helper context refusal is terminal");
        CHECK(mock.markers==mock.flushes,"invalid-context failure never synchronously persists");
    }
}
int main(void)
{
    legacy_cases();
    unsigned original=cases;
    init_cases();
    CHECK(cases-original==42 && cases==100,"58 retained plus42 focused INIT cases");
    printf("PASS: %u original + %u INIT coordinator cases (%u total); actual coordinator, typed helper seams, no real SMC/reset/GPU\n",
        original,cases-original,cases);
    return 0;
}
