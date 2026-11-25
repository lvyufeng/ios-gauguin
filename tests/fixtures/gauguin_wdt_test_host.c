/* Actual watchdog worker/lease + GIC helper, with platform/MMIO/barrier seams only.
 * Host-only: IOSleep merely counts requests; no mapped hardware, sleeps or reset.
 * The tested store helper retains a mandatory DSB seam after every store. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "gauguin_wdt_lease.h"

#define GAUGUIN 1
#define KERN_SUCCESS 0
#define PAGE_SHIFT 14
#define VM_PROT_READ 1u
#define VM_PROT_WRITE 2u
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef uint32_t vm_prot_t;
typedef uint32_t ppnum_t;
typedef int boolean_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *,wait_result_t);
#define CHECK(cond,why) do { if (!(cond)) { \
    fprintf(stderr,"FAIL line %d [%s]: %s\n",__LINE__,case_name,why); exit(1); \
} } while (0)
#define FAKE_WDT UINT64_C(0x100000000)
#define FAKE_GIC UINT64_C(0x200000000)
#define MAX_LOG 100u
#define HOST_CPU_HZ UINT64_C(24000000)
static const char *case_name="setup";
static unsigned cases;
static vm_offset_t gicd_base;
static const char *const conflict_names[]={"sweetwdtpet","sweetreboot","sweetbusprobe",
    "sweetgpuprobe","sweetscmprobe","sweettouchmode","sweetpasprobe","sweetpasstage"};
static struct {
    int requested, bus_vote, conflict[8], thread_error, context, delayed_context, prewrite_context;
    bool bus_mode, budget_mode, quarantine_on_ready_log, quarantine_on_bus_arg, quarantine_during_budget;
    unsigned bus_wait_context, publication_context, readiness_failure, budget_reads, clock_conversions;
    uint32_t budget_count;
    int gpu_service,gpu_mode;
    bool refresh_mode,refresh_irq_bad;
    unsigned refresh_fault,refresh_pulses;
    unsigned refresh_delay_reads,refresh_pending_reads,refresh_ack_reads,refresh_delay_calls;
    uint32_t refresh_before_count;
    bool refresh_ack_polling,refresh_frozen_clock,refresh_oscillate,refresh_running_counter;
    unsigned refresh_delay_us,refresh_read_us,refresh_phase_us;
    uint64_t refresh_reset_ticks;
    uint64_t clock_ticks;
    unsigned starts,deallocations,terminations,sleeps,map_count,translations,pmap_calls,attr_calls;
    unsigned managed,attr,map_failure,translation_failure;
    unsigned gic_translations,gic_translation_failure,gic_reads;
    uint32_t gic_value[2];
    unsigned dmb_wdt,dmb_gic,dsb,pending_dmb,pending_dsb;
    unsigned reads,writes,en_reads,status_reads;
    uint32_t write_offset[4],write_value[4],regs[6];
    uint32_t initial_en,prewrite_en;
    unsigned threshold_failure,arming_failure,fail_sample,fail_sample_en,backward_sample;
    unsigned post_arm_sleeps,markers,flushes,lines;
    char log[MAX_LOG][224];
    thread_continue_t worker;
} mock;

static void idle_barriers(void)
{ CHECK(!mock.pending_dmb && !mock.pending_dsb,"previous MMIO access completed its barrier"); }
static void fake_dmb(void)
{
    CHECK(mock.pending_dmb && !mock.pending_dsb,"DMB immediately after a read");
    if(mock.pending_dmb==1) ++mock.dmb_wdt; else ++mock.dmb_gic;
    mock.pending_dmb=0;
}
static void fake_dsb(void)
{ CHECK(mock.pending_dsb && !mock.pending_dmb,"DSB immediately after a store"); ++mock.dsb; mock.pending_dsb=0; }
static uint32_t fake_gicd_read32(unsigned offset)
{
    idle_barriers(); CHECK(offset==0x104,"only GICD_ISENABLER1 read");
    if(mock.refresh_mode) {
        CHECK(gicd_base==FAKE_GIC,"known runtime GIC mapping");
        ++mock.gic_reads;mock.pending_dmb=2;return mock.refresh_irq_bad?1u:0u;
    }
    CHECK(gicd_base==FAKE_GIC && mock.gic_reads<2,"known GIC mapping, at most two guards");
    mock.pending_dmb=2; return mock.gic_value[mock.gic_reads++];
}
#define gicd_read32(offset) fake_gicd_read32(offset)
vm_offset_t ml_vtophys(vm_offset_t va)
{
    idle_barriers();
    if(va==FAKE_GIC || va==FAKE_GIC+0x104) {
        unsigned which=mock.gic_translations++%2;
        CHECK(va==FAKE_GIC+(which ? 0x104u:0u),"GIC base and exact register translations");
        return UINT64_C(0x17a00000)+(which ? 0x104u:0u)+
            (mock.gic_translation_failure==which+1 ? 1u:0u);
    }
    unsigned which=mock.translations++;
    CHECK(which<2 && va==FAKE_WDT+(which ? 0xfffu:0u),"WDT first and last byte translations only");
    return UINT64_C(0x17c10000)+(which ? 0xfffu:0u)+
        (mock.translation_failure==which+1 ? 1u:0u);
}
@IRQ_HELPER@

static uint32_t fake_wdt_read(unsigned offset)
{
    uint32_t value;
    idle_barriers(); CHECK(mock.map_count==1 && mock.translations==2,"translated WDT before reads");
    CHECK(offset==8 || offset==12 || offset==16 || offset==20,"WDT exact read whitelist, never RST");
    ++mock.reads;
    if(mock.refresh_mode&&mock.refresh_ack_polling) {
        if(offset==8) {
            mock.refresh_ack_polling=false; /* final full register verification */
            if(mock.refresh_fault==8)mock.clock_ticks+=HOST_CPU_HZ/100; /* final readbacks exceed2ms */
            if(mock.refresh_fault==9)mock.budget_count=9; /* counter reverses after equal10pair */
        }
        else {
            CHECK(offset==12,"post-pulse wait only reads STS");++mock.refresh_ack_reads;
            if(!mock.refresh_frozen_clock)mock.clock_ticks+=HOST_CPU_HZ*mock.refresh_read_us/1000000;
            if(mock.refresh_pending_reads)--mock.refresh_pending_reads;
            else if(mock.refresh_fault!=1) {
                if(mock.refresh_running_counter) {
                    if(!mock.refresh_reset_ticks)mock.refresh_reset_ticks=mock.clock_ticks-HOST_CPU_HZ*mock.refresh_phase_us/1000000;
                    mock.budget_count=10+(uint32_t)((mock.clock_ticks-mock.refresh_reset_ticks)*32765/HOST_CPU_HZ);
                } else mock.budget_count=mock.refresh_fault==5?32765u:10u;
                if(mock.refresh_oscillate&&(mock.refresh_ack_reads&1))mock.budget_count=mock.refresh_before_count;
            }
            mock.pending_dmb=1;return mock.budget_count<<1;
        }
    }
    if(mock.budget_mode) {
        static const unsigned offsets[]={8,16,20,12};
        CHECK(offset==offsets[mock.budget_reads%4],"budget reads EN/BARK/BITE/STS exactly once in order");
        ++mock.budget_reads;
        if(mock.quarantine_during_budget && offset==20) gauguin_wdt_lease_quarantine();
        value=offset==12 ? mock.budget_count<<1:mock.regs[offset/4];
        mock.pending_dmb=1; return value;
    }
    if(offset==8) {
        unsigned nth=mock.en_reads++;
        if(nth==0) value=mock.initial_en;
        else if(nth==1) value=mock.prewrite_en;
        else if(mock.arming_failure==1) value=1;
        else if(mock.fail_sample_en && mock.post_arm_sleeps==mock.fail_sample) value=0;
        else value=mock.regs[2];
    } else if(offset==12) {
        ++mock.status_reads;
        uint32_t counter=10+32765*mock.post_arm_sleeps;
        if(mock.fail_sample && !mock.fail_sample_en && mock.post_arm_sleeps==mock.fail_sample)
            counter=mock.backward_sample ? 0:10+32765*(mock.post_arm_sleeps-1);
        value=counter<<1;
    } else {
        value=mock.regs[offset/4];
        if(mock.writes==2 && mock.threshold_failure==(offset==16 ? 1u:2u)) value^=1;
        if(mock.writes==4 && mock.arming_failure==(offset==16 ? 2u:3u)) value^=1;
    }
    if(mock.bus_mode && mock.post_arm_sleeps) {
        if(mock.readiness_failure==1 && offset==8) value=0;
        if(mock.readiness_failure==2 && offset==16) value^=1;
        if(mock.readiness_failure==3 && offset==20) value^=1;
        if(mock.readiness_failure==4 && offset==12) value=20; /* unchanged armed count10 */
        if(mock.readiness_failure==5 && offset==12) value=753595u<<1;
    }
    mock.pending_dmb=1; return value;
}
static void fake_wdt_write(unsigned offset,uint32_t value)
{
    static const unsigned offsets[]={16,20,8,4};
    static const uint32_t values[]={655300,753595,3,1};
    idle_barriers(); CHECK(mock.map_count==1 && mock.translations==2,"translation before stores");
    if(mock.refresh_mode) {
        CHECK(offset==4&&value==1&&mock.regs[2]==3,"runtime can only pulse RST1 on an enabled watchdog");
        ++mock.refresh_pulses;++mock.writes;mock.pending_dsb=1;
        mock.refresh_before_count=mock.budget_count;mock.refresh_pending_reads=mock.refresh_delay_reads;
        mock.refresh_ack_polling=true;mock.refresh_ack_reads=0;mock.refresh_reset_ticks=0;
        if(mock.refresh_fault==2)mock.regs[2]=0;
        if(mock.refresh_fault==3)mock.regs[4]^=1;
        if(mock.refresh_fault==4)mock.regs[5]^=1;
        if(mock.refresh_fault==6)gauguin_wdt_lease_quarantine();
        if(mock.refresh_fault==7)mock.clock_ticks-=2*HOST_CPU_HZ;
        return;
    }
    CHECK(mock.gic_reads==2 && mock.dmb_gic==2 && (mock.gic_value[1]&3)==0,
        "both GIC guards completed before any WDT write");
    CHECK(mock.sleeps==(mock.bus_mode ? 0u:45u) && mock.en_reads==2,"initial+pre-write EN read disabled, correct mode delay");
    CHECK(!mock.initial_en && !mock.prewrite_en,"never arm initially enabled WDT");
    CHECK(mock.writes<4 && offset==offsets[mock.writes] && value==values[mock.writes],
        "only BARK655300 BITE753595 EN3 RST1, in order, once");
    mock.write_offset[mock.writes]=offset; mock.write_value[mock.writes]=value;
    ++mock.writes; mock.regs[offset/4]=value; mock.pending_dsb=1;
}
static int test_printf(const char *fmt,...)
{
    va_list ap; int n; idle_barriers(); CHECK(mock.lines<MAX_LOG,"bounded logs");
    va_start(ap,fmt); n=vsnprintf(mock.log[mock.lines],sizeof(mock.log[0]),fmt,ap); va_end(ap);
    CHECK(n>0 && (size_t)n<sizeof(mock.log[0]) && mock.log[mock.lines][n-1]=='\n',"bounded newline record");
    ++mock.lines; return n;
}
bool PE_parse_boot_argn(const char *key,void *value,size_t bytes)
{
    CHECK(bytes==sizeof(int),"integer boot arg");
    if(!strcmp(key,"sweetgpuservice")){*(int*)value=mock.gpu_service;return true;}
    if(!strcmp(key,"sweetgpuzap")){*(int*)value=mock.gpu_mode;return true;}
    if(!strcmp(key,"sweetwdttest")) { *(int*)value=mock.requested; return true; }
    if(!strcmp(key,"sweetbusvote")) {
        if(mock.quarantine_on_bus_arg) gauguin_wdt_lease_quarantine();
        *(int*)value=mock.bus_vote; return true;
    }
    for(unsigned i=0;i<8;++i) if(!strcmp(key,conflict_names[i])) { *(int*)value=mock.conflict[i]; return true; }
    CHECK(false,"known boot argument"); return false;
}
kern_return_t kernel_thread_start(thread_continue_t fn,void *arg,thread_t *thread)
{
    CHECK(!arg,"null worker argument"); ++mock.starts;
    if(mock.thread_error) return mock.thread_error;
    mock.worker=fn; *thread=(thread_t)(uintptr_t)1; return KERN_SUCCESS;
}
void thread_deallocate(thread_t thread)
{ CHECK(thread==(thread_t)(uintptr_t)1,"known worker"); ++mock.deallocations; }
void thread_terminate_self(void) { ++mock.terminations; }
int ml_get_interrupts_enabled(void) { return mock.context!=1; }
int ml_at_interrupt_context(void) { return mock.context==2; }
int get_preemption_level(void) { return mock.context==3 ? 1:0; }
unsigned long long mach_absolute_time(void) { return mock.clock_ticks; }
void IODelay(unsigned us)
{
    idle_barriers();CHECK(mock.refresh_mode&&mock.refresh_ack_polling&&us==10,"only bounded10us read-only acknowledgement delay");
    ++mock.refresh_delay_calls;
    if(!mock.refresh_frozen_clock)mock.clock_ticks+=HOST_CPU_HZ*(mock.refresh_delay_us?mock.refresh_delay_us:10)/1000000;
}
void absolutetime_to_nanoseconds(uint64_t ticks,uint64_t *out)
{
    CHECK(out && ticks <= UINT64_C(1000000000000),"bounded host clock conversion");
    ++mock.clock_conversions;
    *out=(ticks/HOST_CPU_HZ)*UINT64_C(1000000000)+
        (ticks%HOST_CPU_HZ)*UINT64_C(1000000000)/HOST_CPU_HZ;
}
void IOSleep(unsigned ms)
{
    idle_barriers(); CHECK(ms==1000 && mock.sleeps<75,"bounded requested one-second sleeps");
    mock.clock_ticks+=HOST_CPU_HZ;
    if(mock.bus_mode) {
        CHECK(mock.sleeps==0 && mock.writes==4 && mock.dsb==4,"bus arm requests exactly one wait after four writes");
        ++mock.sleeps; ++mock.post_arm_sleeps; mock.context=(int)mock.bus_wait_context;
        if(mock.readiness_failure==6) mock.clock_ticks+=22*HOST_CPU_HZ;
        return;
    }
    if(mock.sleeps<45) CHECK(!mock.map_count && !mock.reads && !mock.writes,"45s delay before WDT map/access");
    else { CHECK(mock.writes==4 && mock.dsb==4,"post-arm waits only after full write sequence"); ++mock.post_arm_sleeps; }
    if(++mock.sleeps==45) mock.context=mock.delayed_context;
}
void sweet_log_mark_sync(const char *s)
{
    CHECK(mock.context==0,"synchronous mark requires preemptible thread context");
    idle_barriers(); CHECK(!strncmp(s,"SWEET WDT TEST: ",16) || !strncmp(s,"SWEET WDT LEASE: ",17) || !strncmp(s,"SWEET WDT SERVICE: ",19),"marker namespace");
    CHECK(mock.lines && strlen(s)+1==strlen(mock.log[mock.lines-1]) &&
        !strncmp(s,mock.log[mock.lines-1],strlen(s)),"marker matches printed record");
    CHECK(mock.markers==mock.flushes,"previous marker flushed"); ++mock.markers;
}
void sweet_log_flush_now(void)
{
    CHECK(mock.context==0,"synchronous flush requires preemptible thread context");
    CHECK(mock.markers==mock.flushes+1,"one flush per marker"); ++mock.flushes;
    if(mock.prewrite_context && strstr(mock.log[mock.lines-1],"preparing native")) mock.context=mock.prewrite_context;
    if(strstr(mock.log[mock.lines-1],"readiness sample")) {
        if(mock.publication_context) mock.context=(int)mock.publication_context;
        if(mock.quarantine_on_ready_log) gauguin_wdt_lease_quarantine();
    }
}
boolean_t pmap_valid_page(ppnum_t pn)
{ CHECK(pn==(0x17c10000u>>14),"one WDT physical page"); ++mock.pmap_calls; return mock.managed; }
unsigned int pmap_cache_attributes(ppnum_t pn)
{ CHECK(pn==(0x17c10000u>>14),"one WDT cache attribute"); ++mock.attr_calls; return mock.attr; }
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t bytes,vm_prot_t prot)
{
    idle_barriers(); CHECK(pa==0x17c10000u && bytes==0x1000 && prot==3,"exact WDT map Device RW");
    CHECK(mock.sleeps==(mock.bus_mode ? 0u:45u) && mock.pmap_calls==1 && mock.attr_calls==1 && !mock.managed && (mock.attr&255)==7,
        "delay and pmap check before map");
    CHECK(mock.gic_reads==1 && mock.dmb_gic==1 && !(mock.gic_value[0]&3),"first quiet GIC guard before WDT map");
    CHECK(mock.markers==mock.flushes && mock.markers>0 && !mock.map_count,"map marker persisted, no retry");
    ++mock.map_count; return mock.map_failure ? 0:FAKE_WDT;
}
#define printf test_printf
@WORKER@
#undef printf

