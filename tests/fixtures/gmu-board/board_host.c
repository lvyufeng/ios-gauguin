#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "gauguin_gmu_board.h"
#include "gauguin_gmu_clock.h"
#include "gauguin_wdt_lease.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define VM_PROT_READ 1
#define VM_PROT_WRITE 2
#define NSEC_PER_SEC UINT64_C(1000000000)
typedef uintptr_t vm_offset_t;typedef size_t vm_size_t;typedef unsigned ppnum_t,vm_prot_t;typedef int boolean_t;
static _Alignas(16384) uint8_t ram[1048576],reset_page[16384],smmu[65536];
static struct {unsigned maps,nc_maps,translations,fail_translation,map_fail,misalign,pmap_calls,pmap_fail,attr_fail,overflow;
    unsigned owner_calls,owner_fail,budgets,budget_fail,expire,allocs,frees,alloc_fail,smmu_calls,smmu_fail,barriers,corrupt;
    unsigned clock_bad,irq_bad,context,quarantine,reads,writes,writes64;bool live;uint64_t now;} h;
static unsigned cases;
#define CHECK(x) do {if(!(x)){fprintf(stderr,"GMU board failure case%u line%d\n",cases,__LINE__);abort();}}while(0)
static const uint64_t owner=UINT64_C(0xaa200000);
static int host_printf(const char *s,...){(void)s;return 1;}
int ml_get_interrupts_enabled(void){return h.context!=1;}
int ml_at_interrupt_context(void){return h.context==2;}
int get_preemption_level(void){return h.context==3;}
uint64_t mach_absolute_time(void){return h.now;}
void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out){CHECK(n==8&&scale==NSEC_PER_SEC);*out=h.now+8*scale;}
bool gauguin_wdt_lease_check_budget(uint32_t n)
{
    CHECK(n==3u*32765||n==13u*32765);++h.budgets;
    if(h.budgets==h.expire)h.now=8*NSEC_PER_SEC;
    if(h.budgets==h.budget_fail)h.live=false;
    return h.live;
}
void gauguin_wdt_lease_quarantine(void){++h.quarantine;h.live=false;}
bool sweet_gmu_clock_quiet(uint32_t *gx){if(h.clock_bad)return false;*gx=0;return true;}
bool sweet_gmu_irq_quiet(uint32_t raw[3]){raw[0]=raw[1]=raw[2]=0;return !h.irq_bad;}
bool sweet_pas_stage_owner_valid(const struct sweet_pas_cpu_stage *p)
{++h.owner_calls;return h.owner_calls!=h.owner_fail&&p&&p->pa==owner&&p->metadata_bytes==6860&&p->reserved_bytes==16384;}
boolean_t pmap_valid_page(ppnum_t pn)
{
    CHECK((pn>=owner/16384&&pn<(owner+1048576)/16384)||pn==0x3d7c000/16384||
        (pn>=0x3d40000/16384&&pn<0x3d50000/16384));
    return ++h.pmap_calls==h.pmap_fail;
}
unsigned pmap_cache_attributes(ppnum_t pn)
{return h.pmap_calls==h.attr_fail?0:pn>=owner/16384?0xd0000006u:0xd0000007u;}
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t bytes,vm_prot_t prot)
{
    ++h.maps;CHECK(prot==3&&h.maps<=2);
    CHECK(h.maps==1?(pa==0x3d7c000&&bytes==16384):(pa==0x3d40000&&bytes==65536));
    if(h.map_fail==h.maps)return 0;
    if(h.overflow==1&&h.maps==2)return UINTPTR_MAX-16383u;
    return (vm_offset_t)(h.maps==1?reset_page:smmu)+(h.misalign==h.maps);
}
vm_offset_t ml_io_map_wcomb(vm_offset_t pa,vm_size_t bytes)
{CHECK(pa==owner+16384&&bytes==1048576-16384&&!h.nc_maps);++h.nc_maps;return h.overflow==2?UINTPTR_MAX-16383u:(vm_offset_t)(ram+16384);}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    ++h.translations;uint64_t pa=0;
    if(va>=(uintptr_t)reset_page&&va<(uintptr_t)reset_page+sizeof(reset_page))pa=0x3d7c000+va-(uintptr_t)reset_page;
    else if(va>=(uintptr_t)smmu&&va<(uintptr_t)smmu+sizeof(smmu))pa=0x3d40000+va-(uintptr_t)smmu;
    else {CHECK(va>=(uintptr_t)ram+16384&&va<(uintptr_t)ram+sizeof(ram));pa=owner+va-(uintptr_t)ram;}
    return pa+(h.translations==h.fail_translation);
}
void *IOMalloc(size_t n){CHECK(n==65536);++h.allocs;return h.alloc_fail?NULL:malloc(n);}
void IOFree(void *p,size_t n){CHECK(n==65536&&p);++h.frees;free(p);}
void delay(unsigned us){CHECK(us==5||us==10);}
void sweet_log_mark_sync(const char *s){CHECK(s&&strlen(s)<192);}
void sweet_log_flush_now(void){}
static uint32_t mmio_read32(vm_offset_t address)
{
    CHECK(h.live);++h.reads;
    if(address==(uintptr_t)reset_page+0x2000){uint32_t v;memcpy(&v,reset_page+0x2000,4);return v;}
    CHECK(address>=(uintptr_t)smmu&&address+4<=(uintptr_t)smmu+65536);uint32_t v;memcpy(&v,(void *)address,4);return v;
}
static void mmio_write32(vm_offset_t address,uint32_t v)
{CHECK(h.live&&address>=(uintptr_t)smmu&&address+4<=(uintptr_t)smmu+65536);++h.writes;memcpy((void *)address,&v,4);}
static uint64_t mmio_read64(vm_offset_t address)
{CHECK(h.live&&address>=(uintptr_t)smmu&&address+8<=(uintptr_t)smmu+65536);uint64_t v;memcpy(&v,(void *)address,8);++h.reads;return v;}
static void mmio_write64(vm_offset_t address,uint64_t v)
{CHECK(h.live&&address>=(uintptr_t)smmu&&address+8<=(uintptr_t)smmu+65536);++h.writes64;memcpy((void *)address,&v,8);}
static void host_barrier(void)
{
    ++h.barriers;
}
static void host_dsb(void)
{host_barrier();if(h.corrupt==1&&h.nc_maps&&h.allocs&&!h.frees){ram[0x10000]=0x71;h.corrupt=2;}}
enum gsm_result gsm_configure_once(struct gsm_context *ctx,const struct gsm_ops *o,
    const struct ggm_plan *p,struct gsm_receipt *out)
{
    ++h.smmu_calls;CHECK(ctx&&o&&p&&out&&p->owner_pa==owner);
    if(h.smmu_fail==1)return GSM_INHERITED;
    if(!o->guard(o->cookie))return GSM_IO;
    struct ggm_s1_config cfg;
    if(!o->prepare(o->cookie,39,36,&cfg)||!o->guard(o->cookie))return GSM_IO;
    CHECK(cfg.kernel_ttbr0==owner+0x4000&&h.nc_maps==1&&h.allocs==1&&h.frees==1);
    uint32_t a;uint64_t b;
    if(!o->read32(o->cookie,0x20,&a)||!o->write32(o->cookie,0x6060,0x1055)||
       !o->write64(o->cookie,0xa020,UINT64_C(0x30000aa204000))||!o->barrier(o->cookie)||
       !o->read64(o->cookie,0xa020,&b)||!o->guard(o->cookie))return GSM_IO;
    CHECK(b==UINT64_C(0x30000aa204000));
    unsigned reads=h.reads,writes=h.writes,writes64=h.writes64;
    CHECK(!o->read32(NULL,65536,&a)&&!o->read32(NULL,1,&a)&&!o->write32(NULL,65536,0)&&!o->write32(NULL,1,0));
    CHECK(!o->read64(NULL,65536,&b)&&!o->read64(NULL,4,&b)&&!o->write64(NULL,65536,0)&&!o->write64(NULL,4,0));
    CHECK(reads==h.reads&&writes==h.writes&&writes64==h.writes64);
    if(h.smmu_fail==2)return GSM_IO;
    memset(out,0,sizeof(*out));out->mapped_pages=131;out->translations=140;return GSM_OK;
}
#define printf host_printf
@SOURCE@
#undef printf
static void reset(void)
{
    ++cases;memset(&h,0,sizeof(h));h.live=true;memset(ram,0xa5,sizeof(ram));memset(reset_page,0,sizeof(reset_page));memset(smmu,0,sizeof(smmu));
    *(uint32_t *)(void *)(reset_page+0x2000)=1;gmb_lifecycle=0;gmb_deadline=0;gmb_reset=gmb_smmu=gmb_ram=0;
    memset(&gmb_context,0,sizeof(gmb_context));memset(&gmb_work,0,sizeof(gmb_work));memset(&gmb_stage,0,sizeof(gmb_stage));
}
static enum gmb_result run(struct gmb_receipt *out)
{struct sweet_pas_cpu_stage s={owner,6860,16384};return sweet_gmu_smmu_once(&s,out);}
static void failed(void)
{
    struct gmb_receipt out,before;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(run(&out)!=GMB_OK&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!memcmp(&out,&before,sizeof(out)));
    unsigned reads=h.reads,maps=h.maps,budgets=h.budgets;
    CHECK(run(&out)==GMB_ALREADY&&reads==h.reads&&maps==h.maps&&budgets==h.budgets&&!memcmp(&out,&before,sizeof(out)));
    for(unsigned i=0;i<16384;i++)CHECK(ram[i]==0xa5);
    for(unsigned i=0x9c000;i<1048576;i++)CHECK(ram[i]==0xa5);
}
static void happy(void)
{
    reset();struct gmb_receipt out;CHECK(run(&out)==GMB_OK&&sweet_gmu_board_state()==GMB_READY&&!h.quarantine);
    CHECK(out.owner_pa==owner&&out.reset_before==1&&out.smmu.mapped_pages==131&&out.smmu.translations==140);
    CHECK(h.maps==2&&h.nc_maps==1&&h.allocs==1&&h.frees==1&&h.writes64==1);
    unsigned char *expected=malloc(1048576);CHECK(expected);memset(expected,0xa5,1048576);
    struct ggm_plan p;struct ggm_s1_config cfg;CHECK(ggm_plan_build(owner,&p));
    for(unsigned r=0;r<GGM_COUNT;r++)memset(expected+p.region[r].offset,0,p.region[r].reserved);
    CHECK(ggm_emit_tables(&p,39,36,expected+0x4000,32768,&cfg));
    CHECK(ggm_emit_hfi(&p,expected+0x8c000,32768));CHECK(!memcmp(expected,ram,1048576));free(expected);
    unsigned budgets=h.budgets;CHECK(run(&out)==GMB_ALREADY&&h.budgets==budgets);
}
int main(void)
{
    happy();unsigned budgets=h.budgets,translations=h.translations,pmaps=h.pmap_calls;
    reset();CHECK(sweet_gmu_smmu_once(NULL,NULL)==GMB_ARGUMENT&&!gmb_lifecycle);
    for(unsigned i=1;i<=3;i++){reset();h.context=i;failed();CHECK(!h.maps);}
    reset();h.clock_bad=1;failed();reset();h.irq_bad=1;failed();
    for(unsigned i=1;i<=4;i++){reset();h.owner_fail=i;failed();}
    for(unsigned i=1;i<=2;i++){reset();h.map_fail=i;failed();reset();h.misalign=i;failed();}
    for(unsigned i=1;i<=2;i++){reset();h.overflow=i;failed();}
    for(unsigned i=1;i<=translations;i++){reset();h.fail_translation=i;failed();}
    for(unsigned i=1;i<=pmaps;i++){reset();h.pmap_fail=i;failed();reset();h.attr_fail=i;failed();}
    reset();*(uint32_t *)(void *)(reset_page+0x2000)=0;failed();CHECK(h.maps==1&&!h.smmu_calls);
    reset();*(uint32_t *)(void *)(reset_page+0x2000)=UINT32_MAX;failed();CHECK(h.maps==1&&!h.smmu_calls);
    reset();h.smmu_fail=1;failed();CHECK(!h.nc_maps);reset();h.smmu_fail=2;failed();
    reset();h.alloc_fail=1;failed();CHECK(h.allocs==1&&!h.frees);
    reset();h.corrupt=1;failed();CHECK(h.allocs==1&&h.frees==1);
    reset();h.expire=10;failed();
    for(unsigned i=1;i<=budgets;i++){reset();h.budget_fail=i;failed();}
    printf("GMU actual board adapter: %u mapping/owner/reset/budget/failure cases PASS\n",cases);
}
