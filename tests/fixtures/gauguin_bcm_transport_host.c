/* Actual BCM transport with ordinary host platform seams. No MMIO/device,
 * sleeps, hardware clocks, assembly or executable rewriting. Independent
 * register/write oracle and board fixture; the real planner is linked. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "cmd_db_snapshot.h"
#include "gauguin_bcm_transport.h"
#include "gauguin_wdt_lease.h"
#include "gauguin_cx_rail.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define VM_PROT_READ 1u
#define VM_PROT_WRITE 2u
#define NSEC_PER_MSEC UINT64_C(1000000)
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef uint32_t vm_prot_t;
typedef uint32_t ppnum_t;
typedef int boolean_t;
#define CHECK(c,why) do { if(!(c)) { fprintf(stderr,"FAIL line %d [%s]: %s\n",__LINE__,case_name,why); exit(1); } } while(0)
#define FAKE_MAP UINT64_C(0x100000000)
#define OWN 0xfa0u
#define FRAME_WORDS (0x4000u/4u)
#define START_BUDGET 491475u
#define STEP_BUDGET 98295u
static const char *case_name="setup";
static unsigned cases;
static const char *const conflicts[]={"sweettouchmode","sweetwdtpet","sweetreboot",
    "sweetbusprobe","sweetgpuprobe","sweetscmprobe","sweetwdttest"};
static struct {
    int requested,conflict[7],context,cx_requested,pas_init,pas_mem;
    unsigned arc_phase;
    unsigned maps,translations,managed,attr,map_failure,translation_failure;
    unsigned reads,writes,dmb_read,dmb_store,dsb,pending_read,pending_store;
    unsigned write_limit,fail_readback_write,budget_calls,budget_fail_call,budget_fail_writes;
    unsigned quarantine,gic_calls,gic_fail_call,config_reads,change_snapshot;
    unsigned latent_irq,no_completion,foreign_completion,missing_issued,missing_compl,ones_status;
    unsigned bad_idle,bad_control,bad_irq_owner,payload_reread,final_config;
    unsigned clear_stuck,clear_foreign,cleanup_irq_change,deadline_write;
    unsigned triggers,irq_clears,command_status_reads,sleeps,delays,markers,flushes,lines;
    unsigned observed_reads[FRAME_WORDS];
    uint32_t reg[FRAME_WORDS];
    uint32_t write_offset[31],write_value[31];
    uint64_t now,deadline;
    char log[32][224];
} mock;
static const uint32_t addresses[6]={0x50000,0x50004,0x5002c,0x50044,0x5006c,0x50080};
static const uint32_t data_words[6]={0x6fffffff,0x6fffffff,0x2fffffff,0x6fffffff,0x6fffffff,0x60000008};
static struct gbcm_plan plan;
static struct gcr_plan cx_plan;
static struct gbcmt_receipt bcm_history;
static unsigned trigger_write(void) { return mock.arc_phase ? 10u : 25u; }
static unsigned clear_write(void) { return mock.arc_phase ? 15u : 30u; }
static unsigned controls_write(void) { return mock.arc_phase ? 6u : 21u; }
static uint32_t command(unsigned c,unsigned reg) { return OWN+0x14*c+reg; }
static bool read_allowed(unsigned off)
{
    if(off==0xc || off==0xd00 || off==0xd04) return true;
    for(unsigned t=0;t<8;++t) {
        unsigned base=0xd00+t*0x2a0;
        if(off>=base+0x10 && off<=base+0x1c && !(off&3)) return true;
    }
    for(unsigned c=0;c<6;++c) for(unsigned r=0x30;r<=0x3c;r+=4)
        if(off==command(c,r)) return true;
    return false;
}
static void no_pending_barrier(void)
{ CHECK(!mock.pending_read && !mock.pending_store,"previous register access completed barrier"); }
static void fake_dmb_read(void)
{ CHECK(mock.pending_read && !mock.pending_store,"DMB oshld immediately after read"); mock.pending_read=0; ++mock.dmb_read; }
static void fake_dmb_store(void)
{ no_pending_barrier(); mock.pending_store=1; ++mock.dmb_store; }
static void fake_dsb(void)
{ CHECK(mock.pending_store==2 && !mock.pending_read,"DSB osh immediately after write"); mock.pending_store=0; ++mock.dsb; }
static uint32_t fake_read(unsigned off)
{
    no_pending_barrier(); CHECK(mock.maps==1 && mock.translations==2,"translate before read");
    CHECK(off<0x4000 && !(off&3) && read_allowed(off),"exact read whitelist; never IRQ_CLEAR/RESP/PDC");
    ++mock.reads; ++mock.observed_reads[off/4];
    if(off==0xc) {
        ++mock.config_reads;
        if(mock.change_snapshot && mock.config_reads==mock.change_snapshot)
            mock.reg[(0xd00+7*0x2a0+0x18)/4]=2; /* legal but changes repeated snapshot */
    }
    uint32_t value=mock.reg[off/4];
    if(mock.fail_readback_write && mock.writes==mock.fail_readback_write &&
        off==mock.write_offset[mock.writes-1]) value=mock.write_value[mock.writes-1]^1u;
    if(mock.bad_control==1 && mock.writes==controls_write() && off==OWN+0x14) value=1;
    if(mock.bad_irq_owner==1 && mock.writes==controls_write() && off==0xd00) value=7;
    if(mock.final_config && mock.writes==trigger_write()-1 && off==0xc) value^=1;
    if(mock.payload_reread==1 && mock.writes==trigger_write()-1 && off==command(0,0x38)) value^=1;
    if(mock.payload_reread==2 && mock.writes==trigger_write() && off==command(0,0x38)) value^=1;
    if(mock.writes>=trigger_write()) {
        for(unsigned c=0;c<(mock.arc_phase ? 1u:6u);++c) if(off==command(c,0x3c)) {
            ++mock.command_status_reads;
            if(mock.missing_issued==c+1) value&=~0x100u;
            if(mock.missing_compl==c+1) value&=~0x10000u;
            if(mock.ones_status==c+1) value=UINT32_MAX;
        }
        if(mock.bad_idle && off==OWN+0x18) value=mock.bad_idle==1 ? 0:UINT32_MAX;
        if(mock.bad_control==2 && off==OWN+0x14 && mock.writes==trigger_write()) value|=1;
        if(mock.bad_irq_owner==2 && off==0xd00 && mock.writes==trigger_write()) value=7;
    }
    if(mock.cleanup_irq_change && mock.writes==clear_write() && off==0xd00) value=7;
    mock.pending_read=1; return value;
}
static void expected_write(unsigned n,uint32_t *off,uint32_t *value)
{
    if(mock.arc_phase) {
        static const uint32_t offsets[]={0xd00, OWN+0x30, OWN+0x34, OWN+0x38,
            OWN+0x10, OWN+0x1c, OWN+0x14, OWN+0x14, OWN+0x14, OWN+0x14,
            OWN+0x14, OWN+0x14, OWN+0x1c, OWN+0x10, 0xd08, 0xd00};
        static const uint32_t values[]={3,0x10108,0x30000,6,0,1,0,0,0x10000,
            0x1010000,0x10000,0,0,0,2,1};
        CHECK(n<16,"at most16 ARC writes"); *off=offsets[n]; *value=values[n]; return;
    }
    CHECK(n<31,"at most31 writes in successful native flow");
    if(n==0) { *off=0xd00; *value=3; }
    else if(n<=18) {
        unsigned c=(n-1)/3,f=(n-1)%3; *off=command(c,0x30+4*f);
        *value=f==0 ? (c==2 ? 0x10008u:0x10108u):f==1 ? addresses[c]:data_words[c];
    } else {
        static const uint32_t offsets[]={OWN+0x10,OWN+0x1c,OWN+0x14,OWN+0x14,OWN+0x14,
            OWN+0x14,OWN+0x14,OWN+0x14,OWN+0x1c,OWN+0x10,0xd08,0xd00};
        static const uint32_t values[]={0x3b,0x3f,0,0,0x10000,0x1010000,0x10000,0,0,0,2,1};
        *off=offsets[n-19]; *value=values[n-19];
    }
}
static void fake_write(unsigned off,uint32_t value)
{
    uint32_t expected_off,expected_value;
    CHECK(mock.pending_store==1 && !mock.pending_read,"DMB oshst before every write");
    CHECK(mock.maps==1 && mock.translations==2 && mock.config_reads>=3,"three stable snapshots before writes");
    CHECK(mock.writes<mock.write_limit,"no extra write/cleanup after injected uncertainty");
    expected_write(mock.writes,&expected_off,&expected_value);
    CHECK(off==expected_off && value==expected_value,"exact own-slot native write order and values");
    mock.write_offset[mock.writes]=off; mock.write_value[mock.writes]=value; ++mock.writes;
    if(off==0xd08) {
        ++mock.irq_clears; CHECK(value==2 && mock.triggers==1,"ACK only own completed IRQ after trigger");
        if(mock.clear_foreign) mock.reg[0xd04/4]=4;
        else if(!mock.clear_stuck) mock.reg[0xd04/4]&=~value;
    } else {
        mock.reg[off/4]=value;
        if(mock.writes==1 && mock.latent_irq) mock.reg[0xd04/4]=2;
        if(off==OWN+0x14 && (value&0x1000000)) {
            ++mock.triggers; CHECK(mock.triggers==1,"trigger exactly once");
            if(mock.foreign_completion) mock.reg[0xd04/4]=4;
            else if(!mock.no_completion) mock.reg[0xd04/4]=2;
        }
    }
    if(mock.deadline_write && mock.writes==mock.deadline_write) mock.now=mock.deadline;
    mock.pending_store=2;
}
static int test_printf(const char *fmt,...)
{
    va_list ap; int n; no_pending_barrier(); CHECK(mock.lines<32,"bounded transaction log");
    va_start(ap,fmt); n=vsnprintf(mock.log[mock.lines],sizeof(mock.log[0]),fmt,ap); va_end(ap);
    CHECK(n>0 && (size_t)n<sizeof(mock.log[0]) && mock.log[mock.lines][n-1]=='\n',"bounded line"); ++mock.lines; return n;
}
bool PE_parse_boot_argn(const char *key,void *out,size_t bytes)
{
    CHECK(bytes==sizeof(int),"integer boot argument");
    if(!strcmp(key,"sweetbusvote")) { *(int*)out=mock.requested; return true; }
    if(!strcmp(key,"sweetcxpower")) { *(int*)out=mock.cx_requested; return true; }
    if(!strcmp(key,"sweetpasinit")) { *(int*)out=mock.pas_init; return true; }
    if(!strcmp(key,"sweetpasmem")) { *(int*)out=mock.pas_mem; return true; }
    for(unsigned i=0;i<7;++i) if(!strcmp(key,conflicts[i])) { *(int*)out=mock.conflict[i]; return true; }
    CHECK(false,"known boot argument"); return false;
}
int ml_get_interrupts_enabled(void) { return mock.context!=1; }
int ml_at_interrupt_context(void) { return mock.context==2; }
int get_preemption_level(void) { return mock.context==3 ? 1:0; }
unsigned long long mach_absolute_time(void) { no_pending_barrier(); return mock.now; }
void clock_interval_to_deadline(unsigned interval,uint64_t scale,uint64_t *deadline)
{
    CHECK(interval==(mock.arc_phase ? 5000u:10000u) && scale==NSEC_PER_MSEC,"phase shared deadline");
    *deadline=mock.now+interval*scale; mock.deadline=*deadline;
}
void IOSleep(unsigned ms) { no_pending_barrier(); CHECK(ms==1,"one-ms snapshot/poll sleep"); ++mock.sleeps; mock.now+=(uint64_t)ms*1000000; }
void delay(unsigned us) { no_pending_barrier(); CHECK(us==10,"bounded ten-us sync poll"); ++mock.delays; mock.now+=(uint64_t)us*1000; }
void sweet_log_mark_sync(const char *s)
{ CHECK(mock.context==0,"synchronous mark only in preemptible thread context"); CHECK(mock.lines && strstr(mock.log[mock.lines-1],s),"marker matches last record"); CHECK(mock.markers==mock.flushes,"previous flush"); ++mock.markers; }
void sweet_log_flush_now(void) { CHECK(mock.context==0,"synchronous flush only in preemptible thread context"); CHECK(mock.markers==mock.flushes+1,"one flush per marker"); ++mock.flushes; }
boolean_t pmap_valid_page(ppnum_t pn)
{ CHECK(pn==(0x18220000u>>14),"one DRV2 physical page"); return mock.managed; }
unsigned int pmap_cache_attributes(ppnum_t pn)
{ CHECK(pn==(0x18220000u>>14),"one DRV2 cache attribute"); return mock.attr; }
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t size,vm_prot_t prot)
{
    CHECK(pa==0x18220000u && size==0x4000 && prot==3,"exact DRV2 read/write mapping");
    CHECK(!mock.maps && mock.gic_calls==1 && mock.budget_calls==1 && !mock.managed && (mock.attr&255)==7,
        "initial budget/GIC/pmap before map");
    CHECK(mock.markers==mock.flushes && mock.markers>0,"mapping preceded by persisted marker");
    ++mock.maps; return mock.map_failure ? 0:FAKE_MAP;
}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    unsigned endpoint=mock.translations++;
    CHECK(endpoint<2 && va==FAKE_MAP+(endpoint ? 0x3fffu:0u),"exact first/final-byte translations");
    return UINT64_C(0x18220000)+(endpoint ? 0x3fffu:0u)+(mock.translation_failure==endpoint+1 ? 1u:0u);
}
bool gauguin_wdt_lease_check_budget(uint32_t minimum)
{
    no_pending_barrier(); CHECK(minimum==(mock.arc_phase ? 327650u:START_BUDGET) || minimum==STEP_BUDGET,"phase native tick budget request");
    CHECK(!mock.quarantine,"never check lease after quarantine"); ++mock.budget_calls;
    if(mock.budget_calls==1) CHECK(minimum==(mock.arc_phase ? 327650u:START_BUDGET),"initial phase minimum");
    return mock.budget_calls!=mock.budget_fail_call && mock.writes<mock.budget_fail_writes;
}
void gauguin_wdt_lease_quarantine(void)
{ no_pending_barrier(); CHECK(!mock.quarantine,"one software quarantine, no hardware action"); ++mock.quarantine; }
bool sweet_rsc_irq_quiet(uint32_t *value)
{
    no_pending_barrier(); CHECK(value && mock.gic_calls<3,"three bounded GIC quiet checks");
    ++mock.gic_calls; *value=mock.gic_calls==mock.gic_fail_call ? 0x20u:0;
    return *value==0;
}
#define printf test_printf
@SOURCE@
#undef printf