/* Actual SweetWatchdog start-function gate; legacy callout implementations
 * and the unrelated secure-diagnostic scheduler are platform seams here. */
typedef void *thread_call_t;
typedef void (*thread_call_func_t)(void *,void *);
static thread_call_t sweet_wdt_call,sweet_wdt_pet_call;
static struct { unsigned sampler_allocs,pet_allocs,schedules,diag,delayed,fail_pet; } gate;
#define NSEC_PER_SEC UINT64_C(1000000000)
static void sweet_wdt_sample(void *a,void *b) { (void)a; (void)b; CHECK(false,"old sampler never executes in fixture"); }
static void sweet_wdt_pet_sample(void *a,void *b) { (void)a; (void)b; CHECK(false,"old PET never executes in fixture"); }
static thread_call_t thread_call_allocate(thread_call_func_t fn,void *arg)
{
    CHECK(!arg,"null old callout argument");
    if(fn==sweet_wdt_sample) { ++gate.sampler_allocs; return (thread_call_t)(uintptr_t)1; }
    CHECK(fn==sweet_wdt_pet_sample,"known old callback"); ++gate.pet_allocs;
    return gate.fail_pet ? NULL:(thread_call_t)(uintptr_t)2;
}
static void sweet_wdt_schedule(void) { ++gate.schedules; }
static void sweet_secure_diag_start(void) { ++gate.diag; }
static void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out)
{ CHECK(n==1 && scale==NSEC_PER_SEC,"one-second old PET schedule"); *out=42; }
static void thread_call_enter_delayed(thread_call_t call,uint64_t deadline)
{ CHECK(call==(thread_call_t)(uintptr_t)2 && deadline==42,"old PET delayed call"); ++gate.delayed; }
#define IOLog test_printf
@LEGACY_GATE@
#undef IOLog

