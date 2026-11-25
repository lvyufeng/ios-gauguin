#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_gmu_firmware.h"
#include "cmd_db_snapshot.h"
static unsigned checks;
#define CHECK(x) do{assert(x);++checks;}while(0)
static void entries(struct ndb_entry e[4])
{
    static const char *names[]={"MC0","SH0","ACV","SN10"};
    static const uint32_t addr[]={0x50000,0x50004,0x50080,0x50054},unit[]={2050000,3650000,1,530000};
    static const unsigned width[]={16,32,0,8},vcd[]={0,1,11,3};
    memset(e,0,4*sizeof(*e));
    for(unsigned i=0;i<4;i++){
        strcpy(e[i].name,names[i]);e[i].address=addr[i];e[i].owner_slave=5;e[i].bank_version=0x1000;e[i].aux_length=8;
        for(unsigned j=0;j<4;j++)e[i].aux[j]=(uint8_t)(unit[i]>>(8*j));
        e[i].aux[4]=width[i];e[i].aux[6]=vcd[i];
    }
}
static void wire(void)
{
    /* Independent captured-input native query oracle results. Table remains
     * CPU-only; these words do not establish a hardware bandwidth or ACK. */
    const uint32_t mc[]={0,0x30c,0x618,0x925,0xdc1,0x10ad,0x14c3,0x176a,0x1f01,0x2940,0x2f68,0x3700,0x3fce};
    const uint32_t sh[]={0,0xdb,0x1b6,0x291,0x3dc,0x4ae,0x5d4,0x693,0x8b5,0xb95,0xd50,0xf71,0x11ea};
    struct ndb_entry e[4];entries(e);struct gmf_bw_plan p;CHECK(gmf_bw_plan_build(e,&p)&&gmf_bw_plan_valid(&p));
    struct {uint32_t before;struct gmf_bw_table out;uint32_t after;} box;
    memset(&box,0xa7,sizeof(box));CHECK(GMF_BW_WORDS==160&&sizeof(box.out)==640);
    CHECK(gmf_bw_table_build(&p,4,&box.out));
    CHECK(box.before==0xa7a7a7a7&&box.after==0xa7a7a7a7);
    uint32_t expected[160]={0};expected[0]=0x0040a003;expected[1]=13;expected[2]=1;expected[3]=3;
    expected[6]=0x50054;expected[12]=0x40000000;expected[18]=0x60000001;
    expected[24]=0x50000;expected[25]=0x50004;expected[26]=0x50080;
    for(unsigned i=0;i<13;i++){
        expected[32+8*i]=(i?0x60000000u:0x40000000u)|mc[i];
        expected[33+8*i]=(i?0x60000000u:0x40000000u)|sh[i];
        expected[34+8*i]=i?0x60000008u:0x40000000u;
    }
    CHECK(!memcmp(expected,box.out.word,sizeof(expected)));
    for(uint32_t seq=1;seq<=4095;seq++){
        CHECK(gmf_bw_table_build(&p,seq,&box.out));
        CHECK(box.out.word[0]==((seq<<20)|0xa003));
        CHECK(!memcmp(box.out.word+1,expected+1,sizeof(expected)-4));
    }
    for(unsigned i=0;i<4;i++){
        CHECK(p.db[i].bank_version==0x1000);
        e[i].bank_version=0xffff;
    }
    CHECK(gmf_bw_plan_build(e,&p));CHECK(gmf_bw_table_build(&p,4,&box.out));CHECK(!memcmp(box.out.word,expected,sizeof(expected)));
    printf("BW native wire:160 words,13 DDR/2 CNOC rows,VCD order/ACV/minimum rounding,zero waits/unused fields,4095 sequences and observed bank version PASS\n");
}
static void refusals(void)
{
    struct ndb_entry e[4];entries(e);struct gmf_bw_plan p,before;memset(&p,0x71,sizeof(p));before=p;
    for(unsigned row=0;row<4;row++)for(unsigned mode=0;mode<11;mode++){
        struct ndb_entry bad[4];memcpy(bad,e,sizeof(bad));
        if(mode==0)bad[row].name[0]^=1;
        if(mode==1)bad[row].name[8]=1;
        if(mode==2)bad[row].address^=4;
        if(mode==3)bad[row].owner_slave=3;
        if(mode==4)bad[row].aux_length=7;
        if(mode==5)bad[row].aux_length=9;
        if(mode==6)bad[row].aux[0]^=1;
        if(mode==7)bad[row].aux[4]^=1;
        if(mode==8)bad[row].aux[6]^=1;
        if(mode==9)bad[row].aux[7]=1;
        if(mode==10)memcpy(&bad[row],&e[(row+1)%4],sizeof(*e));
        CHECK(!gmf_bw_plan_build(bad,&p)&&!memcmp(&p,&before,sizeof(p)));
    }
    CHECK(!gmf_bw_plan_build(NULL,&p)&&!gmf_bw_plan_build(e,NULL));
    CHECK(!gmf_bw_plan_build((void *)(uintptr_t)(UINTPTR_MAX-4),&p));
    CHECK(!gmf_bw_plan_build(e,(void *)(uintptr_t)(UINTPTR_MAX-4)));
    CHECK(gmf_bw_plan_build(e,&p));struct gmf_bw_table out,saved;memset(&out,0x72,sizeof(out));saved=out;
    for(unsigned row=0;row<4;row++)for(unsigned mode=0;mode<5;mode++){
        struct gmf_bw_plan bad=p;
        if(mode==0)bad.db[row].address^=4;
        if(mode==1)bad.db[row].unit^=1;
        if(mode==2)bad.db[row].width^=1;
        if(mode==3)bad.db[row].vcd^=1;
        if(mode==4)bad.db[row].reserved=1;
        CHECK(!gmf_bw_plan_valid(&bad)&&!gmf_bw_table_build(&bad,4,&out)&&!memcmp(&out,&saved,sizeof(out)));
    }
    const uint32_t seq[]={0,4096,UINT32_MAX};for(unsigned i=0;i<3;i++)CHECK(!gmf_bw_table_build(&p,seq[i],&out)&&!memcmp(&out,&saved,sizeof(out)));
    CHECK(!gmf_bw_plan_valid(NULL)&&!gmf_bw_plan_valid((void *)(uintptr_t)(UINTPTR_MAX-4)));
    CHECK(!gmf_bw_table_build(NULL,4,&out)&&!gmf_bw_table_build(&p,4,NULL));
    CHECK(!gmf_bw_table_build((void *)(uintptr_t)(UINTPTR_MAX-4),4,&out));
    CHECK(!gmf_bw_table_build(&p,4,(void *)(uintptr_t)(UINTPTR_MAX-4)));
    for(unsigned off=0;off<sizeof(e);off+=4){
        union {uint32_t align;uint8_t bytes[2048];} arena,copy;memset(&arena,0x73,sizeof(arena));memcpy(arena.bytes+512,e,sizeof(e));copy=arena;
        CHECK(!gmf_bw_plan_build((void *)(arena.bytes+512),(void *)(arena.bytes+512+off))&&!memcmp(&arena,&copy,sizeof(arena)));
    }
    for(unsigned off=0;off<sizeof(p);off+=4){
        union {uint32_t align;uint8_t bytes[2048];} arena,copy;memset(&arena,0x74,sizeof(arena));memcpy(arena.bytes+768,&p,sizeof(p));copy=arena;
        CHECK(!gmf_bw_table_build((void *)(arena.bytes+768),4,(void *)(arena.bytes+768+off))&&!memcmp(&arena,&copy,sizeof(arena)));
    }
    for(unsigned off=4;off<sizeof(out);off+=4){
        union {uint32_t align;uint8_t bytes[2048];} arena,copy;memset(&arena,0x74,sizeof(arena));memcpy(arena.bytes+768,&p,sizeof(p));copy=arena;
        CHECK(!gmf_bw_table_build((void *)(arena.bytes+768),4,(void *)(arena.bytes+768-off))&&!memcmp(&arena,&copy,sizeof(arena)));
    }
    printf("BW policy refusals: per-entry name/owner/aux/resource and plan fields; bad sequences/null/wrap/overlap preserve outputs PASS\n");
}
int main(void){wire();refusals();printf("GMU bandwidth builder: %u checks PASS (pure CPU construction, no firmware ACK)\n",checks);}
