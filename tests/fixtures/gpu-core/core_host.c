#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_core.h"
static unsigned assertions;
#define CHECK(x) do{++assertions;if(!(x)){fprintf(stderr,"GPU core line%d\n",__LINE__);abort();}}while(0)
struct fake {
    struct ggc_context context;struct ggc_ops ops;struct ggp_plan plan;struct ggs_receipt gpu;
    uint32_t reg[0x24000],memory[1024];
    unsigned step,fail,started,opened,reads,writes,memreads,memwrites,barriers;
    unsigned trace,nested,parent_bad,dirty,corrupt,drop;
    unsigned first[GGC_DONE],last[GGC_DONE],critical[512],critical_count;
    unsigned memory_guards[256],memory_guard_count,ram_burst,max_burst;
};
static bool tick(struct fake *f,bool critical)
{++f->step;if(critical){CHECK(f->critical_count<512);f->critical[f->critical_count++]=f->step;}return f->step!=f->fail;}
static bool guard(void *p,enum ggc_phase phase)
{
    struct fake *f=p;CHECK(phase>=GGC_BUS&&phase<=GGC_FINAL);
    if(phase==GGC_REGLIST){CHECK(f->memory_guard_count<256);f->memory_guards[f->memory_guard_count++]=f->step+1;}
    f->ram_burst=0;
    if(!f->first[phase])f->first[phase]=f->step+1;f->last[phase]=f->step+1;
    if(f->nested){f->nested=0;struct ggc_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned before=f->step;CHECK(ggc_core_once(&f->context,&f->ops,&f->plan,&f->gpu,&out)==GGC_ALREADY&&before==f->step&&!memcmp(&out,&old,sizeof(out)));}
    return tick(f,false);
}
static bool read32(void *p,uint32_t reg,uint32_t *v)
{
    struct fake *f=p;CHECK(f->opened&&reg<0x24000&&ggc_register_allowed(reg,false));if(!tick(f,true))return false;
    *v=f->reg[reg];++f->reads;if(f->trace)printf("R %05x %08x\n",reg,*v);return true;
}
static bool write32(void *p,uint32_t reg,uint32_t v)
{
    struct fake *f=p;CHECK(reg<0x24000&&ggc_register_allowed(reg,true));
    if(!f->writes)CHECK(f->context.phase==GGC_BUS&&reg==0x3c45&&!v&&!f->started&&!f->opened);
    else CHECK(f->opened&&f->context.phase>=GGC_ADDRESS);
    if(!tick(f,true))return false;
    f->reg[reg]=v;++f->writes;if(f->trace)printf("W %05x %08x\n",reg,v);return true;
}
static bool barrier(void *p)
{
    struct fake *f=p;if(!tick(f,true))return false;++f->barriers;
    if(f->corrupt&&f->memwrites==133){f->memory[f->corrupt-1]^=1;f->corrupt=0;}
    return true;
}
static bool start_gpu(void *p,struct ggx_receipt *out)
{
    struct fake *f=p;CHECK(f->context.phase==GGC_MMU_OOB&&f->writes==1&&f->barriers==1&&!f->started&&!f->opened);
    if(!tick(f,true))return false;++f->started;
    *out=(struct ggx_receipt){.bank=f->gpu.bank,.asid=f->gpu.asid,.ttbr0=f->gpu.ttbr0,
        .tlb_status=2,.writes32=7,.writes64=1,.tlb_polls=1,.oob_polls=1,.request_attempted=1,
        .ack_valid=1,.ack_clear_attempted=1,.core_opened=1,.request_retained=1,
        .oob_before=1u<<30,.oob_ack=(1u<<30)|(1u<<24),.oob_cleared=1u<<30};
    if(f->parent_bad==1)out->ttbr0^=4096;
    if(f->parent_bad==2)out->contextidr=1;
    if(f->parent_bad==3)out->ack_valid=0;
    if(f->parent_bad==4)out->request_retained=0;
    if(f->parent_bad==5)out->oob_before|=1u<<24;
    if(f->parent_bad==6)out->oob_ack|=0x8000;
    if(f->parent_bad==7)out->oob_cleared|=1u<<24;
    if(f->parent_bad==8)out->tlb_status=1;
    if(f->parent_bad==9)out->core_opened=0;
    return true;
}
static bool open_registers(void *p)
{struct fake *f=p;CHECK(f->context.phase==GGC_MAP&&f->started==1&&f->writes==1&&!f->opened);if(!tick(f,true))return false;f->opened=1;return true;}
static bool read_reglist(void *p,uint32_t off,uint32_t *v)
{
    struct fake *f=p;CHECK(f->context.phase==GGC_REGLIST&&!(off&3)&&off<4096&&f->opened);
    CHECK(++f->ram_burst<=GGC_MEMORY_BATCH_WORDS);if(f->ram_burst>f->max_burst)f->max_burst=f->ram_burst;
    bool critical=off==0||off==2048||off==4092;
    if(!tick(f,critical))return false;++f->memreads;*v=f->memory[off/4];return true;
}
static bool write_reglist(void *p,uint32_t off,uint32_t v)
{
    struct fake *f=p;CHECK(f->context.phase==GGC_REGLIST&&!(off&3)&&off<4*GGC_REGLIST_WORDS&&f->memreads==1024);
    CHECK(f->memwrites<132?off==16+4*f->memwrites:off==12&&f->memwrites==132);
    CHECK(++f->ram_burst<=GGC_MEMORY_BATCH_WORDS);if(f->ram_burst>f->max_burst)f->max_burst=f->ram_burst;
    if(!tick(f,off==16||off==280||off==540||off==12))return false;
    ++f->memwrites;if(f->drop!=f->memwrites)f->memory[off/4]=v;return true;
}
static struct fake *fresh(unsigned scenario)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan gmu;CHECK(ggm_plan_build(0xaa200000,&gmu)&&ggp_plan_build(&gmu,&f->plan));
    f->gpu=(struct ggs_receipt){.bank=2,.banks=8,.groups=5,.slot=2,.asid=3,.stream_match=1,
        .sctlr=0xc01167,.smr=0x80000000,.s2cr=2,.gpu_pages=18,.gmu_pages=131,.translations=168,
        .ttbr0=(f->plan.owner_pa+0x9c000)|(UINT64_C(3)<<48),.ttbr1=(f->plan.owner_pa+0x9f000)|(UINT64_C(3)<<48)};
    for(unsigned i=0;i<0x24000;i++)f->reg[i]=scenario==3?UINT32_MAX:(0x13579bdfu^(i*0x10203u)^(scenario*0x5a5a5a5au));
    if(scenario==0)f->reg[0xae]=0;if(scenario==1)f->reg[0xae]=0x8aa8aa82;
    f->ops=(struct ggc_ops){f,guard,read32,write32,barrier,start_gpu,open_registers,read_reglist,write_reglist};return f;
}
static enum ggc_result run(struct fake *f,struct ggc_receipt *out)
{return ggc_core_once(&f->context,&f->ops,&f->plan,&f->gpu,out);}
static void stopped(struct fake *f)
{struct ggc_receipt out,old;memset(&out,0x5a,sizeof(out));old=out;unsigned before=f->step;CHECK(run(f,&out)==GGC_ALREADY&&before==f->step&&!memcmp(&out,&old,sizeof(out)));}
static void rejected(struct fake *f,enum ggc_result want)
{struct ggc_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;CHECK(run(f,&out)==want&&f->context.state==3&&!memcmp(&out,&old,sizeof(out)));stopped(f);}
static void check_good(struct fake *f,unsigned scenario)
{
    struct ggc_receipt out;CHECK(run(f,&out)==GGC_OK&&f->context.state==2&&f->context.phase==GGC_DONE);
    CHECK(out.configured==1&&out.requests_retained==1&&out.start.request_retained==1&&out.list_length==132&&out.list_offset==72);
    CHECK(out.writes==(scenario==1?80u:146u)&&out.reads==(scenario==1?69u:71u)&&out.hwcg_skipped==(scenario==1));
    CHECK(out.mem_written==133&&out.mem_compared==1024&&f->memreads==2048&&!memcmp(f->memory,f->context.reglist,sizeof(f->context.reglist)));
    CHECK(f->context.zero_checked==1024&&f->max_burst==64&&GGC_MEMORY_BATCH_WORDS==64);
    for(unsigned i=GGC_REGLIST_WORDS;i<1024;i++)CHECK(!f->memory[i]);
    CHECK(!f->memory[0]&&!f->memory[1]&&!f->memory[2]&&f->memory[3]==0x480084);
    for(unsigned i=4;i<GGC_REGLIST_WORDS;i+=2)CHECK(f->memory[i+1]==f->reg[f->memory[i]]);
    stopped(f);
}
int main(int argc,char **argv)
{
    if(argc==2){unsigned s=(unsigned)strtoul(argv[1],NULL,10);CHECK(s<4);struct fake *f=fresh(s);f->trace=1;printf("BEGIN %u\n",s);check_good(f,s);printf("HEADER 132 72\n");for(unsigned i=0;i<GGC_REGLIST_WORDS;i++)printf("L %u %08x\n",i,f->memory[i]);free(f);return 0;}
    CHECK(argc==1);
    for(unsigned s=0;s<4;s++){
        struct fake *f=fresh(s);f->nested=1;check_good(f,s);unsigned points[600],count=0;
        for(unsigned i=0;i<f->critical_count;i++)points[count++]=f->critical[i];
        for(unsigned i=0;i<f->memory_guard_count;i++)points[count++]=f->memory_guards[i];
        for(unsigned p=GGC_BUS;p<=GGC_FINAL;p++){CHECK(f->first[p]&&f->last[p]);points[count++]=f->first[p];points[count++]=f->last[p];}
        CHECK(count<600);free(f);
        for(unsigned i=0;i<count;i++){
            f=fresh(s);f->fail=points[i];struct ggc_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
            CHECK(run(f,&out)!=GGC_OK&&f->step==f->fail&&f->context.state==3&&!memcmp(&out,&old,sizeof(out)));stopped(f);free(f);
        }
        printf("GPU core scenario%u: native path and%u MMIO/map/parent/barrier/memory/phase failure points PASS\n",s,count);
    }
    for(unsigned n=1;n<=9;n++){struct fake *f=fresh(0);f->parent_bad=n;rejected(f,GGC_PARENT);CHECK(f->writes==1&&!f->opened&&!f->memwrites);free(f);}
    for(unsigned n=0;n<3;n++){struct fake *f=fresh(0);f->memory[n==0?0:n==1?512:1023]=1;rejected(f,GGC_MEMORY);CHECK(!f->memwrites);free(f);}
    for(unsigned n=0;n<4;n++){struct fake *f=fresh(0);f->corrupt=n==0?1:n==1?4:n==2?136:1024;rejected(f,GGC_MEMORY);free(f);}
    for(unsigned n=0;n<3;n++){struct fake *f=fresh(0);f->drop=n==0?1:n==1?65:133;rejected(f,GGC_MEMORY);free(f);}
    struct fake *f=fresh(0);struct ggc_receipt out;f->ops.start_gpu=NULL;CHECK(run(f,&out)==GGC_ARGUMENT&&!f->step&&!f->context.state);free(f);
    f=fresh(0);f->gpu.groups=0;CHECK(run(f,&out)==GGC_ARGUMENT&&!f->step);free(f);
    f=fresh(0);CHECK(ggc_core_once(&f->context,&f->ops,&f->plan,&f->gpu,&f->context.work)==GGC_ARGUMENT&&!f->step);free(f);
    const uint32_t pages[]={0,0xc000,0x20000,0x24000,0x28000,0x2c000,0x3c000,0x68000,0x7c000,0x8c000};CHECK(ggc_register_page_count()==sizeof(pages)/sizeof(pages[0]));
    for(unsigned i=0;i<10;i++){uint32_t v;CHECK(ggc_register_page(i,&v)&&v==pages[i]);}
    uint32_t v=0xa5a5;CHECK(!ggc_register_page(10,&v)&&v==0xa5a5&&!ggc_register_page(0,NULL));
    const uint32_t forbidden[]={0x807,0x808,0x10000,0x12000,0x13fff,0x1f994,0x1f991,0x1f990,0x24000,UINT32_MAX};
    for(unsigned i=0;i<sizeof(forbidden)/sizeof(forbidden[0]);i++)CHECK(!ggc_register_allowed(forbidden[i],true)&&!ggc_register_allowed(forbidden[i],false));
    printf("PASS: %u core assertions; native HWCG skip/RMW/live RGL, all-ones opaque values, failures, output preservation and no CP/IRQ/secure bypass\n",assertions);
    return 0;
}
