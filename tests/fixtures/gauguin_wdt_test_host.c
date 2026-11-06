/* Actual 0114 worker + GIC helper, with platform/MMIO/barrier seams only.
 * Host-only: IOSleep merely counts requests; no mapped hardware, sleeps or reset.
 * The tested store helper retains a mandatory DSB seam after every store. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

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
static const char *case_name="setup";
static unsigned cases;
static vm_offset_t gicd_base;
static const char *const conflict_names[]={"sweetwdtpet","sweetreboot","sweetbusprobe",
    "sweetgpuprobe","sweetscmprobe","sweettouchmode","sweetpasprobe","sweetpasstage"};
static struct {
    int requested,conflict[8],thread_error,context,delayed_context,prewrite_context;
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
    mock.pending_dmb=1; return value;
}
static void fake_wdt_write(unsigned offset,uint32_t value)
{
    static const unsigned offsets[]={16,20,8,4};
    static const uint32_t values[]={655300,753595,3,1};
    idle_barriers(); CHECK(mock.map_count==1 && mock.translations==2,"translation before stores");
    CHECK(mock.gic_reads==2 && mock.dmb_gic==2 && (mock.gic_value[1]&3)==0,
        "both GIC guards completed before any WDT write");
    CHECK(mock.sleeps==45 && mock.en_reads==2,"initial+pre-write EN read disabled after delay");
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
    if(!strcmp(key,"sweetwdttest")) { *(int*)value=mock.requested; return true; }
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
unsigned long long mach_absolute_time(void) { return (unsigned long long)mock.sleeps*1000000000; }
void IOSleep(unsigned ms)
{
    idle_barriers(); CHECK(ms==1000 && mock.sleeps<75,"only75 requested one-second sleeps");
    if(mock.sleeps<45) CHECK(!mock.map_count && !mock.reads && !mock.writes,"45s delay before WDT map/access");
    else { CHECK(mock.writes==4 && mock.dsb==4,"post-arm waits only after full write sequence"); ++mock.post_arm_sleeps; }
    if(++mock.sleeps==45) mock.context=mock.delayed_context;
}
void sweet_log_mark_sync(const char *s)
{
    CHECK(mock.context==0,"synchronous mark requires preemptible thread context");
    idle_barriers(); CHECK(!strncmp(s,"SWEET WDT TEST: ",16),"marker namespace");
    CHECK(mock.lines && strlen(s)+1==strlen(mock.log[mock.lines-1]) &&
        !strncmp(s,mock.log[mock.lines-1],strlen(s)),"marker matches printed record");
    CHECK(mock.markers==mock.flushes,"previous marker flushed"); ++mock.markers;
}
void sweet_log_flush_now(void)
{
    CHECK(mock.context==0,"synchronous flush requires preemptible thread context");
    CHECK(mock.markers==mock.flushes+1,"one flush per marker"); ++mock.flushes;
    if(mock.prewrite_context && strstr(mock.log[mock.lines-1],"preparing native")) mock.context=mock.prewrite_context;
}
boolean_t pmap_valid_page(ppnum_t pn)
{ CHECK(pn==(0x17c10000u>>14),"one WDT physical page"); ++mock.pmap_calls; return mock.managed; }
unsigned int pmap_cache_attributes(ppnum_t pn)
{ CHECK(pn==(0x17c10000u>>14),"one WDT cache attribute"); ++mock.attr_calls; return mock.attr; }
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t bytes,vm_prot_t prot)
{
    idle_barriers(); CHECK(pa==0x17c10000u && bytes==0x1000 && prot==3,"exact WDT map Device RW");
    CHECK(mock.sleeps==45 && mock.pmap_calls==1 && mock.attr_calls==1 && !mock.managed && (mock.attr&255)==7,
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
int main(void)
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
    printf("PASS: %u actual WDT worker/helper host cases; all hardware and waits mocked; no real reset qualified\n",cases);
    return 0;
}