static void put16(uint8_t *p,unsigned v) { p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p,uint32_t v) { for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(v>>(8*i)); }
static void make_plan(void)
{
    static const char *const names[]={"MC0","SH0","SN0","SN6","CE0","ACV"};
    static const uint32_t units[]={2050000,3650000,530000,530000,7935,1};
    static const uint16_t widths[]={16,32,16,16,8,0};
    static const uint8_t vcds[]={0,1,3,3,6,11};
    struct ndb_entry entries[6]; memset(entries,0,sizeof(entries));
    for(unsigned i=0;i<6;++i) {
        memcpy(entries[i].name,names[i],strlen(names[i])); entries[i].address=addresses[i];
        entries[i].owner_slave=5;entries[i].bank_version=0x1000;entries[i].aux_length=8;
        put32(entries[i].aux,units[i]);put16(entries[i].aux+4,widths[i]);entries[i].aux[6]=vcds[i];
    }
    CHECK(gbcm_build(entries,6,&plan)==GBCM_OK,"real planner accepts independent board metadata");
    CHECK(plan.wait_mask==0x3b,"independent wait-mask expectation");
    for(unsigned i=0;i<6;++i)CHECK(plan.cmd[i].data==data_words[i],"independent packet expectation");
}
static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock));case_name=name;++cases;
    mock.requested=1;mock.attr=0xd0000007u;mock.write_limit=31;mock.budget_fail_writes=UINT32_MAX;mock.now=1;
    mock.reg[0xc/4]=0x80008104;mock.reg[0xd00/4]=1;
    for(unsigned t=0;t<8;++t)mock.reg[(0xd00+t*0x2a0+0x18)/4]=1;
    /* Stale complete-looking command statuses are present even BEFORE trigger.
     * They must NEVER stand in for this request's new own IRQ. */
    for(unsigned c=0;c<6;++c)mock.reg[command(c,0x3c)/4]=0x10100;
    gt_state=GBCMT_IDLE;gt_map=0;gt_wrote=false;gt_deadline=0;memset(&gt_receipt,0,sizeof(gt_receipt));make_plan();
    gt_owner=gt_controller_quarantined=0;gcr_lifecycle=GCR_IDLE;gt_arc=false;
    memset(&gcr_receipt,0,sizeof(gcr_receipt));
    struct ndb_entry e={0}; memcpy(e.name,"cx.lvl",6); e.address=0x30000;
    e.owner_slave=3;e.bank_version=0x1000;e.aux_length=32;
    const unsigned levels[]={0,16,64,128,192,256,384,0};
    for(unsigned i=0;i<8;++i) put16(e.aux+2*i,levels[i]);
    CHECK(gcr_plan_build(&e,&cx_plan),"real CX planner accepts board levels");
}
static bool has(const char *needle)
{ for(unsigned i=0;i<mock.lines;++i)if(strstr(mock.log[i],needle))return true;return false; }
static void barriers(void)
{
    no_pending_barrier();CHECK(mock.reads==mock.dmb_read && mock.writes==mock.dmb_store && mock.writes==mock.dsb,
        "every load/store keeps production barrier ordering");
}
static void failure(enum gbcmt_rc want,unsigned writes)
{
    struct gbcmt_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
    enum gbcmt_rc rc=sweet_bcm_submit_once(&plan,&out);barriers();
    if(rc!=want)fprintf(stderr,"rc=%u expected=%u writes=%u expected=%u\n",rc,want,mock.writes,writes);
    CHECK(rc==want && mock.writes==writes,"expected failure point and exact write prefix");
    CHECK(!memcmp(&out,&saved,sizeof(out)),"failure leaves caller receipt unchanged");
    CHECK(!has("native completion verified"),"failure must not log completion");
    CHECK(sweet_bcm_transport_state()==(writes ? GBCMT_QUARANTINED:GBCMT_REJECTED) && mock.quarantine==1,
        "every started failure terminal; writes quarantine controller");
    CHECK(sweet_bcm_submit_once(&plan,&out)==GBCMT_ALREADY,"no second attempt after failure");
    CHECK(mock.writes==writes && !memcmp(&out,&saved,sizeof(out)),"retry causes no cleanup or output");
}
static void success(void)
{
    struct gbcmt_receipt out;memset(&out,0xa5,sizeof(out));
    CHECK(sweet_bcm_submit_once(&plan,&out)==GBCMT_OK,"successful native controller completion");barriers();
    CHECK(mock.writes==31 && mock.triggers==1 && mock.irq_clears==1 && mock.gic_calls==3,"exact successful transaction");
    CHECK(!mock.quarantine && sweet_bcm_transport_state()==GBCMT_COMPLETE,"complete state without quarantine");
    CHECK(has("native completion verified"),"success emits the verified completion record");
    CHECK(out.slot==1 && out.config==0x80008104 && out.irq_before==1 && out.irq_after==1 && out.irq_completed==2,
        "actual receipt fields");
    for(unsigned c=0;c<6;++c)CHECK(out.cmd_status[c]==mock.reg[command(c,0x3c)/4],"six completion statuses retained");
    CHECK(mock.command_status_reads==6 && mock.reg[0xd00/4]==1 && mock.reg[0xd04/4]==0,"own IRQ clear+restore only");
    CHECK(mock.reg[(OWN+0x10)/4]==0 && mock.reg[(OWN+0x1c)/4]==0 && mock.reg[(OWN+0x14)/4]==0,"native slot cleanup");
    for(unsigned c=0;c<6;++c)CHECK(mock.reg[command(c,0x38)/4]==data_words[c],"votes never zeroed on cleanup");
    struct gbcmt_receipt saved=out;CHECK(sweet_bcm_submit_once(&plan,&out)==GBCMT_ALREADY,"success also one-shot");
    CHECK(!memcmp(&out,&saved,sizeof(out)) && mock.writes==31,"no successful reuse");
}
/* Complete the REAL BCM path first, retain all production globals and MMIO
 * words, then reset only per-phase host instrumentation. No synthetic COMPLETE
 * state, new map or driver reset is used to authorize ARC. */
