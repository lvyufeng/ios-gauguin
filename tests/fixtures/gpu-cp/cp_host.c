#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_cp.h"
static unsigned assertions;
#define CHECK(x) do{++assertions;if(!(x)){fprintf(stderr,"GPU CP line%d\n",__LINE__);abort();}}while(0)
static const uint32_t words[15]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0,0x70620002,0xfc010000,0};
struct fake {
    struct ggq_context context;struct ggq_ops ops;struct ggp_plan plan;struct ggc_receipt parent;
    uint32_t reg[0x24000],ring[8192],scratch[1024];
    unsigned step,fail,record,nested,trace,points[4096],point_count;
    unsigned burst,max_burst,mem_writes,mem_reads,barriers,delays,cmds,submitted;
    unsigned drop_fence,fence_reads,fence_writes,rptr_delay,busy_delay,shadow_reads,busy_reads;
    unsigned counter_wrap,counter_reads,mem_fail_read,mem_fail_write,corrupt_read,drop_write;
    unsigned timeout_guard,fault_after_submit,kept,bad_rptr,bad_busy;
};
static bool tick(struct fake *f,bool point)
{
    ++f->step;
    if(f->record&&point){CHECK(f->point_count<4096);f->points[f->point_count++]=f->step;}
    return f->step!=f->fail;
}
static bool guard(void *cookie,enum ggq_phase phase)
{
    struct fake *f=cookie;CHECK(phase>=GGQ_CAPTURE&&phase<=GGQ_FINAL);f->burst=0;
    if(f->nested){
        f->nested=0;struct ggq_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned step=f->step;
        CHECK(ggq_start_once(&f->context,&f->ops,&f->plan,&f->parent,&out)==GGQ_ALREADY&&f->step==step&&!memcmp(&old,&out,sizeof(out)));
    }
    if(phase==GGQ_WAIT&&f->timeout_guard&&f->shadow_reads>=f->timeout_guard)return false;
    return tick(f,true);
}
static bool read32(void *cookie,uint32_t reg,uint32_t *value)
{
    struct fake *f=cookie;CHECK(value&&reg<0x24000&&ggq_register_allowed(reg,false));if(!tick(f,true))return false;
    *value=f->reg[reg];
    if(reg==0x23b13){*value=f->fence_reads++<f->drop_fence?3u:2u;if(!(*value&1u))f->submitted=1;}
    if(reg==0x23b0c){*value=f->bad_busy?UINT32_MAX:f->busy_reads++<f->busy_delay?0x80800000u:0x80000000u;}
    if(reg==0x1f889||reg==0x1f888){
        unsigned n=f->counter_reads++;
        if(!f->counter_wrap)*value=reg==0x1f889?1u:0x12345678u;
        else *value=n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:reg==0x1f889?2u:0x20u;
    }
    if(reg==0x823&&f->fault_after_submit&&f->context.phase==GGQ_WAIT)*value=1;
    if(f->trace&&(reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889))printf("R %05x %08x\n",reg,*value);
    return true;
}
static bool write32(void *cookie,uint32_t reg,uint32_t value)
{
    struct fake *f=cookie;CHECK(reg<0x24000&&ggq_register_allowed(reg,true));if(!tick(f,true))return false;
    CHECK(f->context.work.ring_checked==8192&&f->context.work.scratch_checked==1024);
    if(reg==0x808)CHECK(value==1&&f->context.phase==GGQ_START&&!f->cmds&&!f->kept);
    if(reg==0x1f8c3){CHECK(f->context.phase==GGQ_SUBMIT&&f->cmds==15&&value<=1);f->kept=value;}
    if(reg==0x807){
        CHECK(f->context.phase==GGQ_SUBMIT&&value==15&&f->kept&&f->reg[0x808]==1&&f->cmds==15);
        CHECK(f->reg[0x804]==0xfc010000&&!f->reg[0x805]&&f->reg[0x802]==0x0800020c&&f->reg[0x800]==0xfc008000&&!f->reg[0x801]&&f->reg[0x830]==0xfc000000&&!f->reg[0x831]);
        CHECK(!memcmp(f->ring,words,sizeof(words)));++f->fence_writes;
    }
    f->reg[reg]=value;if(f->trace)printf("W %05x %08x\n",reg,value);return true;
}
static bool barrier(void *cookie)
{
    struct fake *f=cookie;if(!tick(f,true))return false;++f->barriers;
    if(f->trace&&f->context.phase==GGQ_SUBMIT)puts("B");
    if(f->trace&&f->context.phase==GGQ_WAIT)puts("I");return true;
}
static bool delay_us(void *cookie,unsigned us)
{struct fake *f=cookie;CHECK(us==10&&f->context.phase==GGQ_SUBMIT&&f->kept);if(!tick(f,true))return false;++f->delays;if(f->trace)printf("D %u\n",us);return true;}
static uint32_t *address(struct fake *f,enum ggq_memory memory,uint32_t off)
{
    CHECK(memory==GGQ_RING||memory==GGQ_SCRATCH);CHECK(!(off&3)&&off<(memory==GGQ_RING?32768u:4096u));
    CHECK(++f->burst<=64);if(f->burst>f->max_burst)f->max_burst=f->burst;
    return memory==GGQ_RING?&f->ring[off/4]:&f->scratch[off/4];
}
static bool read_memory(void *cookie,enum ggq_memory memory,uint32_t off,uint32_t *value)
{
    struct fake *f=cookie;uint32_t *p=address(f,memory,off);
    CHECK(f->context.phase==GGQ_MEMORY||f->context.phase==GGQ_COMMANDS||f->context.phase==GGQ_WAIT);
    if(!tick(f,off==0||off==256||off==(memory==GGQ_RING?32764u:4092u)))return false;
    ++f->mem_reads;if(f->mem_reads==f->mem_fail_read)return false;
    if(f->context.phase==GGQ_WAIT){
        CHECK(memory==GGQ_SCRATCH&&off==0&&f->submitted&&!f->kept&&f->reg[0x807]==15);
        /* Independent simulated device write, never a production CPU store. */
        if(f->shadow_reads++>=f->rptr_delay)*p=15;
        if(f->bad_rptr)*p=f->bad_rptr;
        if(f->trace)printf("P %08x\n",*p);
    }
    *value=*p;if(f->mem_reads==f->corrupt_read)*value^=1;return true;
}
static bool write_memory(void *cookie,enum ggq_memory memory,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;uint32_t *p=address(f,memory,off);
    CHECK(f->context.phase==GGQ_MEMORY||f->context.phase==GGQ_COMMANDS);
    if(f->context.phase==GGQ_MEMORY)CHECK(!f->context.work.sqe_start_attempted&&value==(memory==GGQ_RING?0xaaaaaaaau:0));
    else{CHECK(memory==GGQ_RING&&off==4*f->cmds&&value==words[f->cmds]&&f->reg[0x808]==1&&!f->submitted);++f->cmds;if(f->trace)printf("C %u %08x\n",off/4,value);}
    if(!tick(f,off==0||off==256||off==(memory==GGQ_RING?32764u:4092u)))return false;
    ++f->mem_writes;if(f->mem_writes==f->mem_fail_write)return false;
    if(f->mem_writes!=f->drop_write)*p=value;return true;
}
static struct fake *fresh(unsigned scenario)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan gmu;CHECK(ggm_plan_build(0xaa200000,&gmu)&&ggp_plan_build(&gmu,&f->plan));
    f->parent=(struct ggc_receipt){.start={.bank=2,.asid=3,.ttbr0=UINT64_C(0x00030000aa29c000),.tlb_status=2,.writes32=7,.writes64=1,.tlb_polls=1,.oob_polls=1,.request_attempted=1,.ack_valid=1,.ack_clear_attempted=1,.core_opened=1,.request_retained=1,.oob_ack=1u<<24},.reads=71,.writes=146,.mem_written=133,.mem_compared=1024,.list_length=132,.list_offset=72,.configured=1,.requests_retained=1};
    f->ops=(struct ggq_ops){f,guard,read32,write32,barrier,delay_us,read_memory,write_memory};
    memset(f->ring,0x5a,sizeof(f->ring));memset(f->scratch,0xa5,sizeof(f->scratch));
    f->drop_fence=scenario==1?1:scenario==2?100:scenario==3?199:0;f->counter_wrap=scenario==4;
    f->rptr_delay=scenario==1?2:0;f->busy_delay=scenario==1?2:0;return f;
}
static enum ggq_result run(struct fake *f,struct ggq_receipt *out)
{return ggq_start_once(&f->context,&f->ops,&f->plan,&f->parent,out);}
static void once(struct fake *f)
{struct ggq_receipt out,old;memset(&out,0x5a,sizeof(out));old=out;unsigned step=f->step;CHECK(run(f,&out)==GGQ_ALREADY&&f->step==step&&!memcmp(&out,&old,sizeof(out)));}
static void good(struct fake *f)
{
    struct ggq_receipt out;CHECK(run(f,&out)==GGQ_OK&&f->context.state==2&&f->context.phase==GGQ_DONE);
    CHECK(out.complete==1&&out.requests_retained==1&&out.ring_written==8192&&out.ring_checked==8192&&out.scratch_written==1024&&out.scratch_checked==1024&&out.commands_written==15&&out.commands_checked==8192);
    CHECK(out.sqe_start_attempted&&out.submit_attempted&&out.keepalive_set_attempted&&out.keepalive_clear_attempted&&!f->kept&&out.rptr==15&&!(out.busy&(1u<<23)));
    CHECK(out.fence_checks==f->drop_fence+1&&f->fence_writes==f->drop_fence+1&&f->delays==f->drop_fence&&out.fence_status==2&&out.fence_slow==(f->drop_fence>=100));
    CHECK(out.counter_before_valid&&out.counter_after_valid==out.fence_slow&&out.counter_before==(f->counter_wrap?UINT64_C(0x200000010):UINT64_C(0x112345678)));
    CHECK(out.writes==11+f->drop_fence&&f->max_burst==64&&GGQ_RB_CNTL==0x0800020c);
    CHECK(!memcmp(f->ring,words,sizeof(words)));for(unsigned i=15;i<8192;i++)CHECK(f->ring[i]==0xaaaaaaaa);once(f);
}
static void stopped(struct fake *f,enum ggq_result want)
{
    struct ggq_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
    CHECK(run(f,&out)==want&&f->context.state==3&&!memcmp(&out,&old,sizeof(out)));once(f);
}
int main(int argc,char **argv)
{
    if(argc==2){unsigned scenario=(unsigned)strtoul(argv[1],NULL,10);CHECK(scenario<5);struct fake *f=fresh(scenario);f->trace=1;good(f);free(f);return 0;}
    CHECK(argc==1);
    for(unsigned s=0;s<5;s++){
        struct fake *f=fresh(s);f->record=1;f->nested=1;good(f);unsigned n=f->point_count;unsigned *points=malloc(n*sizeof(*points));CHECK(points);memcpy(points,f->points,n*sizeof(*points));free(f);
        /* All guarded boundaries plus critical MMIO/selected memory callbacks. */
        if(s<=1)for(unsigned i=0;i<n;i++){
            f=fresh(s);f->fail=points[i];struct ggq_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
            CHECK(run(f,&out)!=GGQ_OK&&f->step==f->fail&&f->context.state==3&&!memcmp(&out,&old,sizeof(out)));once(f);free(f);
        }
        free(points);printf("GPU CP scenario%u: native sequence and%u boundaries PASS%s\n",s,n,s<=1?" (all injected)":"");
    }
    struct fake *f=fresh(0);f->drop_fence=200;stopped(f,GGQ_TIMEOUT);CHECK(f->kept&&!f->submitted&&f->fence_writes==201&&f->fence_reads==200&&!f->shadow_reads&&!f->context.work.keepalive_clear_attempted);free(f);
    f=fresh(0);f->rptr_delay=UINT32_MAX;stopped(f,GGQ_TIMEOUT);CHECK(f->shadow_reads==GGQ_IDLE_LIMIT&&!f->context.work.complete&&!f->kept);free(f);
    f=fresh(0);f->rptr_delay=UINT32_MAX;f->timeout_guard=3;stopped(f,GGQ_GUARD);CHECK(f->shadow_reads==3);free(f);
    f=fresh(0);f->busy_delay=UINT32_MAX;f->timeout_guard=3;stopped(f,GGQ_GUARD);CHECK(f->shadow_reads==3&&f->busy_reads==2);free(f);
    const unsigned mempoints[]={1,64,65,8192,8193,9216,9217,9231};
    for(unsigned i=0;i<sizeof(mempoints)/sizeof(*mempoints);i++){
        f=fresh(0);f->mem_fail_write=mempoints[i];stopped(f,GGQ_IO);CHECK(f->mem_writes==mempoints[i]&&!f->submitted);free(f);
        f=fresh(0);f->drop_write=mempoints[i];stopped(f,GGQ_MEMORY_ERROR);CHECK(!f->submitted);free(f);
    }
    const unsigned readpoints[]={1,64,65,8192,8193,9216,9217,17408};
    for(unsigned i=0;i<sizeof(readpoints)/sizeof(*readpoints);i++){
        f=fresh(0);f->mem_fail_read=readpoints[i];stopped(f,GGQ_IO);CHECK(f->mem_reads==readpoints[i]&&!f->submitted);free(f);
        f=fresh(0);f->corrupt_read=readpoints[i];stopped(f,GGQ_MEMORY_ERROR);CHECK(!f->submitted);free(f);
    }
    for(unsigned bit=0;bit<32;bit++)if(GGQ_RBBM_ERRORS&(1u<<bit)){
        f=fresh(0);f->reg[0x201]=1u<<bit;stopped(f,GGQ_FAULT);CHECK(!f->mem_writes);free(f);
    }
    for(unsigned bit=0;bit<8;bit++)if(GGQ_CP_ERRORS&(1u<<bit)){
        f=fresh(0);f->reg[0x823]=1u<<bit;stopped(f,GGQ_FAULT);CHECK(!f->mem_writes);free(f);
    }
    f=fresh(0);f->fault_after_submit=1;stopped(f,GGQ_FAULT);CHECK(!f->shadow_reads);free(f);
    f=fresh(0);f->bad_rptr=8192;stopped(f,GGQ_MEMORY_ERROR);CHECK(f->shadow_reads==1);free(f);
    f=fresh(0);f->bad_busy=1;stopped(f,GGQ_FAULT);CHECK(f->shadow_reads==1);free(f);
    f=fresh(0);f->mem_fail_read=17409;stopped(f,GGQ_IO);CHECK(f->submitted&&!f->shadow_reads);free(f);
    f=fresh(0);f->reg[0x201]=(1u<<20)|(1u<<15)|(1u<<8)|1u;good(f);free(f);
    for(unsigned reg=0x806;reg<=0x808;reg++){
        f=fresh(0);f->reg[reg]=reg==0x808?UINT32_MAX:1;stopped(f,reg==0x808?GGQ_FAULT:GGQ_DIRTY_STATE);CHECK(!f->mem_writes&&!f->context.work.writes);free(f);
    }
    f=fresh(0);f->parent.hwcg_skipped=1;f->parent.writes=80;f->parent.reads=69;good(f);free(f);
    for(unsigned n=0;n<12;n++){
        f=fresh(0);
        switch(n){case 0:f->parent.configured=0;break;case 1:f->parent.mem_compared=1023;break;case 2:f->parent.start.ttbr0^=4096;break;case 3:f->parent.start.contextidr=1;break;case 4:f->parent.start.tlb_status=1;break;case 5:f->parent.start.oob_before=1u<<24;break;case 6:f->parent.start.ack_valid=0;break;case 7:f->parent.start.request_retained=0;break;case 8:f->parent.list_offset=71;break;case 9:f->ops.barrier=NULL;break;case 10:f->ops.read_memory=NULL;break;default:f->plan.region[GGP_SCRATCH].iova+=4096;break;}
        struct ggq_receipt out,old;memset(&out,0x5a,sizeof(out));old=out;CHECK(run(f,&out)==GGQ_ARGUMENT&&!f->step&&!f->context.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    }
    f=fresh(0);CHECK(ggq_start_once(&f->context,&f->ops,&f->plan,&f->parent,&f->context.work)==GGQ_ARGUMENT&&!f->step);
    struct ggq_command cmd;CHECK(ggq_command_build(&f->plan,&cmd)&&!memcmp(cmd.word,words,sizeof(words)));CHECK(!ggq_command_build(&f->plan,(struct ggq_command *)&f->plan)&&!ggq_command_build(NULL,&cmd));free(f);
    const uint32_t forbidden[]={0x37,0x38,0x10000,0x12000,0x13fff,0x1f994,0x1f991,0x1f990,0x23b14,UINT32_MAX};
    for(unsigned i=0;i<sizeof(forbidden)/sizeof(*forbidden);i++)CHECK(!ggq_register_allowed(forbidden[i],true)&&!ggq_register_allowed(forbidden[i],false));
    printf("PASS: %u CP assertions; actual engine, bounded memory/protocol, native RPTR+busy completion, fault/output/once-state guards; no hardware proof\n",assertions);return 0;
}
