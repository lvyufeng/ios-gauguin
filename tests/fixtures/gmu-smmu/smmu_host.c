#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gmu_smmu.h"
static unsigned checks;
#define CHECK(x) do {assert(x);++checks;} while(0)
#define CB(n) (0x8000u+0x1000u*(n))
struct fake {
    struct gsm_context channel;
    struct ggm_plan plan;
    uint32_t regs[16384];unsigned char tables[32768];
    unsigned step,fail,writes,prepared,atos,barriers;
    unsigned ignore,stuck,wrong_par,drift,opaque_mode;
    bool nested;
};
static bool tick(struct fake *f){return ++f->step!=f->fail;}
static bool guard(void *cookie)
{
    struct fake *f=cookie;
    if(f->nested){
        f->nested=false;struct gsm_receipt out,before;memset(&out,0x71,sizeof(out));before=out;
        struct gsm_ops o=f->channel.ops;
        CHECK(gsm_configure_once(&f->channel,&o,&f->plan,&out)==GSM_ALREADY);
        CHECK(!memcmp(&out,&before,sizeof(out)));
    }
    return tick(f);
}
static bool read32(void *cookie,uint32_t off,uint32_t *out)
{
    struct fake *f=cookie;CHECK(off<65536&&!(off&3));if(!tick(f))return false;
    *out=f->regs[off/4];
    if(f->stuck==1&&off==0x6000)*out&=~8u;
    if(f->stuck==2&&off==0x74)*out=1;
    if(f->stuck==3&&(off&0xfff)==0x7f4)*out=1;
    if(f->stuck==4&&(off&0xfff)==0x8f0)*out=1;
    return true;
}
static uint64_t get64(const unsigned char *p)
{uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static uint64_t reg64(struct fake *f,unsigned off)
{return (uint64_t)f->regs[off/4]|(uint64_t)f->regs[off/4+1]<<32;}
static void set64(struct fake *f,unsigned off,uint64_t v)
{f->regs[off/4]=(uint32_t)v;f->regs[off/4+1]=(uint32_t)(v>>32);}
/* Independent Arm IHI0062D.c PAR fault producer. Walk level comes from
 * the actual missing descriptor, not the driver's expected-hole list. */
static uint64_t model_fault(unsigned level,unsigned flags)
{return ((uint64_t)level<<32)|(2u<<8)|flags|1u;}
static uint64_t walk(struct fake *f,unsigned bank,uint32_t va)
{
    unsigned b=CB(bank);CHECK(f->regs[0x6000/4]&4); /* ATOS while halted */
    CHECK(f->regs[b/4]==0xc01067&&f->regs[(b+4)/4]==0x70000000);
    CHECK(f->regs[(0x1000+4*bank)/4]==0x1f300&&f->regs[(0x1800+4*bank)/4]==1);
    CHECK(f->regs[(b+0x30)/4]==0x802019&&f->regs[(b+0x10)/4]==0x38011);
    CHECK(f->regs[(b+0x38)/4]==0xf404ff44&&f->regs[(b+0x3c)/4]==0xe4);
    uint64_t table=reg64(f,b+0x20)&UINT64_C(0x0000ffffffffffff);
    CHECK((reg64(f,b+0x20)>>48)==bank+1);
    for(unsigned level=1;level<=3;level++){
        if(table<f->plan.owner_pa+0x4000||table+4096>f->plan.owner_pa+0xc000)return model_fault(level,1u<<4);
        unsigned shift=level==1?30:level==2?21:12;
        unsigned offset=(unsigned)(table-f->plan.owner_pa-0x4000)+8*((va>>shift)&511);
        uint64_t entry=get64(f->tables+offset);
        if(!(entry&1))return model_fault(level,1u<<1);
        if((entry&3)!=3)return model_fault(level,1u<<4);
        if(level==3)return entry&UINT64_C(0x0000fffffffff000);
        table=entry&UINT64_C(0x0000fffffffff000);
    }
    abort();
}
static bool write32(void *cookie,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;CHECK(off<65536&&!(off&3));if(!tick(f))return false;++f->writes;
    if(off==f->ignore)return true;
    if(off==0x6b68&&f->opaque_mode){
        CHECK(value==0x9a82a382); /* exact native DT write, never readback-tuned */
        const uint32_t observations[]={0,0x0a800082,UINT32_MAX,0,0x12345678};
        CHECK(f->opaque_mode<sizeof(observations)/sizeof(*observations));
        f->regs[off/4]=observations[f->opaque_mode];
    }else if(off==0x6000)f->regs[off/4]=(value&~8u)|((value&4)?8u:0u);
    else if(off==0x48||(off>=0x8000&&(off&0xfff)==0x58))f->regs[off/4]&=~value;
    else f->regs[off/4]=value;
    return true;
}
static bool read64(void *cookie,uint32_t off,uint64_t *out)
{
    struct fake *f=cookie;CHECK(off<65536&&!(off&7));if(!tick(f))return false;
    *out=reg64(f,off);return true;
}
static bool write64(void *cookie,uint32_t off,uint64_t value)
{
    struct fake *f=cookie;CHECK(off<65536&&!(off&7));if(!tick(f))return false;++f->writes;
    if(off==f->ignore)return true;
    set64(f,off,value);
    if((off&0xfff)==0x800){
        unsigned bank=(off-0x8000)/4096;uint64_t par=walk(f,bank,(uint32_t)value);++f->atos;
        if(f->wrong_par==1&&!(par&1))par+=4096;
        if(par&1)switch(f->wrong_par){
        case 2:par=model_fault(3,1u<<4);break; /* external abort, NOT a hole */
        case 3:par=UINT64_MAX;break;
        case 4:par=0;break;
        case 5:par=model_fault(3,0);break; /* F with no reason */
        case 6:par|=1u<<31;break; /* terminated, even with TF */
        case 7:par|=1u<<2;break; /* mixed access flag fault */
        case 8:par&=~UINT64_C(0x300);break; /* short descriptor */
        case 9:par=model_fault(2,1u<<1);break; /* wrong missing level */
        case 10:par|=UINT64_C(1)<<35;break; /* stage2 */
        case 11:par=model_fault(3,1u<<2);break;
        case 12:par=model_fault(3,1u<<3);break;
        case 13:par=model_fault(3,1u<<5);break;
        case 14:par=model_fault(3,1u<<6);break;
        case 15:par=model_fault(3,1u<<7);break;
        case 16:par|=1u<<29;break; /* invalid context */
        case 17:par=0xf;break; /* OLD fake CPU FST7 must now be rejected */
        case 18:par|=0x100;break; /* reserved format3 */
        case 19:par=(par&~UINT64_C(0x300))|0x100;break; /* AArch32 long */
        case 20:par=model_fault(3,1u<<31);break;
        }
        set64(f,CB(bank)+0x50,par);
    }
    return true;
}
static bool barrier(void *cookie){struct fake *f=cookie;if(!tick(f))return false;++f->barriers;return true;}
static bool wait_us(void *cookie,unsigned us){CHECK(us==5||us==10);return tick(cookie);}
static bool prepare(void *cookie,unsigned ias,unsigned oas,struct ggm_s1_config *cfg)
{
    struct fake *f=cookie;if(!tick(f))return false;++f->prepared;
    CHECK(!f->writes);CHECK(ias==39&&oas==36); /* ID2.IAS differs from OAS */
    CHECK(ggm_emit_tables(&f->plan,ias,oas,f->tables,sizeof(f->tables),cfg));
    if(f->drift==1)f->regs[0xc00/4]^=1;
    if(f->drift==2)f->regs[CB(7)/4]=1;
    if(f->drift==3)f->regs[0]^=0x100;
    if(f->drift==4)cfg->tcr^=1;
    if(f->drift==5)cfg->kernel_ttbr0^=4096;
    if(f->drift==6)cfg->kernel_ttbr1^=4096;
    if(f->drift==7)cfg->user_ttbr0^=4096;
    if(f->drift==8)cfg->user_ttbr1^=4096;
    if(f->drift==9)cfg->tcr^=1;
    if(f->drift==10)cfg->mair0^=1;
    if(f->drift==11)cfg->mair1^=1;
    if(f->drift==12)cfg->ias^=1;
    if(f->drift==13)cfg->oas^=1;
    return true;
}
static struct gsm_ops ops(struct fake *f)
{return (struct gsm_ops){f,guard,read32,write32,read64,write64,barrier,wait_us,prepare};}
static struct fake *fresh(bool match)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);f->ignore=UINT32_MAX;
    CHECK(ggm_plan_build(0xaa200000,&f->plan));
    f->regs[0x20/4]=(1u<<30)|(3u<<9)|(match?((1u<<27)|16u):0u);
    f->regs[0x24/4]=(2u<<28)|8u|(match?(1u<<16):0u);
    f->regs[0x28/4]=(1u<<12)|(2u<<8)|(2u<<4)|1u;
    if(match){
        for(unsigned i=0;i<16;i++)f->regs[(0xc00+4*i)/4]=0x20000;
        const unsigned slots[]={2,3,10,11},sid[]={0,2,4,5},bank[]={1,2,6,4};
        for(unsigned n=0;n<4;n++){
            f->regs[(0x800+4*slots[n])/4]=0x80000000u|sid[n];
            f->regs[(0xc00+4*slots[n])/4]=bank[n];
        }
    }
    return f;
}
static enum gsm_result run(struct fake *f,struct gsm_receipt *out)
{struct gsm_ops o=ops(f);return gsm_configure_once(&f->channel,&o,&f->plan,out);}
static void stopped(struct fake *f)
{
    unsigned step=f->step;struct gsm_receipt r,b;memset(&r,0x64,sizeof(r));b=r;
    struct gsm_diagnostics diagnostic=f->channel.diagnostic;
    struct gsm_impl_sample implementation=f->channel.implementation;
    struct gsm_atos_sample translation=f->channel.translation;
    CHECK(run(f,&r)==GSM_ALREADY);CHECK(f->step==step&&!memcmp(&r,&b,sizeof(r)));
    CHECK(!memcmp(&diagnostic,&f->channel.diagnostic,sizeof(diagnostic)));
    CHECK(!memcmp(&implementation,&f->channel.implementation,sizeof(implementation)));
    CHECK(!memcmp(&translation,&f->channel.translation,sizeof(translation)));
}
static void happy(void)
{
    for(unsigned match=0;match<2;match++){
        struct fake *f=fresh(match);uint32_t original[16384];memcpy(original,f->regs,sizeof(original));
        struct gsm_receipt r;f->nested=true;CHECK(run(f,&r)==GSM_OK);
        CHECK(r.bank[0]==(match?6:1)&&r.bank[1]==(match?4:2));
        CHECK(r.slot[0]==(match?10:4)&&r.slot[1]==(match?11:5));
        CHECK(r.asid[0]==r.bank[0]+1&&r.asid[1]==r.bank[1]+1);
        CHECK(r.translations==140&&r.mapped_pages==131&&f->atos==140);
        CHECK(r.ias==39&&r.oas==36&&r.tcr==0x802019&&r.tcr2==0x38011);
        CHECK(r.cr0_after==0xc01c36&&r.micro_after==0x2370);
        CHECK(r.writes==f->writes&&f->prepared==1&&!(f->regs[0x6000/4]&4));
        CHECK(f->channel.diagnostic.phase==GSP_DONE&&f->channel.diagnostic.check==GSD_NONE);
        CHECK(f->channel.implementation.valid==1&&f->channel.implementation.requested==0x9a82a382&&f->channel.implementation.readback==0x9a82a382);
        CHECK(!f->channel.translation.valid);
        for(unsigned i=0;i<r.groups;i++)if(i!=r.slot[0]&&i!=r.slot[1]){
            CHECK(f->regs[(0xc00+4*i)/4]==original[(0xc00+4*i)/4]);
            if(match)CHECK(f->regs[(0x800+4*i)/4]==original[(0x800+4*i)/4]);
        }
        for(unsigned i=0;i<8;i++)if(i!=r.bank[0]&&i!=r.bank[1])CHECK(f->regs[CB(i)/4]==original[CB(i)/4]);
        stopped(f);printf("SMMU mode%u: userCB%u kernelCB%u,140 ATOS, %u callback boundaries PASS\n",match,r.bank[0],r.bank[1],f->step);free(f);
    }
    /* Empty SMS: allocate two free SMR slots and stage1 banks after S2-only. */
    struct fake *f=fresh(true);memset(f->regs+0x800/4,0,16*4);
    struct gsm_receipt r;CHECK(run(f,&r)==GSM_OK);CHECK(r.slot[0]==0&&r.slot[1]==1&&r.bank[0]==1&&r.bank[1]==2);free(f);
}
static void bad(void)
{
    for(unsigned kind=0;kind<17;kind++){
        struct fake *f=fresh(true);enum gsm_result expected=GSM_CAPABILITY;
        switch(kind){
        case 0:f->regs[0x20/4]=UINT32_MAX;break;
        case 1:f->regs[0x20/4]&=~(1u<<30);break;
        case 2:f->regs[0x20/4]|=1u<<26;break;
        case 3:f->regs[0x20/4]|=1u<<8;break;
        case 4:f->regs[0x24/4]|=1u<<31;break;
        case 5:f->regs[0x24/4]^=1u<<28;break;
        case 6:f->regs[0x28/4]&=~(1u<<12);break;
        case 7:f->regs[0x28/4]|=15;break;
        case 8:f->regs[0x24/4]=2u<<28|1;break;
        case 9:f->regs[0x20/4]=(f->regs[0x20/4]&~255u)|129;break;
        case 10:f->regs[CB(2)/4]=1;expected=GSM_INHERITED;break;
        case 11:f->regs[(CB(3)+0x58)/4]=1u<<30;expected=GSM_INHERITED;break;
        case 12:f->regs[0x6000/4]=4;expected=GSM_INHERITED;break;
        case 13:f->regs[(0x800+4*10)/4]|=1u<<16;expected=GSM_ROUTING;break;
        case 14:f->regs[(0x800+4*12)/4]=0x80000004;expected=GSM_ROUTING;break;
        case 15:f->regs[(0xc00+4*10)/4]=3u<<16;expected=GSM_ROUTING;break;
        case 16:f->regs[(0xc00+4*10)/4]=8;expected=GSM_ROUTING;break;
        }
        struct gsm_receipt r,b;memset(&r,0xa6,sizeof(r));b=r;
        CHECK(run(f,&r)==expected);CHECK(!memcmp(&r,&b,sizeof(r)));CHECK(!f->writes&&!f->prepared);stopped(f);free(f);
    }
    for(unsigned kind=1;kind<=4;kind++){
        struct fake *f=fresh(true);f->drift=kind;struct gsm_receipt r;
        CHECK(run(f,&r)==(kind==4?GSM_READBACK:GSM_INHERITED));CHECK(!f->writes);stopped(f);free(f);
    }
    for(unsigned kind=5;kind<=13;kind++){
        struct fake *f=fresh(true);f->drift=kind;struct gsm_receipt r,b;
        memset(&r,0xa3,sizeof(r));b=r;CHECK(run(f,&r)==GSM_READBACK&&!memcmp(&r,&b,sizeof(r))&&!f->writes);
        const struct gsm_diagnostics *d=&f->channel.diagnostic;
        CHECK(d->phase==GSP_PREPARE&&d->check==GSD_CONFIG&&d->offset==kind-5&&d->mask==UINT64_MAX&&d->expected!=d->actual);
        stopped(f);free(f);
    }
    for(unsigned kind=1;kind<=4;kind++){
        struct fake *f=fresh(true);f->stuck=kind;struct gsm_receipt r,b;memset(&r,0xa3,sizeof(r));b=r;
        CHECK(run(f,&r)==GSM_TIMEOUT);CHECK(!memcmp(&r,&b,sizeof(r)));stopped(f);free(f);
    }
    for(unsigned kind=1;kind<=20;kind++){
        struct fake *f=fresh(true);f->wrong_par=kind;struct gsm_receipt r,b;memset(&r,0xa3,sizeof(r));b=r;
        CHECK(run(f,&r)==GSM_TRANSLATION);CHECK(!memcmp(&r,&b,sizeof(r)));
        const struct gsm_atos_sample *a=&f->channel.translation;
        CHECK(a->valid==1&&a->stream==5&&a->bank==4&&a->iova==(kind==1?0x4000u:0));
        CHECK(a->expected==(kind==1?f->plan.owner_pa+0x10000:UINT64_MAX)&&a->par==reg64(f,CB(4)+0x50));
        CHECK(a->level==(kind==1?0:3));
        CHECK(a->mapped==(kind==1?0:131)&&f->channel.work.translations==(kind==1?1:132));
        stopped(f);free(f);
    }
    printf("SMMU PAR: architected S1/AArch64 TF levels,20 mapped/hole fault variants and old CPU-shaped code rejection PASS\n");
    const unsigned ignore[]={0x6000,0x6060,0x1800+4*6,0x1000+4*6,CB(6)+0x10,CB(6)+0x20,CB(6)+4,CB(6)};
    const uint64_t wanted[]={4,0x1055,1,0x1f300,0x38011,((uint64_t)7<<48)|0xaa20a000,0x70000000,0x00c01067};
    for(unsigned i=0;i<sizeof(ignore)/sizeof(*ignore);i++){
        struct fake *f=fresh(true);f->ignore=ignore[i];struct gsm_receipt r;
        CHECK(run(f,&r)==GSM_READBACK);
        const struct gsm_diagnostics *d=&f->channel.diagnostic;
        CHECK(d->phase==(i<2?GSP_GLOBAL:GSP_USER)&&d->offset==ignore[i]&&d->expected==wanted[i]&&!d->actual);
        CHECK(d->check==(i==5?GSD_STORE64:GSD_STORE32)&&d->mask==(i==5?UINT64_MAX:i==0?(UINT32_MAX&~8u):UINT32_MAX));
        stopped(f);free(f);
    }
}
static void arguments(void)
{
    struct fake *f=fresh(true);struct gsm_ops o=ops(f);struct gsm_receipt r;unsigned s=f->step;
    CHECK(gsm_configure_once(NULL,&o,&f->plan,&r)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,NULL,&f->plan,&r)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,&o,NULL,&r)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,&o,&f->plan,NULL)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,&o,&f->plan,(void *)&f->channel)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,&o,&f->plan,(void *)&f->plan)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,&o,(void *)&f->channel,&r)==GSM_ARGUMENT);
    CHECK(gsm_configure_once(&f->channel,&o,(void *)(UINTPTR_MAX-1),&r)==GSM_ARGUMENT);
    o.write64=NULL;CHECK(gsm_configure_once(&f->channel,&o,&f->plan,&r)==GSM_ARGUMENT);
    CHECK(f->step==s&&!f->channel.state);free(f);
}
static void opaque_native_write(void)
{
    for(unsigned mode=1;mode<=4;mode++){
        struct fake *f=fresh(true);f->opaque_mode=mode;
        struct gsm_receipt r,b;memset(&r,0x84,sizeof(r));b=r;
        CHECK(run(f,&r)==(mode==2?GSM_READBACK:GSM_OK));
        CHECK(f->channel.implementation.valid==1&&f->channel.implementation.requested==0x9a82a382);
        const uint32_t observations[]={0,0x0a800082,UINT32_MAX,0,0x12345678};
        CHECK(f->channel.implementation.readback==observations[mode]);
        if(mode==2){
            CHECK(!memcmp(&r,&b,sizeof(r))&&f->atos==0&&f->writes==13);
            CHECK(f->channel.diagnostic.phase==GSP_GLOBAL&&f->channel.diagnostic.check==GSD_STORE32&&f->channel.diagnostic.offset==0x6b68);
        }else CHECK(r.translations==140&&r.mapped_pages==131&&f->atos==140);
        stopped(f);free(f);
    }
    /* An opaque readback never bypasses architected control or ATOS gates. */
    struct fake *f=fresh(true);f->opaque_mode=1;f->ignore=CB(6);struct gsm_receipt r;
    CHECK(run(f,&r)==GSM_READBACK&&f->channel.diagnostic.offset==CB(6));stopped(f);free(f);
    f=fresh(true);f->opaque_mode=1;f->wrong_par=1;
    CHECK(run(f,&r)==GSM_TRANSLATION);stopped(f);free(f);
    printf("SMMU opaque native-write: observed/non-echo/zero samples, all-ones refusal and independent control/ATOS gates PASS\n");
}
static void faults(void)
{
    struct fake *f=fresh(true);struct gsm_receipt r;CHECK(run(f,&r)==GSM_OK);unsigned steps=f->step;free(f);
    for(unsigned mode=0;mode<=1;mode++)for(unsigned fail=1;fail<=steps;fail++){
        f=fresh(true);f->opaque_mode=mode;f->fail=fail;struct gsm_receipt b;memset(&r,0x84,sizeof(r));b=r;
        CHECK(run(f,&r)==GSM_IO);CHECK(!memcmp(&r,&b,sizeof(r)));stopped(f);free(f);
    }
    printf("SMMU fail-every-callback: %u boundaries x echo/non-echo PASS\n",steps);
}
int main(void){happy();bad();arguments();opaque_native_write();faults();printf("SMMU transaction: %u checks PASS\n",checks);}
