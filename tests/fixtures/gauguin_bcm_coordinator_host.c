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
#include "gauguin_cx_rail.h"
#include "gauguin_cx_power.h"
#include "gauguin_gmu_clock.h"
#include "gauguin_gmu_board.h"
#include "gauguin_gmu_asset.h"
#include "cmd_db_snapshot.h"
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
    int requested,off[7],probe,stage,pasinit,pasmem,context,late_context,after_plan_context,after_tx_context,after_init_context,after_mem_context,thread_error;
    unsigned starts,deallocations,terminations,before_sleeps,claim_sleeps,after_sleeps;
    unsigned claims,ready_after,claimed,plans,arms,transactions,quarantines,state_queries;
    unsigned plan_fail,arm_fail,frozen_wait_clock,markers,flushes,lines;
    unsigned init_requested_queries,init_calls,init_state_queries;
    enum gpi_rc init_result;
    enum gpi_state init_state;
    struct gpi_receipt init_receipt;
    unsigned mem_requested_queries,mem_calls,mem_state_queries;
    enum gpi_rc mem_result;
    enum gpm_state mem_state;
    struct gpm_receipt mem_receipt;
    int cxpower,after_rail_context,after_power_context,gmuclk,gmufw,gmuperf,gmubw,gmudcvs,gpucontext,gpustart;
    unsigned start_calls;enum ggx_result start_result;
    unsigned sqe_calls;
    unsigned gpu_calls;
    unsigned perf_calls,bw_entries_calls,bw_plan_calls,bw_calls,bw_fail_step,dcvs_calls;struct gmf_bw_plan bw_plan;
    unsigned arc_calls,fwplan_calls,asset_calls,fw_calls,fw_state_queries,fw_fail_step;
    enum gmb_result fw_result;struct gmf_plan fw_plan;struct gmb_firmware_receipt fw_receipt;
    unsigned clock_queries,clock_calls,clock_states;enum gcx_rc clock_result;enum gcx_state clock_state;struct gmc_receipt clock_receipt;
    unsigned cx_requested_queries,cx_plans,rail_calls,rail_state_queries,power_calls,power_state_queries;
    enum gbcmt_rc rail_result;
    enum gcr_state rail_state;
    enum gcx_rc power_result;
    enum gcx_state power_state;
    struct gcr_plan cx_plan;
    struct gbcmt_receipt rail_receipt;
    struct gcx_receipt power_receipt;
    uint64_t after_init_ready_pa;
    uint64_t now;
    struct sweet_pas_cpu_stage ready;
    struct gbcm_plan plan;
    struct gbcmt_receipt receipt;
    enum gbcmt_rc tx_result;
    thread_continue_t worker;
    char order[12],log[32][224];unsigned order_count;
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
    if(!strcmp(key,"sweetpasmem")){*(int*)out=mock.pasmem;return true;}
    if(!strcmp(key,"sweetgmuclk")){*(int*)out=mock.gmuclk;return true;}
    if(!strcmp(key,"sweetgmufw")){*(int*)out=mock.gmufw;return true;}
    if(!strcmp(key,"sweetgmuperf")){*(int*)out=mock.gmuperf;return true;}
    if(!strcmp(key,"sweetgmubw")){*(int*)out=mock.gmubw;return true;}
    if(!strcmp(key,"sweetgmudcvs")){*(int*)out=mock.gmudcvs;return true;}
    if(!strcmp(key,"sweetgpustart")){*(int*)out=mock.gpustart;return true;}
    if(!strcmp(key,"sweetgpucontext")){*(int*)out=mock.gpucontext;return true;}
    if(!strcmp(key,"sweetcxpower")){*(int*)out=mock.cxpower;return true;}
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
        CHECK(mock.pasmem==0 || (mock.mem_calls==1 && mock.mem_result==GPI_OK),
            "enabled MEM must complete once before post-transfer reset wait");
        CHECK(mock.cxpower==0 || (mock.rail_calls==1 && mock.rail_result==GBCMT_OK &&
            mock.power_calls==1 && mock.power_result==GCX_OK),"CX mode waits only after both ARC/CX complete");
        CHECK(mock.gmufw==0||(mock.fw_calls==1&&mock.fw_result==GMB_OK),"firmware mode waits only after successful typed bootstrap");
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
    CHECK(mock.cxpower==0 && mock.cx_requested_queries==1 && !mock.cx_plans,"legacy mode uses old plan API only");
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
        (mock.mem_calls==1 && mock.mem_result!=GPI_OK) ||
        (mock.rail_calls==1 && mock.rail_result!=GBCMT_OK) ||
        (mock.power_calls==1 && mock.power_result!=GCX_OK) || (mock.clock_calls==1 && mock.clock_result!=GCX_OK) ||
        (mock.fw_calls==1 && mock.fw_result!=GMB_OK) || mock.after_sleeps==30,
        "quarantine after TX/INIT/MEM/ARC/CX failure or unqualified reset timeout only");
    ++mock.quarantines;order('Q');
}
enum gbcmt_state sweet_bcm_transport_state(void)
{CHECK(mock.transactions==1 && mock.tx_result!=GBCMT_OK,"state queried for failed transfer");++mock.state_queries;return GBCMT_QUARANTINED;}
bool sweet_pas_init_requested(void)
{
    CHECK(mock.transactions==1 && mock.tx_result==GBCMT_OK && !mock.quarantines,
        "optional INIT considered only after native BCM completion");
    CHECK(!mock.cxpower && !mock.cx_plans && !mock.rail_calls && !mock.power_calls,
        "CX mode never even queries PAS option");
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
    if(mock.after_init_ready_pa) mock.ready.pa=mock.after_init_ready_pa;
    mock.context=mock.after_init_context;
    return mock.init_result;
}
enum gpi_state sweet_pas_init_state(void)
{
    CHECK(mock.init_calls==1 && mock.init_result!=GPI_OK && mock.quarantines==1,"INIT state queried only after failed call and coordinator quarantine");
    ++mock.init_state_queries;return mock.init_state;
}
bool sweet_pas_mem_requested(void)
{
    CHECK(mock.init_calls==1 && mock.init_result==GPI_OK && mock.init_state==GPI_COMPLETE &&
        !mock.quarantines && !mock.mem_requested_queries && !strcmp(mock.order,"RPWTI"),
        "MEM considered once only after successful same-path INIT");
    ++mock.mem_requested_queries;return mock.pasmem==1;
}
enum gpi_rc sweet_pas_mem_setup_once(struct gpm_receipt *out)
{
    CHECK(out && mock.pasmem==1 && mock.pasinit==1 && !mock.mem_calls && !mock.quarantines,
        "one explicit MEM call; typed API has no caller PA or size");
    CHECK(mock.init_calls==1 && mock.init_result==GPI_OK && mock.init_state==GPI_COMPLETE &&
        mock.mem_requested_queries==1 && !strcmp(mock.order,"RPWTI"),
        "MEM after READY/plan/WDT/BCM/INIT through one path");
    char expected[192];
    snprintf(expected,sizeof(expected),"PAS INIT returned success pa=%016llx calls=%u; MEM_SETUP pending; no AUTH_RESET/GPU operation",
        (unsigned long long)mock.init_receipt.stage_pa,mock.init_receipt.smc_calls);
    unsigned init_logs=0;
    for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],expected))++init_logs;
    CHECK(init_logs==1,"exact successful INIT receipt logged before MEM call");
    if(mock.context) CHECK(mock.mem_result==GPI_CONTEXT,"MEM seam refuses invalid context");
    ++mock.mem_calls;order('M');
    if(mock.mem_result==GPI_OK) {
        /* Emulates immutable helper publication, never the mutable READY record. */
        mock.mem_receipt.stage_pa=mock.init_receipt.stage_pa;
        mock.mem_receipt.region_bytes=4096;
        mock.mem_state=GPM_COMPLETE;*out=mock.mem_receipt;
    } else {
        memset(out,0xa5,sizeof(*out));
    }
    mock.context=mock.after_mem_context;return mock.mem_result;
}
enum gpm_state sweet_pas_mem_state(void)
{
    CHECK(mock.mem_calls==1 && mock.mem_result!=GPI_OK && mock.quarantines==1 &&
        mock.init_state==GPI_COMPLETE,"MEM state only after failed call; INIT history remains complete");
    ++mock.mem_state_queries;return mock.mem_state;
}
bool sweet_cx_power_requested(void)
{
    CHECK(mock.claimed==1 && !mock.plans && !mock.arms && !mock.transactions &&
        !mock.cx_requested_queries,"CX option queried once after valid READY, before current plan");
    ++mock.cx_requested_queries;return mock.cxpower==1;
}
bool sweet_bus_cx_plan_prepare(struct gbcm_plan *out,struct gcr_plan *cx)
{
    CHECK(out && cx && mock.cxpower==1 && mock.cx_requested_queries==1 && mock.claimed==1 &&
        !mock.plans && !mock.cx_plans && !mock.arms && !mock.transactions,
        "CX mode uses one typed joint-prepare API before WDT");
    ++mock.plans;++mock.cx_plans;order('P');
    if(mock.plan_fail) {memset(out,0xa5,sizeof(*out));memset(cx,0xa5,sizeof(*cx));return false;}
    *out=mock.plan;*cx=mock.cx_plan;mock.context=mock.after_plan_context;return true;
}
enum gbcmt_rc sweet_cx_rail_submit_once(const struct gcr_plan *input,struct gbcmt_receipt *out)
{
    CHECK(input && out && mock.cxpower==1 && !mock.pasinit && !mock.pasmem && mock.cx_plans==1 &&
        mock.transactions==1 && mock.tx_result==GBCMT_OK && !mock.rail_calls && !mock.quarantines &&
        !mock.power_calls && !strcmp(mock.order,"RPWT"),"ARC exactly once after BCM COMPLETE");
    CHECK(!memcmp(input,&mock.cx_plan,sizeof(*input)),"exact jointly prepared CX plan passed unchanged");
    unsigned commands=0,batches=0;
    for(unsigned i=0;i<mock.lines;++i) {
        if(strstr(mock.log[i],"SWEET BCM BOOT: cmd"))++commands;
        if(strstr(mock.log[i],"native batch complete"))++batches;
    }
    CHECK(commands==6 && batches==1 && mock.markers==mock.flushes,
        "BCM header and all six completion receipts logged before ARC");
    if(mock.context)CHECK(mock.rail_result==GBCMT_CONTEXT,"real ARC helper rejects lost context");
    ++mock.rail_calls;order('A');
    if(mock.rail_result==GBCMT_OK) {mock.rail_state=GCR_COMPLETE;*out=mock.rail_receipt;}
    else memset(out,0xa5,sizeof(*out));
    mock.context=mock.after_rail_context;return mock.rail_result;
}
enum gcr_state sweet_cx_rail_state(void)
{
    CHECK(mock.rail_calls==1 && mock.rail_result!=GBCMT_OK && mock.quarantines==1 && !mock.power_calls,
        "ARC state only queried for a failed result, after coordinator quarantine");
    ++mock.rail_state_queries;return mock.rail_state;
}
enum gcx_rc sweet_cx_power_once(struct gcx_receipt *out)
{
    CHECK(out && mock.cxpower==1 && !mock.pasinit && !mock.pasmem && mock.rail_calls==1 &&
        mock.rail_result==GBCMT_OK && mock.rail_state==GCR_COMPLETE && !mock.power_calls &&
        !mock.quarantines && !strcmp(mock.order,"RPWTA"),"CX power exactly once only after ARC COMPLETE");
    char expected[192];
    snprintf(expected,sizeof(expected),"CX rail complete slot=%u config=%08x irq_before=%08x irq_after=%08x irq_completed=%08x status=%08x",
        mock.rail_receipt.slot,mock.rail_receipt.config,mock.rail_receipt.irq_before,
        mock.rail_receipt.irq_after,mock.rail_receipt.irq_completed,mock.rail_receipt.cmd_status[0]);
    unsigned records=0;
    for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],expected))++records;
    CHECK(records==1 && mock.markers==mock.flushes,"exact ARC receipt logged before any GPUCC API");
    if(mock.context)CHECK(mock.power_result==GCX_CONTEXT,"real CX helper rejects lost context");
    ++mock.power_calls;order('C');
    if(mock.power_result==GCX_OK) {mock.power_state=GCX_COMPLETE;*out=mock.power_receipt;}
    else memset(out,0xa5,sizeof(*out));
    mock.context=mock.after_power_context;return mock.power_result;
}
enum gcx_state sweet_cx_power_state(void)
{
    CHECK(mock.power_calls==1 && mock.power_result!=GCX_OK && mock.quarantines==1 &&
        mock.rail_state==GCR_COMPLETE,"CX error cannot erase completed ARC history");
    ++mock.power_state_queries;return mock.power_state;
}

