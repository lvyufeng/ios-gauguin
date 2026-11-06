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
    unsigned ignore,timeout,bad_asset,bad_version,bad_ack,fw_fault,debug,init_positive,bad_readback,sticky_oob,hidden_mode,hidden_fault,pdc_mode,pdc_bad,pdc_clear,pdc_allones,ao_override,cm3_override;
    uint32_t ao_readback,cm3_readback;
    unsigned cache_stores,cache_bad,cache_override;uint32_t cache_readback,cache_raw[3];
    unsigned inject_queue,inject_words,flood_queue,response_flood,response_wide,version_status,drain_sticky,after_init_drain;
    uint32_t inject_data[19];
    unsigned native_ack,native_words[2],native_echo,native_bad_seq,native_bad_type,native_bad_queue;
    uint32_t native_status[2];
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
{
    struct fake *f=cookie;CHECK(w<GMF_WINDOWS&&!(off&3)&&off<(w==GMF_TCM?0xc000u:0x4000u));
    if(!tick(f))return false;*v=f->regs[w][off/4];
    if(f->bad_readback&&w==GMF_AO&&off==0x1038)*v=0x12340000;
    if(w==GMF_AO&&(off==0x1034||off==0x103c||off==0x1044)){
        unsigned n=(off-0x1034)/8;static const uint32_t raw[]={0x82204514,0x12345678,0x60001000};
        if(f->hidden_mode)*v=raw[n];if(f->hidden_fault==n+1)*v=UINT32_MAX;
    }
    if(w==GMF_AO&&off==0x2c18&&f->ao_override)*v=f->ao_readback;
    if(w==GMF_CSR&&off==0x20b4&&f->cm3_override)*v=f->cm3_readback;
    if(w==GMF_PDC)for(unsigned n=0;n<6;n++){
        unsigned address=n<3?0x15d4+16*n:0x1764+16*(n-3);
        if(off!=address)continue;
        if(f->pdc_mode)*v=(*v&~8u)|(f->pdc_mode==2?0x80000000u:0);
        if(f->pdc_bad==n+1)*v&=~f->pdc_clear;
        if(f->pdc_allones==n+1)*v=UINT32_MAX;
    }
    if(w==GMF_CSR&&f->cache_override){
        static const unsigned offsets[]={0x103c,0x1000,0x1004};
        for(unsigned n=0;n<3;n++)if(off==offsets[n])*v=f->cache_raw[n];
    }
    if(w==GMF_CSR&&f->cache_bad){
        static const unsigned offsets[]={0x103c,0x1000,0x1004};
        CHECK(f->cache_bad<=3);
        if(off==offsets[f->cache_bad-1])*v=f->cache_readback;
    }
    return true;
}
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
    if(f->response_flood){uint32_t msg=0x10165;for(unsigned i=0;i<16;i++)reply(f,1,&msg,1);return;}
    if(f->native_ack){
        unsigned n=f->native_words[id];CHECK(n<=20);uint32_t raw[20];
        for(unsigned i=0;i<20;i++)raw[i]=0xc5000000u+i;
        raw[0]=(2u<<16)|(n<<8)|126u;raw[1]=header&GMF_ACK_SEQUENCE_MASK;
        if(f->native_echo==1)raw[1]=header;
        if(f->native_echo==2)raw[1]|=0x000fffffu; /* Other echoed bits unqualified. */
        if(f->native_bad_seq)raw[1]^=0x100000;
        if(f->native_bad_type)raw[0]^=3u<<16;
        raw[2]=f->native_status[id];raw[3]=id?0x100b0000u:0xabcd1234u; /* Synthetic INIT tail. */
        reply(f,1,raw,n?n:1);
        if(f->native_bad_queue)f->shared[28]=1024;
        return;
    }
    if(f->response_wide){
        uint32_t wide[19];for(unsigned i=0;i<19;i++)wide[i]=0xa5000000u+i;
        wide[0]=((id+1)<<20)|(2<<16)|(19<<8)|126;wide[1]=header^0x100000;
        reply(f,1,wide,19);return;
    }
    unsigned n=id?4:3;
    uint32_t ack[4]={((id+1)<<20)|(2<<16)|(n<<8)|126,header,id?0:f->init_positive,0x100b0000};
    if(f->bad_ack==1)ack[1]^=0x100000;
    if(f->bad_ack==2)ack[2]=UINT32_MAX;
    if(f->bad_ack==3)ack[0]^=3u<<16;
    if(f->bad_ack==4){ack[0]=(ack[0]&~0xff00u)|0x200;n=2;}
    if(id&&f->version_status)ack[2]=1;
    if(id&&f->bad_version==2)ack[3]=0x100a0000;
    if(id&&f->bad_version==3)ack[3]=0x200b0000;
    reply(f,1,ack,n);
    if(!id&&f->after_init_drain)reply(f,1,f->inject_data,f->inject_words);
}
static bool write_word(void *cookie,enum gmf_window w,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;CHECK(w<GMF_WINDOWS&&!(off&3)&&off<(w==GMF_TCM?0xc000u:0x4000u));
    if(!tick(f))return false;++f->writes;
    if(w==GMF_CSR&&(off==0x103c||off==0x1000||off==0x1004)){
        /* Exact native power_config order; every prefix failure stays bounded. */
        static const unsigned order[]={0x103c,0x1000,0x1004};
        CHECK(f->channel.phase==GMF_RESET&&value==1&&f->cache_stores<3);
        CHECK(off==order[f->cache_stores++]);
    }
    if(f->ignore==f->writes)return true;
    if(w==GMF_CSR&&off==0x2644){if((!f->sticky_oob||value!=(1u<<30))&&(!f->drain_sticky||value!=4))f->regs[w][0x2648/4]&=~value;return true;}
    if(w==GMF_AO&&off==0x2c10){f->regs[w][0x2c14/4]&=~value;return true;}
    f->regs[w][off/4]=value;
    if(w==GMF_CSR&&off==0x2000){
        CHECK(value==0&&f->channel.phase==GMF_RELEASING&&++f->reset_writes==1);
        CHECK(f->copy_calls==1&&f->regs[GMF_GBIF][0x3114/4]==0);
        CHECK(f->cache_stores==3);
        static const unsigned boot_offsets[]={0x103c,0x1000,0x1004};
        for(unsigned n=0;n<3;n++)CHECK(f->regs[GMF_CSR][boot_offsets[n]/4]==(f->ignore==62+n?0u:1u));
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
        if(f->inject_queue)reply(f,f->inject_queue,f->inject_data,f->inject_words);
        if(f->flood_queue){uint32_t msg=0x10165;for(unsigned i=0;i<16;i++)reply(f,f->flood_queue,&msg,1);}
        if(f->drain_sticky)f->regs[w][0x2648/4]|=4;
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
    f->native_words[0]=f->native_words[1]=4;
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
{unsigned step=f->step;struct gmf_receipt out,before;struct gmf_diagnostic diagnostic=f->channel.diagnostic;struct gmf_reply_diagnostic reply_diagnostic=f->channel.reply_diagnostic;uint32_t mask=f->channel.hidden_valid,raw[3],pdc_mask=f->channel.pdc_msgid_valid,pdc[6],ao_valid=f->channel.ao_mask_valid,ao_raw=f->channel.ao_mask_readback,cfg_valid=f->channel.cm3_config_valid,cfg_raw=f->channel.cm3_config_readback,boot_valid=f->channel.boot_config_valid,boot_raw[3];memcpy(boot_raw,f->channel.boot_config_readback,sizeof(boot_raw));memcpy(raw,f->channel.hidden_readback,sizeof(raw));memcpy(pdc,f->channel.pdc_msgid_readback,sizeof(pdc));memset(&out,0x7c,sizeof(out));before=out;CHECK(run(f,&out)==GMF_ALREADY&&f->step==step&&!memcmp(&out,&before,sizeof(out)));CHECK(!memcmp(&diagnostic,&f->channel.diagnostic,sizeof(diagnostic)));CHECK(!memcmp(&reply_diagnostic,&f->channel.reply_diagnostic,sizeof(reply_diagnostic)));CHECK(mask==f->channel.hidden_valid&&!memcmp(raw,f->channel.hidden_readback,sizeof(raw)));CHECK(pdc_mask==f->channel.pdc_msgid_valid&&!memcmp(pdc,f->channel.pdc_msgid_readback,sizeof(pdc)));CHECK(ao_valid==f->channel.ao_mask_valid&&ao_raw==f->channel.ao_mask_readback);CHECK(cfg_valid==f->channel.cm3_config_valid&&cfg_raw==f->channel.cm3_config_readback);CHECK(boot_valid==f->channel.boot_config_valid&&!memcmp(boot_raw,f->channel.boot_config_readback,sizeof(boot_raw)));}
static void happy(void)
{
    for(unsigned debug=0;debug<2;debug++){
        struct fake *f=fresh();f->debug=debug;f->nested=true;f->init_positive=debug;struct gmf_receipt r;
        CHECK(run(f,&r)==GMF_OK&&r.phase==GMF_DONE&&r.fw_result==0xbabeface);
        CHECK(r.reported_version==0x100b0000&&r.init_ack[1]==0x00100500&&r.version_ack[1]==0x00200201);
        CHECK(r.tcm_written==8192&&r.tcm_checked==8192&&r.writes==f->writes&&f->doorbells==2&&f->reset_writes==1);
        CHECK(!f->channel.reply_diagnostic.valid);CHECK(r.debug_messages==(debug?4u:0u)&&!f->channel.diagnostic.valid&&f->channel.hidden_valid==7&&f->channel.pdc_msgid_valid==63&&f->channel.ao_mask_valid==1&&f->channel.ao_mask_readback==UINT32_MAX&&f->channel.cm3_config_valid==1&&f->channel.cm3_config_readback==0x4052);stopped(f);
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
        CHECK(run(f,&r)!=GMF_OK&&!memcmp(&r,&old,sizeof(r))&&!f->channel.reply_diagnostic.valid);stopped(f);free(f);
    }
    printf("GMU bootstrap fail-every-callback: %u boundaries PASS\n",steps);
}
static void readback_diagnostics(void)
{
    for(unsigned mode=0;mode<2;mode++){
        struct fake *f=fresh();if(mode)f->sticky_oob=1;else f->bad_readback=1;
        struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_READBACK&&!memcmp(&r,&b,sizeof(r)));
        const struct gmf_diagnostic *d=&f->channel.diagnostic;
        CHECK(d->valid==1&&d->phase==(mode?GMF_GX_REQUEST:GMF_RESET));
        CHECK(d->check==(mode?GMFD_OOB_CLEAR:GMFD_STORE32)&&d->window==(mode?GMF_CSR:GMF_AO));
        CHECK(d->offset==(mode?0x2648u:0x1038u)&&d->mask==(mode?(1u<<30):UINT32_MAX));
        CHECK(d->expected==0&&d->actual==(mode?(1u<<30):0x12340000u));
        CHECK(f->reset_writes==(mode?1u:0u)&&f->copy_calls==(mode?1u:0u));
        if(!mode)CHECK(f->writes==4);
        stopped(f);free(f);
    }
    printf("GMU cached READBACK: exact store and OOB-clear tuples; repeat/output preservation PASS (synthetic observations)\n");
}
static void native_hidden_addresses(void)
{
    struct fake *f=fresh();f->hidden_mode=1;struct gmf_receipt r;
    CHECK(run(f,&r)==GMF_OK&&f->channel.hidden_valid==7&&!f->channel.diagnostic.valid);
    CHECK(f->channel.hidden_readback[0]==0x82204514&&f->channel.hidden_readback[1]==0x12345678&&f->channel.hidden_readback[2]==0x60001000);
    CHECK(f->reset_writes==1&&r.tcm_written==8192&&r.version_ack[1]==0x00200201);stopped(f);free(f);
    for(unsigned n=0;n<3;n++){
        f=fresh();f->hidden_mode=1;f->hidden_fault=n+1;struct gmf_receipt b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_READBACK&&!memcmp(&r,&b,sizeof(r)));
        const struct gmf_diagnostic *d=&f->channel.diagnostic;
        CHECK(d->valid&&d->phase==GMF_RESET&&d->check==GMFD_STORE32&&d->window==GMF_AO);
        CHECK(d->offset==0x1034+8*n&&d->mask==UINT32_MAX&&d->expected==0&&d->actual==UINT32_MAX);
        CHECK(f->channel.hidden_valid==(1u<<n)-1&&!f->reset_writes&&!f->copy_calls);stopped(f);free(f);
    }
    printf("Native hidden-address policy: three cached unqualified values, all-ones refusal at each address, repeat/output preservation PASS (host only)\n");
}
static void pdc_msgid_fields(void)
{
    CHECK(GMF_PDC_MSGID_FIELDS==0x10100);
    for(unsigned mode=1;mode<=2;mode++){
        struct fake *f=fresh();f->pdc_mode=mode;f->hidden_mode=1;struct gmf_receipt r;
        CHECK(run(f,&r)==GMF_OK&&f->channel.pdc_msgid_valid==63&&!f->channel.diagnostic.valid);
        for(unsigned n=0;n<6;n++)CHECK(f->channel.pdc_msgid_readback[n]==(0x10100u|(mode==2?0x80000000u:0)));
        CHECK(f->reset_writes==1&&r.tcm_written==8192&&r.version_ack[1]==0x00200201);stopped(f);free(f);
    }
    for(unsigned n=0;n<6;n++)for(unsigned mode=0;mode<3;mode++){
        struct fake *f=fresh();f->pdc_mode=1;
        if(mode==2)f->pdc_allones=n+1;else {f->pdc_bad=n+1;f->pdc_clear=mode?(1u<<8):(1u<<16);}
        struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_READBACK&&!memcmp(&r,&b,sizeof(r)));
        const struct gmf_diagnostic *d=&f->channel.diagnostic;
        CHECK(d->valid&&d->phase==GMF_RESET&&d->check==GMFD_STORE32&&d->window==GMF_PDC);
        CHECK(d->offset==(n<3?0x15d4+16*n:0x1764+16*(n-3)));
        CHECK(d->mask==(mode==2?UINT32_MAX:0x10100u)&&d->expected==(mode==2?0x10108u:0x10100u));
        CHECK(d->actual==(mode==2?UINT32_MAX:(0x10100u&~f->pdc_clear)));
        CHECK(f->channel.pdc_msgid_valid==(1u<<n)-1&&!f->reset_writes&&!f->copy_calls);stopped(f);free(f);
    }
    printf("PDC MSGID: six native writes retain named control fields, other bits unqualified; each missing control bit/all-ones refuses before copy/release PASS (host only)\n");
}
static void ao_mask_fields(void)
{
    CHECK(GMF_AO_IRQ_FIELDS==0x3b);
    static const uint32_t values[]={0x3f,0x3b,0x8000003b,UINT32_MAX};
    for(unsigned n=0;n<sizeof(values)/sizeof(*values);n++){
        struct fake *f=fresh();f->ao_override=1;f->ao_readback=values[n];f->hidden_mode=1;f->pdc_mode=1;struct gmf_receipt r;
        CHECK(run(f,&r)==GMF_OK&&f->channel.ao_mask_valid==1&&f->channel.ao_mask_readback==values[n]&&!f->channel.diagnostic.valid);
        CHECK(f->reset_writes==1&&r.tcm_written==8192&&r.version_ack[1]==0x00200201);stopped(f);free(f);
    }
    static const unsigned bits[]={0,1,3,4,5};
    for(unsigned n=0;n<=sizeof(bits)/sizeof(*bits);n++){
        struct fake *f=fresh();f->ao_override=1;f->ao_readback=n<sizeof(bits)/sizeof(*bits)?0x3fu&~(1u<<bits[n]):0;
        struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_READBACK&&!memcmp(&r,&b,sizeof(r)));
        const struct gmf_diagnostic *d=&f->channel.diagnostic;
        CHECK(d->valid&&d->phase==GMF_RESET&&d->check==GMFD_STORE32&&d->window==GMF_AO);
        CHECK(d->offset==0x2c18&&d->mask==0x3b&&d->expected==0x3b&&d->actual==f->ao_readback);
        CHECK(!f->channel.ao_mask_valid&&!f->reset_writes&&f->copy_calls==1);stopped(f);free(f);
    }
    printf("AO IRQ mask: all five named sources required, raw3f/full mask/synthetic other bits retained, repeat/output preservation PASS (host only)\n");
}
static void cm3_config_fields(void)
{
    CHECK(GMF_CM3_NMI==(1u<<9));
    static const uint32_t good[]={0x52,0x4052,0x80000052};
    for(unsigned n=0;n<sizeof(good)/sizeof(*good);n++){
        struct fake *f=fresh();f->cm3_override=1;f->cm3_readback=good[n];f->ao_override=1;f->ao_readback=0x3f;f->hidden_mode=1;f->pdc_mode=1;struct gmf_receipt r;
        CHECK(run(f,&r)==GMF_OK&&f->channel.cm3_config_valid==1&&f->channel.cm3_config_readback==good[n]&&!f->channel.diagnostic.valid);
        CHECK(f->reset_writes==1&&r.tcm_written==8192&&r.version_ack[1]==0x00200201);stopped(f);free(f);
    }
    static const uint32_t bad[]={0x252,0x4252,UINT32_MAX};
    for(unsigned n=0;n<sizeof(bad)/sizeof(*bad);n++){
        struct fake *f=fresh();f->cm3_override=1;f->cm3_readback=bad[n];struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_READBACK&&!memcmp(&r,&b,sizeof(r)));
        const struct gmf_diagnostic *d=&f->channel.diagnostic;
        CHECK(d->valid&&d->phase==GMF_RESET&&d->check==GMFD_STORE32&&d->window==GMF_CSR);
        CHECK(d->offset==0x20b4&&d->actual==bad[n]);
        CHECK(d->mask==(n==2?UINT32_MAX:0x200u)&&d->expected==(n==2?0x4052u:0));
        CHECK(!f->channel.cm3_config_valid&&!f->reset_writes&&f->copy_calls==1);stopped(f);free(f);
    }
    printf("CM3 CFG: native4052 write, documented NMI9 clear, raw52/4052/synthetic other bits; NMI/all-ones refuse before release PASS (host only)\n");
}
static void native_bus_cache_order(void)
{
    static const unsigned offsets[]={0x103c,0x1000,0x1004};
    static const uint32_t observed[]={0,1,2,0x80000000,0xfffffffe};
    for(unsigned n=0;n<3;n++)for(unsigned k=0;k<sizeof(observed)/sizeof(*observed);k++){
        struct fake *f=fresh();f->cache_bad=n+1;f->cache_readback=observed[k];
        f->cm3_override=1;f->cm3_readback=0x52;f->ao_override=1;f->ao_readback=0x3f;f->pdc_mode=1;f->hidden_mode=1;
        struct gmf_receipt r;CHECK(run(f,&r)==GMF_OK&&f->cache_stores==3&&f->reset_writes==1&&!f->channel.diagnostic.valid);
        CHECK(f->channel.boot_config_valid==7&&r.tcm_written==8192&&r.version_ack[1]==0x00200201);
        for(unsigned i=0;i<3;i++)CHECK(f->channel.boot_config_readback[i]==(i==n?observed[k]:1u));
        stopped(f);free(f);
    }
    for(unsigned n=0;n<3;n++){
        struct fake *f=fresh();f->cache_bad=n+1;f->cache_readback=UINT32_MAX;
        struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_READBACK&&!memcmp(&r,&b,sizeof(r)));
        const struct gmf_diagnostic *d=&f->channel.diagnostic;
        CHECK(d->valid&&d->phase==GMF_RESET&&d->check==GMFD_STORE32&&d->window==GMF_CSR);
        CHECK(d->offset==offsets[n]&&d->mask==UINT32_MAX&&d->expected==1&&d->actual==UINT32_MAX);
        CHECK(f->channel.boot_config_valid==(1u<<n)-1&&f->cache_stores==n+1&&f->writes==62+n&&!f->reset_writes&&!f->doorbells&&f->copy_calls==1);
        for(unsigned i=0;i<3;i++)CHECK(f->channel.boot_config_readback[i]==(i<n?1u:0u));
        stopped(f);free(f);
    }
    /* Callback success does not prove a write took effect: retain zero as
     * unqualified, and rely on separately required fresh result/real ACKs.
     * This fixture synthesizes firmware replies; it is not hardware proof. */
    for(unsigned n=0;n<3;n++){
        struct fake *f=fresh();f->ignore=62+n;struct gmf_receipt r;
        CHECK(run(f,&r)==GMF_OK&&f->cache_stores==3&&f->reset_writes==1);
        CHECK(f->channel.boot_config_valid==7&&f->channel.boot_config_readback[n]==0);
        CHECK(r.fw_result==0xbabeface&&r.version_ack[1]==0x00200201);stopped(f);free(f);
    }
    for(unsigned n=0;n<2;n++){
        struct fake *f=fresh();f->cache_override=1;f->timeout=n?4:1;
        struct gmf_receipt r,b;memset(&r,0x71,sizeof(r));b=r;
        CHECK(run(f,&r)==GMF_TIMEOUT&&!memcmp(&r,&b,sizeof(r)));
        CHECK(f->channel.boot_config_valid==7&&!f->channel.diagnostic.valid&&f->reset_writes==1);
        for(unsigned i=0;i<3;i++)CHECK(f->channel.boot_config_readback[i]==0);
        stopped(f);free(f);
    }
    printf("Native boot CFG: exact BUS/ICACHE/DCACHE fixed1 order, raw0/1/synthetic bits unqualified, per-slot all-ones refusal; repeat/cache/output and mandatory FW/ACK checks PASS (host only)\n");
}
static void reply_failed(struct fake *f,unsigned site,unsigned reason,unsigned queue,
    uint32_t request,unsigned expected,const uint32_t *data,unsigned words)
{
    struct gmf_receipt out,before;memset(&out,0x71,sizeof(out));before=out;
    CHECK(run(f,&out)==GMF_ACK&&!memcmp(&out,&before,sizeof(out)));
    const struct gmf_reply_diagnostic *d=&f->channel.reply_diagnostic;
    CHECK(d->valid==1&&d->phase==GMF_HANDSHAKE&&d->site==site&&d->reason==reason&&d->queue==queue);
    CHECK(d->request_header==request&&d->expected_words==expected&&d->words==words&&d->captured==words);
    for(unsigned i=0;i<GMF_REPLY_WORDS;i++)CHECK(d->data[i]==(i<words?data[i]:0));
    CHECK(f->channel.state==3&&!f->channel.diagnostic.valid);stopped(f);
}
static void hfi_reply_diagnostics(void)
{
    CHECK(GMF_REPLY_WORDS==19);
    /* Drain a refused packet on either queue before the INIT doorbell. */
    for(unsigned queue=1;queue<=2;queue++)for(unsigned mode=0;mode<3;mode++){
        struct fake *f=fresh();f->inject_queue=queue;f->inject_words=mode==2?19:mode?1:3;
        for(unsigned i=0;i<f->inject_words;i++)f->inject_data[i]=0xc5000000u+i;
        f->inject_data[0]=mode==2?(1u<<16)|(19u<<8)|102u:mode?(2u<<16)|(1u<<8)|126u:(2u<<16)|(3u<<8)|126u;
        reply_failed(f,GMFR_DRAIN,mode==2?GMFR_UNEXPECTED_MESSAGE:GMFR_UNEXPECTED_ACK,queue,0x00100500,3,f->inject_data,f->inject_words);
        CHECK(!f->doorbells);free(f);
    }
    static const unsigned reason[]={GMFR_ECHO,GMFR_STATUS,GMFR_UNEXPECTED_MESSAGE,GMFR_SIZE};
    for(unsigned mode=1;mode<=4;mode++){
        struct fake *f=fresh();f->bad_ack=mode;
        uint32_t data[3]={0x0012037e,0x00100500,0};unsigned words=3;
        if(mode==1)data[1]^=0x100000;if(mode==2)data[2]=UINT32_MAX;
        if(mode==3)data[0]^=3u<<16;if(mode==4){data[0]=0x0012027e;words=2;}
        reply_failed(f,GMFR_REQUEST,reason[mode-1],1,0x00100500,3,data,words);CHECK(f->doorbells==1);free(f);
    }
    /* Phase5/GMF_ACK can also occur after a valid INIT ACK while draining
     * before VERSION, with just one command doorbell. Capture that context. */
    for(unsigned mode=0;mode<2;mode++){
        struct fake *f=fresh();f->after_init_drain=1;f->inject_words=mode?1:3;
        f->inject_data[0]=mode?0x10166:0x0012037e;f->inject_data[1]=0x00100500;f->inject_data[2]=0;
        reply_failed(f,GMFR_DRAIN,mode?GMFR_UNEXPECTED_MESSAGE:GMFR_UNEXPECTED_ACK,1,0x00200201,4,f->inject_data,f->inject_words);
        CHECK(f->doorbells==1&&f->channel.work.init_ack[1]==0x00100500);free(f);
    }
    struct fake *f=fresh();f->version_status=1;
    const uint32_t version_bad[]={0x0022047e,0x00200201,1,0x100b0000};
    reply_failed(f,GMFR_REQUEST,GMFR_VERSION_STATUS,1,0x00200201,4,version_bad,4);CHECK(f->doorbells==2);free(f);
    f=fresh();f->response_wide=1;uint32_t wide[19];for(unsigned i=0;i<19;i++)wide[i]=0xa5000000u+i;
    wide[0]=0x0012137e;wide[1]=0x00000500;
    reply_failed(f,GMFR_REQUEST,GMFR_ECHO,1,0x00100500,3,wide,19);free(f);
    for(unsigned queue=1;queue<=2;queue++){
        f=fresh();f->flood_queue=queue;uint32_t debug=0x10165;
        reply_failed(f,GMFR_DRAIN,GMFR_LIMIT,queue,0x00100500,3,&debug,1);CHECK(!f->doorbells&&f->channel.work.debug_messages==16);free(f);
    }
    f=fresh();f->drain_sticky=1;
    reply_failed(f,GMFR_DRAIN,GMFR_LIMIT,2,0x00100500,3,NULL,0);CHECK(!f->doorbells);free(f);
    f=fresh();f->response_flood=1;uint32_t debug=0x10165;
    reply_failed(f,GMFR_REQUEST,GMFR_LIMIT,1,0x00100500,3,&debug,1);CHECK(f->doorbells==1&&f->channel.work.debug_messages==16);free(f);
    /* Invalid arguments preserve stale private bytes; first acquired run clears
     * them. Successful ACKs never become refused-packet diagnostics. */
    f=fresh();memset(&f->channel.reply_diagnostic,0xa5,sizeof(f->channel.reply_diagnostic));
    struct gmf_reply_diagnostic before=f->channel.reply_diagnostic,zero={0};struct gmf_receipt out;
    f->plan.selector[GMF_MX]--;CHECK(run(f,&out)==GMF_ARGUMENT&&!memcmp(&before,&f->channel.reply_diagnostic,sizeof(before)));
    f->plan.selector[GMF_MX]++;CHECK(run(f,&out)==GMF_OK&&!memcmp(&zero,&f->channel.reply_diagnostic,sizeof(zero)));stopped(f);free(f);
    printf("HFI refused-packet diagnostics: both sites/queues, each reason,19-word/short/no-packet bounds, first-claim clear, repeat/output and no success cache PASS (host only)\n");
}
static void native_ack_compatibility(void)
{
    CHECK(GMF_ACK_SEQUENCE_MASK==0xfff00000u);
    /* Captured137 packet shape: type2/INIT4/sequence-only echo/status0.
     * Its opaque fourth word here is synthetic and is never interpreted. */
    for(unsigned mode=0;mode<3;mode++)for(unsigned words=3;words<=19;words++){
        struct fake *f=fresh();f->native_ack=1;f->native_echo=mode;
        f->native_words[0]=words;f->native_words[1]=words<4?4:words;
        struct gmf_receipt out;CHECK(run(f,&out)==GMF_OK&&!f->channel.reply_diagnostic.valid);
        CHECK(out.phase==GMF_DONE&&out.init_ack[2]==0&&out.version_ack[2]==0&&out.reported_version==0x100b0000);
        CHECK(((out.init_ack[0]>>8)&255)==words&&((out.version_ack[0]>>8)&255)==f->native_words[1]);
        CHECK((out.init_ack[1]&GMF_ACK_SEQUENCE_MASK)==0x00100000&&(out.version_ack[1]&GMF_ACK_SEQUENCE_MASK)==0x00200000);
        CHECK(f->doorbells==2&&f->reset_writes==1);stopped(f);free(f);
    }
    struct fake *f=fresh();f->native_ack=1;f->native_status[0]=7;struct gmf_receipt out;
    CHECK(run(f,&out)==GMF_OK&&out.init_ack[2]==7&&out.version_ack[2]==0&&!f->channel.reply_diagnostic.valid);stopped(f);free(f);
    for(unsigned command=0;command<2;command++)for(unsigned words=0;words<(command?4u:3u);words++){
        f=fresh();f->native_ack=1;f->native_words[command]=words;struct gmf_receipt before;
        memset(&out,0x71,sizeof(out));before=out;
        CHECK(run(f,&out)==(words?GMF_ACK:GMF_TRANSPORT)&&!memcmp(&out,&before,sizeof(out)));
        if(words){
            const struct gmf_reply_diagnostic *d=&f->channel.reply_diagnostic;
            CHECK(d->valid&&d->site==GMFR_REQUEST&&d->reason==GMFR_SIZE&&d->words==words&&d->captured==words);
            CHECK(d->request_header==(command?0x00200201u:0x00100500u)&&d->expected_words==(command?4u:3u));
        }else CHECK(!f->channel.reply_diagnostic.valid);
        /* No extra INIT payload may spill into the VERSION public prefix. */
        for(unsigned i=0;i<4;i++)CHECK(f->channel.work.version_ack[i]==0);
        stopped(f);free(f);
    }
    for(unsigned command=0;command<2;command++){
        f=fresh();f->native_ack=1;f->native_words[command]=20;struct gmf_receipt before;
        memset(&out,0x71,sizeof(out));before=out;
        CHECK(run(f,&out)==GMF_TRANSPORT&&!memcmp(&out,&before,sizeof(out))&&!f->channel.reply_diagnostic.valid);stopped(f);free(f);
    }
    f=fresh();f->native_ack=1;f->native_bad_seq=1;
    const uint32_t wrong_seq[]={0x0002047e,0,0,0xabcd1234};
    reply_failed(f,GMFR_REQUEST,GMFR_ECHO,1,0x00100500,3,wrong_seq,4);free(f);
    f=fresh();f->native_ack=1;f->native_status[0]=UINT32_MAX;
    const uint32_t bad_init[]={0x0002047e,0x00100000,UINT32_MAX,0xabcd1234};
    reply_failed(f,GMFR_REQUEST,GMFR_STATUS,1,0x00100500,3,bad_init,4);free(f);
    f=fresh();f->native_ack=1;f->native_status[1]=1;
    const uint32_t bad_version[]={0x0002047e,0x00200000,1,0x100b0000};
    reply_failed(f,GMFR_REQUEST,GMFR_VERSION_STATUS,1,0x00200201,4,bad_version,4);free(f);
    f=fresh();f->native_ack=1;f->native_status[1]=UINT32_MAX;
    const uint32_t failed_version[]={0x0002047e,0x00200000,UINT32_MAX,0x100b0000};
    reply_failed(f,GMFR_REQUEST,GMFR_STATUS,1,0x00200201,4,failed_version,4);free(f);
    f=fresh();f->native_ack=1;f->native_bad_type=1;
    const uint32_t wrong_type[]={0x0001047e,0x00100000,0,0xabcd1234};
    reply_failed(f,GMFR_REQUEST,GMFR_UNEXPECTED_MESSAGE,1,0x00100500,3,wrong_type,4);free(f);
    f=fresh();f->native_ack=1;f->native_bad_queue=1;struct gmf_receipt before;
    memset(&out,0x71,sizeof(out));before=out;
    CHECK(run(f,&out)==GMF_TRANSPORT&&!memcmp(&out,&before,sizeof(out))&&!f->channel.reply_diagnostic.valid);stopped(f);free(f);
    printf("Native ACK compatibility: observed INIT4 shape,3..19/4..19 prefixes, sequence-only echo and opaque tail; short/oversize/type/sequence/status/queue failures preserve output/cache PASS (host only)\n");
}
static void native_perf_table(void)
{
    /* Independent fixed wire oracle: native hfi_dcvstable_v1_cmd has16 GX
     * pairs then4 CX pairs, even though only7/2 are active. The live800MHz
     * curve includes off; CX wanted MIN_SVS48 rounds to ARC64/MX64 index2. */
    const uint32_t golden[43]={
        0x00302b04,7,2,
        0,0,0x00400201,253000,0x00800302,355000,0x00c00403,430000,
        0x01000504,565000,0x01400605,650000,0x01800706,800000,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0x00400202,200000,0,0,0,0
    };
    CHECK(GMF_PERF_WORDS==43&&sizeof(struct gmf_perf_table)==172);
    struct fake *f=fresh();const struct gmf_plan p=f->plan;
    struct {uint32_t before;struct gmf_perf_table table;uint32_t after;} boxed;
    memset(&boxed,0xa6,sizeof(boxed));
    CHECK(gmf_perf_table_build(&p,3,&boxed.table));
    CHECK(!memcmp(boxed.table.word,golden,sizeof(golden)));
    CHECK(boxed.before==0xa6a6a6a6&&boxed.after==0xa6a6a6a6&&!memcmp(&p,&f->plan,sizeof(p)));
    for(uint32_t seq=1;seq<=4095;seq++){
        CHECK(gmf_perf_table_build(&p,seq,&boxed.table));
        CHECK(boxed.table.word[0]==((seq<<20)|0x2b04));
        CHECK(!memcmp(boxed.table.word+1,golden+1,sizeof(golden)-4));
    }
    const uint32_t invalid[]={0,4096,0x10000,0x80000000,UINT32_MAX};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++){
        struct gmf_perf_table before=boxed.table;
        CHECK(!gmf_perf_table_build(&p,invalid[i],&boxed.table));
        CHECK(!memcmp(&before,&boxed.table,sizeof(before)));
    }
    for(unsigned i=0;i<sizeof(p);i++){
        struct gmf_plan bad=p;((uint8_t *)&bad)[i]^=1;
        struct gmf_perf_table before=boxed.table;
        CHECK(!gmf_perf_table_build(&bad,3,&boxed.table));
        CHECK(!memcmp(&before,&boxed.table,sizeof(before)));
    }
    struct gmf_perf_table before=boxed.table;
    CHECK(!gmf_perf_table_build(NULL,3,&boxed.table));
    CHECK(!gmf_perf_table_build((const struct gmf_plan *)(uintptr_t)(UINTPTR_MAX-4),3,&boxed.table));
    CHECK(!memcmp(&before,&boxed.table,sizeof(before)));
    CHECK(!gmf_perf_table_build(&p,3,NULL));
    CHECK(!gmf_perf_table_build(&p,3,(struct gmf_perf_table *)(uintptr_t)(UINTPTR_MAX-4)));
    /* Every aligned overlap, including output beginning before the input. */
    for(unsigned off=0;off<sizeof(p);off+=4){
        union {uint32_t align;uint8_t bytes[768];} arena,saved;
        memset(&arena,0x91,sizeof(arena));memcpy(arena.bytes+256,&p,sizeof(p));saved=arena;
        CHECK(!gmf_perf_table_build((const struct gmf_plan *)(arena.bytes+256),3,(struct gmf_perf_table *)(arena.bytes+256+off)));
        CHECK(!memcmp(&arena,&saved,sizeof(arena)));
    }
    for(unsigned off=4;off<sizeof(struct gmf_perf_table);off+=4){
        union {uint32_t align;uint8_t bytes[768];} arena,saved;
        memset(&arena,0x91,sizeof(arena));memcpy(arena.bytes+256,&p,sizeof(p));saved=arena;
        CHECK(!gmf_perf_table_build((const struct gmf_plan *)(arena.bytes+256),3,(struct gmf_perf_table *)(arena.bytes+256-off)));
        CHECK(!memcmp(&arena,&saved,sizeof(arena)));
    }
    CHECK(!f->step&&!f->writes&&!f->doorbells&&!f->reset_writes&&!f->asset_calls&&!f->copy_calls);
    free(f);
    printf("Native v1 PERF bytes: captured800MHz/off curve,43-word golden,4095 sequences, invalid plan/sequence/span/alias preservation PASS (pure host construction, not firmware ACK)\n");
}
int main(void){native_perf_table();native_ack_compatibility();hfi_reply_diagnostics();native_bus_cache_order();happy();bad();readback_diagnostics();native_hidden_addresses();pdc_msgid_fields();ao_mask_fields();cm3_config_fields();faults();printf("GMU firmware bootstrap: %u checks PASS\n",checks);}
