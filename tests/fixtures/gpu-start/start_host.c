#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_start.h"
static unsigned assertions;
#define CHECK(x) do{++assertions;if(!(x)){fprintf(stderr,"GPU start line%d\n",__LINE__);abort();}}while(0)
struct fake {
    struct ggx_context context;struct ggx_ops ops;struct ggp_plan plan;struct ggs_receipt gpu;
    uint32_t smmu[16384],info,status,status3,step,fail,writes,opened,delays;
    unsigned slow_tlb,slow_ack,stuck_tlb,missing_ack,sticky_ack,root_drift,ignore_context,open_fail;
    unsigned allones_window,allones_off,allones,request,nested;uint32_t hum,dora;
};
static bool tick(struct fake *f){return ++f->step!=f->fail;}
static bool guard(void *p,enum ggx_phase phase)
{
    struct fake *f=p;CHECK(phase>=GGX_CAPTURE&&phase<=GGX_FINAL);
    if(f->nested){
        f->nested=0;struct ggx_receipt out;memset(&out,0xa5,sizeof(out));struct ggx_receipt old=out;
        unsigned step=f->step;CHECK(ggx_start_once(&f->context,&f->ops,&f->plan,&f->gpu,&out)==GGX_ALREADY);
        CHECK(step==f->step&&!memcmp(&out,&old,sizeof(out)));
    }
    return tick(f);
}
static bool read32(void *p,enum ggx_window w,uint32_t off,uint32_t *v)
{
    struct fake *f=p;if(!tick(f))return false;unsigned cb=0x8000+4096*f->gpu.bank;
    if(w==GGX_SMMU){
        CHECK(off==0x6800||off==0x64a0||off==cb||off==cb+0x34||off==cb+0x7f4);
        if(off==0x6800)*v=f->hum;
        else if(off==0x64a0)*v=f->dora;
        else if(off==cb+0x7f4){CHECK(f->writes==6);*v=f->stuck_tlb||f->slow_tlb?1:0;if(f->slow_tlb)f->slow_tlb--;}
        else *v=f->smmu[off/4];
    }else if(w==GGX_CSR){
        CHECK(off==0x2648);
        if(f->request&&f->writes==7&&!f->missing_ack){if(f->slow_ack)f->slow_ack--;else f->info|=1u<<24;}
        *v=f->info;
    }else{CHECK(w==GGX_CORE&&f->opened&&f->writes==8&&!(f->info&(1u<<24)));CHECK(off==0x840||off==0x84c);*v=off==0x840?f->status:f->status3;}
    if(f->allones&&f->allones_window==(unsigned)w&&f->allones_off==off)*v=UINT32_MAX;
    return true;
}
static void write_event(struct fake *f,unsigned width,enum ggx_window w,unsigned off,uint64_t value)
{
    unsigned cb=0x8000+4096*f->gpu.bank;
    const unsigned widths[]={32,32,64,32,32,32,32,32};
    const unsigned windows[]={GGX_SMMU,GGX_SMMU,GGX_SMMU,GGX_SMMU,GGX_SMMU,GGX_SMMU,GGX_CSR,GGX_CSR};
    const unsigned offsets[]={0x6800,0x64a0,cb+0x20,cb+0x34,cb+0x618,cb+0x7f0,0x2650,0x2644};
    const uint64_t values[]={2,1,f->gpu.ttbr0,0,1,0,1u<<16,1u<<24};
    CHECK(f->writes<8&&width==widths[f->writes]&&(unsigned)w==windows[f->writes]&&off==offsets[f->writes]&&value==values[f->writes]);++f->writes;
}
static bool write32(void *p,enum ggx_window w,uint32_t off,uint32_t v)
{
    struct fake *f=p;if(!tick(f))return false;write_event(f,32,w,off,v);
    if(w==GGX_SMMU){if(!(f->ignore_context&&(off&0xfff)==0x34))f->smmu[off/4]=v;}
    else if(off==0x2650){CHECK(f->context.work.request_attempted);f->request=1;}
    else{CHECK(f->context.work.ack_valid&&f->context.work.ack_clear_attempted&&f->info&(1u<<24));if(!f->sticky_ack)f->info&=~v;}
    return true;
}
static bool read64(void *p,uint32_t off,uint64_t *v)
{
    struct fake *f=p;if(!tick(f))return false;CHECK(off==0x8000+4096*f->gpu.bank+0x20);memcpy(v,f->smmu+off/4,8);
    if(f->root_drift&&f->writes>=3)*v^=4096;
    return true;
}
static bool write64(void *p,uint32_t off,uint64_t v)
{struct fake *f=p;if(!tick(f))return false;write_event(f,64,GGX_SMMU,off,v);memcpy(f->smmu+off/4,&v,8);return true;}
static bool barrier(void *p){return tick(p);}
static bool delay(void *p,unsigned us)
{struct fake *f=p;CHECK(us==100);if(!tick(f))return false;++f->delays;return true;}
static bool open_core(void *p)
{
    struct fake *f=p;CHECK(f->context.phase==GGX_CORE_MAP&&f->writes==8&&!f->opened&&!(f->info&(1u<<24)));
    if(!tick(f)||f->open_fail)return false;f->opened=1;return true;
}
static struct fake *fresh(unsigned bank)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan gm;
    CHECK(ggm_plan_build(0xaa200000,&gm)&&ggp_plan_build(&gm,&f->plan));
    f->gpu=(struct ggs_receipt){.bank=bank,.banks=bank+1,.groups=5,.slot=2,.asid=bank+1,.stream_match=1,
        .sctlr=0xc01167,.smr=0x80000000,.s2cr=bank,.gpu_pages=18,.gmu_pages=131,.translations=168,
        .ttbr0=(f->plan.owner_pa+0x9c000)|((uint64_t)(bank+1)<<48),.ttbr1=(f->plan.owner_pa+0x9f000)|((uint64_t)(bank+1)<<48)};
    unsigned cb=0x8000+4096*bank;f->smmu[cb/4]=f->gpu.sctlr;f->smmu[(cb+0x34)/4]=0x4444;memcpy(f->smmu+(cb+0x20)/4,&f->gpu.ttbr0,8);
    f->info=1u<<30;f->hum=0x12345678;f->dora=0;f->status=0x12340000;f->status3=0;
    f->ops=(struct ggx_ops){f,guard,read32,write32,read64,write64,barrier,delay,open_core};return f;
}
static enum ggx_result run(struct fake *f,struct ggx_receipt *out)
{return ggx_start_once(&f->context,&f->ops,&f->plan,&f->gpu,out);}
static void stopped(struct fake *f)
{
    unsigned step=f->step,writes=f->writes;struct ggx_receipt r;
    CHECK(run(f,&r)==GGX_ALREADY&&f->step==step&&f->writes==writes);
}
static void rejected(struct fake *f,enum ggx_result expected)
{
    struct ggx_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
    CHECK(run(f,&out)==expected&&f->context.state==3&&!memcmp(&out,&old,sizeof(out)));stopped(f);
}
static void good(void)
{
    for(unsigned bank=2;bank<8;bank++){
        struct fake *f=fresh(bank);f->nested=1;f->slow_tlb=2;f->slow_ack=3;struct ggx_receipt out;
        CHECK(run(f,&out)==GGX_OK&&f->context.state==2&&f->context.phase==GGX_DONE);
        CHECK(out.bank==bank&&out.asid==bank+1&&out.writes32==7&&out.writes64==1&&out.tlb_polls==3&&out.oob_polls==4);
        CHECK(out.oob_before==(1u<<30)&&out.oob_ack==((1u<<30)|(1u<<24))&&out.oob_cleared==(1u<<30));
        CHECK(out.hum==0x12345678&&!out.dora&&out.core_opened&&out.request_retained&&out.status==f->status&&!out.status3);
        unsigned steps=f->step;stopped(f);free(f);
        for(unsigned fail=1;fail<=steps;fail++){
            f=fresh(bank);f->nested=1;f->slow_tlb=2;f->slow_ack=3;f->fail=fail;
            struct ggx_receipt r,old;memset(&r,0xa5,sizeof(r));old=r;enum ggx_result rc=run(f,&r);
            CHECK(rc!=GGX_OK&&f->step==fail&&f->context.state==3&&!memcmp(&r,&old,sizeof(r)));stopped(f);free(f);
        }
        printf("GPU start CB%u: native MMU/OOB writes, delayed TLB/ACK, raw core reads, all%u callback failures PASS\n",bank,steps);
    }
}
static void failures(void)
{
    struct fake *f=fresh(2);f->info|=1u<<24;rejected(f,GGX_STALE_ACK);CHECK(!f->writes&&!f->opened);free(f);
    f=fresh(2);f->info|=0x8000;rejected(f,GGX_FAULT);CHECK(!f->writes);free(f);
    f=fresh(2);f->stuck_tlb=1;rejected(f,GGX_TIMEOUT);CHECK(f->writes==6&&!f->request&&!f->opened&&f->delays==19999);free(f);
    f=fresh(2);f->missing_ack=1;rejected(f,GGX_TIMEOUT);CHECK(f->writes==7&&f->request&&!f->opened&&f->delays==999);free(f);
    f=fresh(2);f->sticky_ack=1;rejected(f,GGX_READBACK);CHECK(f->writes==8&&!f->opened);free(f);
    f=fresh(2);f->root_drift=1;rejected(f,GGX_READBACK);CHECK(f->writes==4&&!f->request);free(f);
    f=fresh(2);f->ignore_context=1;rejected(f,GGX_READBACK);CHECK(f->writes==4&&!f->request);free(f);
    f=fresh(2);f->open_fail=1;rejected(f,GGX_IO);CHECK(f->writes==8&&!f->opened);free(f);
    for(unsigned n=0;n<4;n++){
        f=fresh(2);f->allones=1;f->allones_window=n==0?GGX_SMMU:n==1?GGX_CSR:GGX_CORE;
        f->allones_off=n==0?0x6800:n==1?0x2648:n==2?0x840:0x84c;rejected(f,GGX_READBACK);free(f);
    }
    for(unsigned n=0;n<5;n++){
        f=fresh(2);if(n==0)f->gpu.ttbr0^=4096;else if(n==1)f->gpu.sctlr=0xc01067;
        else if(n==2)f->gpu.smr=0x80000002;else if(n==3)f->gpu.translations--;else f->gpu.groups=0;
        struct ggx_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
        CHECK(run(f,&out)==GGX_ARGUMENT&&!f->context.state&&!f->step&&!memcmp(&out,&old,sizeof(out)));free(f);
    }
}
static void data_layout(void)
{
    for(unsigned layout=0;layout<4;layout++)for(unsigned pages=17;pages<=20;pages++)for(unsigned atos=167;atos<=172;atos++){
        struct fake *f=fresh(2);f->gpu.layout=layout;f->gpu.gpu_pages=pages;f->gpu.translations=atos;
        struct ggx_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
        bool valid=(layout==GGS_BOOTSTRAP18&&pages==18&&atos==168)||(layout==GGS_DATA19&&pages==19&&atos==171);
        if(valid){CHECK(run(f,&out)==GGX_OK&&out.request_retained&&out.core_opened);stopped(f);}
        else CHECK(run(f,&out)==GGX_ARGUMENT&&!f->context.state&&!f->step&&!memcmp(&out,&old,sizeof(out)));
        free(f);
    }
    puts("GPU start: explicit18/19 layout tags and full page/count mismatch matrix PASS");
}
int main(void)
{good();failures();data_layout();printf("GPU start: %u assertions PASS; no hardware qualification\n",assertions);}