bool sweet_gmu_clock_requested(void){CHECK(mock.power_calls==1 && mock.power_result==GCX_OK && mock.power_state==GCX_COMPLETE && !mock.clock_queries,"clock flag only after CX complete");++mock.clock_queries;return mock.gmuclk==1;}
enum gcx_rc sweet_gmu_clock_once(struct gmc_receipt *out){
 CHECK(out && mock.clock_queries==1 && mock.gmuclk==1 && !mock.clock_calls && !strcmp(mock.order,"RPWTAC") && !mock.quarantines,"clock once after all prerequisites");
 if(mock.context)CHECK(mock.clock_result==GCX_CONTEXT,"real clock helper rejects lost context");
 ++mock.clock_calls;order('G');
 if(mock.clock_result==GCX_OK){mock.clock_state=GCX_COMPLETE;*out=mock.clock_receipt;}else memset(out,0xa5,sizeof(*out));
 return mock.clock_result;
}
enum gcx_state sweet_gmu_clock_state(void){CHECK(mock.clock_calls==1 && mock.clock_result!=GCX_OK && mock.quarantines==1,"clock state only after failed result and quarantine");++mock.clock_states;return mock.clock_state;}
bool sweet_bus_arc_entries(struct ndb_entry *out)
{
 CHECK(mock.gmufw==1&&mock.plans==1&&!mock.arms&&!mock.arc_calls,"ARC view after immutable plan, before WDT");
 ++mock.arc_calls;if(mock.fw_fail_step==1)return false;memset(out,0,4*sizeof(*out));out[0].address=0x30000;return true;
}
bool gmf_plan_build(const struct ndb_entry *in,struct gmf_plan *out)
{
 CHECK(in&&out&&mock.arc_calls==1&&!mock.arms&&!mock.fwplan_calls&&in[0].address==0x30000,"real ARC output passed once before WDT");
 ++mock.fwplan_calls;if(mock.fw_fail_step==2)return false;*out=mock.fw_plan;return true;
}
bool sweet_gmu_asset_view(struct gma_view *out)
{
 CHECK(out&&mock.fwplan_calls==1&&!mock.arms&&!mock.asset_calls,"asset verified after real plan, before WDT");
 ++mock.asset_calls;if(mock.fw_fail_step==3)return false;*out=(struct gma_view){(const uint8_t *)(uintptr_t)0xb0000000,0xb0000000,32768};return true;
}
bool sweet_bus_bw_entries(struct ndb_entry *out)
{
 CHECK(out&&mock.gmubw==1&&mock.asset_calls==1&&!mock.arms&&!mock.bw_entries_calls,"same published BW snapshot before WDT/RSC");
 ++mock.bw_entries_calls;if(mock.bw_fail_step==1)return false;
 memset(out,0,4*sizeof(*out));out[3].address=0x50054;if(mock.bw_fail_step==3)mock.context=1;return true;
}
bool gmf_bw_plan_build(const struct ndb_entry *in,struct gmf_bw_plan *out)
{
 CHECK(in&&out&&mock.bw_entries_calls==1&&!mock.arms&&!mock.bw_plan_calls&&in[3].address==0x50054,"full snapshot BW metadata passed once before WDT");
 ++mock.bw_plan_calls;if(mock.bw_fail_step==2)return false;*out=mock.bw_plan;return true;
}
static enum gmb_result firmware_mock(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,struct gmb_firmware_receipt *out)
{
 CHECK(s&&p&&out&&mock.gmufw==1&&mock.clock_calls==1&&mock.clock_result==GCX_OK&&!mock.fw_calls&&!mock.quarantines&&!strcmp(mock.order,"RPWTACG"),"firmware after completed clock only");
 CHECK(!memcmp(s,&mock.ready,sizeof(*s))&&!memcmp(p,&mock.fw_plan,sizeof(*p)),"exact claimed owner and same-boot firmware plan");
 ++mock.fw_calls;order('F');
 if(mock.fw_result==GMB_OK)*out=mock.fw_receipt;
 else {memset(out,0xa5,sizeof(*out));if(mock.fw_result>=GMB_CONTEXT)gauguin_wdt_lease_quarantine();}
 return mock.fw_result;
}
enum gmb_result sweet_gmu_firmware_once(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,struct gmb_firmware_receipt *out)
{CHECK(mock.gmuperf==0&&!mock.gmubw&&!mock.perf_calls&&!mock.bw_calls,"default firmware entry excludes PERF/BW");return firmware_mock(s,p,out);}
enum gmb_result sweet_gmu_firmware_perf_once(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,struct gmb_firmware_receipt *out)
{CHECK(mock.gmuperf==1&&!mock.gmubw&&!mock.bw_calls&&mock.perf_calls++==0,"PERF uses its explicit once-only entry");return firmware_mock(s,p,out);}
enum gmb_result sweet_gmu_firmware_bw_test_once(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmb_firmware_receipt *out)
{
 CHECK(mock.gmubw==1&&mock.gmuperf==1&&!mock.gmudcvs&&!mock.dcvs_calls&&mock.bw_calls++==0&&!mock.perf_calls&&mock.bw_entries_calls==1&&mock.bw_plan_calls==1,"BW uses explicit combined entry and no separate bootstrap");
 CHECK(bw&&!memcmp(bw,&mock.bw_plan,sizeof(*bw)),"exact same-boot BW plan supplied");return firmware_mock(s,p,out);
}
enum gmb_result sweet_gmu_firmware_dcvs_once(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmb_firmware_receipt *out)
{
 CHECK(mock.gmudcvs==1&&mock.gmubw==1&&mock.gmuperf==1&&mock.dcvs_calls++==0&&!mock.perf_calls&&!mock.bw_calls&&mock.bw_entries_calls==1&&mock.bw_plan_calls==1,"DCVS uses one combined explicit cold API after all preflight");
 CHECK(bw&&!memcmp(bw,&mock.bw_plan,sizeof(*bw)),"exact published BW plan passed into DCVS bootstrap");return firmware_mock(s,p,out);
}
enum gmb_state sweet_gmu_firmware_state(void)
{CHECK(mock.fw_calls==1&&mock.fw_result!=GMB_OK,"state only after refused firmware return");++mock.fw_state_queries;return mock.fw_result>=GMB_CONTEXT?GMB_QUARANTINED:GMB_IDLE;}
enum gmb_result sweet_gmu_firmware_gpu_once(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmb_firmware_receipt *out)
{
 CHECK(mock.gpucontext==1&&mock.gmudcvs==1&&mock.gmubw==1&&mock.gmuperf==1&&mock.gpu_calls++==0&&!mock.dcvs_calls&&!mock.bw_calls&&!mock.perf_calls,"GPU context selects one explicit cold entry");
 CHECK(bw&&!memcmp(bw,&mock.bw_plan,sizeof(*bw)),"GPU uses exact same-boot BW plan");return firmware_mock(s,p,out);
}
enum gmb_result sweet_gmu_firmware_gpu_sqe_once(const struct sweet_pas_cpu_stage *s,const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmb_firmware_receipt *out)
{CHECK(mock.gpustart==1&&mock.sqe_calls++==0,"SQE cold entry only on validated start path");return sweet_gmu_firmware_gpu_once(s,p,bw,out);}
enum ggx_result sweet_gpu_start_once(struct ggx_receipt *out)
{CHECK(mock.gpustart==1&&mock.gpu_calls==1&&mock.fw_result==GMB_OK&&mock.start_calls++==0,"GPU live stage after accepted sole cold bootstrap");order('X');if(mock.start_result!=GGX_OK){++mock.quarantines;return mock.start_result;}memset(out,0,sizeof(*out));return GGX_OK;}
enum gmb_state sweet_gpu_start_state(void)
{return mock.start_result==GGX_OK?GMB_READY:GMB_QUARANTINED;}
#define printf test_printf
@SOURCE@
#undef printf
static bool has(const char *needle){for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))return true;return false;}
static unsigned count(const char *needle){unsigned n=0;for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))++n;return n;}
static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock));case_name=name;++cases;bcm_started=0;
    mock.requested=mock.probe=mock.stage=1;mock.clock_result=GCX_OK;mock.clock_receipt.configured_hz=200000000;mock.clock_receipt.direct_writes=7;mock.clock_receipt.hold_requests=2;mock.clock_receipt.polls=7;mock.ready_after=1;mock.now=1;
    mock.init_result=GPI_OK;mock.init_state=GPI_QUARANTINED;
    mock.init_receipt.has_returned=1;mock.init_receipt.smc_calls=1;
    mock.init_receipt.fresh_attempts=1;
    mock.mem_result=GPI_OK;mock.mem_state=GPM_QUARANTINED;
    mock.mem_receipt.has_returned=1;mock.mem_receipt.smc_calls=1;mock.mem_receipt.fresh_attempts=1;
    mock.rail_result=GBCMT_OK;mock.rail_state=GCR_QUARANTINED;
    mock.power_result=GCX_OK;mock.power_state=GCX_QUARANTINED;
    mock.cx_plan=(struct gcr_plan){0x30000,6,384,7,65535,{0,16,64,128,192,256,384}};
    mock.rail_receipt=(struct gbcmt_receipt){1,0x80008104,1,1,2,{0x10100,0,0,0,0,0}};
    mock.power_receipt=(struct gcx_receipt){9,0x00215801,0x00218801,0x00218800,
        0x80218800,0,2,3};
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
    unsigned memories=mock.mem_calls,mem_queries=mock.mem_requested_queries,mem_states=mock.mem_state_queries;
    unsigned cx_queries=mock.cx_requested_queries,cx_plans=mock.cx_plans,rails=mock.rail_calls,
        rail_states=mock.rail_state_queries,powers=mock.power_calls,power_states=mock.power_state_queries;
    sweet_bcm_vote_init();CHECK(mock.starts==1 && mock.transactions==transactions && mock.arms==arms && mock.plans==plans && mock.claims==claims && mock.init_calls==inits && mock.init_requested_queries==init_queries && mock.init_state_queries==state_queries && mock.mem_calls==memories && mock.mem_requested_queries==mem_queries && mock.mem_state_queries==mem_states,"no retry after any result");
    CHECK(mock.markers==mock.flushes,"all marked logs flushed");
    CHECK(mock.cx_requested_queries==cx_queries && mock.cx_plans==cx_plans && mock.rail_calls==rails &&
        mock.rail_state_queries==rail_states && mock.power_calls==powers && mock.power_state_queries==power_states,
        "no retry/query/side effect for new CX dependencies");
    if(mock.cxpower==0) CHECK(!mock.cx_plans && !mock.rail_calls && !mock.rail_state_queries &&
        !mock.power_calls && !mock.power_state_queries,"CX off preserves legacy APIs only");
    if(mock.cxpower==1) CHECK(!mock.init_requested_queries && !mock.init_calls && !mock.init_state_queries &&
        !mock.mem_requested_queries && !mock.mem_calls && !mock.mem_state_queries,"CX mode excludes all PAS APIs");
    if(mock.pasinit==0) CHECK(mock.init_calls==0 && mock.init_state_queries==0,
        "off flag preserves 115 with no PAS helper/state access");
    if(mock.pasmem==0) CHECK(!mock.mem_calls && !mock.mem_state_queries,
        "MEM off preserves 116 with no MEM helper/state access");
    if(mock.init_result!=GPI_OK || !mock.init_calls) CHECK(!mock.mem_requested_queries && !mock.mem_calls && !mock.mem_state_queries,
        "no MEM option query or API before successful INIT");
    if(!mock.gmudcvs)CHECK(!mock.dcvs_calls,"DCVS default0 adds no transaction API");
    if(!mock.gmubw)CHECK(!mock.bw_entries_calls&&!mock.bw_plan_calls&&!mock.bw_calls,"BW default0 makes no BW snapshot/plan/transaction calls");
    if(!mock.gmufw)CHECK(!mock.arc_calls&&!mock.fwplan_calls&&!mock.asset_calls&&!mock.fw_calls&&!mock.fw_state_queries,"firmware default0 makes no new API calls");
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
static void reset_mem(const char *name)
{reset_init(name);mock.pasmem=1;}
static void no_mem(void)
{CHECK(!mock.mem_requested_queries && !mock.mem_calls && !mock.mem_state_queries,"no MEM access before successful INIT");}
static void mem_success(void)
{
    run_worker();
    CHECK(!strcmp(mock.order,"RPWTIMQ"),"one path READY -> plan -> WDT -> BCM -> INIT -> MEM -> reset wait");
    CHECK(mock.init_calls==1 && mock.mem_requested_queries==1 && mock.mem_calls==1 &&
        !mock.init_state_queries && !mock.mem_state_queries,"one call per helper; no retry or redundant state read");
    CHECK(mock.after_sleeps==30 && mock.quarantines==1,"only bounded original reset wait follows MEM");
    CHECK(count("SWEET BCM BOOT: cmd")==6 && count("calls=")==2,"six BCM statuses and two distinct PAS success receipts");
    char expected[192];
    snprintf(expected,sizeof(expected),"PAS MEM_SETUP returned success pa=%016llx bytes=4096 calls=%u; no code load/AUTH_RESET/GPU operation",
        (unsigned long long)mock.init_receipt.stage_pa,mock.mem_receipt.smc_calls);
    CHECK(has(expected),"MEM log uses exact published INIT PA, fixed span and actual helper count");
    CHECK(has("MEM_SETUP trial done; requests and shared buffer retained; awaiting watchdog reset") &&
        has("survived30 requested seconds after transfer; reset unqualified"),"retain resources; bounded wait is not reset qualification");
    CHECK(!has("PAS INIT trial done") && !has("no MEM_SETUP/AUTH_RESET/GPU operation") &&
        !has("coordinator performed no PAS/SMC/GPU operation") && !has("stopped rc="),"no obsolete off-mode or failure claim");
}
static void mem_cases(void)
{
    const int disabled[]={0,2,-1};
    for(unsigned i=0;i<3;++i){
        reset_mem("MEM cannot enable base coordinator");mock.requested=disabled[i];
        sweet_bcm_vote_init();sweet_bcm_vote_init();
        CHECK(!mock.starts && !mock.lines && !mock.claims,"base flag remains exact1");no_init();no_mem();
    }
    const int invalid[]={-1,2,9};
    for(unsigned i=0;i<3;++i){
        reset_mem("invalid MEM flag rejects whole experiment");mock.pasmem=invalid[i];run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.plans && !mock.arms && !mock.transactions,
            "invalid MEM rejects before delay/READY/plan/WDT/BCM");no_init();no_mem();
    }
    const int no_init_flag[]={0,-1,2};
    for(unsigned i=0;i<3;++i){
        reset_mem("MEM requires INIT flag exact1");mock.pasinit=no_init_flag[i];run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.arms && !mock.transactions,"dependent flags reject before any experiment");no_init();no_mem();
    }
    reset_mem("MEM cannot bypass PET exclusion");mock.off[1]=1;run_worker();
    CHECK(!mock.before_sleeps && !mock.claims,"conflict rejected early");no_init();no_mem();
    for(unsigned i=0;i<2;++i){
        reset_mem("MEM still requires both staging flags");if(i)mock.stage=0;else mock.probe=0;run_worker();
        CHECK(!mock.before_sleeps && !mock.claims,"staging requirements precede experiment");no_init();no_mem();
    }
    for(unsigned rc=GPI_OFF;rc<=GPI_SERVICE;++rc){
        reset_mem("every INIT failure prevents MEM even when enabled");mock.init_result=(enum gpi_rc)rc;run_worker();
        CHECK(!strcmp(mock.order,"RPWTIQ") && mock.init_calls==1 && mock.init_state_queries==1 &&
            mock.quarantines==1 && !mock.after_sleeps,"failed INIT is terminal with MEM enabled");
        CHECK(has("PAS INIT stopped") && !has("calls=") && !has("MEM_SETUP pending") &&
            !has("PAS MEM_SETUP") && !has("survived30"),"no failed INIT receipt consumed or later MEM log");no_mem();
    }
    reset_mem("successful one-path MEM");mem_success();
    reset_mem("MEM receives dynamic INIT publication");mock.ready.pa=UINT64_C(0x9ab00000);mem_success();
    reset_mem("MEM continuation receipt does not cause coordinator retries");
    mock.init_receipt.smc_calls=4;mock.init_receipt.continuations=3;
    mock.mem_receipt.smc_calls=3;mock.mem_receipt.continuations=2;mem_success();
    reset_mem("MEM never takes PA from mutable READY record");mock.after_init_ready_pa=UINT64_C(0xfff00000);mem_success();
    CHECK(mock.init_receipt.stage_pa==UINT64_C(0x94000000) && mock.ready.pa==UINT64_C(0xfff00000),"publication and later record deliberately differ");
    for(unsigned rc=GPI_OFF;rc<=GPI_SERVICE;++rc){
        reset_mem("every MEM helper failure is terminal");mock.mem_result=(enum gpi_rc)rc;run_worker();
        CHECK(!strcmp(mock.order,"RPWTIMQ") && mock.mem_calls==1 && mock.mem_state_queries==1 &&
            mock.quarantines==1 && !mock.after_sleeps && !mock.init_state_queries,"MEM failure quarantines and returns; no retry/wait/later operation");
        char expected[160];snprintf(expected,sizeof(expected),"PAS MEM_SETUP stopped rc=%u state=%u; no retry or later PAS/GPU operation",rc,(unsigned)mock.mem_state);
        CHECK(has(expected) && count("calls=")==1 && !has("bytes=") && !has("a5a5a5a5a5a5a5a5") &&
            !has("PAS MEM_SETUP returned success") && !has("trial done") && !has("survived30"),"MEM error logs rc/state only; poisoned receipt never consumed");
    }
    const enum gpi_rc exceptional_rc[]={GPI_ALREADY,GPI_OFF};
    const enum gpm_state exceptional_state[]={GPM_COMPLETE,GPM_IDLE};
    for(unsigned i=0;i<2;++i){
        reset_mem("MEM state cannot override helper error");mock.mem_result=exceptional_rc[i];mock.mem_state=exceptional_state[i];run_worker();
        CHECK(mock.mem_calls==1 && mock.mem_state_queries==1 && !mock.after_sleeps && mock.quarantines==1 &&
            !has("PAS MEM_SETUP returned success"),"COMPLETE/IDLE state with failed return remains terminal");
    }
    for(int c=1;c<=3;++c){
        reset_mem("MEM helper refuses context lost after INIT");mock.after_init_context=c;mock.after_mem_context=c;mock.mem_result=GPI_CONTEXT;run_worker();
        CHECK(!strcmp(mock.order,"RPWTIMQ") && !mock.after_sleeps && mock.mem_calls==1 &&
            mock.markers==mock.flushes,"context refusal terminates without synchronous persistence");
    }
    const enum gbcmt_rc tx_errors[]={GBCMT_OFF,GBCMT_COMPLETION};
    for(unsigned i=0;i<2;++i){
        reset_mem("MEM cannot bypass BCM failure");mock.tx_result=tx_errors[i];run_worker();
        CHECK(!strcmp(mock.order,"RPWTQ") && !mock.after_sleeps,"BCM error remains terminal before both PAS operations");no_init();no_mem();
    }
    reset_mem("MEM cannot bypass failed CMDDB plan");mock.plan_fail=1;run_worker();
    CHECK(!strcmp(mock.order,"RP") && !mock.arms && !mock.transactions,"plan failure prevents both PAS operations");no_init();no_mem();
    reset_mem("MEM cannot bypass watchdog arm failure");mock.arm_fail=1;run_worker();
    CHECK(!strcmp(mock.order,"RPW") && !mock.transactions,"watchdog failure prevents both PAS operations");no_init();no_mem();
}
static void reset_cx(const char *name)
{reset(name);mock.cxpower=1;}
static void no_cx_operations(void)
{CHECK(!mock.rail_calls && !mock.rail_state_queries && !mock.power_calls && !mock.power_state_queries,
    "no ARC/GPUCC API before successful prerequisites");}
