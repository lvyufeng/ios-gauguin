#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "gauguin_gmu_board.h"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);abort();}}while(0)
#include <stdlib.h>
struct guard_diag {unsigned reason,phase;uint64_t now;uint32_t rbbm,cp;};
static struct driver_state {
 unsigned ggb_started,ggb_argument,ggb_data_selected,ggb_data_ready;
 struct ggs_receipt ggb_smmu;struct ggs_context ggb_context;enum gsm_result ggb_result;
 struct ggd_plan ggb_data_plan;struct gpa_receipt ggb_secure;enum gpa_result ggb_secure_result;
 struct gmb_receipt gmb_work;struct sweet_pas_cpu_stage gmb_stage;struct ggp_plan ggb_plan;
 struct ggx_context ggx_context;struct ggx_receipt ggx_work;enum ggx_result ggx_result;
 struct ggc_context ggc_context;struct ggc_receipt ggc_work;enum ggc_result ggc_result;
 unsigned ggc_maps_ready,ggc_created;struct guard_diag ggc_guard_diagnostic;
 uint64_t ggc_entry,ggc_phase_entry,ggc_deadline,ggc_phase_deadline;
 struct ggq_context ggq_context;struct ggq_receipt ggq_work;enum ggq_result ggq_result;
 struct guard_diag ggq_guard_diagnostic;uint64_t ggq_entry,ggq_phase_entry,ggq_deadline,ggq_phase_deadline;
} state;
@ALIASES@
static bool thread_context;
static struct output_state {char text[65536],marks[65536],flash[65536];unsigned lines,mark_calls,flushes;size_t used,mark_used,flashed;} out;
static bool gmb_thread(void){return thread_context;}
static int host_printf(const char *fmt,...)
{
 va_list ap;va_start(ap,fmt);int n=vsnprintf(out.text+out.used,sizeof(out.text)-out.used,fmt,ap);va_end(ap);
 CHECK(n>0&&(size_t)n<sizeof(out.text)-out.used);out.used+=(size_t)n;++out.lines;return n;
}
static void sweet_log_mark_sync(const char *text)
{
 CHECK(thread_context&&out.lines==out.mark_calls+1);size_t n=strlen(text);CHECK(n+1<sizeof(out.marks)-out.mark_used);
 memcpy(out.marks+out.mark_used,text,n);out.mark_used+=n;out.marks[out.mark_used++]='\n';++out.mark_calls;
 CHECK(out.mark_used==out.used&&!memcmp(out.text,out.marks,out.used));
}
static void sweet_log_flush_now(void)
{
 CHECK(thread_context&&out.mark_calls==out.lines);memcpy(out.flash,out.text,out.used);out.flashed=out.used;++out.flushes;
}
#define printf host_printf
@BASELINE@
@SOURCE@
#undef printf
static void seed(unsigned scenario)
{
 memset(&state,0,sizeof(state));ggb_started=scenario!=3;ggb_argument=15;ggb_result=scenario==1?GSM_ARGUMENT:GSM_OK;
 ggb_smmu=(struct ggs_receipt){.bank=2,.slot=2,.asid=3,.gpu_pages=19,.gmu_pages=131,.translations=171,.ttbr0=0x30000aa29c000,.ttbr1=0x30000aa29f000,.layout=GGS_DATA19};ggb_context.work=ggb_smmu;
 ggb_context.phase=9;ggb_context.diagnostic.check=scenario&1;ggb_context.translation.valid=scenario&1;
 ggb_data_ready=1;ggb_data_plan.data=(struct ggp_region){.offset=0xb8000,.reserved=16384,.mapped=4096,.iova=0xfc018000};
 gmb_stage.pa=0xaa200000;ggb_plan.region[GGP_REGLIST].iova=0xfc014000;ggb_plan.region[GGP_REGLIST].offset=0xb4000;
 ggx_context.phase=8;ggx_context.diagnostic.valid=scenario&1;ggx_work.bank=2;ggx_work.asid=3;ggx_context.work=ggx_work;
 ggc_context.phase=10;ggc_context.diagnostic.valid=scenario&1;ggc_maps_ready=1;ggc_created=6;
 ggc_work=(struct ggc_receipt){.reads=71,.writes=146,.mem_written=133,.mem_compared=1024,.list_length=132,.list_offset=72,.configured=1,.requests_retained=1};ggc_context.work=ggc_work;ggc_context.zero_checked=1024;
 for(unsigned i=0;i<GGC_REGLIST_WORDS;i++)ggc_context.reglist[i]=0x12340000+i;
 ggq_context.phase=9;ggq_context.diagnostic.valid=scenario&1;
 ggq_work=(struct ggq_receipt){.commands_written=15,.commands_checked=8192,.ring_written=8192,.ring_checked=8192,.scratch_written=1024,.scratch_checked=1024,.rptr=15,.complete=1,.requests_retained=1};ggq_context.work=ggq_work;
 for(unsigned i=0;i<GGQ_COMMAND_WORDS;i++)ggq_context.command.word[i]=0xabc00000+i;
}
int main(void)
{
 void (*baseline[])(bool)={baseline_ggb_records,baseline_ggx_records,baseline_ggc_records,baseline_ggq_records};
 void (*actual[])(bool)={ggb_records,ggx_records,ggc_records,ggq_records};unsigned cases=0,saved=0;
 for(unsigned group=0;group<4;group++)for(unsigned mode=0;mode<3;mode++)for(unsigned complete=0;complete<2;complete++)for(unsigned thread=0;thread<2;thread++)for(unsigned scenario=0;scenario<4;scenario++){
  seed(scenario);ggb_data_selected=mode;thread_context=thread!=0;struct driver_state before=state;
  memset(&out,0,sizeof(out));baseline[group](complete!=0);struct output_state expected=out;CHECK(!memcmp(&before,&state,sizeof(state)));
  memset(&out,0,sizeof(out));actual[group](complete!=0);CHECK(!memcmp(&before,&state,sizeof(state)));
  CHECK(out.lines==expected.lines&&out.used==expected.used&&!memcmp(out.text,expected.text,out.used));
  CHECK(out.mark_calls==expected.mark_calls&&out.mark_used==expected.mark_used&&!memcmp(out.marks,expected.marks,out.mark_used));
  CHECK(out.flashed==expected.flashed&&!memcmp(out.flash,expected.flash,out.flashed));
  unsigned wanted=thread&&complete&&mode==1&&out.lines?1:expected.flushes;CHECK(out.flushes==wanted);
  CHECK(!thread||out.mark_calls==out.lines);if(thread&&complete&&mode==1)saved+=expected.flushes-out.flushes;
  ++cases;
 }
 printf("GPU cached records: %u actual/baseline byte/order/mark/drain/read-only cases PASS; %u modeled full-console flushes avoided; NOT hardware timing evidence\n",cases,saved);
 return 0;
}
