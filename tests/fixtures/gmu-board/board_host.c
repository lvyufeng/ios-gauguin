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
#include "gauguin_gmu_asset.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define VM_PROT_READ 1
#define VM_PROT_WRITE 2
#define NSEC_PER_SEC UINT64_C(1000000000)
typedef uintptr_t vm_offset_t;typedef size_t vm_size_t;typedef unsigned ppnum_t,vm_prot_t;typedef int boolean_t;
static _Alignas(16384) uint8_t ram[1048576],reset_page[16384],smmu[65536];
static _Alignas(16384) uint8_t fw_page[5][49152],fw_asset[32768];
static const uint64_t fw_bases[5]={0x03d8c000,0x0b294000,0x0b490000,0x03d6c000,0x03d0c000};
static const unsigned fw_sizes[5]={16384,16384,16384,49152,16384};
static struct {unsigned maps,nc_maps,translations,fail_translation,map_fail,misalign,pmap_calls,pmap_fail,attr_fail,overflow;
    unsigned owner_calls,owner_fail,budgets,budget_fail,expire,allocs,frees,alloc_fail,smmu_calls,smmu_fail,barriers,corrupt;
    unsigned clock_bad,irq_bad,context,quarantine,reads,writes,writes64;bool live;uint64_t now;
    unsigned firmware,asset_calls,asset_fail,engine_calls,engine_fail,gx_on,allow_gx,core_irq,
        fw_read_corrupt,fw_fail_phase,fw_stop_at,fw_steps,fw_stores,fw_forbidden,diag_lines,impl_lines,atos_lines,ctx_fault,fw_diag_lines,fw_impl_lines,fw_pdc_lines;} h;
