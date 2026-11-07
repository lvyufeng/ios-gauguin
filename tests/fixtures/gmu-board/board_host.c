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
        fw_read_corrupt,fw_fail_phase,fw_stop_at,fw_steps,fw_stores,fw_forbidden,diag_lines,impl_lines,atos_lines,ctx_fault,fw_diag_lines,fw_impl_lines,fw_pdc_lines,fw_ao_lines,fw_cm3_lines,fw_bootcfg_lines,fw_reply_lines,fw_word_lines,
        perf_mode,perf_engine_calls,perf_complete_lines,perf_partial_lines,
        bw_mode,bw_engine_calls,bw_complete_lines,bw_partial_lines,test_complete_lines,test_partial_lines,dcvs_mode,dcvs_engine_calls,dcvs_request_lines,dcvs_complete_lines,dcvs_partial_lines,dcvs_missing,
        gpu_mode,gpu_context_calls,gpu_context_fail,gpu_smc_calls,gpu_smc_mode,gpu_drift,gpu_complete_lines,gpu_partial_lines,gpu_ap_complete_lines;} h;
static unsigned cases;
#define CHECK(x) do {if(!(x)){fprintf(stderr,"GMU board failure case%u line%d\n",cases,__LINE__);abort();}}while(0)
static const uint64_t owner=UINT64_C(0xaa200000);
static int host_printf(const char *s,...)
{
    char text[256];va_list ap;va_start(ap,s);int n=vsnprintf(text,sizeof(text),s,ap);va_end(ap);
    CHECK(n>0&&(unsigned)n<sizeof(text));
    if(strstr(text,"SWEET GPU SMMU: complete")){CHECK(h.gpu_mode&&h.live&&!h.quarantine&&h.gpu_complete_lines++==0);}
    if(strstr(text,"SWEET GPU SMMU: partial")){CHECK(h.gpu_mode&&!h.live&&h.quarantine==1);++h.gpu_partial_lines;}
    if(strstr(text,"SWEET GPU APERTURE: complete")){CHECK(h.gpu_mode&&h.gpu_complete_lines==1&&h.live&&!h.quarantine);++h.gpu_ap_complete_lines;}
    if(strstr(text,"SWEET GMU PERF: complete")){
        CHECK(h.perf_mode&&h.perf_engine_calls==1&&h.live&&!h.quarantine&&h.perf_complete_lines++==0);
        CHECK(!strcmp(text,"SWEET GMU PERF: complete request=00302b04 words=43 ack=0002047e/00300000/00000000; no BW/TEST/normal HFI_ON/GPU/Metal qualification\n"));
    }
    if(strstr(text,"SWEET GMU PERF: partial")){
        CHECK(h.perf_mode&&h.quarantine==1&&!h.live&&h.perf_partial_lines++==0);
    }
    if(strstr(text,"SWEET GMU BW: complete")){
        CHECK(h.bw_mode&&h.bw_engine_calls==1&&h.live&&!h.quarantine&&h.bw_complete_lines++==0&&h.perf_complete_lines==1);
        CHECK(!strcmp(text,"SWEET GMU BW: complete request=0040a003 words=160 levels=13 cnoc=1 ddr=3 waits=00000000/00000000 ack=0002047e/00400000/00000000\n"));
    }
    if(strstr(text,"SWEET GMU TEST: complete")){
        CHECK(h.bw_mode&&h.bw_engine_calls==1&&h.live&&!h.quarantine&&h.test_complete_lines++==0&&h.bw_complete_lines==1);
        CHECK(!strcmp(text,"SWEET GMU TEST: complete request=00500105 words=1 ack=0002047e/00500000/00000000; native legacy startup only\n"));
    }
    if(strstr(text,"SWEET GMU BW: partial"))CHECK(h.bw_mode&&h.quarantine==1&&!h.live&&h.bw_partial_lines++==0);
    if(strstr(text,"SWEET GMU TEST: partial"))CHECK(h.bw_mode&&h.quarantine==1&&!h.live&&h.test_partial_lines++==0);
    if(strstr(text,"SWEET GMU DCVS: request")){
        CHECK(h.dcvs_mode&&h.dcvs_engine_calls==1&&h.live&&!h.quarantine&&h.dcvs_request_lines++==0&&h.test_complete_lines==1);
        CHECK(!strcmp(text,"SWEET GMU DCVS: request perf_index=1 hz=253000000 bw_index=5 Bps=2188000000 option=00000000 perf=30000001 bw=00005005; requested, not measured\n"));
    }
    if(strstr(text,"SWEET GMU DCVS: complete")){
        CHECK(h.dcvs_mode&&h.dcvs_engine_calls==1&&h.live&&!h.quarantine&&h.dcvs_complete_lines++==0&&h.dcvs_request_lines==1);
        CHECK(!strcmp(text,"SWEET GMU DCVS: complete before=00000000 ack=80000000 cleared=00000000 return=00000000; native register/OOB request only\n"));
    }
    if(strstr(text,"SWEET GMU DCVS: partial"))CHECK(h.dcvs_mode&&h.quarantine==1&&!h.live&&h.dcvs_partial_lines++<2);
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
    if(strstr(text,"SWEET GMU AO MASK:")){
        CHECK(h.fw_ao_lines++==0);
        CHECK(!strcmp(text,"SWEET GMU AO MASK: off=02c18 requested=ffffffff readback=0000003f checked_mask=0000003b policy=native-write; other bits unqualified\n"));
        CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU CM3 CFG:")){
        CHECK(h.fw_cm3_lines++==0);
        CHECK(!strcmp(text,"SWEET GMU CM3 CFG: off=020b4 requested=00004052 readback=00000052 checked_mask=00000200 expected=00000000 policy=native-write; other bits unqualified\n"));
        CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU BOOT CFG:")){
        unsigned index=h.fw_bootcfg_lines++;CHECK(index<3&&h.fw_cm3_lines==1&&h.fw_ao_lines==1);
        static const unsigned offsets[]={0x103c,0x1000,0x1004};
        static const uint32_t raw[]={0,0,0x80000001};char expected[192];
        snprintf(expected,sizeof(expected),"SWEET GMU BOOT CFG: off=%05x requested=00000001 readback=%08x policy=native-write; equality unqualified\n",offsets[index],raw[index]);
        CHECK(!strcmp(text,expected));CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU HFI REPLY:")){
        CHECK(h.quarantine==1&&!h.live&&h.fw_reply_lines++==0&&h.fw_bootcfg_lines==3);
        const char *expected=h.engine_fail==17?
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=0040a003 expected=3 words=3 captured=3\n":h.engine_fail==19?
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=00500105 expected=3 words=3 captured=3\n":h.engine_fail==14?
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=00302b04 expected=3 words=3 captured=3\n":h.engine_fail==13?
            "SWEET GMU HFI REPLY: phase=5 site=1 reason=7 queue=2 request=00100500 expected=3 words=0 captured=0\n":
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=00100500 expected=3 words=19 captured=19\n";
        CHECK(!strcmp(text,expected));
    }
    if(strstr(text,"SWEET GMU HFI WORD:")){
        unsigned index=h.fw_word_lines++;CHECK(h.quarantine==1&&!h.live&&h.fw_reply_lines==1&&index<19&&(h.engine_fail==12||h.engine_fail==14||h.engine_fail==17||h.engine_fail==19));
        uint32_t raw=(h.engine_fail==17||h.engine_fail==19)?(index==0?0x0002037e:index==1?0x00300000:0):h.engine_fail==14?(index==0?0x0002037e:index==1?0x00200000:0):index==0?0x0012137e:index==1?0x00000500:0xa5000000u+index;char expected[192];
        snprintf(expected,sizeof(expected),"SWEET GMU HFI WORD: index=%u value=%08x\n",index,raw);CHECK(!strcmp(text,expected));
    }
    return n;
}
int ml_get_interrupts_enabled(void){return h.context!=1;}
int ml_at_interrupt_context(void){return h.context==2;}
int get_preemption_level(void){return h.context==3;}
uint64_t mach_absolute_time(void){return h.now;}
void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out){CHECK((n==8||(h.gpu_mode&&n==5))&&scale==NSEC_PER_SEC);*out=h.now+n*scale;}
bool gauguin_wdt_lease_check_budget(uint32_t n)
{
    CHECK(n==3u*32765||n==13u*32765||(h.gpu_mode&&n==10u*32765));++h.budgets;
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
void *IOMalloc(size_t n){CHECK(n==65536||n==16384);++h.allocs;return h.alloc_fail?NULL:malloc(n);}
void IOFree(void *p,size_t n){CHECK((n==65536||n==16384)&&p);++h.frees;free(p);}
void delay(unsigned us){CHECK(us==5||us==10||us==100);}
void IOSleep(unsigned ms){CHECK(h.gpu_mode&&ms==30&&h.gpu_smc_calls&&h.live);h.now+=(uint64_t)ms*1000000;}
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
/* Typed dependency seam; actual policy decoder is exercised in its own suite. */
bool gmf_bw_plan_valid(const struct gmf_bw_plan *p){return p&&p->db[0].address==0x50000&&p->db[3].address==0x50054;}
static uint32_t fw_read32(vm_offset_t address);
static void fw_write32(vm_offset_t address,uint32_t value);
static void host_gpu_smc(void *,struct gpa_registers *);
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
    memset(&ggb_context,0,sizeof(ggb_context));memset(&ggb_plan,0,sizeof(ggb_plan));memset(&ggb_smmu,0,sizeof(ggb_smmu));
    memset(&ggb_aperture,0,sizeof(ggb_aperture));memset(&ggb_secure,0,sizeof(ggb_secure));ggb_deadline=0;ggb_started=0;ggb_result=0;ggb_secure_result=0;
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
    if(address==(uintptr_t)reset_page+0x2650&&value==(1u<<23)){
        CHECK(h.dcvs_mode&&gfw_work.phase==GMF_HANDSHAKE);uint32_t ret=h.engine_fail==23?7:0;memcpy(fw_page[3]+0x6ffc,&ret,4);
    }
    memcpy(p,&value,4);
}
/* Typed engine seam: exercise every actual board callback and both critical
 * ownership transitions. Real GMF sequencing/rings are tested separately by
 * test_gmu_firmware.py; these synthetic receipts are not firmware ACK evidence. */
