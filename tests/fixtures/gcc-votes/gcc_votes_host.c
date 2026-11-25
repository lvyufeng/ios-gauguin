#define GCC_VOTES_HOST_TEST 1
#define GAUGUIN 1
#include "gauguin_gcc_votes.c"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define MAP UINT64_C(0x100000000)
static struct {unsigned maps,translations,reads,writes,managed,attr,failmap,failtrans,context,refuse,guard_calls,fail_guard;uint32_t reg[3];} h;
static unsigned cases;
static bool allow_write(void){++h.guard_calls;return h.guard_calls!=h.fail_guard;}
int ml_get_interrupts_enabled(void){return h.context!=1;}
int ml_at_interrupt_context(void){return h.context==2;}
int get_preemption_level(void){return h.context==3;}
boolean_t pmap_valid_page(ppnum_t p){assert(p==(0x150000>>14));return h.managed;}
unsigned int pmap_cache_attributes(ppnum_t p){assert(p==(0x150000>>14));return h.attr;}
vm_offset_t ml_io_map_with_prot(vm_offset_t p,vm_size_t n,vm_prot_t prot)
{assert(p==0x150000 && n==0x4000 && prot==3 && !h.maps);++h.maps;return h.failmap?0:MAP;}
vm_offset_t ml_vtophys(vm_offset_t p)
{unsigned end=h.translations++;assert(end<2 && p==MAP+(end?0x3fff:0));return 0x150000+(end?0x3fff:0)+(h.failtrans==end+1);}
static unsigned word(uint32_t off)
{assert(off==0x2000 || off==0x2008 || off==0x2010);return off==0x2000?0:off==0x2008?1:2;}
uint32_t ggv_test_read(vm_offset_t p,uint32_t off)
{assert(p==MAP && h.maps==1 && h.translations==2);++h.reads;return h.reg[word(off)];}
void ggv_test_write(vm_offset_t p,uint32_t off,uint32_t v)
{
 assert(p==MAP && h.maps==1 && h.translations==2);unsigned i=word(off);
 assert(!((v^h.reg[i])&~(i==0?0x4c0u:i==1?0x100u:1u)));
 ++h.writes;if(!h.refuse)h.reg[i]=v;
}
static void reset(void)
{++cases;memset(&h,0,sizeof(h));h.attr=0xd0000007;h.reg[0]=0x9c000003;h.reg[1]=0x80;h.reg[2]=0x1e;ggv_map=0;ggv_mapping_state=ggv_gpu_quarantined=ggv_gpu_owner=0;}
static void unavailable(void)
{
 uint32_t out=0xa5a5a5a5;assert(!ggv_gpu_read(GGV_PLL0,&out) && !ggv_gpu_hold(GGV_GPU_DIV,&out,allow_write));
 assert(out==0xa5a5a5a5 && !h.reads && !h.writes && ggv_touch_read()==UINT32_MAX && !ggv_touch_update(0x40,0x40));
}
int main(void)
{
 reset();unavailable();assert(ggv_prepare() && ggv_prepare() && h.maps==1 && h.translations==2);
 assert(ggv_touch_update(0x4c0,0x4c0) && ggv_touch_read()==0x9c0004c3);
 uint32_t out;assert(ggv_gpu_hold(GGV_PLL0,&out,allow_write) && out==0x1f && ggv_gpu_hold(GGV_GPU_DIV,&out,allow_write) && out==0x180);
 unsigned writes=h.writes;assert(ggv_gpu_hold(GGV_PLL0,&out,allow_write) && ggv_gpu_hold(GGV_GPU_DIV,&out,allow_write) && h.writes==writes);
 assert(ggv_touch_update(0x4c0,0) && h.reg[0]==0x9c000003 && h.reg[1]==0x180 && h.reg[2]==0x1f);
 assert(ggv_gpu_read(GGV_PLL0,&out) && out==0x1f && !ggv_gpu_hold((enum ggv_gpu_vote)9,&out,allow_write));
 for(unsigned c=1;c<=3;++c){reset();h.context=c;assert(!ggv_prepare() && !ggv_mapping_state);unavailable();h.context=0;assert(ggv_prepare());}
 for(unsigned bad=0;bad<5;++bad){reset();if(bad==0)h.managed=1;if(bad==1)h.attr=6;if(bad==2)h.failmap=1;if(bad>=3)h.failtrans=bad-2;
  assert(!ggv_prepare() && ggv_mapping_state==3);unsigned maps=h.maps;assert(!ggv_prepare() && h.maps==maps);unavailable();}
 reset();ggv_mapping_state=1;assert(!ggv_prepare() && !h.maps && ggv_mapping_state==1);unavailable();
 const uint32_t badmask[]={0,1,0x100,0x800,0xffffffff};
 for(unsigned i=0;i<5;++i){reset();assert(ggv_prepare());assert(!ggv_touch_update(badmask[i],0) && !h.reads && !h.writes);}
 reset();assert(ggv_prepare() && !ggv_touch_update(0x40,0x80) && !h.reads && !h.writes);
 for(unsigned which=0;which<2;++which){reset();assert(ggv_prepare());h.refuse=1;out=0xa5a5a5a5;
  assert(!ggv_gpu_hold(which?GGV_GPU_DIV:GGV_PLL0,&out,allow_write) && out==0xa5a5a5a5 && h.writes==1 && ggv_gpu_quarantined && !ggv_gpu_owner);
  assert(!ggv_gpu_hold(GGV_PLL0,&out,allow_write) && !ggv_gpu_read(GGV_GPU_DIV,&out) && h.writes==1);
  h.refuse=0;assert(ggv_touch_update(0x40,0x40) && (ggv_touch_read()&0x40));}
 reset();assert(ggv_prepare());ggv_gpu_owner=1;out=0xa5a5a5a5;assert(!ggv_gpu_hold(GGV_PLL0,&out,allow_write) && out==0xa5a5a5a5 && !h.reads && !h.writes && ggv_gpu_owner==1 && !ggv_gpu_quarantined);
 for(unsigned i=0;i<3;++i){reset();assert(ggv_prepare());h.reg[i]=UINT32_MAX;out=0xa5a5a5a5;
  if(i==0)assert(!ggv_touch_update(0x40,0x40));
  else assert(!ggv_gpu_hold(i==1?GGV_GPU_DIV:GGV_PLL0,&out,allow_write) && !ggv_gpu_read(i==1?GGV_GPU_DIV:GGV_PLL0,&out) && out==0xa5a5a5a5);
  assert(!h.writes && !ggv_gpu_owner);}
 reset();assert(ggv_prepare());out=0xa5a5a5a5;assert(!ggv_gpu_hold(GGV_PLL0,NULL,allow_write) && !ggv_gpu_read(GGV_PLL0,NULL) && !h.reads && !h.writes);
 for(unsigned fail=1;fail<=2;++fail){reset();assert(ggv_prepare());h.fail_guard=fail;out=0xa5a5a5a5;
  assert(!ggv_gpu_hold(GGV_PLL0,&out,allow_write) && out==0xa5a5a5a5 && !ggv_gpu_owner);
  assert(h.writes==fail-1 && ggv_gpu_quarantined==(fail==2));
  if(fail==2){assert(!ggv_gpu_hold(GGV_GPU_DIV,&out,allow_write) && h.writes==1);assert(ggv_touch_update(0x40,0x40));}
 }
 printf("PASS: %u shared GCC mapping/vote cases; one map, exact word/masks, touch independent of GPU quarantine\n",cases);return 0;
}