static void cx_success(void)
{
    run_worker();
    CHECK(!strcmp(mock.order,"RPWTACQ"),"READY -> joint CMDDB -> WDT -> BCM -> ARC -> CX -> reset timeout");
    CHECK(mock.cx_requested_queries==1 && mock.cx_plans==1 && mock.rail_calls==1 && mock.power_calls==1 &&
        !mock.rail_state_queries && !mock.power_state_queries,"one call per dependency, no redundant state queries");
    CHECK(mock.after_sleeps==30 && mock.quarantines==1 && mock.rail_state==GCR_COMPLETE &&
        mock.power_state==GCX_COMPLETE,"bounded reset wait does not erase successful component history");
    CHECK(count("SWEET BCM BOOT: cmd")==6 && count("CX rail complete")==1 && count("CX power complete")==1,
        "distinct native BCM, ARC and CX receipt logs");
    char expected[192];
    snprintf(expected,sizeof(expected),"CX power complete gcc=%08x before=%08x final=%08x ahb=%08x writes=%u polls=%u",
        mock.power_receipt.gcc_cfg_ahb,mock.power_receipt.gdsc_before,mock.power_receipt.gdsc_final,
        mock.power_receipt.ahb_final,mock.power_receipt.writes,mock.power_receipt.polls);
    CHECK(has(expected),"all CX fields from exact helper receipt, including zero-write case");
    CHECK(has("CX trial done; ARC/BCM requests retained; awaiting watchdog reset; no PAS/GMU/GX/GPU execution") &&
        has("survived30 requested seconds after transfer; reset unqualified"),"retained votes; no reset, PAS or GPU execution claim");
    CHECK(!has("PAS INIT returned") && !has("PAS MEM_SETUP") && !has("stopped rc=") &&
        !has("coordinator performed no PAS/SMC/GPU operation"),"CX success has no obsolete PAS/off/failure log");
}
static void cx_cases(void)
{
    const int disabled[]={0,-1,2};
    for(unsigned i=0;i<3;++i) {
        reset_cx("CX cannot enable base coordinator");mock.requested=disabled[i];
        sweet_bcm_vote_init();sweet_bcm_vote_init();
        CHECK(!mock.starts && !mock.lines && !mock.claims && !mock.cx_requested_queries,"base flag stays exact1");no_cx_operations();
    }
    const int invalid[]={-1,2,9};
    for(unsigned i=0;i<3;++i) {
        reset_cx("invalid CX flag rejects whole experiment");mock.cxpower=invalid[i];run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.cx_requested_queries && !mock.plans && !mock.arms,
            "malformed CX rejected before delay, READY or any API");no_cx_operations();
    }
    reset("explicit CX off retains BCM path");success();
    for(unsigned combo=0;combo<3;++combo) {
        reset_cx("CX rejects every enabled PAS combination");mock.pasinit=combo!=2;mock.pasmem=combo!=0;run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.plans && !mock.arms && !mock.cx_requested_queries,
            "CX/PAS conflict rejects before CPU stage or watchdog");no_cx_operations();
    }
    reset_cx("CX thread failure has no inline fallback");mock.thread_error=5;
    sweet_bcm_vote_init();sweet_bcm_vote_init();
    CHECK(mock.starts==1 && !mock.worker && !mock.before_sleeps && !mock.cx_requested_queries,"one failed thread, no retry");no_cx_operations();
    for(unsigned flag=0;flag<7;++flag)for(int v=-1;v<=1;v+=2) {
        reset_cx("CX cannot bypass existing conflicting flags");mock.off[flag]=v;run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.cx_requested_queries,"all old exclusions precede work");no_cx_operations();
    }
    for(unsigned flag=0;flag<2;++flag)for(unsigned i=0;i<3;++i) {
        reset_cx("CX retains both CPU staging prerequisites");if(flag)mock.stage=disabled[i];else mock.probe=disabled[i];run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.cx_requested_queries,"both staging flags exact1");no_cx_operations();
    }
    for(int context=1;context<=3;++context) {
        reset_cx("CX early context rejection");mock.context=context;run_worker();
        CHECK(!mock.before_sleeps && !mock.claims && !mock.cx_requested_queries,"early context stops");no_cx_operations();
        reset_cx("CX context lost during worker delay");mock.late_context=context;run_worker();
        CHECK(mock.before_sleeps==45 && !mock.claims && !mock.cx_requested_queries,"post-delay context stops");no_cx_operations();
        reset_cx("CX context lost after joint prepare");mock.after_plan_context=context;run_worker();
        CHECK(!strcmp(mock.order,"RP") && mock.cx_plans==1 && !mock.arms && !mock.transactions,"no arm in invalid context");no_cx_operations();
    }
    for(unsigned freeze=0;freeze<=1;++freeze) {
        reset_cx("CX waits boundedly for unclaimed stage only");mock.ready_after=0;mock.frozen_wait_clock=freeze;run_worker();
        CHECK(mock.claims==500 && mock.claim_sleeps==500 && !mock.cx_requested_queries && !mock.plans && !mock.arms,
            "both count and time deadline precede any CX operation");no_cx_operations();
    }
    reset_cx("CX rejects invalid same-boot stage");mock.ready.pa++;run_worker();
    CHECK(!strcmp(mock.order,"R") && !mock.cx_requested_queries && !mock.plans && !mock.arms,"invalid stage never reaches joint prepare");no_cx_operations();
    reset_cx("joint plan fails before watchdog");mock.plan_fail=1;run_worker();
    CHECK(!strcmp(mock.order,"RP") && mock.cx_plans==1 && !mock.arms && !mock.transactions && !has("a5a5"),
        "failed joint preparation never consumes either poisoned output");no_cx_operations();
    reset_cx("CX requires watchdog arm before any submit");mock.arm_fail=1;run_worker();
    CHECK(!strcmp(mock.order,"RPW") && !mock.transactions && !mock.after_sleeps,"failed arm prevents both submissions");no_cx_operations();
    for(unsigned rc=GBCMT_OFF;rc<=GBCMT_COMPLETION;++rc) {
        reset_cx("every BCM error prevents ARC and GPUCC");mock.tx_result=(enum gbcmt_rc)rc;run_worker();
        CHECK(!strcmp(mock.order,"RPWTQ") && mock.state_queries==1 && !mock.after_sleeps && !has("CX rail complete"),
            "BCM result must succeed before ARC");no_cx_operations();
    }
    reset_cx("full ordered CX trial");cx_success();
    reset_cx("CX after delayed CPU-stage claim");mock.ready_after=3;cx_success();
    CHECK(mock.claims==3 && mock.claim_sleeps==2,"only unclaimed READY may retry");
    reset_cx("already-on CX receipt is not relabeled as written");mock.power_receipt.writes=0;mock.power_receipt.polls=1;
    mock.power_receipt.gdsc_before=mock.power_receipt.gdsc_final;cx_success();
    for(unsigned rc=GBCMT_OFF;rc<=GBCMT_COMPLETION;++rc) {
        reset_cx("every ARC error forbids GPUCC");mock.rail_result=(enum gbcmt_rc)rc;run_worker();
        CHECK(!strcmp(mock.order,"RPWTAQ") && mock.rail_calls==1 && mock.rail_state_queries==1 &&
            !mock.power_calls && !mock.power_state_queries && !mock.after_sleeps,"ARC failure is terminal");
        char expected[160];snprintf(expected,sizeof(expected),"CX rail stopped rc=%u state=%u; no GPUCC access or retry",rc,(unsigned)mock.rail_state);
        CHECK(has(expected) && !has("CX rail complete") && !has("CX power") && !has("a5a5") &&
            !has("trial done") && !has("survived30"),"failed ARC receipt never consumed");
    }
    for(unsigned rc=GCX_OFF;rc<=GCX_READBACK;++rc) {
        reset_cx("every CX error is terminal");mock.power_result=(enum gcx_rc)rc;run_worker();
        CHECK(!strcmp(mock.order,"RPWTACQ") && mock.power_calls==1 && mock.power_state_queries==1 &&
            !mock.rail_state_queries && mock.rail_state==GCR_COMPLETE && !mock.after_sleeps,"CX failure preserves completed ARC, no retry or cleanup");
        char expected[160];snprintf(expected,sizeof(expected),"CX power stopped rc=%u state=%u; no later GPU operation",rc,(unsigned)mock.power_state);
        CHECK(has(expected) && count("CX rail complete")==1 && !has("CX power complete") && !has("a5a5") &&
            !has("trial done") && !has("survived30"),"failed CX receipt never consumed");
    }
    const enum gbcmt_rc rail_errors[]={GBCMT_ALREADY,GBCMT_OFF};
    const enum gcr_state rail_states[]={GCR_COMPLETE,GCR_IDLE};
    const enum gcx_rc power_errors[]={GCX_ALREADY,GCX_OFF};
    const enum gcx_state power_states[]={GCX_COMPLETE,GCX_IDLE};
    for(unsigned i=0;i<2;++i) {
        reset_cx("ARC state cannot override failed return");mock.rail_result=rail_errors[i];mock.rail_state=rail_states[i];run_worker();
        CHECK(!mock.power_calls && mock.rail_state_queries==1 && !mock.after_sleeps && !has("CX rail complete"),"state alone is not current completion");
        reset_cx("CX state cannot override failed return");mock.power_result=power_errors[i];mock.power_state=power_states[i];run_worker();
        CHECK(mock.power_state_queries==1 && !mock.after_sleeps && !has("CX power complete"),"historical CX state cannot turn refusal into success");
    }
    for(int context=1;context<=3;++context) {
        reset_cx("ARC helper refuses context lost after BCM");mock.after_tx_context=context;mock.after_rail_context=context;
        mock.rail_result=GBCMT_CONTEXT;run_worker();
        CHECK(!strcmp(mock.order,"RPWTAQ") && !mock.power_calls && !mock.after_sleeps && mock.markers==mock.flushes,
            "ARC context failure is terminal without invalid-context persistence");
        reset_cx("CX helper refuses context lost after ARC");mock.after_rail_context=context;mock.after_power_context=context;
        mock.power_result=GCX_CONTEXT;run_worker();
        CHECK(!strcmp(mock.order,"RPWTACQ") && !mock.after_sleeps && mock.markers==mock.flushes,
            "CX context failure is terminal without invalid-context persistence");
    }
}

