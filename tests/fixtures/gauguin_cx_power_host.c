/* Actual CX power C; platform and single-word MMIO/barrier seams only.
 * No physical mapping, clocks, sleeps, power changes or watchdog operations. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "gauguin_cx_power.h"
#include "gauguin_cx_rail.h"
#include "gauguin_wdt_lease.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define VM_PROT_READ 1u
#define VM_PROT_WRITE 2u
#define NSEC_PER_SEC UINT64_C(1000000000)
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef uint32_t vm_prot_t;
typedef uint32_t ppnum_t;
typedef int boolean_t;
#define CHECK(c,why) do{if(!(c)){fprintf(stderr,"FAIL line%d [%s]: %s\n",__LINE__,case_name,why);exit(1);}}while(0)
#define FAKE_GCC UINT64_C(0x100000000)
#define FAKE_GPU UINT64_C(0x200000000)
#define CONTROL 0xf007u
#define POWER (1u<<31)
static const char *case_name="setup";
static unsigned cases;
static const char *const conflicts[]={"sweetpasinit","sweetpasmem","sweettouchmode","sweetwdtpet","sweetreboot","sweetbusprobe","sweetgpuprobe","sweetscmprobe","sweetwdttest"};
enum phase { START, CONFIGURE, ENABLE, POLL, FINAL, AHB };
static struct {
    int requested,vote,off[9],context;
    enum gcr_state parent;
    enum phase phase;
    unsigned maps,translations[2],valid_calls[2],attr_calls[2];
    unsigned managed,wrong_attr,map_fail,translation_fail;
    unsigned gcc_reads,gdsc_reads,ahb_reads,writes,write_limit;
    unsigned pending_read,pending_store,dmb_read,dmb_store,dsb;
    unsigned budget_calls,budget_fail_call,budget_live,quarantines;
    unsigned markers,flushes,lines,delays,poll_reads,settles,final_reads;
    unsigned ready_after,power_seen,readback_fault,budget_after_write,deadline_after_write;
    unsigned mode_change_config,mode_change_enable,poll_control_fault,final_power_loss,final_mode_loss;
    unsigned fail_kind;const char *fail_marker;
    uint32_t gcc,gdsc,initial,ahb,last_gdsc,write_values[2];
    uint64_t now,deadline;
    char log[48][224];
} mock;
static void no_pending(void){CHECK(!mock.pending_read && !mock.pending_store,"previous MMIO completed barrier");}
static void fake_dmb_read(void){CHECK(mock.pending_read && !mock.pending_store,"oshld after read");mock.pending_read=0;++mock.dmb_read;}
static void fake_dmb_store(void){no_pending();mock.pending_store=1;++mock.dmb_store;}
static void fake_dsb(void){CHECK(mock.pending_store==2 && !mock.pending_read,"sy after write");mock.pending_store=0;++mock.dsb;}
static uint32_t fake_read(vm_offset_t base,uint32_t off)
{
    no_pending();CHECK(mock.parent==GCR_COMPLETE && mock.budget_live && !mock.context,"held parent/context/budget at each real access");
    uint32_t value;
    if(base==FAKE_GCC){
        CHECK(off==0x1004 && mock.maps==1 && mock.translations[0]==2 && !mock.gcc_reads,"only initial GCC00145004 read");
        ++mock.gcc_reads;value=mock.gcc;
    }else{
        CHECK(base==FAKE_GPU && mock.maps==2 && mock.translations[1]==2 && mock.gcc_reads==1 && (mock.gcc&1) && !(mock.gcc&POWER),"GPUCC only after live GCC gate");
        CHECK(off==0x106c || off==0x1078,"only CX GDSCR and final AHB; noGX/GMU/PLL/SMMU/hw1540");
        if(off==0x1078){CHECK(mock.phase==AHB && mock.power_seen && mock.settles==2 && mock.final_reads==1,"AHB only after final CX-on check");++mock.ahb_reads;value=mock.ahb;}
        else{
            ++mock.gdsc_reads;
            if(mock.phase==POLL){
                ++mock.poll_reads;
                if(mock.ready_after && mock.poll_reads>=mock.ready_after)mock.gdsc|=POWER;
                if(mock.poll_control_fault && mock.poll_reads==mock.poll_control_fault)mock.gdsc|=1;
                if(mock.gdsc&POWER)mock.power_seen=1;
            }
            if(mock.phase==FINAL){++mock.final_reads;if(mock.final_power_loss)mock.gdsc&=~POWER;if(mock.final_mode_loss)mock.gdsc|=2;}
            value=mock.gdsc;
            if(mock.readback_fault && mock.writes==mock.readback_fault)value^=1;
            mock.last_gdsc=value;
        }
    }
    mock.pending_read=1;return value;
}
static void fake_write(uint32_t value)
{
    CHECK(mock.pending_store==1 && !mock.pending_read,"oshst before store");
    CHECK(mock.maps==2 && mock.parent==GCR_COMPLETE && !mock.context && mock.budget_live,"write prerequisites held");
    CHECK(mock.writes<mock.write_limit && mock.writes<2,"no repeat/cleanup writes after uncertainty");
    uint32_t expected;
    if(mock.phase==CONFIGURE)expected=(mock.last_gdsc&~0xf000u)|0x8000u;
    else{CHECK(mock.phase==ENABLE,"writes only configure/enable phases");expected=mock.last_gdsc&~1u;}
    CHECK(!(mock.last_gdsc&6) && value==expected && value!=mock.last_gdsc,"masked write only, preserve all foreign bits and skip no-op");
    mock.write_values[mock.writes++]=value;mock.gdsc=value;
    if(mock.budget_after_write==mock.writes)mock.budget_live=0;
    if(mock.deadline_after_write==mock.writes)mock.now=mock.deadline;
    mock.pending_store=2;
}
static int test_printf(const char *fmt,...)
{
    no_pending();CHECK(mock.lines<48,"bounded log");va_list ap;va_start(ap,fmt);
    int n=vsnprintf(mock.log[mock.lines],sizeof(mock.log[0]),fmt,ap);va_end(ap);
    CHECK(n>0 && (size_t)n<sizeof(mock.log[0]) && mock.log[mock.lines][n-1]=='\n',"bounded newline record");++mock.lines;return n;
}
bool PE_parse_boot_argn(const char *key,void *out,size_t size)
{
    CHECK(size==sizeof(int),"integer flags");
    if(!strcmp(key,"sweetcxpower")){*(int*)out=mock.requested;return true;}
    if(!strcmp(key,"sweetbusvote")){*(int*)out=mock.vote;return true;}
    for(unsigned i=0;i<9;++i)if(!strcmp(key,conflicts[i])){*(int*)out=mock.off[i];return true;}
    CHECK(false,"known flags only");return false;
}
int ml_get_interrupts_enabled(void){return mock.context!=1;}
int ml_at_interrupt_context(void){return mock.context==2;}
int get_preemption_level(void){return mock.context==3 ? 1:0;}
unsigned long long mach_absolute_time(void){no_pending();return mock.now;}
void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out)
{CHECK(n==5 && scale==NSEC_PER_SEC && !mock.deadline,"one5s deadline");mock.deadline=mock.now+5*NSEC_PER_SEC;*out=mock.deadline;}
void delay(unsigned us)
{
    no_pending();CHECK(us==1,"native microsecond delay only");++mock.delays;mock.now+=1000;
    if(mock.phase==ENABLE)mock.phase=POLL;
    else if(mock.phase==POLL && mock.power_seen){++mock.settles;CHECK(mock.settles<=2,"exact native two settle delays");if(mock.settles==2)mock.phase=FINAL;}
    else CHECK(mock.phase==POLL,"no unrelated delay");
}
void sweet_log_mark_sync(const char *line)
{CHECK(!mock.context && mock.lines && strstr(mock.log[mock.lines-1],line),"valid context matching marker");CHECK(mock.markers==mock.flushes,"previous flush");++mock.markers;}
void sweet_log_flush_now(void)
{
    CHECK(!mock.context && mock.markers==mock.flushes+1,"one valid flush");++mock.flushes;
    const char *line=mock.log[mock.lines-1];
    if(strstr(line,"before masked CLK_DIS_WAIT")){mock.phase=CONFIGURE;if(mock.mode_change_config)mock.gdsc|=4;}
    if(strstr(line,"before clearing HLOS")){mock.phase=ENABLE;if(mock.mode_change_enable)mock.gdsc|=2;}
    if(strstr(line,"before final GPUCC AHB"))mock.phase=AHB;
    if(mock.fail_marker && strstr(line,mock.fail_marker)){
        if(mock.fail_kind==1)mock.budget_live=0;
        if(mock.fail_kind==2)mock.now=mock.deadline;
        if(mock.fail_kind==3)mock.parent=GCR_QUARANTINED;
        if(mock.fail_kind==4)mock.context=1;
    }
}
static unsigned page_index(ppnum_t pn)
{CHECK(pn==(0x144000u>>14) || pn==(0x3d90000u>>14),"only two16KiB pages checked");return pn==(0x144000u>>14) ? 0:1;}
boolean_t pmap_valid_page(ppnum_t pn){unsigned i=page_index(pn);++mock.valid_calls[i];return mock.managed==i+1;}
unsigned int pmap_cache_attributes(ppnum_t pn){unsigned i=page_index(pn);++mock.attr_calls[i];return mock.wrong_attr==i+1 ? 6:0xd0000007u;}
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t size,vm_prot_t prot)
{
    no_pending();unsigned id=pa==0x144000u ? 0:1;
    CHECK(pa==(id ? 0x3d90000u:0x144000u) && size==0x4000 && prot==(id ? 3u:1u),"exact aligned maps and protections");
    CHECK(mock.maps==id && mock.parent==GCR_COMPLETE && mock.budget_live && !mock.context,"parent/budget before mapping, no retry");
    CHECK(mock.valid_calls[id]==1 && mock.attr_calls[id]==1,"pmap checks before map");
    CHECK(mock.markers==mock.flushes,"map log persisted before guard/map");
    if(id)CHECK(mock.gcc_reads==1 && (mock.gcc&1) && !(mock.gcc&POWER),"noGPUCC map before live GCC gate");
    ++mock.maps;return mock.map_fail==id+1 ? 0:(id ? FAKE_GPU:FAKE_GCC);
}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    unsigned id=(va==FAKE_GCC || va==FAKE_GCC+0x3fff) ? 0:1;
    unsigned which=mock.translations[id]++;
    CHECK(which<2 && va==(id ? FAKE_GPU:FAKE_GCC)+(which ? 0x3fffu:0u),"first/lastBYTE translations only");
    return (id ? 0x3d90000u:0x144000u)+(which ? 0x3fffu:0u)+(mock.translation_fail==id*2+which+1 ? 1u:0u);
}
enum gcr_state sweet_cx_rail_state(void){return mock.parent;}
bool gauguin_wdt_lease_check_budget(uint32_t minimum)
{
    no_pending();CHECK(!mock.quarantines,"no budget checks after terminal quarantine");
    CHECK(minimum==(mock.budget_calls<2 ? 163825u:98295u),"firstentry/map5s thenstep3s");
    ++mock.budget_calls;return mock.budget_live && mock.budget_calls!=mock.budget_fail_call;
}
void gauguin_wdt_lease_quarantine(void){no_pending();CHECK(!mock.quarantines,"software quarantine once");++mock.quarantines;}
#define printf test_printf
@SOURCE@
#undef printf
static void reset(const char *name)
{
    memset(&mock,0,sizeof(mock));case_name=name;++cases;
    mock.requested=mock.vote=mock.budget_live=1;mock.parent=GCR_COMPLETE;mock.gcc=9;
    mock.gdsc=mock.initial=0x00215801;mock.ahb=0x101;mock.write_limit=2;mock.ready_after=3;mock.now=1;
    gcx_lifecycle=GCX_IDLE;gcx_gcc=gcx_gpucc=0;gcx_deadline=0;memset(&gcx_work,0,sizeof(gcx_work));
}
static void check_barriers(void)
{no_pending();CHECK(mock.dmb_read==mock.gcc_reads+mock.gdsc_reads+mock.ahb_reads && mock.dmb_store==mock.writes && mock.dsb==mock.writes,"actual helper barriers on every access");}
static void failed(enum gcx_rc wanted,unsigned writes)
{
    struct gcx_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
    enum gcx_rc rc=sweet_cx_power_once(&out);check_barriers();
    if(rc!=wanted)fprintf(stderr,"rc=%u want=%u writes=%u\n",rc,wanted,mock.writes);
    CHECK(rc==wanted && mock.writes==writes && !memcmp(&out,&saved,sizeof(out)),"failure point/outputunchanged");
    CHECK(sweet_cx_power_state()==GCX_QUARANTINED && mock.quarantines==1,"started failure terminal quarantine");
    unsigned reads=mock.gcc_reads+mock.gdsc_reads+mock.ahb_reads,maps=mock.maps,logs=mock.lines;
    CHECK(sweet_cx_power_once(&out)==GCX_ALREADY && !memcmp(&out,&saved,sizeof(out)),"no retry after failure");
    CHECK(mock.writes==writes && mock.maps==maps && mock.lines==logs && reads==mock.gcc_reads+mock.gdsc_reads+mock.ahb_reads,"no cleanup/read/map on retry");
}
static void succeeded(unsigned writes,unsigned polls)
{
    struct gcx_receipt out;memset(&out,0xa5,sizeof(out));
    CHECK(sweet_cx_power_once(&out)==GCX_OK,"CX power result");check_barriers();
    CHECK(sweet_cx_power_state()==GCX_COMPLETE && !mock.quarantines && mock.writes==writes && mock.poll_reads==polls,"exact success writes/polls");
    CHECK(out.gcc_cfg_ahb==mock.gcc && out.gdsc_before==mock.initial && out.gdsc_config==((mock.initial&~0xf000u)|0x8000u),"raw pre/config receipt");
    CHECK(out.gdsc_enable==(out.gdsc_config&~1u) && out.gdsc_final==(out.gdsc_enable|POWER) && out.ahb_final==mock.ahb,"raw enable/final/AHB receipt");
    CHECK(out.writes==writes && out.polls==polls && mock.settles==2 && mock.final_reads==1 && mock.ahb_reads==1,"bounded native settle before finalAHB");
    CHECK((out.gdsc_final&~(CONTROL|POWER))==(mock.initial&~(CONTROL|POWER)),"foreignbits retained");
    const struct gcx_receipt saved=out;CHECK(sweet_cx_power_once(&out)==GCX_ALREADY && !memcmp(&out,&saved,sizeof(out)) && mock.writes==writes,"successone-shot");
}
int main(void)
{
    const int off[]={0,2,-1};
    for(unsigned i=0;i<3;++i){reset("exact defaultoff");mock.requested=off[i];struct gcx_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;CHECK(!sweet_cx_power_requested() && sweet_cx_power_once(&out)==GCX_OFF && !memcmp(&out,&saved,sizeof(out)) && sweet_cx_power_state()==GCX_IDLE && !mock.lines && !mock.maps,"offnoeffects");}
    reset("NULLoutput");CHECK(sweet_cx_power_once(NULL)==GCX_ARGUMENT && sweet_cx_power_state()==GCX_IDLE && !mock.maps,"NULLdoesnotclaim");
    reset("cold CX on");succeeded(2,3);
    reset("already configured collapsed");mock.initial=mock.gdsc=0x00218801;succeeded(1,3);
    reset("already software-on but pending power");mock.initial=mock.gdsc=0x00218800;succeeded(0,3);
    reset("already on and owned");mock.initial=mock.gdsc=0x80218800;succeeded(0,1);
    reset("foreign power-on with own collapse set");mock.initial=mock.gdsc=0x80218801;succeeded(1,1);
    reset("AHB zero is observation only");mock.ahb=0;succeeded(2,3);
    reset("last bounded poll succeeds");mock.ready_after=500;succeeded(2,500);CHECK(mock.delays==502,"bounded500poll timing plus native delays");
    for(int c=1;c<=3;++c){reset("context rejected");mock.context=c;failed(GCX_CONTEXT,0);}
    for(unsigned i=0;i<3;++i){reset("busvote exact1");mock.vote=off[i];failed(GCX_CONFIG,0);}
    for(unsigned i=0;i<9;++i)for(int v=-1;v<=1;v+=2){reset("oldprobes/PAS conflict");mock.off[i]=v;failed(GCX_CONFIG,0);}
    for(unsigned s=GCR_IDLE;s<=GCR_QUARANTINED;++s)if(s!=GCR_COMPLETE){reset("parent not complete");mock.parent=(enum gcr_state)s;failed(GCX_PARENT,0);CHECK(!mock.maps && !mock.gcc_reads,"no hardwarewithoutparent");}
    reset("entry budget lost");mock.budget_fail_call=1;failed(GCX_BUDGET,0);CHECK(!mock.maps,"budgetbeforemap");
    for(unsigned p=1;p<=2;++p){reset("managed physicalpage");mock.managed=p;failed(GCX_MAPPING,0);CHECK(mock.maps==p-1,"managed prevents affectedmap");reset("wrongcachepage");mock.wrong_attr=p;failed(GCX_MAPPING,0);CHECK(mock.maps==p-1,"cache prevents affectedmap");reset("mapfailed");mock.map_fail=p;failed(GCX_MAPPING,0);}
    for(unsigned endpoint=1;endpoint<=4;++endpoint){reset("translation mismatch");mock.translation_fail=endpoint;failed(GCX_MAPPING,0);CHECK(!mock.gdsc_reads,"wrongtranslationnoGPUCCread");}
    const uint32_t gcc_bad[]={0,8,0x80000001,UINT32_MAX};
    for(unsigned i=0;i<4;++i){reset("GCC gate closed");mock.gcc=gcc_bad[i];failed(GCX_ACCESS_GATE,0);CHECK(mock.maps==1 && !mock.gdsc_reads,"closedgatepreventsGPUCCmap");}
    const uint32_t modes[]={2,4,6,UINT32_MAX};
    for(unsigned i=0;i<4;++i){reset("hardwaremode no takeover");mock.gdsc|=modes[i];failed(GCX_MODE,0);CHECK(mock.gdsc_reads==1,"stoponinitialmode");}
    reset("mode changed before configwrite");mock.mode_change_config=1;failed(GCX_MODE,0);
    reset("mode changed before enablewrite");mock.mode_change_enable=1;mock.write_limit=1;failed(GCX_MODE,1);
    const char *markers[]={"before map pa=00144000","before GCC CFG_AHB","before map pa=03d90000","before first GDSCR","before masked CLK_DIS_WAIT","before clearing HLOS","before final GPUCC AHB","final gdsc="};
    const unsigned writes_at_marker[]={0,0,0,0,0,1,2,2};
    const enum gcx_rc reason[]={GCX_BUDGET,GCX_TIMEOUT,GCX_PARENT,GCX_CONTEXT};
    for(unsigned i=0;i<8;++i)for(unsigned failure=1;failure<=4;++failure){reset("blockinglog consumesguard");mock.fail_marker=markers[i];mock.fail_kind=failure;mock.write_limit=writes_at_marker[i];failed(reason[failure-1],writes_at_marker[i]);}
    for(unsigned n=1;n<=2;++n){
        reset("write readback mismatch");mock.readback_fault=n;mock.write_limit=n;failed(GCX_READBACK,n);
        reset("budget expires after write");mock.budget_after_write=n;mock.write_limit=n;failed(GCX_BUDGET,n);
        reset("deadline expires after write");mock.deadline_after_write=n;mock.write_limit=n;failed(GCX_TIMEOUT,n);
    }
    reset("never powers on");mock.ready_after=0;failed(GCX_TIMEOUT,2);CHECK(mock.poll_reads==500 && mock.delays==501 && !mock.ahb_reads,"bounded500polls/noAHB");
    reset("controlschange duringpoll");mock.poll_control_fault=2;failed(GCX_READBACK,2);CHECK(mock.poll_reads==2 && !mock.ahb_reads,"stopatfirstchangedcontrol");
    reset("power lost aftersettle");mock.final_power_loss=1;failed(GCX_READBACK,2);CHECK(!mock.ahb_reads,"noAHBafterpowerloss");
    reset("mode lost aftersettle");mock.final_mode_loss=1;failed(GCX_READBACK,2);CHECK(!mock.ahb_reads,"noAHBaftermodechange");
    reset("AHB allones");mock.ahb=UINT32_MAX;failed(GCX_READBACK,2);
    printf("PASS: %u actualCXpower hostcases; parent/clockgates, maskedGDSCRwrites, boundedpolls, no otherMMIO; hardwareunqualified\n",cases);return 0;
}
