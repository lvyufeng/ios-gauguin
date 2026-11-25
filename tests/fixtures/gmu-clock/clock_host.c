/* Actual private clock transaction only. CX/BCM/ARC and shared-GCC are typed
 * dependency seams; their actual implementations have separate host fixtures.
 * Exact allowlist and independent synthetic native profile, no device. */
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "gauguin_gmu_clock.h"
#include "gauguin_cx_rail.h"
#include "gauguin_gcc_votes.h"
#define PAGE_SHIFT 14
#define VM_PROT_READ 1u
#define VM_PROT_WRITE 2u
#define NSEC_PER_SEC UINT64_C(1000000000)
#define GCX_PAGE 0x4000u
#define GCX_STEP_TICKS 98295u
typedef uintptr_t vm_offset_t;typedef size_t vm_size_t;typedef uint32_t vm_prot_t,ppnum_t;
#define PLL UINT64_C(0x100000000)
#define AXI UINT64_C(0x200000000)
#define GCC UINT64_C(0x300000000)
#define GPU UINT64_C(0x400000000)
#define CHECK(c) do{if(!(c)){fprintf(stderr,"FAIL line%d case%u\n",__LINE__,cases);exit(1);}}while(0)
static unsigned cases;
static vm_offset_t gcx_gcc=GCC,gcx_gpucc=GPU;
static bool gcx_gcc_writable;
static struct {uint32_t reg[GMC_COUNT];unsigned maps,trans[2],mapfail,transfail,managed,attrbad;
 unsigned reads,direct,shared,holdcalls,polls,delays,lines,guards,quarantine;
 unsigned noactive,update_stuck,branch_stuck,fail_write,budget_after_write,deadline_after_write;
 unsigned holdfail,preparefail,mutate_cfg,dirty_on_cfg,gx_gdsc,fail_guard;
 uint64_t now,deadline;int flag,context;bool powerflag,flags,live;
 enum gcx_state cx;enum gcr_state rail;enum gbcmt_state bcm;} h;
static bool gcx_context(void){return !h.context;}
bool sweet_cx_power_requested(void){return h.powerflag;}
static bool gcx_flags(void){return h.flags;}
enum gcx_state sweet_cx_power_state(void){return h.cx;}
enum gcr_state sweet_cx_rail_state(void){return h.rail;}
enum gbcmt_state sweet_bcm_transport_state(void){return h.bcm;}
bool PE_parse_boot_argn(const char *s,void *out,size_t n){CHECK(!strcmp(s,"sweetgmuclk")&&n==sizeof(int));*(int*)out=h.flag;return true;}
uint64_t mach_absolute_time(void){return h.now;}
void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out){CHECK(n==5&&scale==NSEC_PER_SEC);*out=h.deadline=h.now+5*scale;}
bool gauguin_wdt_lease_check_budget(uint32_t n){CHECK(n==8*32765u||n==GCX_STEP_TICKS);++h.guards;return h.live&&h.guards!=h.fail_guard;}
void gauguin_wdt_lease_quarantine(void){CHECK(!h.quarantine);++h.quarantine;h.live=false;}
void delay(unsigned n){CHECK(n==1||n==10);++h.delays;h.now+=n*1000;}
static void gcx_record(const char *line){CHECK(line&&strlen(line)<192);++h.lines;}
static int host_printf(const char *fmt,...){(void)fmt;++h.lines;return 1;}
bool pmap_valid_page(ppnum_t p){CHECK(p==0x100000>>14||p==0x12c000>>14);return h.managed;}
unsigned pmap_cache_attributes(ppnum_t p){CHECK(p==0x100000>>14||p==0x12c000>>14);return h.attrbad?6:0xd0000007;}
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t n,vm_prot_t prot){
 unsigned i=h.maps++;CHECK(i<2&&n==0x4000&&pa==(i?0x12c000:0x100000)&&prot==(i?3:1));return h.mapfail==i+1?0:i?AXI:PLL;
}
vm_offset_t ml_vtophys(vm_offset_t va){unsigned i=va>=AXI?1:0;vm_offset_t map=i?AXI:PLL;unsigned end=h.trans[i]++;
 CHECK(end<2&&va==map+(end?0x3fff:0));return(i?0x12c000:0x100000)+(end?0x3fff:0)+(h.transfail==2*i+end+1);}