static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock)); memset(&gate,0,sizeof(gate)); sweet_wdt_call=NULL; sweet_wdt_pet_call=NULL; case_name=name; ++cases;
    mock.requested=1; mock.attr=0xd0000007u; gicd_base=FAKE_GIC; wdt_started=0; wdt_mapping=0;
    mock.clock_ticks=300*HOST_CPU_HZ;
    wdt_lease_state=WDL_IDLE; wdt_budget_busy=0; memset(&wdt_lease_record,0,sizeof(wdt_lease_record));
    wdt_lease_last_count=0; wdt_lease_last_at=0;
    wdt_refresh_sequence=0;
}
static unsigned count_line(const char *needle)
{ unsigned n=0; for(unsigned i=0;i<mock.lines;++i) if(strstr(mock.log[i],needle)) ++n; return n; }
static void has(const char *needle) { CHECK(count_line(needle)>0,needle); }
static void absent(const char *needle) { CHECK(!count_line(needle),needle); }
static void run_worker(void)
{
    sweet_wdt_test_init(); CHECK(mock.starts==1 && mock.worker && mock.deallocations==1,"thread scheduled exactly once");
    CHECK(!mock.sleeps && !mock.map_count && !mock.writes,"no inline execution");
    mock.worker(NULL,0); CHECK(mock.terminations==1,"worker terminates once"); idle_barriers();
    CHECK(mock.reads==mock.dmb_wdt && mock.gic_reads==mock.dmb_gic && mock.writes==mock.dsb,
        "every register access has its correct barrier");
    CHECK(mock.flushes==mock.markers,"all markers persisted");
}
static void no_writes(void) { CHECK(!mock.writes && !mock.dsb,"no writes or cleanup"); }
static void exactly_four_writes(void)
{ CHECK(mock.writes==4 && mock.dsb==4,"exact four writes with DSB, no retry or cleanup"); }
static void legacy_cases(void)
{
    uint32_t out;
    for(int pet=0;pet<=1;++pet) {
        reset("actual gate excludes old callouts"); mock.conflict[0]=pet;
        sweet_wdt_thread_start(); sweet_wdt_thread_start();
        CHECK(!gate.sampler_allocs && !gate.pet_allocs && !gate.schedules && !gate.delayed,
            "exact test flag prevents both legacy aliases before any allocation/scheduling");
        CHECK(gate.diag==2 && !mock.map_count && !mock.writes,"secure diagnostics retained; no watchdog access");
        has("legacy sampler/PET excluded before scheduling");
    }
    for(int requested=0;requested<=2;requested+=2) for(int pet=0;pet<=2;++pet) {
        reset("actual gate preserves default legacy start"); mock.requested=requested; mock.conflict[0]=pet;
        sweet_wdt_thread_start(); sweet_wdt_thread_start();
        CHECK(gate.sampler_allocs==1 && gate.schedules==1 && gate.diag==1,"old sampler starts once when test off");
        CHECK(gate.pet_allocs==(pet==1 ? 1u:0u) && gate.delayed==(pet==1 ? 1u:0u),"legacy PET remains exact1 opt-in");
    }
    reset("actual gate preserves PET allocation failure"); mock.requested=0; mock.conflict[0]=1; gate.fail_pet=1;
    sweet_wdt_thread_start(); CHECK(gate.pet_allocs==1 && !gate.delayed && gate.schedules==1,"failed PET allocation never scheduled"); has("PET: allocation failed");
    /* Execute the ACTUAL helper directly, independent of the worker. */
    reset("helper NULL output"); CHECK(!sweet_wdt_irq_quiet(NULL),"NULL output rejected"); CHECK(!mock.gic_reads && !mock.gic_translations,"no reads for NULL");
    reset("helper no initialized base"); gicd_base=0; out=0x11223344;
    CHECK(!sweet_wdt_irq_quiet(&out) && out==0x11223344,"missing base leaves output untouched"); CHECK(!mock.gic_reads && !mock.gic_translations,"no translate/read without base");
    for(unsigned i=1;i<=2;++i) {
        reset("helper wrong physical translation"); mock.gic_translation_failure=i; out=0x11223344;
        CHECK(!sweet_wdt_irq_quiet(&out) && out==0x11223344,"translation failure preserves output");
        CHECK(mock.gic_translations==i && !mock.gic_reads && !mock.dmb_gic,"no register read after wrong physical");
    }
    const uint32_t irq_values[]={0,1,2,3,4,0xfffffffcu,UINT32_MAX};
    for(unsigned i=0;i<sizeof(irq_values)/sizeof(irq_values[0]);++i) {
        reset("helper quiet bit mask"); mock.gic_value[0]=irq_values[i]; out=0x11223344;
        CHECK(sweet_wdt_irq_quiet(&out)==((irq_values[i]&3)==0) && out==irq_values[i],"actual helper exposes NS value and checks bits0/1 only");
        CHECK(mock.gic_translations==2 && mock.gic_reads==1 && mock.dmb_gic==1,"helper one read with DMB");
    }
    const int disabled[]={0,2,-1,9};
    for(unsigned i=0;i<sizeof(disabled)/sizeof(disabled[0]);++i) {
        reset("exact default off"); mock.requested=disabled[i]; CHECK(!sweet_wdt_test_requested(),"only exact1 enables");
        sweet_wdt_test_init(); sweet_wdt_test_init(); CHECK(!mock.starts && !mock.lines && !mock.map_count,"off no effects");
    }
    reset("thread creation failure"); mock.thread_error=5; sweet_wdt_test_init(); sweet_wdt_test_init();
    CHECK(mock.starts==1 && !mock.worker && !mock.sleeps && !mock.map_count,"one failed attempt, no inline fallback"); has("thread creation failed=5");
    for(int bad=1;bad<=3;++bad) {
        reset("bad early context"); mock.context=bad; run_worker(); CHECK(!mock.sleeps && !mock.map_count,"early context stops"); no_writes();
        reset("bad context after delay"); mock.delayed_context=bad; run_worker(); CHECK(mock.sleeps==45 && !mock.map_count,"late context stops"); no_writes();
        reset("context changes before write"); mock.prewrite_context=bad; run_worker(); CHECK(mock.gic_reads==1,"context short-circuits second guard"); no_writes();
    }
    for(unsigned i=0;i<8;++i) for(int sign=-1;sign<=1;sign+=2) {
        reset("conflicting diagnostic or writer"); mock.conflict[i]=sign; run_worker();
        CHECK(!mock.sleeps && !mock.map_count && !mock.gic_reads,"conflict rejected before delay/map"); no_writes(); has("conflict ");
    }
    reset("managed watchdog page"); mock.managed=1; run_worker(); CHECK(mock.sleeps==45 && !mock.map_count && !mock.gic_reads,"managed stops before GIC/map"); no_writes();
    reset("wrong watchdog cache type"); mock.attr=6; run_worker(); CHECK(!mock.map_count && !mock.gic_reads,"wrong attr stops before GIC/map"); no_writes();
    reset("missing GIC base in worker"); gicd_base=0; run_worker(); CHECK(!mock.map_count && !mock.gic_reads,"missing helper base stops mapping"); no_writes();
    for(unsigned i=1;i<=3;++i) {
        reset("first NS IRQ guard fails"); mock.gic_value[0]=i; run_worker(); CHECK(mock.gic_reads==1 && !mock.map_count,"first IRQ guard before map"); no_writes();
        reset("NS IRQ changes before write"); mock.gic_value[1]=i; run_worker(); CHECK(mock.gic_reads==2 && mock.map_count==1,"second guard checked"); no_writes();
    }
    reset("map failure"); mock.map_failure=1; run_worker(); CHECK(mock.map_count==1 && !mock.translations && !mock.reads,"map failure no access"); no_writes();
    for(unsigned i=1;i<=2;++i) {
        reset("WDT translation failure"); mock.translation_failure=i; run_worker(); CHECK(mock.translations==i && !mock.reads,"first/last-byte failure before register access"); no_writes();
    }
    const uint32_t enabled_values[]={1,2,3,UINT32_MAX};
    for(unsigned i=0;i<sizeof(enabled_values)/sizeof(enabled_values[0]);++i) {
        reset("initial EN nonzero"); mock.initial_en=enabled_values[i]; run_worker(); CHECK(mock.reads==4 && mock.gic_reads==1,"initial state observed then stops"); no_writes();
        reset("EN changes before write"); mock.prewrite_en=enabled_values[i]; run_worker(); CHECK(mock.en_reads==2 && mock.gic_reads==2,"rechecks EN immediately before writing"); no_writes();
    }
    for(unsigned i=1;i<=2;++i) {
        reset("threshold readback mismatch"); mock.threshold_failure=i; run_worker();
        CHECK(mock.writes==2 && mock.dsb==2 && mock.sleeps==45,"threshold failure never writes EN/RST or waits");
        CHECK(mock.regs[2]==0 && mock.regs[1]==0,"disabled with no reset pulse"); has("threshold readback mismatch"); absent("armed readback");
    }
    for(unsigned i=1;i<=3;++i) {
        reset("arming readback mismatch"); mock.arming_failure=i; run_worker(); exactly_four_writes();
        CHECK(mock.sleeps==45,"arming failure stops sampling"); has("arming readback failed; no retry/cleanup/pet"); absent("sample=");
        sweet_wdt_test_init(); CHECK(mock.starts==1,"arming failure cannot restart this boot"); exactly_four_writes();
    }
    for(unsigned i=1;i<=5;++i) {
        reset("counter stops increasing"); mock.fail_sample=i; run_worker(); exactly_four_writes();
        CHECK(mock.post_arm_sleeps==i && count_line("sample=")==i,"strict monotonic failure stops at first invalid sample");
        has("no monotonic enabled counter"); absent("counter advancing,");
        reset("sample EN disabled"); mock.fail_sample=i; mock.fail_sample_en=1; run_worker(); exactly_four_writes();
        CHECK(mock.post_arm_sleeps==i && count_line("sample=")==i,"EN must remain3 for every sample"); has("no monotonic enabled counter");
    }
    reset("counter goes backwards"); mock.fail_sample=3; mock.backward_sample=1; run_worker(); exactly_four_writes(); CHECK(mock.post_arm_sleeps==3,"backwards count rejected");
    reset("five increasing samples, no reset"); mock.gic_value[0]=mock.gic_value[1]=0xfffffffcu;
    run_worker(); exactly_four_writes(); CHECK(mock.sleeps==75 && mock.post_arm_sleeps==30,"45s preparation plus30s requested wait, not real sleeping");
    CHECK(count_line("sample=")==5 && mock.status_reads==7 && mock.en_reads==8,"five enabled monotonic samples plus initial/armed observations");
    has("counter advancing, no pets; awaiting actual reset (readback is not reset proof)");
    has("survived 30 requested seconds after arm; automatic reset NOT qualified; no retry");
    sweet_wdt_test_init(); CHECK(mock.starts==1,"atomic one start after full experiment"); exactly_four_writes();
    CHECK(cases==87,"all 87 original diagnostic/helper/start-gate cases retained");
    printf("PASS: retained %u original WDT worker/helper cases\n",cases);
}

