@GMU_FIXTURE@
#include "gauguin_gpu_smmu.h"
#define SMR(n) (0x800u+4u*(n))
#define S2CR(n) (0xc00u+4u*(n))
struct gpu_fake {struct fake old;struct ggs_context gpu;struct ggp_plan plan;struct gsm_receipt baseline;
    uint8_t tables[16384];unsigned step,fail,writes,prepared,atos,tf_mode,wrong,drift,ignore,stuck;bool nested;};
static struct gpu_fake *templates[3];
static bool gpu_tick(struct gpu_fake *f){return ++f->step!=f->fail;}
static bool gpu_guard(void *cookie)
{
    struct gpu_fake *f=cookie;
    if(f->nested){
        f->nested=false;struct ggs_receipt out,before;memset(&out,0x79,sizeof(out));before=out;
        struct ggs_ops o=f->gpu.ops;
        CHECK(ggs_configure_once(&f->gpu,&o,&f->plan,&f->baseline,&out)==GSM_ALREADY&&!memcmp(&out,&before,sizeof(out)));
    }
    return gpu_tick(f);
}
static bool gpu_r32(void *cookie,uint32_t off,uint32_t *out)
{
    struct gpu_fake *f=cookie;CHECK(off<65536&&!(off&3));if(!gpu_tick(f))return false;
    *out=f->old.regs[off/4];
    if(off>=0x8000&&(off&4095)==0x58){unsigned n=(off-0x8000)/4096;if(f->old.regs[(0x1800+4*n)/4]==1)*out=(*out&~0x600u)|0x400u;}
    if(f->stuck==1&&off==0x6000)*out&=~8u;
    if(f->stuck==2&&off>=0x8000&&(off&4095)==0x7f4)*out=1;
    if(f->stuck==3&&off>=0x8000&&(off&4095)==0x8f0)*out=1;
    return true;
}
static bool gpu_w32(void *cookie,uint32_t off,uint32_t value)
{
    struct gpu_fake *f=cookie;CHECK(off<65536&&!(off&3));if(!gpu_tick(f))return false;++f->writes;
    unsigned n=f->gpu.work.bank,slot=f->gpu.work.slot;
    bool bank=off>=CB(n)&&off<CB(n)+4096;
    bool tf=off>=0x8000&&(off&4095)==0x58&&value==2;
    CHECK(off==0x6000||off==SMR(slot)||off==S2CR(slot)||off==0x1000+4*n||off==0x1800+4*n||bank||tf);
    CHECK(off!=0&&off!=0x48&&off!=0x68&&off!=0x6c&&off!=0x70&&off!=0x6800&&off!=0x64a0);
    if(off==f->ignore)return true;
    if(off==0x6000)f->old.regs[off/4]=(value&~8u)|((value&4)?8u:0);
    else if(off>=0x8000&&(off&4095)==0x58)f->old.regs[off/4]&=~(value&0x800001feu);
    else f->old.regs[off/4]=value;
    return true;
}
static bool gpu_r64(void *cookie,uint32_t off,uint64_t *out)
{struct gpu_fake *f=cookie;CHECK(off<65536&&!(off&7));if(!gpu_tick(f))return false;*out=reg64(&f->old,off);return true;}
static uint64_t gpu_walk(struct gpu_fake *f,unsigned bank,uint32_t va)
{
    CHECK(f->old.regs[0x6000/4]&4);unsigned b=CB(bank);
    CHECK(f->old.regs[b/4]==(bank==f->gpu.work.bank?0xc01167u:0xc01067u));
    CHECK(f->old.regs[(b+4)/4]==0x70000000&&f->old.regs[(0x1000+4*bank)/4]==0x1f300&&f->old.regs[(0x1800+4*bank)/4]==1);
    uint64_t table=reg64(&f->old,b+0x20)&UINT64_C(0x0000ffffffffffff);
    for(unsigned level=1;level<=3;level++){
        unsigned shift=level==1?30:level==2?21:12;const uint8_t *p;
        if(table>=f->plan.owner_pa+0x4000&&table+4096<=f->plan.owner_pa+0xc000)p=f->old.tables+(table-f->plan.owner_pa-0x4000);
        else if(table>=f->plan.owner_pa+0x9c000&&table+4096<=f->plan.owner_pa+0xa0000)p=f->tables+(table-f->plan.owner_pa-0x9c000);
        else return model_fault(level,1u<<4);
        uint64_t e=get64(p+8*((va>>shift)&511));if(!e)return model_fault(level,2);if((e&3)!=3)return model_fault(level,16);
        if(level==3)return e&UINT64_C(0x0000fffffffff000);table=e&UINT64_C(0x0000fffffffff000);
    }
    abort();
}
static bool gpu_w64(void *cookie,uint32_t off,uint64_t value)
{
    struct gpu_fake *f=cookie;CHECK(off<65536&&!(off&7));if(!gpu_tick(f))return false;++f->writes;
    unsigned n=f->gpu.work.bank;bool atos=off>=0x8000&&(off&4095)==0x800;
    CHECK(off==CB(n)+0x20||off==CB(n)+0x28||atos);if(off==f->ignore)return true;
    set64(&f->old,off,value);
    if(atos){
        unsigned bank=(off-0x8000)/4096;CHECK(bank==n||bank==f->baseline.bank[0]||bank==f->baseline.bank[1]);
        uint64_t par=gpu_walk(f,bank,(uint32_t)value);++f->atos;
        if(f->wrong==1&&!(par&1))par+=4096;
        if(par&1)switch(f->wrong){
        case 2:par=model_fault(3,16);break;case 3:par=UINT64_MAX;break;case 4:par=0;break;
        case 5:par=model_fault(3,0);break;case 6:par|=1u<<31;break;case 7:par|=4;break;
        case 8:par&=~UINT64_C(0x300);break;case 9:par=model_fault(2,2);break;case 10:par|=UINT64_C(1)<<35;break;
        case 11:par|=1u<<29;break;case 12:par=0xf;break;
        }
        set64(&f->old,CB(bank)+0x50,par);
        if((par&1)&&f->tf_mode)f->old.regs[(CB(bank)+0x58)/4]|=f->tf_mode==1?2u:8u;
    }
    return true;
}
static bool gpu_barrier(void *cookie){return gpu_tick(cookie);}
static bool gpu_delay(void *cookie,unsigned us){CHECK(us==5||us==10);return gpu_tick(cookie);}
static bool gpu_prepare(void *cookie,unsigned ias,unsigned oas,struct ggp_s1_config *cfg)
{
    struct gpu_fake *f=cookie;if(!gpu_tick(f))return false;++f->prepared;CHECK(!f->writes);
    CHECK(ggp_emit_tables(&f->plan,ias,oas,f->tables,sizeof(f->tables),cfg));
    switch(f->drift){
    case 1:cfg->ttbr0^=4096;break;case 2:cfg->ttbr1^=4096;break;case 3:cfg->tcr^=1;break;
    case 4:cfg->mair0^=1;break;case 5:cfg->mair1^=1;break;case 6:cfg->ias^=1;break;case 7:cfg->oas^=1;break;
    case 8:f->old.regs[0]^=0x100;break;case 9:f->old.regs[CB(f->baseline.bank[1])/4]^=0x100;break;
    case 10:f->old.regs[S2CR(f->baseline.slot[0])/4]^=1;break;
    case 11:f->old.regs[0x6000/4]|=4;break;case 12:f->old.regs[CB(7)/4]|=1;break;
    }
    return true;
}
static struct ggs_ops gpu_ops(struct gpu_fake *f)
{return (struct ggs_ops){f,gpu_guard,gpu_r32,gpu_w32,gpu_r64,gpu_w64,gpu_barrier,gpu_delay,gpu_prepare};}
static struct gpu_fake *gpu_fresh(unsigned mode)
{
    CHECK(mode<3);
    if(!templates[mode]){
        struct fake *m=fresh(mode!=0);
        if(mode==2){m->regs[0x24/4]=2u<<28|8;memset(m->regs+0x800/4,0,16*4);}
        struct gsm_receipt r;CHECK(run(m,&r)==GSM_OK);struct gpu_fake *t=calloc(1,sizeof(*t));CHECK(t);
        t->old=*m;t->baseline=r;CHECK(ggp_plan_build(&m->plan,&t->plan));free(m);templates[mode]=t;
    }
    struct gpu_fake *f=malloc(sizeof(*f));CHECK(f);*f=*templates[mode];f->ignore=UINT32_MAX;return f;
}
static enum gsm_result gpu_run(struct gpu_fake *f,struct ggs_receipt *out)
{struct ggs_ops o=gpu_ops(f);return ggs_configure_once(&f->gpu,&o,&f->plan,&f->baseline,out);}
static void gpu_stopped(struct gpu_fake *f)
{
    unsigned step=f->step;struct ggs_receipt r,b;memset(&r,0x75,sizeof(r));b=r;
    struct gsm_diagnostics d=f->gpu.diagnostic;struct gsm_atos_sample t=f->gpu.translation;
    CHECK(gpu_run(f,&r)==GSM_ALREADY&&!memcmp(&r,&b,sizeof(r))&&f->step==step);
    CHECK(!memcmp(&d,&f->gpu.diagnostic,sizeof(d))&&!memcmp(&t,&f->gpu.translation,sizeof(t)));
}
static void gpu_good(void)
{
    for(unsigned mode=0;mode<3;mode++)for(unsigned tf=0;tf<2;tf++){
        struct gpu_fake *f=gpu_fresh(mode);f->tf_mode=tf;f->nested=true;struct ggs_receipt r;
        CHECK(gpu_run(f,&r)==GSM_OK);CHECK(r.bank==(mode==0?3u:mode==1?1u:2u));
        CHECK(r.slot==(mode==0?0u:mode==1?2u:2u));CHECK(r.gpu_pages==18&&r.gmu_pages==131&&r.translations==168&&f->atos==168);
        CHECK(r.writes==f->writes&&f->prepared==1&&f->gpu.phase==GGS_DONE&&!(f->old.regs[0x6000/4]&4));
        CHECK(r.sctlr==0xc01167&&r.tcr==0x802019&&r.tcr2==0x38011&&r.cr0==f->baseline.cr0_after);
        CHECK(!memcmp(f->old.tables,templates[mode]->old.tables,sizeof(f->old.tables)));
        for(unsigned i=0;i<r.groups;i++)if(i!=r.slot){CHECK(f->old.regs[S2CR(i)/4]==templates[mode]->old.regs[S2CR(i)/4]);if(mode)CHECK(f->old.regs[SMR(i)/4]==templates[mode]->old.regs[SMR(i)/4]);}
        printf("GPU SMMU mode%u TF%u: SID0 slot%u CB%u ASID%u,18 GPU +131 GMU leaves/168 ATOS, %u callback boundaries PASS\n",mode,tf,r.slot,r.bank,r.asid,f->step);
        gpu_stopped(f);free(f);
    }
}
static void gpu_bad(void)
{
    for(unsigned mode=0;mode<3;mode++){
        struct gpu_fake *ok=gpu_fresh(mode);struct ggs_receipt r;CHECK(gpu_run(ok,&r)==GSM_OK);unsigned steps=ok->step;free(ok);
        for(unsigned fail=1;fail<=steps;fail++){
            struct gpu_fake *f=gpu_fresh(mode);f->fail=fail;struct ggs_receipt b;memset(&r,0x96,sizeof(r));b=r;
            CHECK(gpu_run(f,&r)!=GSM_OK&&f->step==fail&&!memcmp(&r,&b,sizeof(r)));gpu_stopped(f);free(f);
        }
        printf("GPU SMMU mode%u: all%u callback failures stopped exactly with output unchanged/no retry PASS\n",mode,steps);
    }
    for(unsigned drift=1;drift<=12;drift++){
        struct gpu_fake *f=gpu_fresh(2);f->drift=drift;struct ggs_receipt r;
        CHECK(gpu_run(f,&r)!=GSM_OK&&!f->writes);gpu_stopped(f);free(f);
    }
    for(unsigned wrong=1;wrong<=12;wrong++){
        struct gpu_fake *f=gpu_fresh(2);f->wrong=wrong;struct ggs_receipt r;
        CHECK(gpu_run(f,&r)==GSM_TRANSLATION&&f->gpu.translation.valid);gpu_stopped(f);free(f);
    }
    for(unsigned stuck=1;stuck<=3;stuck++){
        struct gpu_fake *f=gpu_fresh(2);f->stuck=stuck;struct ggs_receipt r;
        CHECK(gpu_run(f,&r)==GSM_TIMEOUT);gpu_stopped(f);free(f);
    }
    struct gpu_fake *f=gpu_fresh(2);f->tf_mode=2;struct ggs_receipt r;
    CHECK(gpu_run(f,&r)==GSM_READBACK&&(f->old.regs[(CB(f->gpu.work.bank)+0x58)/4]&8));gpu_stopped(f);free(f);
    for(unsigned kind=0;kind<8;kind++){
        f=gpu_fresh(2);
        switch(kind){
        case 0:f->old.regs[SMR(2)/4]=0x80010000;break;
        case 1:f->old.regs[SMR(2)/4]=0x80000000;f->old.regs[SMR(3)/4]=0x80000000;break;
        case 2:f->old.regs[SMR(2)/4]=0x80000004;break;
        case 3:f->old.regs[CB(3)/4]=1;break;
        case 4:f->old.regs[(CB(3)+0x58)/4]=1u<<30;break;
        case 5:f->old.regs[SMR(2)/4]=0x80000002;f->old.regs[S2CR(2)/4]=8;break;
        case 6:f->baseline.ttbr0[0]^=4096;break;
        case 7:f->baseline.tcr^=1;break;
        }
        CHECK(gpu_run(f,&r)!=GSM_OK&&!f->writes&&!f->prepared);gpu_stopped(f);free(f);
    }
}
static void gpu_arguments(void)
{
    struct gpu_fake *f=gpu_fresh(2);struct ggs_ops o=gpu_ops(f);struct ggs_receipt out={0};struct ggs_receipt saved_out=out;
    struct ggs_context saved=f->gpu;CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,&out)==0&&!f->step&&!memcmp(&saved,&f->gpu,sizeof(saved)));
    CHECK(ggs_argument_reason(NULL,&o,&f->plan,&f->baseline,&out)==1);
    CHECK(ggs_argument_reason(&f->gpu,NULL,&f->plan,&f->baseline,&out)==2);
    CHECK(ggs_argument_reason(&f->gpu,&o,NULL,&f->baseline,&out)==3);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,NULL,&out)==4);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,NULL)==5);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->gpu.plan,&f->baseline,&out)==6);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->gpu.gmu,&out)==7);
    CHECK(ggs_argument_reason(&f->gpu,&f->gpu.ops,&f->plan,&f->baseline,&out)==8);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,&f->gpu.work)==9);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,(const struct ggs_receipt *)&f->plan)==10);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,(const struct ggs_receipt *)&f->baseline)==11);
    CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,(const struct ggs_receipt *)&o)==12);
    struct ggp_plan p=f->plan;p.region[0].offset^=4096;CHECK(ggs_argument_reason(&f->gpu,&o,&p,&f->baseline,&out)==13);
    for(unsigned code=14;code<=21;code++){
        struct gsm_receipt m=f->baseline;
        switch(code){case 14:m.groups=0;break;case 15:m.mapped_pages=130;break;case 16:m.bank[1]=m.bank[0];break;
        case 17:m.slot[0]=m.groups;break;case 18:m.asid[0]=0;break;case 19:m.sctlr[0]^=1;break;case 20:m.smr_after[0]^=1;break;case 21:m.asid[1]=m.asid[0];break;}
        CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&m,&out)==code);
        CHECK(ggs_configure_once(&f->gpu,&o,&f->plan,&m,&out)==GSM_ARGUMENT&&!f->step&&!f->gpu.state);
    }
    o.prepare=NULL;CHECK(ggs_argument_reason(&f->gpu,&o,&f->plan,&f->baseline,&out)==22);
    CHECK(!f->step&&!memcmp(&saved,&f->gpu,sizeof(saved))&&!memcmp(&saved_out,&out,sizeof(out)));free(f);
}
int main(void){gpu_good();gpu_bad();gpu_arguments();for(unsigned i=0;i<3;i++)free(templates[i]);printf("GPU SMMU: %u total assertions PASS; independent real-table walks/route and GMU preservation, exact fault classification, all callback failures and pure argument diagnostics; no hardware qualification\n",checks);}
