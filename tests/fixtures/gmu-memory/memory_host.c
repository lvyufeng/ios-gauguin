#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gmu_memory.h"

/* Independent policy oracle: firmware VAs/sizes/permissions, CPU reservations.
 * Walk emitted descriptors as an SMMU would, rather than comparing a second
 * implementation of the emitter. Check the entire 32-bit VA space for holes. */
static const uint32_t starts[]={0x4000,0x44000,0x60000000,0x60001000,0x60006000,0x6000a000};
static const uint32_t pages[]={60,60,1,5,4,1};
static const uint32_t physical[]={0x10000,0x4c000,0x88000,0x8c000,0x94000,0x98000};
static const uint32_t reserved[]={0x3c000,0x3c000,0x4000,0x8000,0x4000,0x4000};
static const unsigned user[]={0,0,0,1,1,0};
static unsigned checks;
#define CHECK(c) do {assert(c);++checks;} while(0)
static uint64_t get64(const unsigned char *b)
{uint64_t n=0;for(unsigned i=0;i<8;i++)n|=(uint64_t)b[i]<<(8*i);return n;}
static uint32_t get32(const unsigned char *b)
{return (uint32_t)get64((const unsigned char[8]){b[0],b[1],b[2],b[3],0,0,0,0});}
static uint64_t walk(const unsigned char *b,uint64_t pa,uint32_t va)
{
    unsigned off=0;
    for(unsigned level=1;level<=3;level++){
        unsigned shift=level==1?30:level==2?21:12;
        uint64_t e=get64(b+off+8*((va>>shift)&511));
        if(!e)return 0;
        CHECK((e&3)==3);
        if(level==3)return e;
        uint64_t next=e&~UINT64_C(0xfff);
        CHECK(next>=pa&&next+4096<=pa+32768);
        CHECK((e&0xfff)==3);
        off=(unsigned)(next-pa);
    }
    abort();
}
static void good(uint64_t owner)
{
    struct ggm_plan p;CHECK(ggm_plan_build(owner,&p));CHECK(ggm_plan_valid(&p));
    for(unsigned r=0;r<6;r++){
        CHECK(p.region[r].offset==physical[r]);CHECK(p.region[r].reserved==reserved[r]);
        CHECK(p.region[r].iova==starts[r]);CHECK(p.region[r].bytes==pages[r]*4096);
        CHECK(p.region[r].privileged==!user[r]);CHECK(!(p.region[r].offset&16383));
        CHECK(p.region[r].offset>=16384&&p.region[r].offset+p.region[r].reserved<=1048576);
        for(unsigned s=0;s<r;s++)CHECK(p.region[s].offset+p.region[s].reserved<=p.region[r].offset);
    }
    unsigned char b[32768+32];memset(b,0xa5,sizeof(b));struct ggm_s1_config cfg;
    CHECK(ggm_emit_tables(&p,39,40,b+1,32768+30,&cfg));
    CHECK(b[0]==0xa5);for(unsigned i=32769;i<sizeof(b);i++)CHECK(b[i]==0xa5);
    CHECK(cfg.kernel_ttbr0==owner+0x4000);CHECK(cfg.kernel_ttbr1==owner+0x9000);
    CHECK(cfg.user_ttbr0==owner+0xa000);CHECK(cfg.user_ttbr1==owner+0xb000);
    CHECK(cfg.tcr==UINT64_C(0x200802019));CHECK(cfg.mair0==0xf404ff44&&cfg.mair1==0xe4);
    CHECK(cfg.ias==39&&cfg.oas==40);
    unsigned leaves=0;
    for(uint64_t va=0;va<UINT64_C(0x100000000);va+=4096){
        uint64_t e=walk(b+1,owner+0x4000,(uint32_t)va),expected=0;
        for(unsigned r=0;r<6;r++)if(va>=starts[r]&&va-starts[r]<pages[r]*4096u){
            expected=(owner+physical[r]+va-starts[r])|UINT64_C(0xe03)|(user[r]?0x40:0);break;
        }
        CHECK(e==expected);if(e)++leaves;
    }
    CHECK(leaves==131);
    /* Exactly four table descriptors +131 leaves; no hidden empty-root maps. */
    unsigned nonzero=0;for(unsigned i=0;i<32768;i+=8)if(get64(b+1+i))++nonzero;
    CHECK(nonzero==135);
    for(unsigned i=0x5000;i<0x8000;i++)CHECK(b[1+i]==0);
    static const unsigned widths[]={32,36,40,42,44,48};
    for(unsigned i=0;i<6;i++)for(unsigned ias=32;ias<=39;ias++){
        CHECK(ggm_emit_tables(&p,ias,widths[i],b+1,32768,&cfg));
        CHECK(cfg.tcr==((uint64_t)i<<32|UINT64_C(0x802000)|(64-ias)));
    }
    memset(b,0xa5,sizeof(b));CHECK(ggm_emit_hfi(&p,b+1,32768+30));
    CHECK(b[0]==0xa5);for(unsigned i=32769;i<sizeof(b);i++)CHECK(b[i]==0xa5);
    /* Native four-queue binary header, including disabled fourth queue. */
    static const uint32_t head[]={0,54,6,12,4,4};
    static const uint32_t types[]={0x0a00,0x0a04,0x2805,0x1401};
    for(unsigned i=0;i<32768;i+=4){
        uint32_t expected=0;
        if(i<24)expected=head[i/4];
        else if(i<216){unsigned q=(i-24)/48,field=((i-24)%48)/4;
            if(field==0)expected=q<3;
            if(field==1)expected=0x600010e0u+4096*q;
            if(field==2)expected=types[q];
            if(field==3)expected=1024;
        }
        CHECK(get32(b+1+i)==expected);
    }
}
static void rejected(const struct ggm_plan *p,unsigned ias,unsigned oas,size_t cap)
{
    unsigned char b[32768],old[32768];memset(b,0xa6,sizeof(b));memcpy(old,b,sizeof(b));
    struct ggm_s1_config c,before;memset(&c,0x7e,sizeof(c));before=c;
    CHECK(!ggm_emit_tables(p,ias,oas,b,cap,&c));
    CHECK(!memcmp(b,old,sizeof(b)));CHECK(!memcmp(&c,&before,sizeof(c)));
}
static void bad(void)
{
    struct ggm_plan p,before;memset(&p,0x3f,sizeof(p));before=p;
    const uint64_t invalid[]={0,1,0xfffff,0x100001,0x100000000,UINT64_MAX};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++){
        CHECK(!ggm_plan_build(invalid[i],&p));CHECK(!memcmp(&p,&before,sizeof(p)));
    }
    CHECK(!ggm_plan_build(0x100000,NULL));CHECK(!ggm_plan_valid(NULL));
    CHECK(ggm_plan_build(0x100000,&p));
    rejected(NULL,39,40,32768);rejected(&p,31,40,32768);rejected(&p,40,40,32768);
    rejected(&p,39,0,32768);rejected(&p,39,35,32768);rejected(&p,39,64,32768);
    rejected(&p,39,40,0);rejected(&p,39,40,32767);
    for(unsigned r=0;r<6;r++)for(unsigned field=0;field<5;field++){
        struct ggm_plan broken=p;
        uint32_t *v=field==0?&broken.region[r].offset:field==1?&broken.region[r].reserved:
            field==2?&broken.region[r].iova:field==3?&broken.region[r].bytes:&broken.region[r].privileged;
        *v^=1;CHECK(!ggm_plan_valid(&broken));rejected(&broken,39,40,32768);
        unsigned char buf[32768],old[32768];memset(buf,0xa7,sizeof(buf));memcpy(old,buf,sizeof(buf));
        CHECK(!ggm_emit_hfi(&broken,buf,sizeof(buf)));CHECK(!memcmp(old,buf,sizeof(buf)));
    }
    unsigned char b[65536],old[65536];memset(b,0x3f,sizeof(b));memcpy(old,b,sizeof(b));
    struct ggm_s1_config cfg,cfg_before;memset(&cfg,0xc7,sizeof(cfg));cfg_before=cfg;
    CHECK(!ggm_emit_tables(&p,39,40,NULL,32768,&cfg));CHECK(!memcmp(&cfg,&cfg_before,sizeof(cfg)));
    CHECK(!ggm_emit_tables(&p,39,40,b,32768,NULL));
    CHECK(!ggm_emit_tables(&p,39,40,(void *)(UINTPTR_MAX-1),32768,&cfg));
    CHECK(!ggm_emit_tables(&p,39,40,b,32768,(struct ggm_s1_config *)(UINTPTR_MAX-1)));
    CHECK(!ggm_emit_tables(&p,39,40,b,32768,(struct ggm_s1_config *)(void *)(b+8)));
    CHECK(!ggm_emit_tables(&p,39,40,&p,32768,&cfg));
    CHECK(!ggm_emit_tables(&p,39,40,b,32768,(struct ggm_s1_config *)(void *)&p));
    CHECK(!ggm_emit_hfi(&p,NULL,32768));CHECK(!ggm_emit_hfi(&p,b,32767));
    CHECK(!ggm_emit_hfi(&p,(void *)(UINTPTR_MAX-1),32768));CHECK(!ggm_emit_hfi(&p,&p,32768));
    CHECK(!memcmp(b,old,sizeof(b)));CHECK(!memcmp(&cfg,&cfg_before,sizeof(cfg)));
    /* Input plan just inside the last byte of output is also overlapping. */
    union {max_align_t a;unsigned char b[65536];} aligned;
    struct ggm_plan *inside=(void *)(aligned.b+32760);*inside=p;
    memcpy(old,aligned.b,sizeof(old));
    CHECK(!ggm_emit_tables(inside,39,40,aligned.b,32768,&cfg));
    CHECK(!ggm_emit_hfi(inside,aligned.b,32768));CHECK(!memcmp(old,aligned.b,sizeof(old)));
}
int main(void)
{
    good(0x100000);good(0xaa200000);good(0xfff00000);bad();
    printf("GMU memory policy, exhaustive4GiB walks and failure atomicity: %u checks PASS\n",checks);
}