struct effects {
    unsigned reads,writes,gic_reads,map_count,sleeps,lines,markers,flushes;
    unsigned translations,gic_translations,pmap_calls,attr_calls,starts;
};
static struct effects effects_now(void)
{
    return (struct effects){mock.reads,mock.writes,mock.gic_reads,mock.map_count,
        mock.sleeps,mock.lines,mock.markers,mock.flushes,mock.translations,
        mock.gic_translations,mock.pmap_calls,mock.attr_calls,mock.starts};
}
static void effects_equal(struct effects a,const char *why)
{
    struct effects b=effects_now();
    CHECK(a.reads==b.reads && a.writes==b.writes && a.gic_reads==b.gic_reads &&
        a.map_count==b.map_count && a.sleeps==b.sleeps && a.lines==b.lines &&
        a.markers==b.markers && a.flushes==b.flushes && a.translations==b.translations &&
        a.gic_translations==b.gic_translations && a.pmap_calls==b.pmap_calls &&
        a.attr_calls==b.attr_calls && a.starts==b.starts,why);
}
static void reset_bus(const char *name)
{
    reset(name); mock.requested=0; mock.bus_vote=1; mock.bus_mode=true;
}
static void lease_failed_unchanged(void)
{
    struct gauguin_wdt_lease_record out,before;
    memset(&out,0xa5,sizeof(out)); before=out;
    CHECK(!gauguin_wdt_lease_arm(&out),"bus arm rejected");
    CHECK(!memcmp(&out,&before,sizeof(out)),"failed arm leaves entire output unchanged");
    idle_barriers();
    CHECK(wdt_lease_state==WDL_QUARANTINED && wdt_started==1,"started arm failure quarantines and consumes shared attempt");
}
static void permanently_refused(void)
{
    struct effects effects=effects_now();
    struct gauguin_wdt_lease_record out,before;
    memset(&out,0xa5,sizeof(out)); before=out;
    CHECK(wdt_lease_state==WDL_QUARANTINED && wdt_started==1,"terminal quarantine");
    CHECK(!gauguin_wdt_lease_check_budget(1),"quarantine denies budget before hardware access");
    CHECK(!gauguin_wdt_lease_arm(&out) && !memcmp(&out,&before,sizeof(out)),"quarantine denies another arm with unchanged output");
    int prior=mock.requested; mock.requested=1; sweet_wdt_test_init(); mock.requested=prior;
    effects_equal(effects,"quarantine cannot retry test/arm/budget, log or touch hardware");
}
static struct gauguin_wdt_lease_record lease_ready(void)
{
    struct gauguin_wdt_lease_record out;
    memset(&out,0xa5,sizeof(out));
    CHECK(gauguin_wdt_lease_arm(&out),"valid bus lease arms");
    exactly_four_writes(); idle_barriers();
    CHECK(mock.sleeps==1 && mock.post_arm_sleeps==1 && !mock.starts && !mock.worker,
        "explicit arm only, exactly one readiness sleep, no scheduled test worker");
    CHECK(out.armed_at_ticks==300*HOST_CPU_HZ && out.ready_at_ticks==301*HOST_CPU_HZ &&
        out.ready_count==32775 && out.bark_ticks==655300 && out.bite_ticks==753595 &&
        out.clock_hz==32765,"integer-only metadata with independent CPU/WDT units");
    CHECK(wdt_lease_state==WDL_READY && wdt_started==1,"READY after successful preparation");
    CHECK(mock.reads==mock.dmb_wdt && mock.writes==mock.dsb && mock.gic_reads==mock.dmb_gic,
        "all arm accesses retain barriers");
    CHECK(mock.flushes==mock.markers && mock.clock_conversions==1,"ready evidence persisted and CPU window checked");
    mock.budget_mode=true; mock.budget_count=out.ready_count;
    return out;
}
static void budget_success(uint32_t minimum)
{
    struct effects before=effects_now(); unsigned conversions=mock.clock_conversions;
    CHECK(gauguin_wdt_lease_check_budget(minimum),"budget accepted"); idle_barriers();
    CHECK(mock.reads==before.reads+4 && mock.budget_reads%4==0 && mock.reads==mock.dmb_wdt,
        "successful budget performs exactly four ordered read-only accesses");
    CHECK(mock.writes==before.writes && mock.gic_reads==before.gic_reads &&
        mock.map_count==before.map_count && mock.sleeps==before.sleeps &&
        mock.lines==before.lines && mock.markers==before.markers && mock.flushes==before.flushes,
        "successful budget has no write/sleep/log/remap");
    CHECK(mock.clock_conversions==conversions+1 && wdt_lease_state==WDL_READY,"CPU window also checked");
}
static void budget_fails(uint32_t minimum,bool reads)
{
    unsigned before=mock.reads,writes=mock.writes,sleeps=mock.sleeps;
    CHECK(!gauguin_wdt_lease_check_budget(minimum),"budget rejected"); idle_barriers();
    CHECK(mock.reads==before+(reads ? 4u:0u),"rejected budget expected read boundary");
    CHECK(mock.writes==writes && mock.sleeps==sleeps,"budget failure never pets/disables/sleeps");
    permanently_refused();
}
static void lease_cases(void)
{
    /* The actual C++ startup function calls the same exclusive flag policy. */
    const int test_flags[]={0,1,2,-1};
    for(unsigned i=0;i<sizeof(test_flags)/sizeof(test_flags[0]);++i) for(int pet=0;pet<=1;++pet) {
        reset_bus("bus mode excludes old callouts despite conflicting flags"); mock.requested=test_flags[i]; mock.conflict[0]=pet;
        sweet_wdt_thread_start(); sweet_wdt_thread_start();
        CHECK(!gate.sampler_allocs && !gate.pet_allocs && !gate.schedules && !gate.delayed && gate.diag==2,
            "busvote1 suppresses sampler/PET before allocation; preserves secure diagnostics");
        CHECK(!mock.map_count && !mock.writes,"gate itself does not arm");
    }
    const int off[]={0,2,-1,9};
    for(unsigned i=0;i<sizeof(off)/sizeof(off[0]);++i) {
        reset_bus("bus mode exact-one flag gate"); mock.bus_vote=off[i];
        struct gauguin_wdt_lease_record out,before; memset(&out,0xa5,sizeof(out)); before=out;
        struct effects effects=effects_now();
        CHECK(!gauguin_wdt_lease_arm(&out) && !memcmp(&out,&before,sizeof(out)),"inactive bus arm leaves output");
        CHECK(wdt_started==0 && wdt_lease_state==WDL_IDLE,"inactive mode does not consume attempt");
        CHECK(!gauguin_wdt_lease_check_budget(0),"IDLE has no budget even for invalid minimum");
        effects_equal(effects,"off mode has no hardware/log/sleep effects");
        sweet_wdt_thread_start();
        CHECK(gate.sampler_allocs==1 && gate.schedules==1,"non-one bus flags preserve default legacy sampler");
    }
    reset_bus("NULL arm result does not consume attempt");
    CHECK(!gauguin_wdt_lease_arm(NULL) && !wdt_started && wdt_lease_state==WDL_IDLE,"NULL output inert");
    CHECK(!mock.map_count && !mock.lines && !mock.sleeps,"NULL arm no effects");
    (void)lease_ready(); /* a subsequent valid call is still the first real attempt */
    reset("diagnostic mode conflicts with requested bus vote"); mock.bus_vote=1; run_worker();
    no_writes(); CHECK(!mock.sleeps && !mock.map_count,"diagnostic rejects dual mode before access"); has("conflict sweetbusvote=1");
    reset("diagnostic creation consumes shared attempt"); sweet_wdt_test_init();
    CHECK(mock.starts==1 && mock.worker && wdt_started==1,"test owns shared attempt");
    mock.requested=0; mock.bus_vote=1; mock.bus_mode=true;
    struct gauguin_wdt_lease_record out,before; memset(&out,0xa5,sizeof(out)); before=out;
    struct effects effects=effects_now();
    CHECK(!gauguin_wdt_lease_arm(&out) && !memcmp(&out,&before,sizeof(out)),"bus cannot arm after diagnostic reserved attempt");
    CHECK(!gauguin_wdt_lease_check_budget(1),"diagnostic does not publish lease READY");
    effects_equal(effects,"shared attempt rejection has no additional effects");

    for(int bad=1;bad<=3;++bad) {
        reset_bus("invalid bus arm context"); mock.context=bad; lease_failed_unchanged();
        CHECK(!mock.map_count && !mock.markers && !mock.flushes,"invalid entry context never persists or maps"); permanently_refused();
        reset_bus("bus context changes before stores"); mock.prewrite_context=bad; lease_failed_unchanged();
        no_writes(); CHECK(mock.map_count==1 && mock.gic_reads==1,"pre-store context refusal"); permanently_refused();
        reset_bus("invalid context after bus readiness sleep"); mock.bus_wait_context=(unsigned)bad; lease_failed_unchanged();
        exactly_four_writes(); CHECK(mock.sleeps==1,"only readiness wait occurred"); permanently_refused();
        reset_bus("invalid context while publishing readiness"); mock.publication_context=(unsigned)bad; lease_failed_unchanged();
        exactly_four_writes(); permanently_refused();
    }
    for(unsigned i=0;i<6;++i) for(int sign=-1;sign<=1;sign+=2) {
        reset_bus("bus rejects conflicting active diagnostic or writer"); mock.conflict[i]=sign;
        lease_failed_unchanged(); CHECK(!mock.sleeps && !mock.map_count && !mock.gic_reads,"conflicting flags stop before hardware"); no_writes(); permanently_refused();
    }
    for(int sign=-1;sign<=1;sign+=2) {
        reset_bus("bus rejects nonzero isolated-test flag"); mock.requested=sign;
        lease_failed_unchanged(); CHECK(!mock.map_count && !mock.sleeps,"test conflict stops before hardware"); permanently_refused();
    }
    for(unsigned i=6;i<8;++i) for(int bad=-1;bad<=2;bad+=3) {
        reset_bus("bus rejects invalid CPU-only preparation flag"); mock.conflict[i]=bad;
        lease_failed_unchanged(); CHECK(!mock.map_count && !mock.sleeps,"invalid CPU flag stops"); permanently_refused();
    }
    for(int probe=0;probe<=1;++probe) for(int stage=0;stage<=1;++stage) {
        reset_bus("CPU-only PAS flags are allowed without claiming PAS preparation"); mock.conflict[6]=probe; mock.conflict[7]=stage;
        (void)lease_ready(); budget_success(32765);
    }
    reset_bus("managed bus watchdog page"); mock.managed=1; lease_failed_unchanged(); no_writes(); permanently_refused();
    reset_bus("wrong bus watchdog cache attribute"); mock.attr=6; lease_failed_unchanged(); no_writes(); permanently_refused();
    reset_bus("bus has no GIC initialization"); gicd_base=0; lease_failed_unchanged(); no_writes(); permanently_refused();
    for(unsigned i=1;i<=2;++i) {
        reset_bus("bus bad GIC translation"); mock.gic_translation_failure=i; lease_failed_unchanged(); no_writes(); permanently_refused();
        reset_bus("bus bad WDT translation"); mock.translation_failure=i; lease_failed_unchanged(); no_writes(); permanently_refused();
        reset_bus("bus invalid threshold readback"); mock.threshold_failure=i; lease_failed_unchanged();
        CHECK(mock.writes==2 && mock.dsb==2 && !mock.sleeps && !mock.regs[2] && !mock.regs[1],"no EN/RST after threshold failure"); permanently_refused();
    }
    for(unsigned i=1;i<=3;++i) {
        reset_bus("bus first GIC guard fails"); mock.gic_value[0]=i; lease_failed_unchanged(); no_writes(); permanently_refused();
        reset_bus("bus final GIC guard fails"); mock.gic_value[1]=i; lease_failed_unchanged(); no_writes(); permanently_refused();
        reset_bus("bus arming readback mismatch"); mock.arming_failure=i; lease_failed_unchanged(); exactly_four_writes();
        CHECK(!mock.sleeps,"arming failure no readiness wait"); permanently_refused();
    }
    reset_bus("bus mapping failure"); mock.map_failure=1; lease_failed_unchanged(); no_writes(); permanently_refused();
    reset_bus("bus initially enabled watchdog"); mock.initial_en=3; lease_failed_unchanged(); no_writes(); permanently_refused();
    reset_bus("bus EN changes before write"); mock.prewrite_en=1; lease_failed_unchanged(); no_writes(); permanently_refused();
    for(unsigned i=1;i<=6;++i) {
        reset_bus("bus readiness check fails"); mock.readiness_failure=i; lease_failed_unchanged();
        exactly_four_writes(); CHECK(mock.sleeps==1,"readiness failure exactly one requested wait"); permanently_refused();
    }
    reset_bus("quarantine during READY log cannot be overwritten by publication"); mock.quarantine_on_ready_log=true;
    lease_failed_unchanged(); exactly_four_writes(); permanently_refused();

    reset_bus("valid lease and repeated rapid budgets"); struct gauguin_wdt_lease_record ready=lease_ready();
    effects=effects_now(); memset(&out,0xa5,sizeof(out)); before=out;
    CHECK(!gauguin_wdt_lease_arm(&out) && !memcmp(&out,&before,sizeof(out)),"second arm denied without destroying existing READY");
    effects_equal(effects,"second arm never re-arms or logs");
    mock.requested=1; sweet_wdt_test_init(); mock.requested=0; CHECK(!mock.starts,"lease shared attempt excludes isolated-test creation");
    budget_success(32765); budget_success(32765); /* same counter and time is legal */
    mock.clock_ticks+=HOST_CPU_HZ/1000; budget_success(32765); /* count may not tick between immediate calls */
    mock.budget_count+=40; mock.clock_ticks+=HOST_CPU_HZ/1000; budget_success(32765);
    CHECK(wdt_lease_last_count==mock.budget_count && wdt_lease_last_at==mock.clock_ticks,"successful checks update monotonic observation");
    (void)ready;
    const uint32_t invalid_min[]={0,753595,753596,UINT32_MAX};
    for(unsigned i=0;i<sizeof(invalid_min)/sizeof(invalid_min[0]);++i) {
        reset_bus("invalid budget minimum"); (void)lease_ready(); budget_fails(invalid_min[i],false);
    }
    reset_bus("exact counter remaining boundary accepted"); ready=lease_ready(); budget_success(753595-ready.ready_count);
    reset_bus("one tick beyond remaining refused"); ready=lease_ready(); budget_fails(753595-ready.ready_count+1,true);
    for(unsigned i=0;i<3;++i) {
        reset_bus("changed EN or threshold quarantines READY"); (void)lease_ready();
        if(i==0) mock.regs[2]=0; else mock.regs[i==1 ? 4:5]^=1;
        budget_fails(32765,true);
    }
    reset_bus("counter moved backwards"); ready=lease_ready(); mock.budget_count=ready.ready_count-1; budget_fails(1,true);
    reset_bus("counter reached bite threshold"); (void)lease_ready(); mock.budget_count=753595; budget_fails(1,true);
    reset_bus("20-bit counter wrapped"); (void)lease_ready(); mock.budget_count=0; budget_fails(1,true);
    reset_bus("CPU clock moved backwards"); ready=lease_ready(); mock.clock_ticks=ready.ready_at_ticks-1; budget_fails(1,true);
    reset_bus("CPU window exact remaining boundary"); ready=lease_ready();
    mock.clock_ticks=ready.armed_at_ticks+22*HOST_CPU_HZ; budget_success(32765);
    budget_fails(32766,true);
    reset_bus("frozen counter cannot outlive CPU 23-second window"); ready=lease_ready();
    mock.clock_ticks=ready.armed_at_ticks+23*HOST_CPU_HZ; budget_fails(1,true);
    reset_bus("very delayed caller cannot recover expired window"); ready=lease_ready();
    mock.clock_ticks=ready.armed_at_ticks+30*HOST_CPU_HZ; budget_fails(1,true);
    for(int bad=1;bad<=3;++bad) {
        reset_bus("budget invalid context"); (void)lease_ready(); mock.context=bad;
        unsigned marks=mock.markers,flushes=mock.flushes;
        budget_fails(32765,false); CHECK(mock.markers==marks && mock.flushes==flushes,"invalid budget context never persists UFS");
    }
    reset_bus("mode no longer enabled in budget seam"); (void)lease_ready(); mock.bus_vote=0; budget_fails(1,false);
    reset_bus("concurrent budget check rejected without spin"); (void)lease_ready(); wdt_budget_busy=1;
    budget_fails(1,false); CHECK(wdt_budget_busy==1,"failed contender does not release another check's guard");
    reset_bus("quarantine between READY load and guard acquisition"); (void)lease_ready(); mock.quarantine_on_bus_arg=true;
    budget_fails(1,false); CHECK(wdt_budget_busy==0,"acquired guard released after racing quarantine");
    reset_bus("quarantine during a budget read remains terminal"); (void)lease_ready(); mock.quarantine_during_budget=true;
    budget_fails(1,true); CHECK(wdt_budget_busy==0,"in-flight reader releases guard but never republishes READY");
    reset_bus("explicit pre-arm quarantine has zero hardware effects"); effects=effects_now(); gauguin_wdt_lease_quarantine();
    effects_equal(effects,"software-only quarantine has no reads/writes/log/sleep"); permanently_refused();
    reset_bus("explicit post-arm quarantine has zero hardware effects"); (void)lease_ready(); effects=effects_now(); gauguin_wdt_lease_quarantine();
    effects_equal(effects,"quarantine never pets/disables/remaps/reads"); permanently_refused();
}
static void refresh_ready(const char *name)
{
    reset_bus(name);(void)lease_ready();mock.gpu_service=1;mock.gpu_mode=12;mock.refresh_mode=true;
    mock.refresh_delay_reads=3; /* real177: immediate post-RST still showed old count */
    mock.clock_ticks+=HOST_CPU_HZ;mock.budget_count+=32765;
}
static void refresh_failure(unsigned expected_pulses)
{
    struct gauguin_wdt_refresh_record out,before;memset(&out,0xa5,sizeof(out));before=out;
    uint64_t epoch=wdt_lease_record.armed_at_ticks;unsigned writes=mock.writes;
    CHECK(!gauguin_wdt_lease_refresh(&out)&&!memcmp(&out,&before,sizeof(out)),"failed refresh leaves output untouched");
    CHECK(mock.refresh_pulses==expected_pulses&&mock.writes==writes+expected_pulses,"exact failed refresh pulse boundary, no enable/disable/retry");
    CHECK(wdt_lease_state==WDL_QUARANTINED&&wdt_lease_record.armed_at_ticks==epoch,"failure cannot move CPU epoch or restore READY");
    writes=mock.writes;
    CHECK(!gauguin_wdt_lease_refresh(&out)&&mock.writes==writes,"quarantine cannot refresh again");
    permanently_refused();idle_barriers();
}
static void service_cases(void)
{
    unsigned first=cases;
    const int off[]={0,2,-1};
    struct gauguin_wdt_refresh_record out,before;
    for(unsigned i=0;i<sizeof(off)/sizeof(off[0]);i++) {
        refresh_ready("service exact flag");mock.gpu_service=off[i];struct effects e=effects_now();
        memset(&out,0xa5,sizeof(out));before=out;
        CHECK(!gauguin_wdt_lease_refresh(&out)&&!memcmp(&out,&before,sizeof(out)),"service off leaves output");
        effects_equal(e,"no service no pulse/read/log");CHECK(wdt_lease_state==WDL_READY,"legacy lease remains usable");
        refresh_ready("service exact mode12");mock.gpu_mode=off[i];e=effects_now();
        CHECK(!gauguin_wdt_lease_refresh(&out),"service requires dynamic mode12");effects_equal(e,"wrong mode inert");
    }
    refresh_ready("NULL refresh output");struct effects e=effects_now();CHECK(!gauguin_wdt_lease_refresh(NULL),"NULL refresh inert");effects_equal(e,"NULL output no effects");
    for(unsigned state=WDL_IDLE;state<=WDL_QUARANTINED;state++)if(state!=WDL_READY) {
        refresh_ready("not READY cannot refresh");wdt_lease_state=state;e=effects_now();
        CHECK(!gauguin_wdt_lease_refresh(&out),"READY required");effects_equal(e,"non-ready no hardware");
    }
    refresh_ready("600 healthy renewals beyond original 23-second epoch");
    for(unsigned i=1;i<=600;i++) {
        uint32_t count=mock.budget_count;uint64_t now=mock.clock_ticks;
        CHECK(gauguin_wdt_lease_refresh(&out),"healthy owner refreshes");
        CHECK(out.sequence==i&&out.before_count==count&&out.after_count==10&&out.refreshed_at_ticks==now,"exact refresh receipt");
        CHECK(mock.refresh_pulses==i&&mock.writes==4+i&&mock.dsb==mock.writes,"one RST1 per refresh, every store DSB");
        CHECK(wdt_lease_record.armed_at_ticks==now&&wdt_lease_record.ready_count==10&&wdt_lease_state==WDL_READY,"verified new CPU/counter epoch");
        CHECK(mock.sleeps==1&&mock.map_count==1&&mock.regs[2]==3&&mock.regs[4]==655300&&mock.regs[5]==753595,"no sleep/remap/threshold/enable changes");
        budget_success(32765);
        mock.clock_ticks+=HOST_CPU_HZ;mock.budget_count+=32765;
    }
    for(int bad=1;bad<=3;bad++){refresh_ready("refresh wrong context");mock.context=bad;refresh_failure(0);}
    refresh_ready("lost exclusive owner");mock.bus_vote=0;refresh_failure(0);
    refresh_ready("runtime NS IRQ conflict");mock.refresh_irq_bad=true;refresh_failure(0);
    refresh_ready("concurrent lease operation");wdt_budget_busy=1;refresh_failure(0);CHECK(wdt_budget_busy==1,"contender cannot release another guard");
    refresh_ready("refresh sequence cannot wrap");wdt_refresh_sequence=UINT32_MAX;refresh_failure(0);
    for(unsigned n=0;n<3;n++) {
        refresh_ready("pre-pulse enable/threshold corruption");mock.regs[n==0?2:n==1?4:5]^=1;refresh_failure(0);
    }
    refresh_ready("counter moved backwards");mock.budget_count=wdt_lease_last_count-1;refresh_failure(0);
    refresh_ready("counter stuck since epoch");mock.budget_count=wdt_lease_record.ready_count;refresh_failure(0);
    refresh_ready("counter progressing too slowly");mock.budget_count=wdt_lease_record.ready_count+1;refresh_failure(0);
    refresh_ready("counter progressing implausibly quickly");mock.budget_count+=200000;refresh_failure(0);
    refresh_ready("counter too close to bite");mock.budget_count=753595-3*32765+1;refresh_failure(0);
    refresh_ready("counter cannot wrap");mock.budget_count=0;refresh_failure(0);
    refresh_ready("CPU moved backwards");mock.clock_ticks=wdt_lease_record.ready_at_ticks-1;refresh_failure(0);
    refresh_ready("expired CPU epoch cannot be revived");mock.clock_ticks=wdt_lease_record.armed_at_ticks+23*HOST_CPU_HZ;refresh_failure(0);
    refresh_ready("refresh too early to prove advancement");mock.clock_ticks=wdt_lease_record.ready_at_ticks+HOST_CPU_HZ/100;mock.budget_count=wdt_lease_record.ready_count+327;refresh_failure(0);
    refresh_ready("quarantine during pre-pulse reads");mock.quarantine_during_budget=true;refresh_failure(0);
    for(unsigned fault=1;fault<=7;fault++) {
        refresh_ready("post-pulse counter/enable/threshold/context/quarantine failure");mock.refresh_fault=fault;refresh_failure(1);
    }
    const unsigned delays[]={0,1,3,32,128};
    for(unsigned i=0;i<sizeof(delays)/sizeof(delays[0]);i++) {
        refresh_ready("asynchronous counter reset acknowledged without another pulse");mock.refresh_delay_reads=delays[i];
        CHECK(gauguin_wdt_lease_refresh(&out)&&mock.refresh_pulses==1,"delayed acknowledgement succeeds with exactly ONE RST1");
        CHECK(mock.refresh_ack_reads>=delays[i]+2&&mock.refresh_delay_calls>=delays[i],"two stable decreased reads after delayed hardware delivery");
        CHECK(out.after_count==10&&wdt_lease_state==WDL_READY,"publish epoch only after acknowledgement");
    }
    refresh_ready("acknowledgement past2ms refuses without pulse replay");mock.refresh_delay_reads=250;refresh_failure(1);
    CHECK(mock.refresh_delay_calls<=200,"independent2ms CPU bound");
    refresh_ready("stalled CPU clock cannot make acknowledgement unbounded");mock.refresh_fault=1;mock.refresh_frozen_clock=true;refresh_failure(1);
    CHECK(mock.refresh_delay_calls<=256&&mock.refresh_ack_reads<=256,"independent256-sample bound with stuck clock");
    refresh_ready("one transient low sample cannot acknowledge");mock.refresh_oscillate=true;refresh_failure(1);
    refresh_ready("179 running counter advances across delayed samples");
    mock.refresh_running_counter=true;mock.refresh_read_us=2;mock.refresh_delay_us=48;
    CHECK(gauguin_wdt_lease_refresh(&out)&&mock.refresh_pulses==1,"running counter confirms an adjacent pair without another reset pulse");
    CHECK(mock.refresh_ack_reads==mock.refresh_delay_reads+2&&mock.refresh_delay_calls==mock.refresh_delay_reads,"no delay between equal confirmation reads");
    const unsigned read_us[]={0,2,10,20},delay_us[]={31,48,100,500},phase_us[]={0,15,29};
    for(unsigned r=0;r<4;r++)for(unsigned d=0;d<4;d++)for(unsigned p=0;p<3;p++) {
        refresh_ready("counter continues ticking; adjacent pair can straddle one tick");mock.refresh_delay_reads=0;
        mock.refresh_running_counter=true;mock.refresh_read_us=read_us[r];mock.refresh_delay_us=delay_us[d];mock.refresh_phase_us=phase_us[p];
        CHECK(gauguin_wdt_lease_refresh(&out)&&mock.refresh_pulses==1&&wdt_lease_state==WDL_READY,"bounded equal adjacent pair on a running counter");
        CHECK(mock.refresh_ack_reads>=2&&mock.refresh_ack_reads<=256,"at most256total STS loads, not256pairs");
    }
    refresh_ready("final register verification exceeds2ms after equal pair");mock.refresh_fault=8;refresh_failure(1);
    refresh_ready("final counter must not reverse after equal confirmation");mock.refresh_fault=9;refresh_failure(1);
    printf("PASS: %u watchdog service cases; 600 actual refresh calls, exact RST-only writes and terminal failures; host-only\n",cases-first);
}
int main(void)
{
    legacy_cases();
    unsigned legacy=cases;
    lease_cases();
    printf("PASS: %u original + %u lease cases (%u total); actual worker/header/GIC helper/start gate; host-only, no reset qualification\n",
        legacy,cases-legacy,cases);
    service_cases();
    return 0;
}