enum gmf_result gmf_bootstrap_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,struct gmf_receipt *out)
{
    ++h.engine_calls;CHECK(ctx&&p&&out&&gmf_plan_valid(p));
    if(h.gpu_drift==1){uint32_t bad=0;memcpy(smmu+0x8000+4096*ggb_smmu.bank,&bad,4);}
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
    ctx->ao_mask_valid=1;ctx->ao_mask_readback=0x3f;
    if(h.engine_fail==8)return GMF_TIMEOUT;
    ctx->cm3_config_valid=1;ctx->cm3_config_readback=0x52;
    if(h.engine_fail==9)return GMF_TIMEOUT;
    ctx->boot_config_valid=h.engine_fail==10?1u:7u;
    ctx->boot_config_readback[0]=0;ctx->boot_config_readback[1]=0;ctx->boot_config_readback[2]=0x80000001;
    if(h.engine_fail==10||h.engine_fail==11)return GMF_TIMEOUT;
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
    if(h.engine_fail==12||h.engine_fail==13){
        struct gmf_reply_diagnostic *d=&ctx->reply_diagnostic;
        *d=(struct gmf_reply_diagnostic){.valid=1,.phase=GMF_HANDSHAKE,.site=h.engine_fail==13?GMFR_DRAIN:GMFR_REQUEST,.reason=h.engine_fail==13?GMFR_LIMIT:GMFR_ECHO,.queue=h.engine_fail==13?2:1,.request_header=0x00100500,.expected_words=3,.words=h.engine_fail==13?0:19,.captured=h.engine_fail==13?0:19};
        for(unsigned i=0;i<d->captured;i++)d->data[i]=i==0?0x0012137e:i==1?0x00000500:0xa5000000u+i;
        return GMF_ACK;
    }
    CHECK(!o->guard(NULL,GMF_RESET)&&!o->guard(NULL,GMF_DONE+1));
    memset(out,0,sizeof(*out));out->phase=GMF_DONE;out->fw_result=0xbabeface;out->reported_version=0x100b0000;return GMF_OK;
}
enum gmf_result gmf_bootstrap_perf_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,struct gmf_receipt *out)
{
    CHECK(h.perf_mode&&h.perf_engine_calls++==0);ctx->perf_requested=1;
    enum gmf_result rc=gmf_bootstrap_once(ctx,o,p,out);if(rc)return rc;
    ctx->perf_started=1;
    if(h.engine_fail==14){
        ctx->reply_diagnostic=(struct gmf_reply_diagnostic){.valid=1,.phase=GMF_HANDSHAKE,.site=GMFR_REQUEST,.reason=GMFR_ECHO,.queue=1,.request_header=0x00302b04,.expected_words=3,.words=3,.captured=3,.data={0x0002037e,0x00200000,0}};
        return GMF_ACK;
    }
    if(h.engine_fail!=15){ctx->perf_valid=1;ctx->perf_ack[0]=0x0002047e;ctx->perf_ack[1]=0x00300000;}
    if(h.engine_fail==16)h.now=gfw_deadline;
    return GMF_OK;
}
enum gmf_result gmf_bootstrap_bw_test_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmf_receipt *out)
{
    CHECK(h.bw_mode&&h.bw_engine_calls++==0&&gmf_bw_plan_valid(bw));ctx->bw_requested=1;
    enum gmf_result rc=gmf_bootstrap_perf_once(ctx,o,p,out);if(rc)return rc;
    if(!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;
    ctx->bw_started=1;
    if(h.engine_fail==17||h.engine_fail==19){
        unsigned test=h.engine_fail==19;
        if(test){ctx->bw_valid=1;ctx->test_started=1;}
        ctx->reply_diagnostic=(struct gmf_reply_diagnostic){.valid=1,.phase=GMF_HANDSHAKE,.site=GMFR_REQUEST,.reason=GMFR_ECHO,.queue=1,.request_header=test?0x00500105:0x0040a003,.expected_words=3,.words=3,.captured=3,.data={0x0002037e,0x00300000,0}};
        return GMF_ACK;
    }
    ctx->bw_ack[0]=0x0002047e;ctx->bw_ack[1]=0x00400000;
    ctx->bw_valid=h.engine_fail!=18;
    ctx->test_started=1;ctx->test_valid=h.engine_fail!=20;
    ctx->test_ack[0]=0x0002047e;ctx->test_ack[1]=0x00500000;
    if(h.engine_fail==21)h.now=gfw_deadline;
    return GMF_OK;
}
enum gmf_result gmf_bootstrap_dcvs_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmf_receipt *out)
{
    CHECK(h.dcvs_mode&&h.dcvs_engine_calls++==0);ctx->dcvs_requested=1;
    enum gmf_result rc=gmf_bootstrap_bw_test_once(ctx,o,p,bw,out);if(rc)return rc;
    if(!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;ctx->dcvs_started=1;
    const unsigned window[]={GMF_TCM,GMF_TCM,GMF_TCM,GMF_CSR,GMF_CSR,GMF_CSR};
    const uint32_t off[]={0x6ff0,0x6ff4,0x6ff8,0x2650,0x2644,0x2650};
    const uint32_t value[]={0,0x30000001,0x5005,1u<<23,1u<<31,1u<<31};
    for(unsigned n=0;n<6;n++){
        if(n==3)ctx->dcvs_trigger_attempted=1;
        if(n==4){if(h.engine_fail==22)return GMF_TIMEOUT;ctx->dcvs_ack_valid=1;ctx->dcvs_ack=0x80000000;}
        if(n==5){if(!o->read(NULL,GMF_TCM,0x6ffc,&ctx->dcvs_return))return GMF_IO;ctx->dcvs_return_valid=1;ctx->dcvs_clear_attempted=1;}
        if(!o->guard(NULL,GMF_HANDSHAKE)||!o->barrier(NULL)||!o->write(NULL,(enum gmf_window)window[n],off[n],value[n])||!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;
    }
    if(ctx->dcvs_return)return GMF_DCVS_RESULT;
    ctx->dcvs_valid=h.engine_fail!=24;
    if(h.dcvs_missing){uint32_t *flag[]={&ctx->dcvs_requested,&ctx->dcvs_started,&ctx->dcvs_trigger_attempted,&ctx->dcvs_ack_valid,&ctx->dcvs_return_valid,&ctx->dcvs_clear_attempted,&ctx->dcvs_valid};
        CHECK(h.dcvs_missing<=8);if(h.dcvs_missing==8)ctx->dcvs_return=1;else *flag[h.dcvs_missing-1]=0;}
    if(h.engine_fail==25)h.now=gfw_deadline;
    if(h.gpu_drift==2){uint32_t bad=0x20000;memcpy(smmu+0xc00+4*ggb_smmu.slot,&bad,4);}
    return GMF_OK;
}
static enum gmb_result firmware_run(struct gmb_firmware_receipt *out)
{struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;struct gmf_bw_plan bw={0};bw.db[0].address=0x50000;bw.db[3].address=0x50054;return h.gpu_mode?sweet_gmu_firmware_gpu_once(&s,&p,&bw,out):h.dcvs_mode?sweet_gmu_firmware_dcvs_once(&s,&p,&bw,out):h.bw_mode?sweet_gmu_firmware_bw_test_once(&s,&p,&bw,out):h.perf_mode?sweet_gmu_firmware_perf_once(&s,&p,out):sweet_gmu_firmware_once(&s,&p,out);}
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
    CHECK(h.impl_lines==1&&!h.fw_reply_lines&&!h.fw_word_lines);
    CHECK(out.reset==0&&out.release_attempted==1&&out.oob_attempted==1&&out.phase==GMF_DONE&&h.allow_gx);
    CHECK(out.firmware.fw_result==0xbabeface&&out.asset_pa==0xb0000000&&h.fw_impl_lines==3&&h.fw_pdc_lines==6&&h.fw_ao_lines==1&&h.fw_cm3_lines==1&&h.fw_bootcfg_lines==3);
    CHECK(out.fsr[0]==0x400&&out.fsr[1]==0x400);
    CHECK(sweet_gmu_firmware_state()==GMB_READY&&sweet_gmu_board_state()==GMB_READY);
    unsigned budgets=h.budgets,maps=h.maps;CHECK(firmware_run(&out)==GMB_ALREADY&&h.budgets==budgets&&h.maps==maps);
    for(unsigned n=1;n<=2;n++){reset();h.firmware=1;h.asset_fail=n;firmware_failed();if(n==1)CHECK(!h.maps&&!h.fw_stores);}
    for(unsigned n=3;n<=7;n++){reset();h.firmware=1;h.map_fail=n;firmware_failed();CHECK(!h.engine_calls);reset();h.firmware=1;h.misalign=n;firmware_failed();}
    for(unsigned n=1;n<=4;n++){reset();h.firmware=1;h.engine_fail=n;firmware_failed();CHECK(gfw_work.release_attempted==(n>=2));CHECK(gfw_work.oob_attempted==(n>=3));}
    reset();h.firmware=1;h.engine_fail=5;firmware_failed();CHECK(h.fw_diag_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=6;firmware_failed();CHECK(h.fw_impl_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=7;firmware_failed();CHECK(h.fw_impl_lines==3&&h.fw_pdc_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=8;firmware_failed();CHECK(h.fw_ao_lines==1&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=9;firmware_failed();CHECK(h.fw_cm3_lines==1&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=10;firmware_failed();CHECK(h.fw_bootcfg_lines==1&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=11;firmware_failed();CHECK(h.fw_bootcfg_lines==3&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=12;firmware_failed();CHECK(h.fw_reply_lines==1&&h.fw_word_lines==19&&gfw_work.release_attempted&&gfw_work.oob_attempted);
    reset();h.firmware=1;h.engine_fail=13;firmware_failed();CHECK(h.fw_reply_lines==1&&!h.fw_word_lines&&gfw_work.release_attempted&&gfw_work.oob_attempted);
    for(unsigned n=1;n<=24;n++){reset();h.firmware=1;h.fw_fail_phase=n;firmware_failed();}
    const unsigned faultbits[]={1,2,3,4,5,6,7,8,30,31};
    for(unsigned n=0;n<sizeof(faultbits)/sizeof(*faultbits);n++){reset();h.firmware=1;h.ctx_fault=1u<<faultbits[n];firmware_failed();}
    reset();h.firmware=1;h.ctx_fault=UINT32_MAX;firmware_failed();
    for(unsigned n=1;n<=8192;n+=257){reset();h.firmware=1;h.fw_read_corrupt=n;firmware_failed();CHECK(!gfw_work.release_attempted);}
    reset();h.firmware=1;h.core_irq=1;firmware_failed();CHECK(!h.maps&&!h.engine_calls&&!h.fw_stores);
    reset();h.firmware=1;h.gx_on=1;firmware_failed();CHECK(!h.engine_calls);
    printf("GMU firmware board: %u real callback/map/copy/phase/IRQ/fault cases PASS (typed engine seam, no hardware ACKs)\n",cases-first);
}
/* Typed SMMU engine seam: actual transaction/ATOS is covered separately.
 * This exercises the real board NC publisher, retained aliases and guards. */
enum gsm_result ggs_configure_once(struct ggs_context *c,const struct ggs_ops *o,
    const struct ggp_plan *p,const struct gsm_receipt *gmu,struct ggs_receipt *out)
{
    CHECK(h.gpu_mode&&h.gpu_context_calls++==0&&h.live&&!h.engine_calls&&!h.gpu_smc_calls);
    CHECK(gmu==&gmb_work.smmu&&p->owner_pa==owner&&ggp_plan_valid(p));
    c->state=1;c->phase=GGS_PREPARE;c->ops=*o;c->plan=*p;c->gmu=*gmu;
    if(h.gpu_context_fail==1)return GSM_INHERITED;
    struct ggp_s1_config cfg;
    if(!o->guard(NULL)||!o->prepare(NULL,39,36,&cfg)||!o->guard(NULL))return GSM_IO;
    CHECK(h.nc_maps==1&&h.maps==2&&cfg.ttbr0==owner+0x9c000&&cfg.ttbr1==owner+0x9f000);
    CHECK(h.allocs==2&&h.frees==2);
    if(h.gpu_context_fail==2)return GSM_READBACK;
    struct ggs_receipt s={.slot=0,.bank=3,.asid=4,.ias=39,.oas=36,.groups=128,.banks=8,.stream_match=1,
        .cr0=gmu->cr0_after,.micro_before=gmu->micro_after,.micro_after=gmu->micro_after,
        .smr=0x80000000,.s2cr=3,.sctlr=0xc01167,.tcr=(uint32_t)cfg.tcr,.tcr2=(uint32_t)(cfg.tcr>>32)|0x38010,
        .mair0=cfg.mair0,.mair1=cfg.mair1,.writes=200,.polls=169,.gpu_pages=18,.gmu_pages=131,.translations=168,
        .ttbr0=cfg.ttbr0|UINT64_C(4)<<48,.ttbr1=cfg.ttbr1|UINT64_C(4)<<48};
    const unsigned offs[]={0xb000,0xb004,0xb010,0xb030,0xb038,0xb03c,0x100c,0x180c,0x800,0xc00};
    const uint32_t vals[]={s.sctlr,0x70000000,s.tcr2,s.tcr,s.mair0,s.mair1,0x1f300,1,s.smr,s.s2cr};
    for(unsigned i=0;i<10;i++)memcpy(smmu+offs[i],&vals[i],4);
    memcpy(smmu+0xb020,&s.ttbr0,8);memcpy(smmu+0xb028,&s.ttbr1,8);
    c->work=s;*out=s;c->phase=GGS_DONE;c->state=2;return GSM_OK;
}
static void host_gpu_smc(void *cookie,struct gpa_registers *r)
{
    CHECK(!cookie&&h.gpu_mode&&h.live&&!h.quarantine&&!h.engine_calls&&ggb_context_valid());
    uint32_t reset;memcpy(&reset,reset_page+0x2000,4);CHECK(reset==1&&!h.gx_on);
    ++h.gpu_smc_calls;
    if(h.gpu_smc_calls==1||h.gpu_smc_mode!=2){
        const uint64_t want[]={0x42000c1b,4,0xffff0003,0xffffffff,0xffffffff,0xffffffff,0};CHECK(!memcmp(r->x,want,sizeof(want)));
    }else CHECK(r->x[0]==1&&r->x[6]==0x619);
    r->x[0]=h.gpu_smc_mode==1?UINT64_C(0xfffffffffffffffe):h.gpu_smc_mode==2&&h.gpu_smc_calls==1?1:0;
    r->x[1]=0x111;r->x[6]=0x619; /* native CP callsite does not require x1==0 */
    if(h.gpu_smc_mode==3){uint32_t bad=0;memcpy(smmu+0xb000,&bad,4);}
}
static void firmware_perf_cases(void)
{
    unsigned first=cases;
    reset();h.firmware=h.perf_mode=1;struct gmb_firmware_receipt out;
    CHECK(firmware_run(&out)==GMB_OK&&h.perf_engine_calls==1&&h.engine_calls==1&&h.perf_complete_lines==1&&!h.perf_partial_lines);
    CHECK(out.phase==GMF_DONE&&h.maps==7&&h.nc_maps==1&&!h.quarantine);
    struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;
    unsigned budgets=h.budgets,stores=h.fw_stores,maps=h.maps;
    CHECK(sweet_gmu_firmware_once(&s,&p,&out)==GMB_ALREADY&&firmware_run(&out)==GMB_ALREADY);
    CHECK(h.budgets==budgets&&h.fw_stores==stores&&h.maps==maps&&h.perf_complete_lines==1);
    for(unsigned n=1;n<=16;n++){reset();h.firmware=h.perf_mode=1;h.engine_fail=n;firmware_failed();CHECK(h.perf_partial_lines==1&&!h.perf_complete_lines);}
    for(unsigned n=1;n<=24;n++){reset();h.firmware=h.perf_mode=1;h.fw_fail_phase=n;firmware_failed();CHECK(!h.perf_complete_lines);}
    for(unsigned n=3;n<=7;n++){reset();h.firmware=h.perf_mode=1;h.map_fail=n;firmware_failed();CHECK(!h.perf_engine_calls&&!h.perf_partial_lines);}
    for(unsigned n=1;n<=2;n++){reset();h.firmware=h.perf_mode=1;h.asset_fail=n;firmware_failed();CHECK(!h.perf_complete_lines);}
    reset();h.firmware=1;CHECK(firmware_run(&out)==GMB_OK&&!h.perf_engine_calls&&!h.perf_complete_lines);
    budgets=h.budgets;maps=h.maps;CHECK(sweet_gmu_firmware_perf_once(&s,&p,&out)==GMB_ALREADY&&h.budgets==budgets&&h.maps==maps);
    printf("GMU PERF board: %u shared lifecycle, dependency/refusal/guard and post-quarantine logging cases PASS (typed engine seam)\n",cases-first);
}
static void firmware_bw_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out,before;
    reset();h.firmware=h.perf_mode=h.bw_mode=1;
    CHECK(firmware_run(&out)==GMB_OK&&h.bw_engine_calls==1&&h.perf_engine_calls==1&&h.engine_calls==1);
    CHECK(h.perf_complete_lines==1&&h.bw_complete_lines==1&&h.test_complete_lines==1&&!h.bw_partial_lines&&!h.test_partial_lines);
    CHECK(out.phase==GMF_DONE&&h.maps==7&&h.nc_maps==1&&!h.quarantine);
    struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;
    struct gmf_bw_plan bw={0};bw.db[0].address=0x50000;bw.db[3].address=0x50054;
    unsigned budgets=h.budgets,stores=h.fw_stores,maps=h.maps;
    CHECK(sweet_gmu_firmware_once(&s,&p,&out)==GMB_ALREADY&&sweet_gmu_firmware_perf_once(&s,&p,&out)==GMB_ALREADY&&firmware_run(&out)==GMB_ALREADY);
    CHECK(h.budgets==budgets&&h.fw_stores==stores&&h.maps==maps&&h.test_complete_lines==1);
    for(unsigned n=1;n<=21;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.engine_fail=n;firmware_failed();
        CHECK(h.bw_partial_lines==1&&h.test_partial_lines==1&&!h.perf_complete_lines&&!h.bw_complete_lines&&!h.test_complete_lines);
    }
    for(unsigned n=1;n<=24;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.fw_fail_phase=n;firmware_failed();
        CHECK(!h.perf_complete_lines&&!h.bw_complete_lines&&!h.test_complete_lines);
    }
    for(unsigned n=3;n<=7;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.map_fail=n;firmware_failed();
        CHECK(!h.bw_engine_calls&&!h.bw_partial_lines&&!h.test_partial_lines);
    }
    for(unsigned n=1;n<=2;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.asset_fail=n;firmware_failed();CHECK(!h.bw_complete_lines&&!h.test_complete_lines);
    }
    reset();h.firmware=h.perf_mode=h.bw_mode=1;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,NULL,&out)==GMB_ARGUMENT);
    bw.db[3].address^=4;CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ARGUMENT);
    CHECK(!gfw_lifecycle&&!h.maps&&!h.budgets&&!h.engine_calls&&!memcmp(&out,&before,sizeof(out)));
    reset();h.firmware=1;CHECK(firmware_run(&out)==GMB_OK&&!h.bw_engine_calls&&!h.bw_complete_lines&&!h.test_complete_lines);
    bw.db[3].address^=4;CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ALREADY);
    reset();h.firmware=h.perf_mode=1;CHECK(firmware_run(&out)==GMB_OK&&!h.bw_engine_calls&&!h.bw_complete_lines&&!h.test_complete_lines);
    CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ALREADY);
    printf("GMU BW/TEST board: %u shared ownership/once-state, prerequisites, ACK/guard refusals, post-quarantine partial and final-only completion cases PASS (typed seams)\n",cases-first);
}
static void firmware_dcvs_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out,before;
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;
    CHECK(firmware_run(&out)==GMB_OK&&h.dcvs_engine_calls==1&&h.bw_engine_calls==1&&h.perf_engine_calls==1&&h.engine_calls==1);
    CHECK(h.dcvs_request_lines==1&&h.dcvs_complete_lines==1&&!h.dcvs_partial_lines&&h.test_complete_lines==1&&out.phase==GMF_DONE&&!h.quarantine);
    struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;
    struct gmf_bw_plan bw={0};bw.db[0].address=0x50000;bw.db[3].address=0x50054;
    unsigned stores=h.fw_stores,maps=h.maps,budgets=h.budgets;
    CHECK(sweet_gmu_firmware_once(&s,&p,&out)==GMB_ALREADY&&sweet_gmu_firmware_perf_once(&s,&p,&out)==GMB_ALREADY&&sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ALREADY&&firmware_run(&out)==GMB_ALREADY);
    CHECK(h.fw_stores==stores&&h.maps==maps&&h.budgets==budgets&&h.dcvs_complete_lines==1);
    for(unsigned n=1;n<=25;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.engine_fail=n;firmware_failed();
        CHECK(h.dcvs_partial_lines==2&&!h.dcvs_request_lines&&!h.dcvs_complete_lines&&!h.test_complete_lines);
    }
    for(unsigned n=1;n<=8;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.dcvs_missing=n;firmware_failed();
        CHECK(!h.dcvs_complete_lines&&!h.dcvs_request_lines);
    }
    for(unsigned n=1;n<=24;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.fw_fail_phase=n;firmware_failed();CHECK(!h.dcvs_complete_lines);
    }
    for(unsigned n=3;n<=7;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.map_fail=n;firmware_failed();CHECK(!h.dcvs_engine_calls&&!h.dcvs_partial_lines);
    }
    for(unsigned n=1;n<=2;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.asset_fail=n;firmware_failed();CHECK(h.dcvs_engine_calls==n-1&&h.dcvs_partial_lines==2*(n-1)&&!gfw_context.dcvs_started);
    }
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(sweet_gmu_firmware_dcvs_once(&s,&p,NULL,&out)==GMB_ARGUMENT);
    bw.db[3].address^=4;CHECK(sweet_gmu_firmware_dcvs_once(&s,&p,&bw,&out)==GMB_ARGUMENT);bw.db[3].address^=4;
    CHECK(!gfw_lifecycle&&!h.maps&&!h.budgets&&!memcmp(&out,&before,sizeof(out)));
    for(unsigned mode=0;mode<3;mode++){
        reset();h.firmware=1;h.perf_mode=mode>0;h.bw_mode=mode>1;
        CHECK(firmware_run(&out)==GMB_OK&&!h.dcvs_engine_calls&&!h.dcvs_request_lines&&!h.dcvs_complete_lines);
        CHECK(sweet_gmu_firmware_dcvs_once(&s,&p,&bw,&out)==GMB_ALREADY);
    }
    printf("GMU DCVS board: %u native mailbox callback/owner/receipt/guard/four-entry once-state and quarantine cases PASS (typed engine seams)\n",cases-first);
}
static void firmware_gpu_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out;
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;
    CHECK(firmware_run(&out)==GMB_OK&&h.gpu_context_calls==1&&h.gpu_smc_calls==1&&h.engine_calls==1);
    CHECK(h.gpu_complete_lines==1&&h.gpu_ap_complete_lines==1&&!h.gpu_partial_lines&&h.maps==7&&h.nc_maps==1);
    unsigned budgets=h.budgets,owners=h.owner_calls,translations=h.translations,pmaps=h.pmap_calls;
    CHECK(ggb_secure.returned.x[1]==0x111&&ggb_secure.returned.x[0]==0&&ggb_secure.calls==1);
    for(unsigned n=0;n<16384;n++)CHECK(ram[n]==0xa5);
    for(unsigned n=GGP_ARENA_END;n<sizeof(ram);n++)CHECK(ram[n]==0xa5);
    struct ggm_plan old;CHECK(ggm_plan_build(owner,&old));
    for(unsigned n=0;n<GGM_COUNT;n++)if(n!=GGM_HFI)for(unsigned j=0;j<old.region[n].reserved;j++)CHECK(ram[old.region[n].offset+j]==0);
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_smc_mode=2;
    CHECK(firmware_run(&out)==GMB_OK&&h.gpu_smc_calls==2&&ggb_secure.continuations==1);
    for(unsigned n=1;n<=2;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_context_fail=n;firmware_failed();CHECK(!h.gpu_smc_calls&&!h.engine_calls&&!h.gpu_complete_lines&&h.gpu_partial_lines==1);}
    for(unsigned n=1;n<=3;n+=2){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_smc_mode=n;firmware_failed();CHECK(h.gpu_smc_calls==1&&!h.engine_calls&&!h.gpu_complete_lines);}
    for(unsigned n=1;n<=2;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_drift=n;firmware_failed();CHECK(h.gpu_smc_calls==1&&!h.gpu_complete_lines&&!h.gpu_ap_complete_lines);}
    for(unsigned n=1;n<=budgets;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.budget_fail=n;firmware_failed();CHECK(!h.gpu_complete_lines&&!h.gpu_ap_complete_lines);}
    for(unsigned n=1;n<=owners;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.owner_fail=n;firmware_failed();}
    for(unsigned n=1;n<=translations;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.fail_translation=n;firmware_failed();}
    for(unsigned n=1;n<=pmaps;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.pmap_fail=n;firmware_failed();reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.attr_fail=n;firmware_failed();}
    printf("GPU context board: %u retained-alias/NC-publication/SCM-order/continuation/owner/budget/translation/attribute/final-drift cases PASS (typed SMMU/SMC seams, actual aperture engine)\n",cases-first);
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
    firmware_perf_cases();
    firmware_bw_cases();
    firmware_dcvs_cases();
    firmware_gpu_cases();
}
