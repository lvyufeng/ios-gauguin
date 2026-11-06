#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gmu_firmware.h"
#include "gauguin_gmu_memory.h"
#include "cmd_db_snapshot.h"
static unsigned checks;
#define CHECK(x) do {assert(x);++checks;} while(0)
struct fake {struct gmf_context channel;struct gmf_plan plan;
    uint32_t regs[GMF_WINDOWS][12288],shared[8192];uint8_t image[32768];
    unsigned step,fail,writes,doorbells,reset_writes,asset_calls,copy_calls,delays;
    unsigned ignore,timeout,bad_asset,bad_version,bad_ack,fw_fault,debug,init_positive;
    bool nested;};
static bool tick(struct fake *f){return ++f->step!=f->fail;}
static bool guard(void *cookie,enum gmf_phase phase)
{
    struct fake *f=cookie;CHECK(phase==f->channel.phase);
    if(phase==GMF_RESET)CHECK(f->regs[GMF_CSR][0x2000/4]==1);
    else if(phase!=GMF_RELEASING)CHECK(f->regs[GMF_CSR][0x2000/4]==0);
    if(f->nested){f->nested=false;struct gmf_ops o=f->channel.ops;struct gmf_receipt out,before;
        memset(&out,0x4a,sizeof(out));before=out;
        CHECK(gmf_bootstrap_once(&f->channel,&o,&f->plan,&out)==GMF_ALREADY);
        CHECK(!memcmp(&out,&before,sizeof(out)));}
    return tick(f);
}
static bool read_word(void *cookie,enum gmf_window w,uint32_t off,uint32_t *v)
{struct fake *f=cookie;CHECK(w<GMF_WINDOWS&&!(off&3)&&off<(w==GMF_TCM?0xc000u:0x4000u));if(!tick(f))return false;*v=f->regs[w][off/4];return true;}
static void reply(struct fake *f,unsigned queue,const uint32_t *p,unsigned words)
{
    unsigned wi=6+12*queue+11,write=f->shared[wi];
    for(unsigned i=0;i<words;i++)f->shared[56+1024*queue+(write+i)%1024]=p[i];
    f->shared[wi]=(write+words)%1024;f->regs[GMF_CSR][0x2648/4]|=queue==1?1:4;
}
static void response(struct fake *f)
{
    unsigned rd=f->shared[16],wr=f->shared[17],base=56+rd;
    uint32_t header=f->shared[base];unsigned words=(header>>8)&255,id=header&255;
    CHECK(f->channel.phase==GMF_HANDSHAKE&&f->regs[GMF_CSR][0x2600/4]==1);
    CHECK((id==0&&words==5&&header==0x00100500)||(id==1&&words==2&&header==0x00200201));
    CHECK((wr+1024-rd)%1024==words);
    if(id==0){CHECK(f->shared[base+1]==0&&f->shared[base+2]==0x60006000&&f->shared[base+3]==0x4000&&f->shared[base+4]==1);}
    else CHECK(f->shared[base+1]==0x100b0000);
    f->shared[16]=wr; /* Native firmware consumes command before ACK. */
    if(f->timeout==4+id)return;
    if(f->debug){uint32_t msg=0x10165;reply(f,1,&msg,1);}
    unsigned n=id?4:3;
    uint32_t ack[4]={((id+1)<<20)|(2<<16)|(n<<8)|126,header,id?0:f->init_positive,0x100b0000};
    if(f->bad_ack==1)ack[1]^=0x100000;
    if(f->bad_ack==2)ack[2]=UINT32_MAX;
    if(f->bad_ack==3)ack[0]^=3u<<16;
    if(f->bad_ack==4){ack[0]=(ack[0]&~0xff00u)|0x200;n=2;}
    if(id&&f->bad_version==2)ack[3]=0x100a0000;
    if(id&&f->bad_version==3)ack[3]=0x200b0000;
    reply(f,1,ack,n);
}
static bool write_word(void *cookie,enum gmf_window w,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;CHECK(w<GMF_WINDOWS&&!(off&3)&&off<(w==GMF_TCM?0xc000u:0x4000u));
    if(!tick(f))return false;++f->writes;
    if(f->ignore==f->writes)return true;
    if(w==GMF_CSR&&off==0x2644){f->regs[w][0x2648/4]&=~value;return true;}
    if(w==GMF_AO&&off==0x2c10){f->regs[w][0x2c14/4]&=~value;return true;}
    f->regs[w][off/4]=value;
    if(w==GMF_CSR&&off==0x2000){
        CHECK(value==0&&f->channel.phase==GMF_RELEASING&&++f->reset_writes==1);
        CHECK(f->copy_calls==1&&f->regs[GMF_GBIF][0x3114/4]==0);
        CHECK(f->regs[GMF_AO][0x1600/4]==0xa7a506a0&&f->regs[GMF_SEQ][0]==0xfebea1e1);
        CHECK(f->regs[GMF_PDC][0x500/4]==0x80000001&&f->regs[GMF_PDC][0x520/4]==0);
        CHECK(f->regs[GMF_PDC][0x15d8/4]==0x30010&&f->regs[GMF_PDC][0x15dc/4]==1);
        CHECK(f->regs[GMF_PDC][0x1768/4]==0x30010&&f->regs[GMF_PDC][0x176c/4]==2);
        CHECK(f->regs[GMF_CSR][0x2004/4]==2&&f->regs[GMF_AO][0x2c44/4]==0x80a008a0);
        CHECK(f->regs[GMF_CSR][0x2608/4]==0x06019000&&f->regs[GMF_CSR][0x2730/4]==1);
        CHECK(f->regs[GMF_CSR][0x2614/4]==0x60001000&&f->regs[GMF_CSR][0x2400/4]==0x6000a000);
        CHECK(f->regs[GMF_CSR][0x2300/4]==0x09c40407&&f->regs[GMF_CSR][0x23a0/4]==0xf11);
        CHECK(f->regs[GMF_CSR][0x264c/4]==UINT32_MAX&&f->regs[GMF_AO][0x2c18/4]==UINT32_MAX);
        if(f->timeout!=1)f->regs[w][0x2070/4]=0xbabeface;
        if(f->fw_fault==1)f->regs[w][0x2648/4]|=0x8000;
    }
    if(w==GMF_CSR&&off==0x2650){
        if(value==(1u<<22)){
            CHECK(f->channel.phase==GMF_GX_REQUEST&&f->regs[w][0x2070/4]==0xbabeface);
            CHECK(f->regs[GMF_TCM][0x6fe0/4]==0&&f->regs[GMF_TCM][0x6fe4/4]==7&&f->regs[GMF_TCM][0x6fe8/4]==7);
            if(f->timeout!=2)f->regs[w][0x2648/4]|=1u<<30;
            if(f->fw_fault==2)f->regs[w][0x2648/4]|=0x8000;
        }else {CHECK(value==1);++f->doorbells;response(f);}
    }
    if(w==GMF_CSR&&off==0x2618){
        CHECK(value==1&&f->channel.phase==GMF_HFI_START);
        if(f->timeout!=3)f->regs[w][0x2600/4]=1;
        if(f->debug){uint32_t msg=0x10165;reply(f,1,&msg,1);reply(f,2,&msg,1);}
    }
    return true;
}
static bool barrier(void *cookie){return tick(cookie);}
static bool wait_us(void *cookie,unsigned us){struct fake *f=cookie;CHECK(us==100);++f->delays;return tick(f);}
static bool asset(void *cookie,const uint8_t **data,size_t *bytes)
{
    struct fake *f=cookie;if(!tick(f))return false;CHECK(!f->writes);++f->asset_calls;
    *data=f->image;*bytes=f->bad_asset==2?32767:32768;return f->bad_asset!=1;
}
static bool copy(void *cookie,const uint8_t *image,size_t bytes,struct gmf_copy *out)
{
    struct fake *f=cookie;if(!tick(f))return false;
    CHECK(f->channel.phase==GMF_RESET&&image==f->image&&bytes==32768&&f->asset_calls==1);
    memcpy((uint8_t *)f->regs[GMF_TCM]+0x1000,image,bytes);++f->copy_calls;
    if(f->bad_version==1)f->regs[GMF_TCM][0x8ff0/4]=1;
    *out=(struct gmf_copy){8192,f->bad_asset==3?8191:8192};return true;
}
static bool shared_read(void *cookie,uint32_t word,uint32_t *v)
{struct fake *f=cookie;CHECK(word<4152);if(!tick(f))return false;*v=f->shared[word];return true;}
static bool shared_write(void *cookie,uint32_t word,uint32_t v)
{struct fake *f=cookie;CHECK(word<4152);if(!tick(f))return false;f->shared[word]=v;return true;}
static struct gmf_ops ops(struct fake *f)
{return (struct gmf_ops){f,guard,read_word,write_word,barrier,wait_us,asset,copy,shared_read,shared_write};}
static struct fake *fresh(void)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);f->regs[GMF_CSR][0x2000/4]=1;
    f->regs[GMF_GBIF][0x3114/4]=3;
    for(unsigned i=0;i<32736;i++)f->image[i]=(uint8_t)(i*17);
    static const uint32_t address[]={0x30000,0x30010,0x30050,0x300a0},count[]={7,8,8,4};
    static const uint16_t level[4][16]={{0,16,64,128,192,256,384},{0,16,64,128,192,256,320,384},{0,64,128,192,256,320,384,416},{0,32,80,128}};
    struct ndb_entry entries[4]={0};const char *names[]={"cx.lvl","mx.lvl","gfx.lvl","xo.lvl"};
    for(unsigned n=0;n<4;n++){
        strcpy(entries[n].name,names[n]);entries[n].address=address[n];entries[n].owner_slave=3;entries[n].bank_version=0x1000;entries[n].aux_length=32;
        for(unsigned i=0;i<count[n];i++){entries[n].aux[2*i]=(uint8_t)level[n][i];entries[n].aux[2*i+1]=(uint8_t)(level[n][i]>>8);}
    }
    CHECK(gmf_plan_build(entries,&f->plan));
    struct ggm_plan p;CHECK(ggm_plan_build(0xaa200000,&p));CHECK(ggm_emit_hfi(&p,f->shared,sizeof(f->shared)));
    return f;
}
static enum gmf_result run(struct fake *f,struct gmf_receipt *out)
{struct gmf_ops o=ops(f);return gmf_bootstrap_once(&f->channel,&o,&f->plan,out);}
static void stopped(struct fake *f)
{unsigned step=f->step;struct gmf_receipt out,before;memset(&out,0x7c,sizeof(out));before=out;CHECK(run(f,&out)==GMF_ALREADY&&f->step==step&&!memcmp(&out,&before,sizeof(out)));}
static void happy(void)
{
    for(unsigned debug=0;debug<2;debug++){
        struct fake *f=fresh();f->debug=debug;f->nested=true;f->init_positive=debug;struct gmf_receipt r;
        CHECK(run(f,&r)==GMF_OK&&r.phase==GMF_DONE&&r.fw_result==0xbabeface);
        CHECK(r.reported_version==0x100b0000&&r.init_ack[1]==0x00100500&&r.version_ack[1]==0x00200201);
        CHECK(r.tcm_written==8192&&r.tcm_checked==8192&&r.writes==f->writes&&f->doorbells==2&&f->reset_writes==1);
        CHECK(r.debug_messages==(debug?4u:0u));stopped(f);
        printf("Legacy GMU bootstrap debug%u: native sequence and two real ring ACKs, %u boundaries PASS\n",debug,f->step);free(f);
    }
}
static void bad(void)
{
    for(unsigned mode=0;mode<20;mode++){
        struct fake *f=fresh();enum gmf_result expected;
        if(mode<3){f->bad_asset=mode+1;expected=GMF_ASSET;}
        else if(mode<6){f->bad_version=mode-2;expected=GMF_VERSION;}
        else if(mode<10){f->bad_ack=mode-5;expected=GMF_ACK;}
        else if(mode<15){f->timeout=mode-9;expected=GMF_TIMEOUT;}
        else if(mode<17){f->fw_fault=mode-14;expected=GMF_FAULT;}
        else {expected=GMF_INHERITED;if(mode==17)f->regs[GMF_AO][0x1404/4]=1;if(mode==18)f->regs[GMF_PDC][0x15c8/4]=1;if(mode==19)f->regs[GMF_CSR][0x2600/4]=1;}
        struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==expected&&!memcmp(&r,&b,sizeof(r)));stopped(f);free(f);
    }
    struct fake *f=fresh();struct gmf_receipt r;struct gmf_ops o=ops(f);
    CHECK(gmf_bootstrap_once(&f->channel,&o,&f->plan,(void *)&f->channel)==GMF_ARGUMENT&&!f->step);
    f->plan.selector[GMF_MX]--;CHECK(run(f,&r)==GMF_ARGUMENT&&!f->step);free(f);
}
static void faults(void)
{
    struct fake *f=fresh();struct gmf_receipt r;CHECK(run(f,&r)==GMF_OK);unsigned steps=f->step;free(f);
    for(unsigned n=1;n<=steps;n++){
        f=fresh();f->fail=n;struct gmf_receipt old;memset(&r,0x87,sizeof(r));old=r;
        CHECK(run(f,&r)!=GMF_OK&&!memcmp(&r,&old,sizeof(r)));stopped(f);free(f);
    }
    printf("GMU bootstrap fail-every-callback: %u boundaries PASS\n",steps);
}
int main(void){happy();bad();faults();printf("GMU firmware bootstrap: %u checks PASS\n",checks);}