static void clock_cases(void){
 for(int value=-1;value<=2;++value)if(value!=0&&value!=1){reset_cx("bad clock flag");mock.gmuclk=value;run_worker();CHECK(!mock.claims&&!mock.clock_queries,"invalid clock stops before experiment");}
 reset("clock requires CX mode");mock.gmuclk=1;run_worker();CHECK(!mock.claims&&!mock.clock_queries,"dependency flags rejected early");
 reset_cx("native clock dependency success");mock.gmuclk=1;run_worker();
 CHECK(!strcmp(mock.order,"RPWTACGQ")&&mock.clock_calls==1&&!mock.clock_states&&mock.after_sleeps==30,"one clock call then reset wait");
 CHECK(has("GMU clock complete configured_hz=200000000 direct_writes=7 hold_requests=2 polls=7")&&has("GMU clock trial done")&&!has("CX trial done;"),"clock receipt and correct terminal marker");
 for(unsigned rc=GCX_OFF;rc<=GCX_READBACK;++rc){reset_cx("clock failure terminal");mock.gmuclk=1;mock.clock_result=(enum gcx_rc)rc;run_worker();
  CHECK(!strcmp(mock.order,"RPWTACGQ")&&mock.clock_calls==1&&mock.clock_states==1&&!mock.after_sleeps,"failed clock no wait/retry");
  CHECK(has("GMU clock stopped")&&!has("GMU clock complete")&&!has("trial done")&&!has("a5a5"),"failure receipt never consumed");
 }
 reset_cx("CX error prevents clock");mock.gmuclk=1;mock.power_result=GCX_READBACK;run_worker();CHECK(!mock.clock_queries&&!mock.clock_calls,"no clock before successful CX");
 for(int context=1;context<=3;++context){reset_cx("clock refuses lost context");mock.gmuclk=1;mock.after_power_context=context;mock.clock_result=GCX_CONTEXT;run_worker();CHECK(!mock.after_sleeps&&mock.clock_calls==1&&mock.markers==mock.flushes,"context failure stops");}
}
static void reset_fw(const char *name)
{
 reset_cx(name);mock.gmuclk=mock.gmufw=1;mock.fw_plan.address[0]=0x30000;
 mock.fw_plan.selector[GMF_GFX]=mock.fw_plan.selector[GMF_MX]=7;
 mock.fw_receipt.phase=GMF_DONE;mock.fw_receipt.firmware.fw_result=0xbabeface;
 mock.fw_receipt.firmware.reported_version=0x100b0000;
 mock.fw_receipt.firmware.tcm_written=mock.fw_receipt.firmware.tcm_checked=8192;
}
static void firmware_cases(void)
{
 for(int n=-1;n<=2;n++)if(n!=0&&n!=1){reset_fw("invalid firmware flag");mock.gmufw=n;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.arc_calls,"flag exact1");}
 reset_fw("firmware requires clocks");mock.gmuclk=0;run_worker();CHECK(!mock.claims&&!mock.arms,"clock prerequisite checked before wait");
 reset_fw("firmware requires CX");mock.cxpower=0;run_worker();CHECK(!mock.claims&&!mock.arms,"CX prerequisite checked before wait");
 for(unsigned n=1;n<=3;n++){
  reset_fw("pre-arm asset/plan failure");mock.fw_fail_step=n;run_worker();
  CHECK(!strcmp(mock.order,"RP")&&!mock.arms&&!mock.transactions&&!mock.fw_calls&&!mock.quarantines,"all firmware preflight failures precede watchdog/RSC");
  CHECK(has("real ARC plan/pinned asset unavailable")&&!has("a5a5"),"failed preflight output never consumed");
 }
 for(int n=1;n<=3;n++){
  reset_fw("context lost before preflight");mock.after_plan_context=n;run_worker();
  CHECK(!mock.arc_calls&&!mock.asset_calls&&!mock.arms&&!mock.fw_calls,"lost context cannot acquire asset/plan or WDT");
 }
 reset_fw("full firmware order");run_worker();
 CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&!mock.fw_state_queries&&mock.after_sleeps==30,"current plan/asset before WDT, real firmware API after clock, bounded reset wait");
 CHECK(mock.arc_calls==1&&mock.fwplan_calls==1&&mock.asset_calls==1,"one same-boot preflight");
 CHECK(has("firmware complete phase=6 fw=babeface version=100b0000 copy=8192/8192")&&count("tcm_version")==5,"exact dynamic helper receipt logged");
 CHECK(has("INIT/version diagnostic done")&&!has("GMU clock trial done"),"correct final stage marker");
 reset_fw("clock failure forbids firmware");mock.clock_result=GCX_READBACK;run_worker();CHECK(!mock.fw_calls&&!mock.after_sleeps,"no firmware after failed clock");
 reset_fw("watchdog failure forbids all stores");mock.arm_fail=1;run_worker();CHECK(!mock.transactions&&!mock.fw_calls&&mock.asset_calls==1,"preflight cannot bypass watchdog failure");
 for(unsigned n=GMB_ARGUMENT;n<=GMB_FIRMWARE;n++){
  reset_fw("every firmware refusal terminal");mock.fw_result=(enum gmb_result)n;run_worker();
  CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&mock.fw_state_queries==1&&!mock.after_sleeps&&mock.quarantines==1,"one helper refusal, no retry/cleanup/wait or duplicate quarantine");
  CHECK(has("firmware stopped")&&!has("firmware complete")&&!has("a5a5"),"failed receipt never consumed");
 }
}
static void perf_cases(void)
{
 for(int n=-1;n<=2;n++)if(n!=0&&n!=1){reset_fw("invalid PERF flag");mock.gmuperf=n;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.perf_calls,"PERF flag exact0/1 before work");}
 for(unsigned dep=0;dep<3;dep++){
  reset_fw("PERF prerequisite missing");mock.gmuperf=1;
  if(dep==0)mock.gmufw=0;else if(dep==1)mock.gmuclk=0;else mock.cxpower=0;
  run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.fw_calls&&!mock.perf_calls,"PERF requires firmware/clocks/CX before any experiment");
 }
 for(unsigned n=1;n<=3;n++){
  reset_fw("PERF preflight failure");mock.gmuperf=1;mock.fw_fail_step=n;run_worker();
  CHECK(!mock.arms&&!mock.transactions&&!mock.perf_calls&&!mock.quarantines,"PERF cannot bypass same-boot preflight");
 }
 for(unsigned n=GMB_ARGUMENT;n<=GMB_FIRMWARE;n++){
  reset_fw("every PERF bootstrap refusal terminal");mock.gmuperf=1;mock.fw_result=(enum gmb_result)n;run_worker();
  CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&mock.perf_calls==1&&!mock.after_sleeps&&mock.quarantines==1,"PERF refusal never retries or consumes poisoned output");
  CHECK(has("firmware stopped")&&!has("firmware complete")&&!has("PERF diagnostic done")&&!has("a5a5"),"no false completion after PERF refusal");
 }
 reset_fw("PERF opt-in order");mock.gmuperf=1;run_worker();
 CHECK(mock.perf_calls==1&&mock.fw_calls==1&&!strcmp(mock.order,"RPWTACGFQ")&&mock.after_sleeps==30,"one combined cold transaction after clocks, one diagnostic reset wait");
 CHECK(has("PERF diagnostic done")&&has("no BW/TEST/normal HFI_ON/GPU commands/Metal")&&!has("INIT/version diagnostic done"),"PERF final marker does not claim complete HFI/GPU");
 reset_fw("PERF default0 preserves prior stage");run_worker();CHECK(!mock.perf_calls&&mock.fw_calls==1&&has("INIT/version diagnostic done")&&!has("PERF diagnostic done"),"default selects existing API");
 reset_fw("PERF forbidden after failed clock");mock.gmuperf=1;mock.clock_result=GCX_READBACK;run_worker();CHECK(!mock.fw_calls&&!mock.perf_calls,"clock failure stops before PERF API");
 reset_fw("PERF forbidden after failed watchdog arm");mock.gmuperf=1;mock.arm_fail=1;run_worker();CHECK(!mock.fw_calls&&!mock.perf_calls&&!mock.transactions,"no PERF after arm failure");
}
static void reset_bw(const char *name)
{
 reset_fw(name);mock.gmuperf=mock.gmubw=1;
 const uint32_t addr[]={0x50000,0x50004,0x50080,0x50054},unit[]={2050000,3650000,1,530000};
 const uint16_t width[]={16,32,0,8};const uint8_t vcd[]={0,1,11,3};
 for(unsigned n=0;n<4;n++)mock.bw_plan.db[n]=(struct gbcm_db){.address=addr[n],.unit=unit[n],.width=width[n],.vcd=vcd[n],.bank_version=0x1000};
}
static void bw_cases(void)
{
 for(int n=-1;n<=2;n++)if(n!=0&&n!=1){reset_bw("invalid BW flag");mock.gmubw=n;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.bw_calls&&!mock.bw_entries_calls,"BW flag exact0/1 before work");}
 for(unsigned dep=0;dep<4;dep++){
  reset_bw("BW prerequisite missing");if(dep==0)mock.gmuperf=0;else if(dep==1)mock.gmufw=0;else if(dep==2)mock.gmuclk=0;else mock.cxpower=0;
  run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.fw_calls&&!mock.bw_calls&&!mock.bw_entries_calls,"BW requires PERF/FW/clocks/CX before experiment");
 }
 for(unsigned n=1;n<=3;n++){
  reset_bw("BW ARC/asset preflight failure");mock.fw_fail_step=n;run_worker();
  CHECK(!mock.arms&&!mock.transactions&&!mock.bw_entries_calls&&!mock.bw_calls&&!mock.quarantines,"BW cannot bypass earlier preflight");
 }
 for(unsigned n=1;n<=2;n++){
  reset_bw("BW metadata/plan preflight failure");mock.bw_fail_step=n;run_worker();
  CHECK(!strcmp(mock.order,"RP")&&!mock.arms&&!mock.transactions&&!mock.bw_calls&&!mock.quarantines,"no WDT/RSC after missing BW entries or invalid plan");
  CHECK(has("same-boot bandwidth plan unavailable")&&!has("BW PLAN:"),"no fallback or false plan publication");
 }
 reset_bw("context lost after BW capture");mock.bw_fail_step=3;run_worker();
 CHECK(!mock.arms&&!mock.transactions&&!mock.bw_calls&&!mock.quarantines,"lost context before WDT prevents hardware transaction");
 for(unsigned n=GMB_ARGUMENT;n<=GMB_FIRMWARE;n++){
  reset_bw("every combined BW/TEST refusal terminal");mock.fw_result=(enum gmb_result)n;run_worker();
  CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&mock.bw_calls==1&&!mock.perf_calls&&!mock.after_sleeps&&mock.quarantines==1,"one combined call, no retry/poisoned receipt");
  CHECK(has("firmware stopped")&&!has("firmware complete")&&!has("PERF/BW/TEST startup done")&&!has("a5a5"),"no false completion after refusal");
 }
 reset_bw("BW full order");run_worker();
 CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&mock.bw_calls==1&&!mock.perf_calls&&mock.after_sleeps==30,"one combined cold bootstrap followed by bounded diagnostic reset wait");
 CHECK(count("SWEET GMU BW PLAN:")==4&&has("index=3 address=50054 unit=530000 width=8 vcd=3 bank=1000"),"same-boot four-resource metadata binding includes SN10");
 CHECK(has("PERF/BW/TEST startup done")&&has("no async HFI/power lifecycle/GPU commands/Metal")&&!has("PERF diagnostic done")&&!has("INIT/version diagnostic done"),"native startup completion remains bounded claim");
 reset_bw("BW forbidden after failed clock");mock.clock_result=GCX_READBACK;run_worker();CHECK(!mock.fw_calls&&!mock.bw_calls,"failed clock stops combined API");
 reset_bw("BW forbidden after WDT arm failure");mock.arm_fail=1;run_worker();CHECK(!mock.transactions&&!mock.fw_calls&&!mock.bw_calls,"failed watchdog prevents all later writes");
 reset_bw("BW excludes PAS");mock.pasinit=1;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.bw_calls,"PAS conflict rejects before work");
}
static void dcvs_cases(void)
{
 for(int n=-1;n<=2;n++)if(n!=0&&n!=1){reset_bw("invalid DCVS flag");mock.gmudcvs=n;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.dcvs_calls,"DCVS exact0/1 before work");}
 for(unsigned dep=0;dep<5;dep++){
  reset_bw("DCVS prerequisite missing");mock.gmudcvs=1;
  if(dep==0)mock.gmubw=0;else if(dep==1)mock.gmuperf=0;else if(dep==2)mock.gmufw=0;else if(dep==3)mock.gmuclk=0;else mock.cxpower=0;
  run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.fw_calls&&!mock.dcvs_calls,"DCVS requires BW/PERF/FW/clocks/CX before any work");
 }
 for(unsigned n=1;n<=3;n++){
  reset_bw("DCVS ARC/asset preflight failure");mock.gmudcvs=1;mock.fw_fail_step=n;run_worker();CHECK(!mock.arms&&!mock.transactions&&!mock.dcvs_calls&&!mock.quarantines,"DCVS cannot bypass ARC/asset preflight");
 }
 for(unsigned n=1;n<=3;n++){
  reset_bw("DCVS BW metadata/plan/context preflight failure");mock.gmudcvs=1;mock.bw_fail_step=n;run_worker();CHECK(!mock.arms&&!mock.transactions&&!mock.dcvs_calls&&!mock.quarantines,"DCVS cannot bypass snapshot/plan/context before WDT");
 }
 for(unsigned n=GMB_ARGUMENT;n<=GMB_FIRMWARE;n++){
  reset_bw("every DCVS bootstrap refusal terminal");mock.gmudcvs=1;mock.fw_result=(enum gmb_result)n;run_worker();
  CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&mock.dcvs_calls==1&&!mock.bw_calls&&!mock.perf_calls&&!mock.after_sleeps&&mock.quarantines==1,"one combined call; failure never retries/falls back");
  CHECK(has("firmware stopped")&&!has("firmware complete")&&!has("native DCVS request done")&&!has("a5a5"),"failed output not consumed");
 }
 reset_bw("DCVS full order");mock.gmudcvs=1;run_worker();
 CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.fw_calls==1&&mock.dcvs_calls==1&&!mock.bw_calls&&!mock.perf_calls&&mock.after_sleeps==30,"one combined startup after clock with bounded reset wait");
 CHECK(has("native DCVS request done")&&has("no measured rate/async HFI/power lifecycle/GPU commands/Metal")&&!has("PERF/BW/TEST startup done"),"request completion is not measured rate or GPU execution");
 reset_bw("DCVS default0 keeps BW/TEST");run_worker();CHECK(mock.bw_calls==1&&!mock.dcvs_calls&&has("PERF/BW/TEST startup done"),"old opt-in path unchanged");
 reset_bw("DCVS forbidden after failed clock");mock.gmudcvs=1;mock.clock_result=GCX_READBACK;run_worker();CHECK(!mock.fw_calls&&!mock.dcvs_calls,"failed clock prevents DCVS");
 reset_bw("DCVS forbidden after failed watchdog arm");mock.gmudcvs=1;mock.arm_fail=1;run_worker();CHECK(!mock.transactions&&!mock.fw_calls&&!mock.dcvs_calls,"failed WDT prevents DCVS");
 reset_bw("DCVS excludes PAS");mock.gmudcvs=1;mock.pasinit=1;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.dcvs_calls,"PAS conflict before work");
}
static void gpu_cases(void)
{
 for(int n=-1;n<=2;n++)if(n!=0&&n!=1){reset_bw("invalid GPU context flag");mock.gmudcvs=1;mock.gpucontext=n;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.gpu_calls,"GPU context exact0/1 before work");}
 for(unsigned dep=0;dep<6;dep++){
  reset_bw("GPU context missing prerequisite");mock.gmudcvs=mock.gpucontext=1;
  if(dep==0)mock.gmudcvs=0;else if(dep==1)mock.gmubw=0;else if(dep==2)mock.gmuperf=0;else if(dep==3)mock.gmufw=0;else if(dep==4)mock.gmuclk=0;else mock.cxpower=0;
  run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.gpu_calls,"GPU context requires full validated chain before work");
 }
 for(unsigned n=GMB_ARGUMENT;n<=GMB_GPU;n++){
  reset_bw("every GPU context refusal terminal");mock.gmudcvs=mock.gpucontext=1;mock.fw_result=(enum gmb_result)n;run_worker();
  CHECK(mock.gpu_calls==1&&mock.fw_calls==1&&!mock.dcvs_calls&&!mock.bw_calls&&!mock.perf_calls&&!mock.after_sleeps&&mock.quarantines==1,"one GPU cold API, no fallback/retry");
 }
 reset_bw("GPU context full order");mock.gmudcvs=mock.gpucontext=1;run_worker();
 CHECK(!strcmp(mock.order,"RPWTACGFQ")&&mock.gpu_calls==1&&mock.fw_calls==1&&!mock.dcvs_calls&&mock.after_sleeps==30,"GPU cold entry consumes existing order and sole boot");
 reset_bw("GPU context defaults off");mock.gmudcvs=1;run_worker();CHECK(mock.dcvs_calls==1&&!mock.gpu_calls,"legacy DCVS remains selected by default");
}
static void gpu_start_cases(void)
{
 for(int n=-1;n<=2;n++)if(n!=0&&n!=1){reset_bw("invalid GPU start flag");mock.gmudcvs=mock.gpucontext=1;mock.gpustart=n;run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.start_calls,"start exact0/1 before any work");}
 for(unsigned dep=0;dep<7;dep++){
  reset_bw("GPU start prerequisite missing");mock.gmudcvs=mock.gpucontext=mock.gpustart=1;
  if(dep==0)mock.gpucontext=0;else if(dep==1)mock.gmudcvs=0;else if(dep==2)mock.gmubw=0;else if(dep==3)mock.gmuperf=0;else if(dep==4)mock.gmufw=0;else if(dep==5)mock.gmuclk=0;else mock.cxpower=0;
  run_worker();CHECK(!mock.claims&&!mock.arms&&!mock.start_calls,"full147 chain required before start");
 }
 for(unsigned n=GGX_ARGUMENT;n<=GGX_TIMEOUT;n++){
  reset_bw("all GPU start errors terminal");mock.gmudcvs=mock.gpucontext=mock.gpustart=1;mock.start_result=(enum ggx_result)n;run_worker();
  CHECK(mock.sqe_calls==1&&mock.start_calls==1&&mock.quarantines==1&&!mock.after_sleeps&&has("GPU START BOOT: stopped")&&!has("native MMU/OOB/core reads done"),"no retry/fallback/false completion after failed live stage");
 }
 reset_bw("GPU start full order");mock.gmudcvs=mock.gpucontext=mock.gpustart=1;run_worker();
 CHECK(!strcmp(mock.order,"RPWTACGFXQ")&&mock.sqe_calls==1&&mock.start_calls==1&&mock.after_sleeps==30&&has("native MMU/OOB/core reads done"),"MMU/OOB live API follows accepted sole GPU cold firmware startup");
 reset_bw("GPU start default off");mock.gmudcvs=mock.gpucontext=1;run_worker();CHECK(!mock.sqe_calls&&!mock.start_calls&&!strcmp(mock.order,"RPWTACGFQ"),"147 path unchanged by default");
 reset_bw("GPU start after refused cold path forbidden");mock.gmudcvs=mock.gpucontext=mock.gpustart=1;mock.fw_result=GMB_GPU;run_worker();CHECK(!mock.start_calls,"no live API on cold-path error");
}
int main(void)
{
    legacy_cases();
    unsigned original=cases;
    init_cases();
    CHECK(cases-original==42 && cases==100,"58 retained plus42 focused INIT cases");
    printf("PASS: %u original + %u INIT coordinator cases (%u total); MEM disabled, original assertions preserved\n",
        original,cases-original,cases);
    unsigned before_mem=cases;
    mem_cases();
    CHECK(cases-before_mem==49 && cases==149,"100 retained plus49 focused MEM cases");
    printf("PASS: 100 retained + %u MEM coordinator cases (%u total); actual coordinator, typed helper seams, no real SMC/reset/GPU\n",
        cases-before_mem,cases);
    unsigned before_cx=cases;
    cx_cases();
    printf("PASS: 149 retained + %u CX coordinator cases (%u total); BCM -> ARC -> CX, no PAS, typed seams only\n",
        cases-before_cx,cases);
    CHECK(cases==241,"all241 coordinator cases retained");unsigned before_clock=cases;clock_cases();
    printf("PASS: 241 retained + %u GMU clock coordinator cases (%u total)\n",cases-before_clock,cases);
    unsigned before_fw=cases;firmware_cases();
    printf("PASS: %u retained + %u GMU firmware coordinator cases (%u total); typed seams only\n",before_fw,cases-before_fw,cases);
    unsigned before_perf=cases;perf_cases();
    CHECK(cases-before_perf==23,"23 focused PERF coordinator cases");
    printf("PASS: %u retained + %u PERF coordinator cases (%u total); typed seams only\n",before_perf,cases-before_perf,cases);
    unsigned before_bw=cases;bw_cases();
    printf("PASS: %u retained + %u BW/TEST coordinator cases (%u total); typed seams only\n",before_bw,cases-before_bw,cases);
    unsigned before_dcvs=cases;dcvs_cases();
    printf("PASS: %u retained + %u DCVS coordinator cases (%u total); typed seams only\n",before_dcvs,cases-before_dcvs,cases);
    unsigned before_gpu=cases;gpu_cases();
    printf("PASS: %u retained + %u GPU context coordinator cases (%u total); typed seams only\n",before_gpu,cases-before_gpu,cases);
    unsigned before_start=cases;gpu_start_cases();
    printf("PASS: %u retained + %u GPU start coordinator cases (%u total); typed seams only\n",before_start,cases-before_start,cases);
    return 0;
}
