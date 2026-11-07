#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_memory.h"
static unsigned checks;
#define CHECK(x) do {assert(x);++checks;} while(0)
static uint64_t get64(const uint8_t *b)
{uint64_t x=0;for(unsigned i=0;i<8;i++)x|=(uint64_t)b[i]<<(8*i);return x;}
static uint64_t walk(const uint8_t *b,uint64_t base,uint32_t va)
{
    unsigned off=0;
    for(unsigned level=1;level<=3;level++){
        unsigned shift=level==1?30:level==2?21:12;
        uint64_t e=get64(b+off+8*((va>>shift)&511));
        if(!e)return 0;CHECK((e&3)==3);
        if(level==3)return e;
        CHECK((e&0xfff)==3);uint64_t next=e&~UINT64_C(0xfff);
        CHECK(next>=base&&next+4096<=base+GGP_TABLE_BYTES);off=(unsigned)(next-base);
    }
    abort();
}
static const uint32_t va[]={0xfc000000,0xfc008000,0xfc010000,0xfc014000};
static const uint32_t off[]={0xa0000,0xa8000,0xb0000,0xb4000},pages[]={8,8,1,1};
static const uint64_t attrs[]={0xec3,UINT64_C(0x0060000000000ec3),UINT64_C(0x0060000000000e03),UINT64_C(0x0060000000000e03)};
static void good(uint64_t owner,bool exhaustive)
{
    struct ggm_plan gmu,saved;CHECK(ggm_plan_build(owner,&gmu));saved=gmu;
    struct ggp_plan p;CHECK(ggp_plan_build(&gmu,&p)&&ggp_plan_valid(&p));CHECK(!memcmp(&gmu,&saved,sizeof(gmu)));
    CHECK(p.owner_pa==owner&&GGP_TABLE_OFFSET==0x9c000&&GGP_TABLE_BYTES==16384&&GGP_ARENA_END==0xb8000);
    CHECK(GGP_SQE_BYTES==32300&&p.region[GGP_RING].bytes==32768);
    for(unsigned r=0;r<4;r++){
        CHECK(p.region[r].offset==off[r]&&p.region[r].iova==va[r]&&p.region[r].mapped==pages[r]*4096);
        CHECK(!(p.region[r].offset&16383)&&!(p.region[r].reserved&16383));
        CHECK(p.region[r].offset>=GGP_TABLE_OFFSET+GGP_TABLE_BYTES&&p.region[r].offset+p.region[r].reserved<=GGP_ARENA_END);
        for(unsigned j=0;j<GGM_COUNT;j++)CHECK(p.region[r].offset>=gmu.region[j].offset+gmu.region[j].reserved);
    }
    uint8_t *b=malloc(GGP_TABLE_BYTES+128),*before=malloc(GGP_TABLE_BYTES+128);CHECK(b&&before);
    static const unsigned widths[]={32,36,40,42,44,48};
    for(unsigned ias=32;ias<=39;ias++)for(unsigned ips=0;ips<6;ips++){
        struct ggp_s1_config c;memset(b,0xa7,GGP_TABLE_BYTES+128);memcpy(before,b,GGP_TABLE_BYTES+128);
        CHECK(ggp_emit_tables(&p,ias,widths[ips],b+64,GGP_TABLE_BYTES+64,&c));
        CHECK(!memcmp(b,before,64)&&!memcmp(b+64+GGP_TABLE_BYTES,before+64+GGP_TABLE_BYTES,64));
        CHECK(c.ttbr0==owner+GGP_TABLE_OFFSET&&c.ttbr1==c.ttbr0+0x3000);
        CHECK(c.tcr==((uint64_t)ips<<32|0x802000u|(64-ias))&&c.mair0==0xf404ff44&&c.mair1==0xe4&&c.ias==ias&&c.oas==widths[ips]);
        unsigned mapped=0;
        for(unsigned r=0;r<4;r++)for(unsigned n=0;n<pages[r];n++){
            CHECK(walk(b+64,c.ttbr0,va[r]+4096*n)==((owner+off[r]+4096*n)|attrs[r]));++mapped;
        }
        CHECK(mapped==18);
        for(unsigned n=0;n<4096;n++)CHECK(b[64+0x3000+n]==0);
        if(exhaustive&&ias==39&&ips==1){
            unsigned present=0;
            for(uint64_t v=0;v<UINT64_C(0x100000000);v+=4096){
                uint64_t e=walk(b+64,c.ttbr0,(uint32_t)v);bool expected=false;
                for(unsigned r=0;r<4;r++)if(v>=va[r]&&v<va[r]+pages[r]*4096)expected=true;
                CHECK((e!=0)==expected);present+=e!=0;
            }
            CHECK(present==18);
        }
    }
    struct {uint32_t before;struct ggp_cp_init cmd;uint32_t after;} box;memset(&box,0xa7,sizeof(box));
    CHECK(ggp_cp_init_build(&p,&box.cmd));
    const uint32_t expected[]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0};
    CHECK(!memcmp(box.cmd.word,expected,sizeof(expected))&&box.before==0xa7a7a7a7&&box.after==0xa7a7a7a7);
    free(before);free(b);
}
static void reject_emit(const struct ggp_plan *p,unsigned ias,unsigned oas,size_t capacity)
{
    uint8_t a[GGP_TABLE_BYTES+64],b[sizeof(a)];struct ggp_s1_config out,before;
    memset(a,0x97,sizeof(a));memcpy(b,a,sizeof(a));memset(&out,0x91,sizeof(out));before=out;
    CHECK(!ggp_emit_tables(p,ias,oas,a,capacity,&out)&&!memcmp(a,b,sizeof(a))&&!memcmp(&out,&before,sizeof(out)));
}
static void bad(void)
{
    struct ggm_plan gmu;CHECK(ggm_plan_build(0xaa200000,&gmu));struct ggp_plan p;CHECK(ggp_plan_build(&gmu,&p));
    for(unsigned r=0;r<4;r++)for(unsigned field=0;field<8;field++){
        struct ggp_plan q=p;uint32_t v;uint8_t *fieldp=(uint8_t *)&q.region[r]+4*field;memcpy(&v,fieldp,4);v^=1;memcpy(fieldp,&v,4);CHECK(!ggp_plan_valid(&q));reject_emit(&q,39,36,GGP_TABLE_BYTES);
        struct ggp_cp_init cmd,before;memset(&cmd,0x75,sizeof(cmd));before=cmd;CHECK(!ggp_cp_init_build(&q,&cmd)&&!memcmp(&cmd,&before,sizeof(cmd)));
    }
    for(unsigned i=0;i<4;i++){
        struct ggp_plan q=p;q.owner_pa=(uint64_t[]){0,0xaa200001,0x100000000,UINT64_MAX}[i];CHECK(!ggp_plan_valid(&q));reject_emit(&q,39,36,GGP_TABLE_BYTES);
    }
    for(unsigned ias=0;ias<64;ias++)if(ias<32||ias>39)reject_emit(&p,ias,36,GGP_TABLE_BYTES);
    for(unsigned oas=0;oas<64;oas++)if(oas!=32&&oas!=36&&oas!=40&&oas!=42&&oas!=44&&oas!=48)reject_emit(&p,39,oas,GGP_TABLE_BYTES);
    reject_emit(&p,39,36,0);reject_emit(&p,39,36,GGP_TABLE_BYTES-1);reject_emit(NULL,39,36,GGP_TABLE_BYTES);
    reject_emit((const struct ggp_plan *)(uintptr_t)(UINTPTR_MAX-4),39,36,GGP_TABLE_BYTES);
    struct ggp_s1_config c;uint8_t b[GGP_TABLE_BYTES+256],saved[sizeof(b)];memset(b,0x94,sizeof(b));memcpy(saved,b,sizeof(b));
    CHECK(!ggp_emit_tables(&p,39,36,NULL,GGP_TABLE_BYTES,&c));CHECK(!ggp_emit_tables(&p,39,36,(void *)(uintptr_t)(UINTPTR_MAX-4),GGP_TABLE_BYTES,&c));
    CHECK(!ggp_emit_tables(&p,39,36,b,GGP_TABLE_BYTES,NULL));CHECK(!ggp_emit_tables(&p,39,36,b,GGP_TABLE_BYTES,(void *)(uintptr_t)(UINTPTR_MAX-4)));
    CHECK(!ggp_emit_tables(&p,39,36,b,GGP_TABLE_BYTES,(struct ggp_s1_config *)(b+8))&&!memcmp(b,saved,sizeof(b)));
    union {uint64_t align;uint8_t bytes[GGP_TABLE_BYTES+512];} arena,copy;
    for(unsigned delta=0;delta<sizeof(p);delta+=8){
        memset(&arena,0x81,sizeof(arena));memcpy(arena.bytes+128,&p,sizeof(p));copy=arena;
        CHECK(!ggp_emit_tables((const struct ggp_plan *)(arena.bytes+128),39,36,arena.bytes+128+delta,GGP_TABLE_BYTES,&c)&&!memcmp(&arena,&copy,sizeof(arena)));
        CHECK(!ggp_cp_init_build((const struct ggp_plan *)(arena.bytes+128),(struct ggp_cp_init *)(arena.bytes+128+delta))&&!memcmp(&arena,&copy,sizeof(arena)));
    }
    struct ggp_cp_init cmd,before;memset(&cmd,0x81,sizeof(cmd));before=cmd;
    CHECK(!ggp_cp_init_build(NULL,&cmd)&&!memcmp(&cmd,&before,sizeof(cmd)));CHECK(!ggp_cp_init_build(&p,NULL));
    for(unsigned i=0;i<GGM_COUNT;i++){
        struct ggm_plan q=gmu;q.region[i].offset^=0x4000;struct ggp_plan out,old;memset(&out,0x71,sizeof(out));old=out;
        CHECK(!ggp_plan_build(&q,&out)&&!memcmp(&out,&old,sizeof(out)));
    }
    CHECK(!ggp_plan_build(NULL,&p));CHECK(!ggp_plan_build(&gmu,NULL));
    CHECK(!ggp_plan_build((const struct ggm_plan *)(uintptr_t)(UINTPTR_MAX-4),&p));
    CHECK(!ggp_plan_build(&gmu,(struct ggp_plan *)(uintptr_t)(UINTPTR_MAX-4)));
    struct ggm_plan old=gmu;CHECK(!ggp_plan_build(&gmu,(struct ggp_plan *)&gmu)&&!memcmp(&gmu,&old,sizeof(gmu)));
}
int main(void){good(0x100000,false);good(0xaa200000,true);good(0xfff00000,false);bad();printf("GPU memory/CP_INIT: %u checks PASS;18 permission-qualified leaves, all32-bit holes, empty TTBR1, retained GMU separation, exact12 words and failure atomicity (CPU-only, no DMA/launch)\n",checks);}