static void arc_reset(const char *name)
{
    reset(name); success(); bcm_history=gt_receipt;
    uint32_t registers[FRAME_WORDS]; memcpy(registers,mock.reg,sizeof(registers));
    memset(&mock,0,sizeof(mock));memcpy(mock.reg,registers,sizeof(registers));
    mock.arc_phase=1;mock.maps=1;mock.attr=0xd0000007u;mock.requested=1;mock.cx_requested=1;
    mock.write_limit=16;mock.budget_fail_writes=UINT32_MAX;mock.now=1;
}
static void retained(void)
{
    CHECK(sweet_bcm_transport_state()==GBCMT_COMPLETE && !memcmp(&bcm_history,&gt_receipt,sizeof(bcm_history)),"ARC never rewrites BCM history");
    CHECK(mock.maps==1 && gt_map==FAKE_MAP,"ARC retains single original mapping");
    CHECK(gt_owner==0,"owner released only on return"); barriers();
}
static void arc_failure(enum gbcmt_rc want,unsigned writes)
{
    struct gbcmt_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
    enum gbcmt_rc rc=sweet_cx_rail_submit_once(&cx_plan,&out);
    if(rc!=want)fprintf(stderr,"ARC rc=%u expected=%u writes=%u expected=%u\n",rc,want,mock.writes,writes);
    CHECK(rc==want && mock.writes==writes,"ARC exact failure write prefix");
    CHECK(!memcmp(&out,&saved,sizeof(out)),"ARC failure caller unchanged");retained();
    CHECK(sweet_cx_rail_state()==(writes ? GCR_QUARANTINED:GCR_REJECTED) && mock.quarantine==1 && gt_controller_quarantined==1,"ARC failure quarantines shared controller and lease");
    CHECK(!has("synchronous completion verified"),"no premature ARC success");
    CHECK(sweet_cx_rail_submit_once(&cx_plan,&out)==GBCMT_ALREADY && sweet_bcm_submit_once(&plan,&out)==(mock.requested==1 ? GBCMT_ALREADY:GBCMT_OFF),"no retry via either API");
    CHECK(mock.writes==writes && !memcmp(&out,&saved,sizeof(out)),"no retry cleanup/output");
}
static void arc_tests(void)
{
    const int off[]={0,2,-1};
    for(unsigned i=0;i<3;++i) {
        arc_reset("ARC exact default off");mock.cx_requested=off[i];
        struct gbcmt_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
        CHECK(sweet_cx_rail_submit_once(&cx_plan,&out)==GBCMT_OFF,"ARC flag exact1");
        CHECK(!mock.writes && !mock.budget_calls && !mock.quarantine && !mock.translations && sweet_cx_rail_state()==GCR_IDLE && !memcmp(&out,&saved,sizeof(out)),"ARC off no effects");retained();
    }
    arc_reset("ARC null arguments");struct gbcmt_receipt out;
    CHECK(sweet_cx_rail_submit_once(NULL,&out)==GBCMT_ARGUMENT && sweet_cx_rail_submit_once(&cx_plan,NULL)==GBCMT_ARGUMENT && sweet_cx_rail_state()==GCR_IDLE && !mock.quarantine,"ARC argument does not consume attempt");retained();
    arc_reset("ARC native synchronous completion");memset(&out,0xa5,sizeof(out));
    CHECK(sweet_cx_rail_submit_once(&cx_plan,&out)==GBCMT_OK,"ARC completion");retained();
    CHECK(mock.writes==16 && mock.triggers==1 && mock.irq_clears==1 && mock.command_status_reads==1 && mock.gic_calls==3,"exact ARC request and fresh IRQ");
    CHECK(!mock.quarantine && !gt_controller_quarantined && sweet_cx_rail_state()==GCR_COMPLETE && has("synchronous completion verified"),"ARC success state");
    CHECK(out.slot==1 && out.config==0x80008104 && out.irq_before==1 && out.irq_after==1 && out.irq_completed==2 && out.cmd_status[0]==0x10100,"ARC real receipt");
    for(unsigned i=1;i<6;++i) CHECK(out.cmd_status[i]==0,"no old BCM status published in ARC receipt");
    CHECK(mock.reg[command(0,0x38)/4]==6 && mock.reg[(OWN+0x10)/4]==0 && mock.reg[(OWN+0x1c)/4]==0 && mock.reg[(OWN+0x14)/4]==0,"ARC retained request/native cleanup");
    CHECK(sweet_cx_rail_submit_once(&cx_plan,&out)==GBCMT_ALREADY && mock.writes==16,"ARC one attempt");
    for(unsigned api=0;api<2;++api) {
        reset("shared owner BUSY untouched");mock.cx_requested=1;gt_owner=1;
        struct gbcmt_receipt saved;memset(&out,0xa5,sizeof(out));saved=out;
        CHECK((api ? sweet_cx_rail_submit_once(&cx_plan,&out):sweet_bcm_submit_once(&plan,&out))==GBCMT_BUSY,"non-owner BUSY");
        CHECK(gt_owner==1 && gt_state==GBCMT_IDLE && gcr_lifecycle==GCR_IDLE && !gt_controller_quarantined && !gt_arc && !mock.quarantine && !mock.maps && !mock.budget_calls && !memcmp(&out,&saved,sizeof(out)),"non-owner no state/output/lease effects");
    }
    reset("ARC before BCM rejected");mock.cx_requested=1;
    CHECK(sweet_cx_rail_submit_once(&cx_plan,&out)==GBCMT_CONFIG && sweet_cx_rail_state()==GCR_REJECTED && sweet_bcm_transport_state()==GBCMT_IDLE && !mock.maps && !mock.writes && !mock.budget_calls && mock.quarantine==1 && gt_controller_quarantined==1 && !gt_owner,"requires real BCM mapping/completion");
    for(unsigned i=0;i<3;++i){arc_reset("ARC context invalid");mock.context=(int)i+1;arc_failure(GBCMT_CONTEXT,0);}
    for(unsigned key=0;key<7;++key)for(int v=-1;v<=1;v+=2){arc_reset("ARC legacy conflict");mock.conflict[key]=v;arc_failure(GBCMT_CONFIG,0);}
    for(int v=-1;v<=2;++v)if(v!=0){arc_reset("ARC PAS INIT prohibited");mock.pas_init=v;arc_failure(GBCMT_CONFIG,0);arc_reset("ARC PAS MEM prohibited");mock.pas_mem=v;arc_failure(GBCMT_CONFIG,0);}
    for(unsigned i=0;i<3;++i){arc_reset("ARC bus flag exact1");mock.requested=off[i];arc_failure(GBCMT_CONFIG,0);}
    for(unsigned field=0;field<21;++field){
        arc_reset("ARC plan exact domain");
        if(field==0)cx_plan.address^=4;if(field==1)cx_plan.selector=2;if(field==2)cx_plan.level=64;
        if(field==3)cx_plan.count=8;if(field==4)cx_plan.max_level--;
        if(field>=5)cx_plan.levels[field-5]^=1;arc_failure(GBCMT_CONFIG,0);
    }
    arc_reset("ARC armed lease lost");mock.budget_fail_call=1;arc_failure(GBCMT_BUDGET,0);
    arc_reset("ARC GIC initial guard");mock.gic_fail_call=1;arc_failure(GBCMT_CONFIG,0);
    arc_reset("ARC pmap managed");mock.managed=1;arc_failure(GBCMT_MAPPING,0);
    arc_reset("ARC wrong attr");mock.attr=6;arc_failure(GBCMT_MAPPING,0);
    for(unsigned i=1;i<=2;++i){arc_reset("ARC translation rechecked");mock.translation_failure=i;arc_failure(GBCMT_MAPPING,0);}
    arc_reset("ARC initial own pending IRQ");mock.reg[0xd04/4]=2;arc_failure(GBCMT_BUSY,0);
    arc_reset("ARC initial foreign IRQ");mock.reg[0xd04/4]=4;arc_failure(GBCMT_BUSY,0);
    for(unsigned t=0;t<8;++t)for(unsigned field=0;field<4;++field){arc_reset("ARC repeated all-slot inert check");mock.reg[(0xd00+t*0x2a0+0x10+4*field)/4]=field==2 ? 0:1;arc_failure(GBCMT_BUSY,0);}
    for(unsigned i=2;i<=3;++i){arc_reset("ARC snapshots changed");mock.change_snapshot=i;arc_failure(GBCMT_BUSY,0);}
    arc_reset("ARC latent IRQ");mock.latent_irq=1;mock.write_limit=1;arc_failure(GBCMT_BUSY,1);CHECK(!mock.irq_clears && !mock.triggers,"ARC latent IRQ not ACKed");
    for(unsigned n=1;n<=16;++n)if(n!=10 && n!=15){arc_reset("ARC uncertain sync readback");mock.fail_readback_write=n;mock.write_limit=n;arc_failure(GBCMT_READBACK,n);CHECK(mock.delays==1000,"bounded single store readback");}
    arc_reset("ARC control before trigger changes");mock.bad_control=1;mock.write_limit=6;arc_failure(GBCMT_BUSY,6);
    arc_reset("ARC IRQ owner before trigger changes");mock.bad_irq_owner=1;mock.write_limit=6;arc_failure(GBCMT_BUSY,6);
    arc_reset("ARC final GIC changed");mock.gic_fail_call=3;mock.write_limit=9;arc_failure(GBCMT_BUSY,9);
    arc_reset("ARC final geometry changed");mock.final_config=1;mock.write_limit=9;arc_failure(GBCMT_BUSY,9);
    arc_reset("ARC payload changed");mock.payload_reread=1;mock.write_limit=9;arc_failure(GBCMT_BUSY,9);
    arc_reset("ARC stale statuses no own IRQ");mock.no_completion=1;mock.write_limit=10;arc_failure(GBCMT_TIMEOUT,10);CHECK(!mock.command_status_reads && !mock.irq_clears,"ARC stale status never accepted");
    arc_reset("ARC foreign completion");mock.foreign_completion=1;mock.write_limit=10;arc_failure(GBCMT_BUSY,10);CHECK(!mock.irq_clears,"no foreign ACK");
    arc_reset("ARC missing issued");mock.missing_issued=1;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);
    arc_reset("ARC WAIT0 still requires COMPL");mock.missing_compl=1;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);
    arc_reset("ARC status unavailable");mock.ones_status=1;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);
    for(unsigned i=1;i<=2;++i){arc_reset("ARC completed slot not idle");mock.bad_idle=i;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);}
    arc_reset("ARC completed control changed");mock.bad_control=2;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);
    arc_reset("ARC completed IRQ owner changed");mock.bad_irq_owner=2;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);
    arc_reset("ARC completed payload changed");mock.payload_reread=2;mock.write_limit=10;arc_failure(GBCMT_COMPLETION,10);
    arc_reset("ARC IRQ clear timeout");mock.clear_stuck=1;mock.write_limit=15;arc_failure(GBCMT_TIMEOUT,15);
    arc_reset("ARC foreign IRQ during cleanup");mock.clear_foreign=1;mock.write_limit=15;arc_failure(GBCMT_BUSY,15);
    arc_reset("ARC IRQ ownership lost during cleanup");mock.cleanup_irq_change=1;mock.write_limit=15;arc_failure(GBCMT_BUSY,15);
    arc_reset("ARC lease expires after trigger");mock.budget_fail_writes=10;mock.write_limit=10;arc_failure(GBCMT_TIMEOUT,10);
    arc_reset("ARC lease lost mid cleanup");mock.budget_fail_writes=12;mock.write_limit=12;arc_failure(GBCMT_READBACK,12);
    arc_reset("ARC shared deadline expires");mock.deadline_write=10;mock.write_limit=10;arc_failure(GBCMT_TIMEOUT,10);
}
int main(void)
{
    const int off[]={0,2,-1};
    for(unsigned i=0;i<3;++i) {
        reset("exact default off");mock.requested=off[i];struct gbcmt_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
        CHECK(!sweet_bcm_vote_requested() && sweet_bcm_submit_once(&plan,&out)==GBCMT_OFF,"flag exact1");
        CHECK(!mock.maps && !mock.writes && !mock.budget_calls && !mock.quarantine && sweet_bcm_transport_state()==GBCMT_IDLE && !memcmp(&out,&saved,sizeof(out)),"off has no effects");
    }
    reset("null argument");struct gbcmt_receipt out;CHECK(sweet_bcm_submit_once(NULL,&out)==GBCMT_ARGUMENT && sweet_bcm_submit_once(&plan,NULL)==GBCMT_ARGUMENT,"nonnull required");
    CHECK(!mock.maps && !mock.quarantine && sweet_bcm_transport_state()==GBCMT_IDLE,"argument failure does not consume attempt");
    reset("normal completion");success();
    reset("non-wait SN0 needs ISSUED only");mock.reg[command(2,0x3c)/4]=0x100;success();
    for(int c=1;c<=3;++c) {reset("invalid context");mock.context=c;failure(GBCMT_CONTEXT,0);}
    for(unsigned key=0;key<7;++key)for(int value=-1;value<=1;value+=2) {reset("conflicting boot flag");mock.conflict[key]=value;failure(GBCMT_CONFIG,0);}
    for(unsigned mutation=0;mutation<8;++mutation) {
        reset("invalid plan");
        if(mutation==0)plan.wait_mask^=1;if(mutation==1)plan.cmd[0].data^=1;
        if(mutation==2)plan.cmd[2].wait=1;if(mutation==3)plan.db[3].unit++;
        if(mutation==4)plan.db[4].reserved=1;if(mutation==5)plan.db[5].width=1;
        if(mutation==6)plan.cmd[0].address+=4;if(mutation==7)plan.db[1].vcd++;
        failure(GBCMT_CONFIG,0);
    }
    reset("no armed lease");mock.budget_fail_call=1;failure(GBCMT_BUDGET,0);
    reset("GIC initial guard");mock.gic_fail_call=1;failure(GBCMT_CONFIG,0);
    reset("managed map page");mock.managed=1;failure(GBCMT_MAPPING,0);
    reset("wrong cache attribute");mock.attr=6;failure(GBCMT_MAPPING,0);
    reset("mapping fails");mock.map_failure=1;failure(GBCMT_MAPPING,0);
    for(unsigned i=1;i<=2;++i){reset("endpoint translation fails");mock.translation_failure=i;failure(GBCMT_MAPPING,0);}
    const uint32_t configs[]={0,(7u<<12)|(16u<<27),(8u<<12)|(5u<<27),(8u<<12)|(17u<<27)};
    for(unsigned i=0;i<4;++i){reset("bad geometry");mock.reg[3]=configs[i];failure(GBCMT_BUSY,0);}
    reset("own IRQ already enabled");mock.reg[0xd00/4]=3;failure(GBCMT_BUSY,0);
    reset("IRQ enable unknown");mock.reg[0xd00/4]=UINT32_MAX;failure(GBCMT_BUSY,0);
    reset("initial pending foreign IRQ");mock.reg[0xd04/4]=4;failure(GBCMT_BUSY,0);
    for(unsigned t=0;t<8;++t)for(unsigned field=0;field<4;++field) {
        reset("every normal slot must be inert");mock.reg[(0xd00+t*0x2a0+0x10+4*field)/4]=field==2 ? 0:1;failure(GBCMT_BUSY,0);
    }
    for(unsigned i=2;i<=3;++i){reset("repeated snapshot changes");mock.change_snapshot=i;failure(GBCMT_BUSY,0);}
    reset("prewrite GIC changes");mock.gic_fail_call=2;failure(GBCMT_BUSY,0);
    reset("prewrite budget lost");mock.budget_fail_call=2;failure(GBCMT_BUSY,0);
    reset("latent IRQ after own enable");mock.latent_irq=1;mock.write_limit=1;failure(GBCMT_BUSY,1);CHECK(!mock.irq_clears && !mock.triggers,"never ACK latent IRQ");
    /* Every synchronous write must stop on its first uncertain readback.
     * Trigger and W1C are deliberately not synchronous writes or retried. */
    for(unsigned n=1;n<=31;++n)if(n!=25 && n!=30) {
        reset("single sync write readback fails");mock.fail_readback_write=n;mock.write_limit=n;failure(GBCMT_READBACK,n);
        CHECK(mock.delays==1000,"bounded readback attempts, one store only");
    }
    reset("ownership control changes before trigger");mock.bad_control=1;mock.write_limit=21;failure(GBCMT_BUSY,21);
    reset("ownership IRQ enable changes before trigger");mock.bad_irq_owner=1;mock.write_limit=21;failure(GBCMT_BUSY,21);
    reset("third GIC guard fails");mock.gic_fail_call=3;mock.write_limit=24;failure(GBCMT_BUSY,24);
    reset("final config changes");mock.final_config=1;mock.write_limit=24;failure(GBCMT_BUSY,24);
    reset("payload changes before trigger");mock.payload_reread=1;mock.write_limit=24;failure(GBCMT_BUSY,24);
    reset("stale statuses without new IRQ");mock.no_completion=1;mock.write_limit=25;failure(GBCMT_TIMEOUT,25);
    CHECK(!mock.command_status_reads && !mock.irq_clears && mock.triggers==1,"stale statuses cannot complete request; no fallback or ACK");
    reset("foreign completion IRQ");mock.foreign_completion=1;mock.write_limit=25;failure(GBCMT_BUSY,25);CHECK(!mock.irq_clears,"never ACK foreign completion");
    for(unsigned c=0;c<6;++c) {
        reset("missing ISSUED");mock.missing_issued=c+1;mock.write_limit=25;failure(GBCMT_COMPLETION,25);
        reset("unknown command status");mock.ones_status=c+1;mock.write_limit=25;failure(GBCMT_COMPLETION,25);
        if(c!=2){reset("missing wait COMPL");mock.missing_compl=c+1;mock.write_limit=25;failure(GBCMT_COMPLETION,25);}
    }
    for(unsigned idle=1;idle<=2;++idle){reset("completion not idle");mock.bad_idle=idle;mock.write_limit=25;failure(GBCMT_COMPLETION,25);}
    reset("completed control changed");mock.bad_control=2;mock.write_limit=25;failure(GBCMT_COMPLETION,25);
    reset("completed IRQ ownership changed");mock.bad_irq_owner=2;mock.write_limit=25;failure(GBCMT_COMPLETION,25);
    reset("completed payload changed");mock.payload_reread=2;mock.write_limit=25;failure(GBCMT_COMPLETION,25);
    reset("own IRQ never clears");mock.clear_stuck=1;mock.write_limit=30;failure(GBCMT_TIMEOUT,30);
    reset("foreign IRQ during cleanup");mock.clear_foreign=1;mock.write_limit=30;failure(GBCMT_BUSY,30);
    reset("IRQ ownership changed during cleanup");mock.cleanup_irq_change=1;mock.write_limit=30;failure(GBCMT_BUSY,30);
    reset("budget lost after trigger");mock.budget_fail_writes=25;mock.write_limit=25;failure(GBCMT_TIMEOUT,25);
    reset("budget lost in partial cleanup");mock.budget_fail_writes=27;mock.write_limit=27;failure(GBCMT_READBACK,27);
    reset("deadline expires after trigger");mock.deadline_write=25;mock.write_limit=25;failure(GBCMT_TIMEOUT,25);
    reset("deadline expires after payload store");mock.deadline_write=2;mock.write_limit=2;failure(GBCMT_READBACK,2);
    CHECK(cases==147,"all147 legacy BCM cases retained");
    arc_tests();
    printf("PASS: %u actual BCM + ARC transport cases; exact ACTIVE1 writes, native IRQ completion, terminal failures; no hardware qualification\n",cases);
    return 0;
}
