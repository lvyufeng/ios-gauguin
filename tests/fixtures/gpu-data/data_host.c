#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_data.h"
static unsigned checks,cases;
#define CHECK(x) do{assert(x);++checks;}while(0)
static uint64_t get64(const uint8_t *p)
{uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static uint64_t walk(const uint8_t *b,uint64_t base,uint32_t va)
{
    unsigned off=0;
    for(unsigned level=1;level<=3;level++){
        unsigned shift=level==1?30:level==2?21:12;
        uint64_t e=get64(b+off+8*((va>>shift)&511));if(!e)return 0;
        CHECK((e&3)==3);if(level==3)return e;
        uint64_t next=e&~UINT64_C(0xfff);CHECK((e&0xfff)==3&&next>=base&&next+4096<=base+GGP_TABLE_BYTES);off=(unsigned)(next-base);
    }
    abort();
}
static void good(uint64_t owner,bool exhaustive)
{
    struct ggm_plan gmu;struct ggp_plan p,saved;struct ggd_plan d;
    CHECK(ggm_plan_build(owner,&gmu)&&ggp_plan_build(&gmu,&p));saved=p;
    CHECK(ggd_plan_build(&p,&d)&&ggd_plan_valid(&d)&&!memcmp(&p,&saved,sizeof(p)));
    CHECK(!memcmp(&d.bootstrap,&p,sizeof(p))&&d.data.offset==GGP_ARENA_END);
    CHECK(d.data.offset+d.data.reserved==GGD_ARENA_END&&GGD_ARENA_END<=GGM_REGION_BYTES);
    CHECK(d.data.offset%16384==0&&d.data.reserved==16384&&d.data.mapped==4096);
    CHECK(!d.data.privileged&&!d.data.readonly&&!d.data.executable);
    for(unsigned i=0;i<GGP_COUNT;i++)CHECK(p.region[i].offset+p.region[i].reserved<=d.data.offset);
    for(unsigned i=0;i<GGM_COUNT;i++)CHECK(gmu.region[i].offset+gmu.region[i].reserved<=d.data.offset);
    uint8_t legacy[GGP_TABLE_BYTES],buf[GGP_TABLE_BYTES+128],before[sizeof(buf)];
    static const unsigned widths[]={32,36,40,42,44,48};
    for(unsigned ias=32;ias<=39;ias++)for(unsigned ips=0;ips<6;ips++){
        ++cases;struct ggp_s1_config old,c;
        CHECK(ggp_emit_tables(&p,ias,widths[ips],legacy,sizeof(legacy),&old));
        memset(buf,0x71,sizeof(buf));memcpy(before,buf,sizeof(buf));
        CHECK(ggd_emit_tables(&d,ias,widths[ips],buf+64,GGP_TABLE_BYTES,&c));
        uint64_t table[GGP_TABLE_BYTES/8],copy[GGP_TABLE_BYTES/8];memcpy(table,buf+64,sizeof(table));memcpy(copy,table,sizeof(copy));
        CHECK(ggd_tables_match(&d,table,sizeof(table))&&!memcmp(table,copy,sizeof(table)));
        if(exhaustive&&ias==39&&ips==1){
            for(unsigned slot=0;slot<GGP_TABLE_BYTES/8;slot++)for(unsigned bit=0;bit<64;bit++){
                ++cases;table[slot]^=UINT64_C(1)<<bit;CHECK(!ggd_tables_match(&d,table,sizeof(table)));table[slot]^=UINT64_C(1)<<bit;
            }
            CHECK(!memcmp(table,copy,sizeof(table))&&ggd_tables_match(&d,table,sizeof(table)));
        }
        memcpy(table,legacy,sizeof(table));CHECK(!ggd_tables_match(&d,table,sizeof(table)));
        CHECK(!memcmp(&c,&old,sizeof(c))&&!memcmp(buf,before,64)&&!memcmp(buf+64+GGP_TABLE_BYTES,before+64+GGP_TABLE_BYTES,64));
        CHECK(walk(buf+64,c.ttbr0,GGD_DATA_IOVA)==((owner+GGD_DATA_OFFSET)|UINT64_C(0x0060000000000e43)));
        unsigned index=(GGD_DATA_IOVA>>12)&511;CHECK(index==24);
        CHECK(get64(legacy+0x2000+8*index)==0);
        for(unsigned i=0;i<GGP_TABLE_BYTES;i++)if(i<0x2000+8*index||i>=0x2000+8*index+8)CHECK(buf[64+i]==legacy[i]);
        for(unsigned pad=4096;pad<16384;pad+=4096)CHECK(walk(buf+64,c.ttbr0,GGD_DATA_IOVA+pad)==0);
        if(exhaustive&&ias==39&&ips==1){
            unsigned present=0;
            for(uint64_t va=0;va<UINT64_C(0x100000000);va+=4096){
                uint64_t oldleaf=walk(legacy,old.ttbr0,(uint32_t)va),leaf=walk(buf+64,c.ttbr0,(uint32_t)va);
                CHECK(leaf==(va==GGD_DATA_IOVA?((owner+GGD_DATA_OFFSET)|UINT64_C(0x0060000000000e43)):oldleaf));present+=leaf!=0;
            }
            CHECK(present==19);
        }
    }
    struct {uint32_t before;struct ggd_write_command cmd;uint32_t after;} b;
    memset(&b,0x91,sizeof(b));CHECK(ggd_write_command_build(&d,&b.cmd));
    const uint32_t words[]={0x703d8003,0xfc018000,0,0x47504431,0x703d8003,0xfc018ffc,0,0x47504432};
    CHECK(!memcmp(b.cmd.word,words,sizeof(words))&&b.before==0x91919191&&b.after==0x91919191);
}
static void reject_emit(const struct ggd_plan *p,unsigned ias,unsigned oas,size_t size)
{
    ++cases;uint8_t buf[GGP_TABLE_BYTES],old[sizeof(buf)];struct ggp_s1_config c,saved;
    memset(buf,0x76,sizeof(buf));memcpy(old,buf,sizeof(buf));memset(&c,0x45,sizeof(c));saved=c;
    CHECK(!ggd_emit_tables(p,ias,oas,buf,size,&c)&&!memcmp(buf,old,sizeof(buf))&&!memcmp(&c,&saved,sizeof(c)));
}
static void bad(void)
{
    struct ggm_plan gmu;struct ggp_plan p;struct ggd_plan d;
    CHECK(ggm_plan_build(0xaa200000,&gmu)&&ggp_plan_build(&gmu,&p)&&ggd_plan_build(&p,&d));
    for(unsigned byte=0;byte<sizeof(d);byte++)for(unsigned bit=0;bit<8;bit++){
        struct ggd_plan q=d;((uint8_t *)&q)[byte]^=1u<<bit;
        /* A different valid aligned owner is legal, not a geometry error. */
        if(ggd_plan_valid(&q)){CHECK(q.bootstrap.owner_pa!=d.bootstrap.owner_pa);continue;}
        reject_emit(&q,39,36,GGP_TABLE_BYTES);struct ggd_write_command c,old;memset(&c,0x87,sizeof(c));old=c;
        CHECK(!ggd_write_command_build(&q,&c)&&!memcmp(&c,&old,sizeof(c)));
    }
    for(unsigned ias=0;ias<64;ias++)if(ias<32||ias>39)reject_emit(&d,ias,36,GGP_TABLE_BYTES);
    for(unsigned oas=0;oas<64;oas++)if(oas!=32&&oas!=36&&oas!=40&&oas!=42&&oas!=44&&oas!=48)reject_emit(&d,39,oas,GGP_TABLE_BYTES);
    reject_emit(&d,39,36,0);reject_emit(&d,39,36,GGP_TABLE_BYTES-1);reject_emit(NULL,39,36,GGP_TABLE_BYTES);
    reject_emit((const struct ggd_plan *)(uintptr_t)(UINTPTR_MAX-4),39,36,GGP_TABLE_BYTES);
    struct ggp_s1_config c;uint8_t buf[GGP_TABLE_BYTES+512];memset(buf,0x51,sizeof(buf));
    CHECK(!ggd_emit_tables(&d,39,36,NULL,GGP_TABLE_BYTES,&c));
    CHECK(!ggd_emit_tables(&d,39,36,(void *)(uintptr_t)(UINTPTR_MAX-4),GGP_TABLE_BYTES,&c));
    CHECK(!ggd_emit_tables(&d,39,36,buf,GGP_TABLE_BYTES,NULL));
    CHECK(!ggd_emit_tables(&d,39,36,buf,GGP_TABLE_BYTES,(struct ggp_s1_config *)(uintptr_t)(UINTPTR_MAX-4)));
    union {uint64_t align;uint8_t b[GGP_TABLE_BYTES+512];} arena,saved;
    for(unsigned delta=0;delta<sizeof(d);delta+=8){
        memset(&arena,0x31,sizeof(arena));memcpy(arena.b+256,&d,sizeof(d));saved=arena;
        CHECK(!ggd_emit_tables((const struct ggd_plan *)(arena.b+256),39,36,arena.b+256+delta,GGP_TABLE_BYTES,&c)&&!memcmp(&arena,&saved,sizeof(arena)));
        CHECK(!ggd_write_command_build((const struct ggd_plan *)(arena.b+256),(struct ggd_write_command *)(arena.b+256+delta))&&!memcmp(&arena,&saved,sizeof(arena)));
    }
    for(unsigned delta=0;delta<sizeof(c);delta+=8){
        memset(&arena,0x62,sizeof(arena));saved=arena;
        CHECK(!ggd_emit_tables(&d,39,36,arena.b,GGP_TABLE_BYTES,(struct ggp_s1_config *)(arena.b+delta))&&!memcmp(&arena,&saved,sizeof(arena)));
    }
    for(unsigned delta=0;delta<sizeof(d);delta+=8){
        memset(&arena,0x31,sizeof(arena));memcpy(arena.b+256,&d,sizeof(d));saved=arena;
        CHECK(!ggd_emit_tables((const struct ggd_plan *)(arena.b+256),39,36,arena.b+512,GGP_TABLE_BYTES,(struct ggp_s1_config *)(arena.b+256+delta))&&!memcmp(&arena,&saved,sizeof(arena)));
    }
    for(unsigned delta=0;delta<sizeof(p);delta+=8){
        memset(&arena,0x42,sizeof(arena));memcpy(arena.b+256,&p,sizeof(p));saved=arena;
        CHECK(!ggd_plan_build((const struct ggp_plan *)(arena.b+256),(struct ggd_plan *)(arena.b+256+delta))&&!memcmp(&arena,&saved,sizeof(arena)));
    }
    struct ggd_plan old;memset(&old,0x61,sizeof(old));d=old;
    CHECK(!ggd_plan_build(NULL,&d)&&!memcmp(&d,&old,sizeof(d)));
    CHECK(!ggd_plan_build((const struct ggp_plan *)(uintptr_t)(UINTPTR_MAX-4),&d)&&!memcmp(&d,&old,sizeof(d)));
    CHECK(!ggd_plan_build(&p,NULL)&&!ggd_plan_build(&p,(struct ggd_plan *)(uintptr_t)(UINTPTR_MAX-4)));
    p.owner_pa=0;CHECK(!ggd_plan_build(&p,&d)&&!memcmp(&d,&old,sizeof(d)));
    CHECK(!ggd_write_command_build(NULL,(struct ggd_write_command *)buf));
    CHECK(!ggd_write_command_build(&old,NULL));
    CHECK(ggm_plan_build(0xaa200000,&gmu)&&ggp_plan_build(&gmu,&p)&&ggd_plan_build(&p,&d));
    uint64_t table[GGP_TABLE_BYTES/8];struct ggp_s1_config cfg;CHECK(ggd_emit_tables(&d,39,36,table,sizeof(table),&cfg));
    CHECK(!ggd_tables_match(NULL,table,sizeof(table))&&!ggd_tables_match(&d,NULL,sizeof(table)));
    CHECK(!ggd_tables_match(&d,table,sizeof(table)-1)&&!ggd_tables_match(&d,(uint8_t *)table+1,sizeof(table)));
    CHECK(!ggd_tables_match(&d,(const volatile void *)(uintptr_t)(UINTPTR_MAX-7),sizeof(table)));
    CHECK(!ggd_tables_match((const struct ggd_plan *)(uintptr_t)(UINTPTR_MAX-4),table,sizeof(table)));
    CHECK(!ggd_tables_match(&d,&d,sizeof(table)));
}
int main(void){good(0x100000,false);good(0xaa200000,true);good(0xfff00000,false);bad();printf("GPU data: %u cases/%u checks PASS;19 permission-qualified leaves, all32-bit holes, legacy18/config unchanged, exact8 MEM_WRITE words, overlap/failure atomicity; CPU-only, no live mapping/submission/rendering\n",cases,checks);}