static unsigned cases;
#define CHECK(x) do {if(!(x)){fprintf(stderr,"GMU board failure case%u line%d\n",cases,__LINE__);abort();}}while(0)
static const uint64_t owner=UINT64_C(0xaa200000);
static int host_printf(const char *s,...)
{
    char text[256];va_list ap;va_start(ap,s);int n=vsnprintf(text,sizeof(text),s,ap);va_end(ap);
    CHECK(n>0&&(unsigned)n<sizeof(text));
    if(strstr(text,"SWEET GMU SMMU FAIL:")){CHECK(h.quarantine==1&&!h.live);++h.diag_lines;}
    if(strstr(text,"SWEET GMU SMMU IMPL:")){
        CHECK(!strcmp(text,"SWEET GMU SMMU IMPL: off=06b68 requested=9a82a382 readback=0a800082 policy=native-write; equality unqualified\n"));
        CHECK(h.live?!h.quarantine:h.quarantine==1);++h.impl_lines;
    }
    if(strstr(text,"SWEET GMU ATOS FAIL:")){
        CHECK(h.quarantine==1&&!h.live);
        CHECK(!strcmp(text,"SWEET GMU ATOS FAIL: stream=5 bank=4 iova=00000000 expected=ffffffffffffffff par=0000000300000211 mapped=131 level=3\n"));
        ++h.atos_lines;
    }
    if(strstr(text,"SWEET GMU FW READBACK:")){
        CHECK(h.quarantine==1&&!h.live);
        CHECK(!strcmp(text,"SWEET GMU FW READBACK: phase=0 check=1 window=1 off=01038 mask=ffffffff expected=00000000 actual=12340000\n"));
        ++h.fw_diag_lines;
    }
    if(strstr(text,"SWEET GMU FW IMPL:")){
        unsigned index=h.fw_impl_lines++;CHECK(index<3);char expected[192];
        static const uint32_t raw[]={0x82204514,0x12345678,0x60001000};
        snprintf(expected,sizeof(expected),"SWEET GMU FW IMPL: off=%05x requested=00000000 readback=%08x policy=native-write; equality unqualified\n",0x1034+8*index,raw[index]);
        CHECK(!strcmp(text,expected));CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU PDC MSGID:")){
        unsigned index=h.fw_pdc_lines++;CHECK(index<6);char expected[192];
        unsigned off=index<3?0x15d4+16*index:0x1764+16*(index-3);
        snprintf(expected,sizeof(expected),"SWEET GMU PDC MSGID: off=%05x requested=00010108 readback=00010100 checked_mask=00010100 policy=native-write; other bits unqualified\n",off);
        CHECK(!strcmp(text,expected));CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    return n;
}
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
bool sweet_gmu_clock_live(bool allow,uint32_t *gx)
{h.allow_gx+=allow;*gx=h.gx_on?0x80000000u:0;return !h.clock_bad&&(allow||!h.gx_on);}
bool sweet_gmu_irq_quiet(uint32_t raw[3]){raw[0]=raw[2]=0;raw[1]=h.core_irq?0x1000:0;return !h.irq_bad;}
bool sweet_pas_stage_owner_valid(const struct sweet_pas_cpu_stage *p)
{++h.owner_calls;return h.owner_calls!=h.owner_fail&&p&&p->pa==owner&&p->metadata_bytes==6860&&p->reserved_bytes==16384;}
boolean_t pmap_valid_page(ppnum_t pn)
{
    bool found=(pn>=owner/16384&&pn<(owner+1048576)/16384)||pn==0x3d7c000/16384||
        (pn>=0x3d40000/16384&&pn<0x3d50000/16384);
    for(unsigned n=0;n<5;n++)found|=pn>=fw_bases[n]/16384&&pn<(fw_bases[n]+fw_sizes[n])/16384;
    CHECK(found);
    return ++h.pmap_calls==h.pmap_fail;
}
unsigned pmap_cache_attributes(ppnum_t pn)
{return h.pmap_calls==h.attr_fail?0:pn>=owner/16384?0xd0000006u:0xd0000007u;}
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t bytes,vm_prot_t prot)
{
    ++h.maps;CHECK(prot==3&&h.maps<=(h.firmware?7u:2u));
    if(h.maps<=2)CHECK(h.maps==1?(pa==0x3d7c000&&bytes==16384):(pa==0x3d40000&&bytes==65536));
    else CHECK(pa==fw_bases[h.maps-3]&&bytes==fw_sizes[h.maps-3]);
    if(h.map_fail==h.maps)return 0;
    if(h.overflow==1&&h.maps==2)return UINTPTR_MAX-16383u;
    return (vm_offset_t)(h.maps==1?reset_page:h.maps==2?smmu:fw_page[h.maps-3])+(h.misalign==h.maps);
}
vm_offset_t ml_io_map_wcomb(vm_offset_t pa,vm_size_t bytes)
{CHECK(pa==owner+16384&&bytes==1048576-16384&&!h.nc_maps);++h.nc_maps;return h.overflow==2?UINTPTR_MAX-16383u:(vm_offset_t)(ram+16384);}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    ++h.translations;uint64_t pa=0;
    if(va>=(uintptr_t)reset_page&&va<(uintptr_t)reset_page+sizeof(reset_page))pa=0x3d7c000+va-(uintptr_t)reset_page;
    else if(va>=(uintptr_t)smmu&&va<(uintptr_t)smmu+sizeof(smmu))pa=0x3d40000+va-(uintptr_t)smmu;
    else if(va>=(uintptr_t)ram+16384&&va<(uintptr_t)ram+sizeof(ram))pa=owner+va-(uintptr_t)ram;
    else {bool found=false;for(unsigned n=0;n<5;n++)if(va>=(uintptr_t)fw_page[n]&&va<(uintptr_t)fw_page[n]+fw_sizes[n]){found=true;pa=fw_bases[n]+va-(uintptr_t)fw_page[n];break;}CHECK(found);}
    return pa+(h.translations==h.fail_translation);
}
void *IOMalloc(size_t n){CHECK(n==65536);++h.allocs;return h.alloc_fail?NULL:malloc(n);}
void IOFree(void *p,size_t n){CHECK(n==65536&&p);++h.frees;free(p);}
void delay(unsigned us){CHECK(us==5||us==10||us==100);}
void sweet_log_mark_sync(const char *s){CHECK(s&&strlen(s)<192);}
void sweet_log_flush_now(void){}
static uint32_t mmio_read32(vm_offset_t address)
{
    CHECK(h.live);++h.reads;
    if(address==(uintptr_t)reset_page+0x2000){uint32_t v;memcpy(&v,reset_page+0x2000,4);return v;}
    CHECK(address>=(uintptr_t)smmu&&address+4<=(uintptr_t)smmu+65536);uint32_t v;memcpy(&v,(void *)address,4);
    unsigned off=(unsigned)(address-(uintptr_t)smmu);
    if(off>=0x8000&&(off&0xfff)==0x58){
        unsigned bank=(off-0x8000)/4096;uint32_t cbar,cba2r;
        memcpy(&cbar,smmu+0x1000+4*bank,4);memcpy(&cba2r,smmu+0x1800+4*bank,4);
        if(((cbar>>16)&3)==1&&(cba2r&1))v=(v&~0x600u)|0x400u;
    }
    return v;
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
    ctx->implementation=(struct gsm_impl_sample){1,0x9a82a382,0x0a800082};
    if(h.smmu_fail==2){ctx->diagnostic=(struct gsm_diagnostics){GSP_USER,GSD_STORE32,0xe000,UINT32_MAX,0xc01067,0};return GSM_READBACK;}
    if(h.smmu_fail==3){
        ctx->diagnostic.phase=GSP_ATOS;
        ctx->translation=(struct gsm_atos_sample){UINT64_MAX,UINT64_C(0x300000211),1,5,4,0,131,3};
        ctx->work.translations=132;ctx->work.mapped_pages=131;return GSM_TRANSLATION;
    }
    memset(out,0,sizeof(*out));out->mapped_pages=131;out->translations=140;
    if(h.firmware){
        out->banks=8;out->groups=128;out->stream_match=1;out->micro_after=0x2378;
        out->tcr=(uint32_t)cfg.tcr;out->tcr2=(uint32_t)(cfg.tcr>>32)|0x38010;out->mair0=cfg.mair0;out->mair1=cfg.mair1;
        memcpy(smmu+0x6000,&out->micro_after,4);
        for(unsigned n=0;n<2;n++){
            out->bank[n]=n+1;out->slot[n]=n+4;out->sctlr[n]=0x00c01067;
            out->actlr[n]=0x70000000;
            out->smr_after[n]=0x80000004u+n;out->s2cr_after[n]=n+1;
            out->ttbr0[n]=owner+0x4000+0x4000*n;out->ttbr1[n]=owner+0x5000+0x4000*n;
            unsigned cb=0x8000+0x1000*(n+1);
            memcpy(smmu+cb,&out->sctlr[n],4);memcpy(smmu+cb+0x20,&out->ttbr0[n],8);memcpy(smmu+cb+0x28,&out->ttbr1[n],8);
            memcpy(smmu+cb+4,&out->actlr[n],4);memcpy(smmu+cb+0x10,&out->tcr2,4);memcpy(smmu+cb+0x30,&out->tcr,4);
            memcpy(smmu+cb+0x38,&out->mair0,4);memcpy(smmu+cb+0x3c,&out->mair1,4);
            uint32_t cbar=0x1f300,cba2r=1;memcpy(smmu+0x1000+4*(n+1),&cbar,4);memcpy(smmu+0x1800+4*(n+1),&cba2r,4);
            memcpy(smmu+0x800+4*(n+4),&out->smr_after[n],4);memcpy(smmu+0xc00+4*(n+4),&out->s2cr_after[n],4);
        }
    }
    return GSM_OK;
}
bool sweet_gmu_asset_view(struct gma_view *out)
{++h.asset_calls;if(h.asset_fail==h.asset_calls)return false;*out=(struct gma_view){fw_asset,0xb0000000,32768};return true;}
bool gmf_plan_valid(const struct gmf_plan *p){return p&&p->address[0]==0x30000;}
static uint32_t fw_read32(vm_offset_t address);
static void fw_write32(vm_offset_t address,uint32_t value);
enum gmf_result gmf_bootstrap_once(struct gmf_context *,const struct gmf_ops *,const struct gmf_plan *,struct gmf_receipt *);
#define printf host_printf
@SOURCE@
#undef printf
static void reset(void)
{
    ++cases;memset(&h,0,sizeof(h));h.live=true;memset(ram,0xa5,sizeof(ram));memset(reset_page,0,sizeof(reset_page));memset(smmu,0,sizeof(smmu));
    *(uint32_t *)(void *)(reset_page+0x2000)=1;gmb_lifecycle=0;gmb_deadline=0;gmb_reset=gmb_smmu=gmb_ram=0;
    memset(&gmb_context,0,sizeof(gmb_context));memset(&gmb_work,0,sizeof(gmb_work));memset(&gmb_stage,0,sizeof(gmb_stage));
    gfw_lifecycle=0;gfw_deadline=0;memset(gfw_map,0,sizeof(gfw_map));memset(&gfw_context,0,sizeof(gfw_context));memset(&gfw_work,0,sizeof(gfw_work));memset(&gfw_asset,0,sizeof(gfw_asset));
    gfw_copy_issued=gfw_copy_compared=0;
    memset(fw_page,0,sizeof(fw_page));for(unsigned n=0;n<sizeof(fw_asset);n++)fw_asset[n]=(uint8_t)(n*19+3);
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
static uint8_t *fw_address(vm_offset_t address)
{
    if(address>=(uintptr_t)reset_page&&address+4<=(uintptr_t)reset_page+sizeof(reset_page))return (uint8_t *)address;
    if(address>=(uintptr_t)ram+0x8c000&&address+4<=(uintptr_t)ram+0x94000)return (uint8_t *)address;
    for(unsigned n=0;n<5;n++)if(address>=(uintptr_t)fw_page[n]&&address+4<=(uintptr_t)fw_page[n]+fw_sizes[n])return (uint8_t *)address;
    CHECK(false);return NULL;
}
static uint32_t fw_read32(vm_offset_t address)
{
    CHECK(h.live);uint32_t value;memcpy(&value,fw_address(address),4);
    if(h.fw_read_corrupt&&address==(uintptr_t)fw_page[3]+0x1000+4*(h.fw_read_corrupt-1))value^=1;
    return value;
}
static void fw_write32(vm_offset_t address,uint32_t value)
{
    CHECK(h.live);uint8_t *p=fw_address(address);++h.fw_stores;
    if(address==(uintptr_t)reset_page+0x2000){CHECK(gfw_work.release_attempted==1&&gfw_work.phase==GMF_RELEASING&&value==0);if(h.fw_fail_phase==24)return;}
    if(address==(uintptr_t)reset_page+0x2650&&value==(1u<<22)){CHECK(gfw_work.oob_attempted&&gfw_work.phase==GMF_GX_REQUEST);h.gx_on=1;}
    memcpy(p,&value,4);
}
/* Typed engine seam: exercise every actual board callback and both critical
 * ownership transitions. Real GMF sequencing/rings are tested separately by
 * test_gmu_firmware.py; these synthetic receipts are not firmware ACK evidence. */
enum gmf_result gmf_bootstrap_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,struct gmf_receipt *out)
{
    ++h.engine_calls;CHECK(ctx&&p&&out&&gmf_plan_valid(p));
    if(h.engine_fail==1)return GMF_TIMEOUT;
    if(h.engine_fail==5){ctx->diagnostic=(struct gmf_diagnostic){1,GMF_RESET,GMFD_STORE32,GMF_AO,0x1038,UINT32_MAX,0,0x12340000};return GMF_READBACK;}
    ctx->hidden_valid=h.engine_fail==6?1u:7u;
    ctx->hidden_readback[0]=0x82204514;ctx->hidden_readback[1]=0x12345678;ctx->hidden_readback[2]=0x60001000;
    if(h.engine_fail==6)return GMF_TIMEOUT;
    ctx->pdc_msgid_valid=h.engine_fail==7?1u:63u;
    for(unsigned n=0;n<6;n++)ctx->pdc_msgid_readback[n]=0x10100;
    if(h.engine_fail==7)return GMF_TIMEOUT;
    const uint8_t *data=NULL;size_t bytes=0;struct gmf_copy copy;
    if(!o->guard(NULL,GMF_RESET)||!o->asset(NULL,&data,&bytes)||
       !o->copy(NULL,data,bytes,&copy))return GMF_ASSET;
    CHECK(copy.written==8192&&copy.checked==8192&&!memcmp(fw_page[3]+0x1000,fw_asset,32768));
    for(unsigned i=0;i<4096;i++)CHECK(!fw_page[3][i]);
    for(unsigned i=0x9000;i<49152;i++)CHECK(!fw_page[3][i]);
    uint32_t v;unsigned stores=h.fw_stores;
    CHECK(!o->read(NULL,GMF_WINDOWS,0,&v)&&!o->read(NULL,GMF_CSR,1,&v)&&!o->read(NULL,GMF_CSR,0x4000,&v));
    CHECK(!o->write(NULL,GMF_TCM,0xc000,0)&&!o->write(NULL,GMF_CSR,0x2000,0));
    CHECK(!o->shared_read(NULL,8192,&v)&&!o->shared_write(NULL,8192,1)&&h.fw_stores==stores);
    if(!o->shared_read(NULL,0,&v)||!o->shared_write(NULL,8191,0x98761234)||
       !o->shared_read(NULL,8191,&v)||v!=0x98761234)return GMF_IO;
    CHECK(!o->delay_us(NULL,1)&&o->delay_us(NULL,100));
    if(h.fw_fail_phase==1)h.core_irq=1;
    if(!o->guard(NULL,GMF_RELEASING)||!o->write(NULL,GMF_CSR,0x2000,0)||
       !o->barrier(NULL)||!o->guard(NULL,GMF_RELEASING))return GMF_IO;
    CHECK(!o->write(NULL,GMF_CSR,0x2000,0)&&!o->write(NULL,GMF_CSR,0x2000,1));
    if(h.engine_fail==2)return GMF_FAULT;
    if(h.fw_fail_phase==2)h.gx_on=1;
    if(!o->guard(NULL,GMF_BOOTING)||!o->guard(NULL,GMF_GX_REQUEST)||
       !o->write(NULL,GMF_CSR,0x2650,1u<<22)||!o->guard(NULL,GMF_GX_REQUEST))return GMF_IO;
    CHECK(!o->write(NULL,GMF_CSR,0x2650,1u<<22)&&h.allow_gx);
    if(h.engine_fail==3)return GMF_FAULT;
    if(h.fw_fail_phase==3){uint32_t one=1;memcpy(reset_page+0x2000,&one,4);}
    if(h.fw_fail_phase==4){uint32_t one=1;memcpy(smmu+0x48,&one,4);}
    if(h.fw_fail_phase==5){uint32_t one=2;memcpy(smmu+0x9058,&one,4);}
    if(h.fw_fail_phase==6){uint32_t one=1;memcpy(fw_page[0]+0x2c14,&one,4);}
    if(h.fw_fail_phase==7){uint32_t one=0x8000;memcpy(reset_page+0x2648,&one,4);}
    if(h.fw_fail_phase==8){uint32_t one=1;memcpy(smmu+0x810,&one,4);}
    const unsigned changed[]={0x9004,0x9010,0x9030,0x9038,0x903c,0x1004,0x1804,0x9020,0x902c,0xc10,0x6000,0};
    if(h.fw_fail_phase>=9&&h.fw_fail_phase<9+sizeof(changed)/sizeof(*changed))smmu[changed[h.fw_fail_phase-9]]^=1;
    if(h.fw_fail_phase==21)h.live=false;
    if(h.fw_fail_phase==22)h.now=gfw_deadline;
    if(h.fw_fail_phase==23)h.budget_fail=h.budgets+2;
    if(h.ctx_fault)memcpy(smmu+0x9058,&h.ctx_fault,4);
    if(!o->guard(NULL,GMF_HFI_START)||!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;
    if(h.engine_fail==4)return GMF_FAULT;
    CHECK(!o->guard(NULL,GMF_RESET)&&!o->guard(NULL,GMF_DONE+1));
    memset(out,0,sizeof(*out));out->phase=GMF_DONE;out->fw_result=0xbabeface;out->reported_version=0x100b0000;return GMF_OK;
}
static enum gmb_result firmware_run(struct gmb_firmware_receipt *out)
{struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;return sweet_gmu_firmware_once(&s,&p,out);}
static void firmware_failed(void)
{
    struct gmb_firmware_receipt out,before;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(firmware_run(&out)!=GMB_OK&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!memcmp(&out,&before,sizeof(out)));
    unsigned maps=h.maps,budgets=h.budgets,stores=h.fw_stores;
    CHECK(firmware_run(&out)==GMB_ALREADY&&maps==h.maps&&budgets==h.budgets&&stores==h.fw_stores&&!memcmp(&out,&before,sizeof(out)));
}
static void firmware_cases(void)
{
    unsigned first=cases;
    reset();h.firmware=1;struct gmb_firmware_receipt out;
    CHECK(firmware_run(&out)==GMB_OK&&h.maps==7&&h.nc_maps==1&&h.engine_calls==1&&!h.quarantine);
    CHECK(h.impl_lines==1);
    CHECK(out.reset==0&&out.release_attempted==1&&out.oob_attempted==1&&out.phase==GMF_DONE&&h.allow_gx);
    CHECK(out.firmware.fw_result==0xbabeface&&out.asset_pa==0xb0000000&&h.fw_impl_lines==3&&h.fw_pdc_lines==6);
    CHECK(out.fsr[0]==0x400&&out.fsr[1]==0x400);
    CHECK(sweet_gmu_firmware_state()==GMB_READY&&sweet_gmu_board_state()==GMB_READY);
    unsigned budgets=h.budgets,maps=h.maps;CHECK(firmware_run(&out)==GMB_ALREADY&&h.budgets==budgets&&h.maps==maps);
    for(unsigned n=1;n<=2;n++){reset();h.firmware=1;h.asset_fail=n;firmware_failed();if(n==1)CHECK(!h.maps&&!h.fw_stores);}
    for(unsigned n=3;n<=7;n++){reset();h.firmware=1;h.map_fail=n;firmware_failed();CHECK(!h.engine_calls);reset();h.firmware=1;h.misalign=n;firmware_failed();}
    for(unsigned n=1;n<=4;n++){reset();h.firmware=1;h.engine_fail=n;firmware_failed();CHECK(gfw_work.release_attempted==(n>=2));CHECK(gfw_work.oob_attempted==(n>=3));}
    reset();h.firmware=1;h.engine_fail=5;firmware_failed();CHECK(h.fw_diag_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=6;firmware_failed();CHECK(h.fw_impl_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=7;firmware_failed();CHECK(h.fw_impl_lines==3&&h.fw_pdc_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    for(unsigned n=1;n<=24;n++){reset();h.firmware=1;h.fw_fail_phase=n;firmware_failed();}
    const unsigned faultbits[]={1,2,3,4,5,6,7,8,30,31};
    for(unsigned n=0;n<sizeof(faultbits)/sizeof(*faultbits);n++){reset();h.firmware=1;h.ctx_fault=1u<<faultbits[n];firmware_failed();}
    reset();h.firmware=1;h.ctx_fault=UINT32_MAX;firmware_failed();
    for(unsigned n=1;n<=8192;n+=257){reset();h.firmware=1;h.fw_read_corrupt=n;firmware_failed();CHECK(!gfw_work.release_attempted);}
    reset();h.firmware=1;h.core_irq=1;firmware_failed();CHECK(!h.maps&&!h.engine_calls&&!h.fw_stores);
    reset();h.firmware=1;h.gx_on=1;firmware_failed();CHECK(!h.engine_calls);
    printf("GMU firmware board: %u real callback/map/copy/phase/IRQ/fault cases PASS (typed engine seam, no hardware ACKs)\n",cases-first);
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
    reset();h.smmu_fail=1;failed();CHECK(!h.nc_maps&&!h.impl_lines);reset();h.smmu_fail=2;failed();CHECK(h.diag_lines==2&&h.impl_lines==1);
    reset();h.smmu_fail=3;failed();CHECK(h.diag_lines==2&&h.impl_lines==1&&h.atos_lines==1);
    reset();h.alloc_fail=1;failed();CHECK(h.allocs==1&&!h.frees);
    reset();h.corrupt=1;failed();CHECK(h.allocs==1&&h.frees==1);
    reset();h.expire=10;failed();
    for(unsigned i=1;i<=budgets;i++){reset();h.budget_fail=i;failed();}
    printf("GMU actual board adapter: %u mapping/owner/reset/budget/failure cases PASS\n",cases);
    firmware_cases();
}