bool ggv_prepare(void){CHECK(h.bcm==GBCMT_COMPLETE&&h.cx==GCX_COMPLETE&&h.rail==GCR_COMPLETE);return !h.preparefail;}
bool ggv_gpu_read(enum ggv_gpu_vote vote,uint32_t *out){CHECK(vote==GGV_PLL0||vote==GGV_GPU_DIV);*out=h.reg[vote==GGV_PLL0?GMC_PLL_VOTE:GMC_DIV_VOTE];return *out!=UINT32_MAX;}
bool ggv_gpu_hold(enum ggv_gpu_vote vote,uint32_t *out,bool(*guard)(void)){
 CHECK(guard&&h.live&&!h.context);++h.holdcalls;if(h.holdfail==h.holdcalls)return false;
 unsigned reg=vote==GGV_PLL0?GMC_PLL_VOTE:GMC_DIV_VOTE;uint32_t bit=vote==GGV_PLL0?1:0x100;
 if(!(h.reg[reg]&bit)){CHECK(guard());++h.shared;h.reg[reg]|=bit;CHECK(guard());}
 if(vote==GGV_PLL0&&!h.noactive)h.reg[GMC_MODE]|=0x40000000;
 *out=h.reg[reg];return true;
}
static unsigned reg_at(vm_offset_t map,uint32_t off){
 if(map==PLL){if(off==0)return GMC_MODE;if(off==4)return GMC_L;CHECK(off==0x38);return GMC_FRAC;}
 if(map==AXI){CHECK(off==0x1038);return GMC_AXI;}
 if(map==GCC){if(off==0x1004)return GMC_CFG_AHB;if(off==0x100c)return GMC_MEM;CHECK(off==0x114c);return GMC_DIV;}
 CHECK(map==GPU);switch(off){case 0x1078:return GMC_AHB;case 0x106c:return GMC_GDSC;case 0x1120:return GMC_CMD;case 0x1124:return GMC_CFG;case 0x1098:return GMC_CX;case 0x1064:return GMC_GX;case 0x109c:return GMC_CXO;default:CHECK(false);return 0;}
}
static uint32_t fake_read(vm_offset_t map,uint32_t off){
 CHECK(h.live&&!h.context&&h.cx==GCX_COMPLETE);++h.reads;
 if(map==GPU&&off==0x100c)return h.gx_gdsc;
 unsigned r=reg_at(map,off);
 if(r==GMC_CMD&&h.reg[r]!=UINT32_MAX&&(h.reg[r]&1)&&!h.update_stuck)h.reg[r]&=~0x11u;
 if(r==GMC_CFG&&h.mutate_cfg&&h.holdcalls==2)h.reg[r]^=0x100;
 return h.reg[r];
}
static void fake_write(vm_offset_t map,uint32_t off,uint32_t v){
 CHECK(h.live&&!h.context);unsigned r=reg_at(map,off);uint32_t mask=0;
 if(r==GMC_AHB||r==GMC_CXO||r==GMC_AXI||r==GMC_MEM)mask=1;
 if(r==GMC_CX)mask=0xff1;if(r==GMC_CFG)mask=0x10371f;if(r==GMC_CMD)mask=1;
 CHECK(mask&&!((v^h.reg[r])&~mask));++h.direct;
 if(h.direct!=h.fail_write){h.reg[r]=v;
  if(r==GMC_CFG&&h.dirty_on_cfg)h.reg[GMC_CMD]|=0x10;
  if((r==GMC_CX||r==GMC_CXO||r==GMC_AXI||r==GMC_MEM)&&(v&1)&&h.branch_stuck!=r+1)h.reg[r]&=~0x80000000u;}
 if(h.direct==h.budget_after_write)h.live=false;
 if(h.direct==h.deadline_after_write)h.now=h.deadline;
}
#define printf host_printf
@SOURCE@
#undef printf
static void reset(void){++cases;memset(&h,0,sizeof(h));h.flag=1;h.dirty_on_cfg=1;h.flags=h.powerflag=h.live=true;h.cx=GCX_COMPLETE;h.rail=GCR_COMPLETE;h.bcm=GBCMT_COMPLETE;
 h.reg[GMC_MODE]=0xc0100000;h.reg[GMC_L]=31;h.reg[GMC_FRAC]=0x4000;h.reg[GMC_DIV]=1;h.reg[GMC_CFG_AHB]=9;
 h.reg[GMC_PLL_VOTE]=0x1e;h.reg[GMC_DIV_VOTE]=0x80;h.reg[GMC_AHB]=1;h.reg[GMC_GDSC]=0xf8228000;
 h.reg[GMC_CMD]=0x80000000;h.reg[GMC_CX]=h.reg[GMC_GX]=h.reg[GMC_CXO]=0x80000000;
 h.reg[GMC_AXI]=h.reg[GMC_MEM]=0x80000002;h.now=1;gcx_gcc_writable=true;
 gmc_lifecycle=0;gmc_pll=gmc_axi=0;gmc_deadline=0;memset(&gmc_work,0,sizeof(gmc_work));
}
static void failed(void){struct gmc_receipt out,before;memset(&out,0xa5,sizeof(out));before=out;
 CHECK(sweet_gmu_clock_once(&out)!=GCX_OK&&sweet_gmu_clock_state()==GCX_QUARANTINED&&h.quarantine==1&&!memcmp(&out,&before,sizeof(out)));
 unsigned writes=h.direct,holds=h.holdcalls;CHECK(sweet_gmu_clock_once(&out)==GCX_ALREADY&&h.direct==writes&&h.holdcalls==holds);
}
static void success(void){struct gmc_receipt out;CHECK(sweet_gmu_clock_once(&out)==GCX_OK);
 CHECK(sweet_gmu_clock_state()==GCX_COMPLETE&&!h.quarantine&&out.configured_hz==200000000&&out.direct_writes==h.direct&&out.hold_requests==2);
 CHECK(h.maps==2&&h.trans[0]==2&&h.trans[1]==2&&out.after[GMC_CFG]==0x602&&(out.after[GMC_CX]&0xff1)==0xff1);
 unsigned writes=h.direct;CHECK(sweet_gmu_clock_once(&out)==GCX_ALREADY&&h.direct==writes);
}
static void quiet_cases(void)
{
 reset();success();uint32_t out=0xa5;
 h.now=h.deadline+1000; /* The new owner supplies its own CPU deadline. */
 CHECK(sweet_gmu_clock_quiet(&out)&&out==0&&!h.quarantine);
 CHECK(!sweet_gmu_clock_quiet(NULL));
 const unsigned regs[]={GMC_MODE,GMC_L,GMC_FRAC,GMC_DIV,GMC_AHB,GMC_GDSC,
  GMC_CMD,GMC_CFG,GMC_CX,GMC_CXO,GMC_AXI,GMC_MEM,GMC_GX};
 for(unsigned i=0;i<sizeof(regs)/sizeof(*regs);i++){
  reset();success();h.reg[regs[i]]=UINT32_MAX;out=0xa5;
  CHECK(!sweet_gmu_clock_quiet(&out)&&out==0xa5);
 }
 reset();success();h.gx_gdsc=0x80000000;out=0xa5;
 CHECK(!sweet_gmu_clock_quiet(&out)&&out==0xa5);
 reset();success();h.cx=GCX_IDLE;out=0xa5;CHECK(!sweet_gmu_clock_quiet(&out)&&out==0xa5);
 for(unsigned i=1;i<=28;i++){
  reset();success();h.fail_guard=h.guards+i;out=0xa5;
  CHECK(!sweet_gmu_clock_quiet(&out)&&out==0xa5);
 }
 for(unsigned mode=0;mode<4;mode++){
  reset();success();h.gx_gdsc=(mode&1)?0x80000000:0;
  h.reg[GMC_GX]=(mode&2)?1:0x80000000;out=0xa5;
  unsigned writes=h.direct,maps=h.maps;
  CHECK(sweet_gmu_clock_live(true,&out)&&out==h.gx_gdsc&&h.direct==writes&&h.maps==maps);
  out=0xa5;CHECK(sweet_gmu_clock_live(false,&out)==(mode==0));
  if(mode)CHECK(out==0xa5);
 }
 for(unsigned i=0;i<sizeof(regs)/sizeof(*regs);i++){
  reset();success();h.gx_gdsc=0x80000000;h.reg[regs[i]]=UINT32_MAX;out=0xa5;
  CHECK(!sweet_gmu_clock_live(true,&out)&&out==0xa5);
 }
 for(unsigned i=1;i<=28;i++){
  reset();success();h.gx_gdsc=0x80000000;h.fail_guard=h.guards+i;out=0xa5;
  CHECK(!sweet_gmu_clock_live(true,&out)&&out==0xa5);
 }
}
int main(void){
 reset();success();CHECK(h.direct==7&&h.shared==2);
 reset();h.dirty_on_cfg=0;success();
 reset();h.fail_write=2;failed();CHECK(h.direct==2&&!(h.reg[GMC_CX]&1));
 reset();h.reg[GMC_CFG]=0x602;success();CHECK(h.direct==5);
 reset();h.reg[GMC_PLL_VOTE]|=1;h.reg[GMC_DIV_VOTE]|=0x100;success();CHECK(!h.shared);
 const int off[]={0,-1,2};for(unsigned i=0;i<3;++i){reset();h.flag=off[i];struct gmc_receipt out,before;memset(&out,0xa5,sizeof(out));before=out;CHECK(sweet_gmu_clock_once(&out)==GCX_OFF&&!h.maps&&!h.reads&&!h.quarantine&&!memcmp(&out,&before,sizeof(out)));}
 reset();CHECK(sweet_gmu_clock_once(NULL)==GCX_ARGUMENT&&!h.maps&&!gmc_lifecycle);
 reset();h.context=1;failed();reset();h.flags=false;failed();reset();gcx_gcc_writable=false;failed();
 reset();h.cx=GCX_IDLE;failed();reset();h.bcm=GBCMT_IDLE;failed();reset();h.rail=GCR_IDLE;failed();reset();h.live=false;failed();
 reset();h.preparefail=1;failed();CHECK(!h.maps&&!h.reads);
 reset();h.managed=1;failed();reset();h.attrbad=1;failed();
 for(unsigned i=1;i<=2;++i){reset();h.mapfail=i;failed();}
 for(unsigned i=1;i<=4;++i){reset();h.transfail=i;failed();}
 for(unsigned i=0;i<GMC_COUNT;++i){reset();h.reg[i]=UINT32_MAX;failed();CHECK(!h.direct&&!h.holdcalls);}
 const unsigned regs[]={GMC_L,GMC_FRAC,GMC_DIV,GMC_MODE,GMC_CFG_AHB,GMC_GDSC,GMC_CFG,GMC_CMD,GMC_CX,GMC_GX};
 for(unsigned i=0;i<sizeof(regs)/sizeof(regs[0]);++i){reset();unsigned r=regs[i];
  if(r==GMC_L)h.reg[r]=30;if(r==GMC_FRAC)h.reg[r]=0;if(r==GMC_DIV)h.reg[r]=0;if(r==GMC_MODE)h.reg[r]&=~0x100000u;
  if(r==GMC_CFG_AHB)h.reg[r]=0;if(r==GMC_GDSC)h.reg[r]&=~0x80000000u;if(r==GMC_CFG)h.reg[r]=0x100000;if(r==GMC_CMD)h.reg[r]|=2;
  if(r==GMC_CX||r==GMC_GX)h.reg[r]|=1;failed();CHECK(!h.direct&&!h.holdcalls);}
 reset();h.reg[GMC_GX]=0;failed();CHECK(!h.holdcalls);reset();h.reg[GMC_CX]=0;failed();CHECK(!h.holdcalls);
 reset();h.noactive=1;h.reg[GMC_MODE]&=~0x40000000u;failed();CHECK(!h.direct&&h.shared==1);
 for(unsigned i=1;i<=2;++i){reset();h.holdfail=i;failed();CHECK(!h.direct);}
 reset();h.update_stuck=1;failed();CHECK(h.direct==2);
 reset();h.branch_stuck=GMC_CX+1;failed();CHECK(h.direct==4);
 reset();h.mutate_cfg=1;failed();CHECK(!h.direct&&h.shared==2);
 /* UPDATE is self-clearing: absent acknowledgement is indistinguishable
  * from an ignored store. Test its stuck case above; do not pretend simple
  * register readback proves a measured/latched frequency. */
 for(unsigned i=1;i<=7;++i)if(i!=2){reset();h.fail_write=i;failed();CHECK(h.direct==i);}
 for(unsigned i=1;i<=7;++i){reset();h.budget_after_write=i;failed();CHECK(h.direct==i);}
 reset();h.deadline_after_write=2;failed();CHECK(h.direct==2);
 quiet_cases();
 printf("PASS: %u actual GMU clock cases; fixed profile/ordering, live quiet guards, strict MMIO allowlist, terminal failures; no hardware\n",cases);return 0;
}
