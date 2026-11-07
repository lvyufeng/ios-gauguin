/* Explicit hostile GPU MODEL, never IR3/Gallium/hardware emulation.
 * Golden native words are independent frozen source inputs. Only the modeled
 * DEVICE writes DATA; every production CPU write must be an exact RO artifact
 * or seven-word append. Pixel/EOP effects are modeled only after full staging
 * checks, never claimed as actual shader execution. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_draw.h"
#include "native_words.h"
static unsigned checks,cases;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"GPU triangle line%d\n",__LINE__);abort();}}while(0)
static const uint32_t prefix[20]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0,0x70620002,0xfc010000,0,0x70e60001,0,0x70620002,0xfc010000,0};
static const uint32_t command[7]={0x70bf8003,0xfc00c000,0,203,0x70620002,0xfc010000,0};
static uint32_t stage_offsets[1632],stage_values[1632];
static unsigned stage_count;
static const struct draw171_native_blob *golden_blob(unsigned id)
{return id<24?&draw171_rings[id]:id<27?&draw171_programs[id-24]:NULL;}
static bool golden_artifact(unsigned off)
{
    if(off&3)return false;
    for(unsigned id=0;id<27;id++){
        const struct draw171_native_blob *b=golden_blob(id);
        if(b->words&&off>=b->iova-DRAW171_RING_BASE&&off-(b->iova-DRAW171_RING_BASE)<b->gpu_serialized_extent)return true;
    }
    return false;
}
static void init_golden(void)
{
    for(unsigned id=0;id<27;id++){
        const struct draw171_native_blob *b=golden_blob(id);
        if(!b->words)continue;
        for(unsigned i=0;i<b->gpu_serialized_extent/4;i++){
            CHECK(stage_count<1632);stage_offsets[stage_count]=b->iova-DRAW171_RING_BASE+4*i;
            stage_values[stage_count++]=i<b->words?b->data[i]:0;
        }
    }
    CHECK(stage_count==1632);
}
struct fake {
    struct ggt_context c;struct ggt_ops ops;struct ggd_plan p;
    uint32_t ring[8192],scratch[1024],data[1024],reg[0x24000];
    unsigned step,fail,quarantined,sealed,seal_calls,private_ok,nested,trace;
    unsigned reads,writes,mem_reads,mem_writes,drop_command,corrupt_phase,corrupt_mem,corrupt_offset;
    unsigned kept,submitted,fence_reads,fence_writes,drop_fence,counter_reads,wrap;
    unsigned shadow_reads,busy_reads,rptr_delay,busy_delay,bad_rptr,bad_busy,timeout_guard,fault_after;
    unsigned nc_since_guard,max_nc_seen;
    unsigned device_done,device_writes,drop_data,drop_pixels,corrupt_data,eop_done,eop_reads,eop_delay,drop_eop,bad_eop,eop_guard;
    unsigned idle_control_pending;
};
static bool tick(struct fake *f)
{CHECK(!f->quarantined);return ++f->step!=f->fail;}
static bool guard(void *cookie,enum ggt_phase phase)
{
    struct fake *f=cookie;CHECK(f->c.state==1&&phase>=GGT_SEAL&&phase<=GGT_FINAL);
    CHECK(f->nc_since_guard<=64);if(f->max_nc_seen<f->nc_since_guard)f->max_nc_seen=f->nc_since_guard;
    f->nc_since_guard=0;
    if(f->nested){f->nested=0;struct ggt_receipt out,old;memset(&out,0x61,sizeof(out));old=out;unsigned steps=f->step;
        CHECK(ggt_start_once(&f->c,&f->ops,&f->p,&out)==GGT_ALREADY&&f->step==steps&&!memcmp(&out,&old,sizeof(out)));}
    if(phase==GGT_WAIT&&f->timeout_guard&&f->shadow_reads>=f->timeout_guard)return false;
    if(phase==GGT_WAIT&&f->eop_guard&&f->eop_reads>=f->eop_guard)return false;
    return tick(f);
}
static bool seal(void *cookie,uint64_t pa)
{struct fake *f=cookie;CHECK(f->c.phase==GGT_SEAL&&!f->seal_calls++);if(!tick(f)||!f->private_ok||pa!=0xaa200000)return false;f->sealed=1;return true;}
static void quarantine(void *cookie)
{struct fake *f=cookie;CHECK(f->c.state==3&&!f->quarantined);f->quarantined=1;}
static void device_execute(struct fake *f)
{
    CHECK(!f->device_done&&f->submitted&&f->reg[0x807]==27);f->device_done=1;
    CHECK(!memcmp(f->ring+20,command,sizeof(command))&&!(f->ring[23]&(1u<<20)));
    for(unsigned i=0;i<1632;i++)CHECK(f->ring[stage_offsets[i]/4]==stage_values[i]);
    for(unsigned i=0;i<256;i++){
        if(!f->drop_pixels&&f->drop_data!=i+1)f->data[i]=0xff00ff00;
        ++f->device_writes;
    }
}
static void device_eop(struct fake *f)
{
    CHECK(f->device_done&&!f->eop_done&&f->reg[0x807]==27);
    /* Six native source-aware addressed events, independently retained. */
    unsigned events=0;const uint32_t *ib=draw171_ring_00;
    for(unsigned i=0;i+4<203;i++)if(ib[i]==0x70460004u){
        CHECK(!(ib[i+1]&0xc0000000u)&&ib[i+2]==0xfc018c00u&&!ib[i+3]&&ib[i+4]==++events);
    }
    CHECK(events==6);f->data[768]=f->bad_eop?f->bad_eop:6;f->device_writes+=6;f->eop_done=1;
    if(f->corrupt_data){CHECK(f->corrupt_data<=1024);f->data[f->corrupt_data-1]^=1;}
}
static bool read32(void *cookie,uint32_t reg,uint32_t *out)
{
    struct fake *f=cookie;CHECK(f->sealed&&out&&ggt_register_allowed(reg,false));if(!tick(f))return false;++f->reads;*out=f->reg[reg];
    if(reg==0x23b13){*out=f->fence_reads++<f->drop_fence?3:2;if(!(*out&1)){f->submitted=1;if(!f->device_done)device_execute(f);}}
    if(reg==0x23b0c&&f->c.phase==GGT_WAIT)*out=f->bad_busy?~0u:f->busy_reads++<f->busy_delay?0x80800000u:0x80000000u;
    if(reg==0x823&&((f->fault_after==1&&f->c.phase==GGT_WAIT)||(f->fault_after==2&&f->c.phase==GGT_VERIFY)))*out=1;
    if(reg==0x1f888||reg==0x1f889){unsigned n=f->counter_reads++;*out=!f->wrap?(reg==0x1f889?1u:0x12345678u):n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:reg==0x1f889?2u:0x20u;}
    if(f->trace&&f->c.phase>=GGT_SUBMIT&&(reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889))printf("R %05x %08x\n",reg,*out);
    return true;
}
static bool write32(void *cookie,uint32_t reg,uint32_t value)
{
    struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGT_SUBMIT&&ggt_register_allowed(reg,true));
    CHECK(f->mem_writes==1639&&f->c.work.commands_checked==7&&f->c.work.artifact_checked==1632);
    CHECK(!memcmp(f->ring,prefix,sizeof(prefix))&&!memcmp(f->ring+20,command,sizeof(command)));
    for(unsigned i=0;i<1632;i++)CHECK(f->ring[stage_offsets[i]/4]==stage_values[i]);
    if(!tick(f))return false;++f->writes;
    if(reg==0x1f8c3){CHECK(value<=1);f->kept=value;}else{CHECK(value==27&&f->kept);++f->fence_writes;}
    f->reg[reg]=value;if(f->trace)printf("W %05x %08x\n",reg,value);return true;
}
static bool barrier(void *cookie)
{struct fake *f=cookie;if(!tick(f))return false;if(f->trace&&f->c.phase==GGT_SUBMIT)puts("B");if(f->trace&&f->c.phase==GGT_WAIT)puts("I");return true;}
static bool delay_us(void *cookie,unsigned us)
{struct fake *f=cookie;CHECK(us==10&&f->c.phase==GGT_SUBMIT&&f->kept);return tick(f);}
static bool read_memory(void *cookie,enum ggt_memory mem,uint32_t off,uint32_t *out)
{
    struct fake *f=cookie;CHECK(f->sealed&&out&&!(off&3));
    bool ring=mem==GGT_RING&&(off<108||golden_artifact(off));
    bool data=mem==GGT_DATA&&off<4096,scratch=mem==GGT_SCRATCH&&off==0;
    CHECK((f->c.phase==GGT_CAPTURE&&(ring||data||scratch))||
          (f->c.phase==GGT_COMMANDS&&ring&&(off>=80))||
          (f->c.phase==GGT_WAIT&&(scratch||(data&&(off==3072||off==3076))))||
          (f->c.phase==GGT_VERIFY&&(ring||data)));
    if(!tick(f))return false;++f->mem_reads;CHECK(++f->nc_since_guard<=64);
    if(f->c.phase==GGT_WAIT&&scratch){
        CHECK(f->submitted&&!f->kept&&f->device_done);f->idle_control_pending=1;
        if(f->shadow_reads++>=f->rptr_delay)f->scratch[0]=27;
        if(f->bad_rptr)f->scratch[0]=f->bad_rptr;
    }
    if(f->c.phase==GGT_WAIT&&data&&off==3072){
        if(f->idle_control_pending)f->idle_control_pending=0;
        else{
            if(f->eop_reads++>=f->eop_delay&&!f->eop_done&&!f->drop_eop)device_eop(f);
        }
    }
    *out=mem==GGT_RING?f->ring[off/4]:mem==GGT_DATA?f->data[off/4]:f->scratch[0];
    if(f->corrupt_phase==f->c.phase&&f->corrupt_mem==(unsigned)mem&&f->corrupt_offset==off)*out^=1;
    return true;
}
static bool write_memory(void *cookie,enum ggt_memory mem,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGT_COMMANDS&&mem==GGT_RING&&!(off&3));
    unsigned n=f->mem_writes;
    CHECK(n<1639&&off==(n<1632?stage_offsets[n]:80+4*(n-1632))&&value==(n<1632?stage_values[n]:command[n-1632]));
    if(!tick(f))return false;++f->mem_writes;CHECK(++f->nc_since_guard<=64);
    if(f->mem_writes!=f->drop_command)f->ring[off/4]=value;
    if(f->trace)printf("N %u %u %08x\n",mem,off/4,value);return true;
}
static struct fake *fresh(unsigned scenario)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan m;struct ggp_plan p;
    CHECK(ggm_plan_build(0xaa200000,&m)&&ggp_plan_build(&m,&p)&&ggd_plan_build(&p,&f->p));
    f->ops=(struct ggt_ops){f,guard,seal,read32,write32,barrier,delay_us,read_memory,write_memory,quarantine};f->private_ok=1;
    memset(f->ring,0xaa,sizeof(f->ring));memcpy(f->ring,prefix,sizeof(prefix));
    for(unsigned i=0;i<1024;i++)f->scratch[i]=0xd5432100u+i;f->scratch[0]=20;
    f->reg[0x807]=20;f->reg[0x23b0c]=0x71000000;
    f->drop_fence=scenario==1?1:scenario==2?100:scenario==3?199:0;f->wrap=scenario==4;
    f->rptr_delay=scenario==1?2:0;f->busy_delay=scenario==1?2:0;f->eop_delay=scenario==1?2:0;return f;
}
static enum ggt_result run(struct fake *f,struct ggt_receipt *out)
{return ggt_start_once(&f->c,&f->ops,&f->p,out);}
static void once(struct fake *f)
{struct ggt_receipt out,old;memset(&out,0x61,sizeof(out));old=out;unsigned steps=f->step;CHECK(run(f,&out)==GGT_ALREADY&&f->step==steps&&!memcmp(&out,&old,sizeof(out)));}
static void untouched(struct fake *f)
{
    CHECK(!memcmp(f->ring,prefix,sizeof(prefix)));
    for(unsigned i=27;i<8192;i++)if(!golden_artifact(i*4))CHECK(f->ring[i]==0xaaaaaaaa);
    for(unsigned i=1;i<1024;i++)CHECK(f->scratch[i]==0xd5432100u+i);
}
static void good(struct fake *f)
{
    struct ggt_receipt out;CHECK(run(f,&out)==GGT_OK&&f->c.state==2&&f->c.phase==GGT_DONE&&!f->quarantined);++cases;
    CHECK(out.sealed&&out.complete&&out.requests_retained&&out.prefix_checked==20&&out.clean_checked==7&&out.commands_written==7&&out.commands_checked==7);
    CHECK(out.artifact_clean_checked==1632&&out.artifact_written==1632&&out.artifact_checked==1632&&out.artifact_after_checked==1632);
    for(unsigned id=0;id<27;id++){
        unsigned size=golden_blob(id)->gpu_serialized_extent/4;
        CHECK(out.blob_clean_checked[id]==size&&out.blob_written[id]==size&&out.blob_checked[id]==size&&out.blob_after_checked[id]==size);
    }
    CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.pixels_checked==256&&out.foreground_checked==256&&!out.background_checked&&out.unchanged_checked==767&&out.eop_checked==1);
    CHECK(out.eop_complete==1&&out.eop_value==6&&out.eop_polls==f->eop_delay+1&&out.ring_after_checked==27&&f->device_writes==262);
    CHECK(out.max_nc_batch_words==64&&f->max_nc_seen<=64&&out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==27&&!(out.busy&(1u<<23)));
    CHECK(out.writes==3+f->drop_fence&&out.reads==f->reads&&out.fence_checks==f->drop_fence+1&&out.fence_slow==(f->drop_fence>=100));
    CHECK(out.counter_before_valid&&out.counter_after_valid==out.fence_slow&&out.counter_before==(f->wrap?UINT64_C(0x200000010):UINT64_C(0x112345678)));
    CHECK(out.submit_attempted&&out.keepalive_set_attempted&&out.keepalive_clear_attempted&&!f->kept&&out.wait_samples==out.idle_polls&&!out.wait_control_hi);
    for(unsigned i=0;i<1024;i++)CHECK(f->data[i]==(i<256?0xff00ff00u:i==768?6u:0u));
    untouched(f);once(f);
}
static void stopped(struct fake *f,enum ggt_result result)
{struct ggt_receipt out,old;memset(&out,0x61,sizeof(out));old=out;CHECK(run(f,&out)==result&&f->c.state==3&&f->quarantined&&!memcmp(&out,&old,sizeof(out)));++cases;untouched(f);once(f);}
int main(int argc,char **argv)
{
    init_golden();
    if(argc==2){unsigned scenario=(unsigned)strtoul(argv[1],NULL,10);CHECK(scenario<5);struct fake *f=fresh(scenario);f->trace=1;good(f);free(f);return 0;}CHECK(argc==1);
    for(unsigned s=0;s<5;s++){
        struct fake *f=fresh(s);f->nested=1;good(f);unsigned steps=f->step;free(f);
        if(s<2)for(unsigned i=1;i<=steps;i++){
            f=fresh(s);f->fail=i;struct ggt_receipt out,old;memset(&out,0x61,sizeof(out));old=out;
            CHECK(run(f,&out)!=GGT_OK&&f->c.state==3&&f->quarantined&&f->step==i&&!memcmp(&out,&old,sizeof(out)));++cases;untouched(f);once(f);free(f);
        }
        printf("GPU triangle scenario%u: all27 slots/1632 padded artifact words/pixels256/EOP6; %u callback boundaries PASS%s\n",s,steps,s<2?" (all injected)":"");fflush(stdout);
    }
    for(unsigned phase=GGT_CAPTURE;phase<=GGT_VERIFY;phase++){
        if(phase!=GGT_CAPTURE&&phase!=GGT_COMMANDS&&phase!=GGT_VERIFY)continue;
        for(unsigned off=(phase==GGT_COMMANDS?80u:0u);off<108;off+=4){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGT_RING;f->corrupt_offset=off;stopped(f,GGT_MEMORY_ERROR);free(f);}
        for(unsigned i=0;i<1632;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGT_RING;f->corrupt_offset=stage_offsets[i];stopped(f,GGT_MEMORY_ERROR);free(f);}
        if(phase!=GGT_COMMANDS)for(unsigned off=0;off<4096;off+=4){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGT_DATA;f->corrupt_offset=off;stopped(f,GGT_MEMORY_ERROR);free(f);}
    }
    for(unsigned i=1;i<=1639;i++){struct fake *f=fresh(0);f->drop_command=i;stopped(f,GGT_MEMORY_ERROR);CHECK(!f->writes&&!f->device_writes);free(f);}
    for(unsigned i=1;i<=1024;i++){struct fake *f=fresh(0);f->corrupt_data=i;stopped(f,GGT_MEMORY_ERROR);CHECK(f->device_writes==262);free(f);}
    for(unsigned i=1;i<=256;i++){struct fake *f=fresh(0);f->drop_data=i;stopped(f,GGT_MEMORY_ERROR);free(f);}
    for(unsigned delay=1;delay<=1023;delay=delay==1?2:delay==2?1023:1024){struct fake *f=fresh(0);f->eop_delay=delay;good(f);free(f);}
    {struct fake *f=fresh(0);f->drop_eop=1;stopped(f,GGT_TIMEOUT);CHECK(f->eop_reads==1024&&f->scratch[0]==27&&!f->kept&&f->device_writes==256);free(f);}
    {const unsigned wrong[]={1,5,7,0x0cf49802u,~0u};for(unsigned i=0;i<5;i++){
        struct fake *f=fresh(0);f->bad_eop=wrong[i];stopped(f,GGT_MEMORY_ERROR);CHECK(f->eop_reads==1&&!f->c.work.eop_complete&&!f->c.work.data_after_checked);free(f);
    }}
    {struct fake *f=fresh(0);f->drop_eop=1;f->eop_guard=3;stopped(f,GGT_GUARD);free(f);}
    for(unsigned off=3072;off<=3076;off+=4){struct fake *f=fresh(0);f->corrupt_phase=GGT_WAIT;f->corrupt_mem=GGT_DATA;f->corrupt_offset=off;stopped(f,GGT_MEMORY_ERROR);free(f);}
    {struct fake *f=fresh(0);f->drop_pixels=1;stopped(f,GGT_MEMORY_ERROR);CHECK(f->eop_done&&f->data[768]==6&&f->scratch[0]==27);free(f);}
    struct fake *f=fresh(0);f->private_ok=0;stopped(f,GGT_OWNER);CHECK(!f->reads&&!f->mem_reads&&!f->writes);free(f);
    for(unsigned bit=0;bit<32;bit++){
        if(GGQ_RBBM_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x201]=1u<<bit;stopped(f,GGT_FAULT);free(f);}
        if(GGQ_CP_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x823]=1u<<bit;stopped(f,GGT_FAULT);free(f);}
    }
    for(unsigned i=1;i<=2;i++){f=fresh(0);f->fault_after=i;stopped(f,GGT_FAULT);free(f);}
    f=fresh(0);f->reg[0x807]=19;stopped(f,GGT_DIRTY_STATE);free(f);
    f=fresh(0);f->scratch[0]=19;stopped(f,GGT_MEMORY_ERROR);free(f);
    f=fresh(0);f->reg[0x23b0c]|=1u<<23;stopped(f,GGT_FAULT);free(f);
    f=fresh(0);f->bad_rptr=8192;stopped(f,GGT_MEMORY_ERROR);free(f);
    f=fresh(0);f->bad_busy=1;stopped(f,GGT_FAULT);free(f);
    f=fresh(0);f->drop_fence=200;stopped(f,GGT_TIMEOUT);CHECK(f->fence_reads==200&&f->fence_writes==201&&f->kept&&!f->submitted);free(f);
    f=fresh(0);f->rptr_delay=~0u;stopped(f,GGT_TIMEOUT);CHECK(f->shadow_reads==200000);free(f);
    for(unsigned busy=0;busy<2;busy++){f=fresh(0);if(busy)f->busy_delay=~0u;else f->rptr_delay=~0u;f->timeout_guard=3;stopped(f,GGT_GUARD);free(f);}
    f=fresh(0);struct ggt_receipt out,old;memset(&out,0x61,sizeof(out));old=out;
    CHECK(ggt_start_once(NULL,&f->ops,&f->p,&out)==GGT_ARGUMENT);
    CHECK(ggt_start_once(&f->c,NULL,&f->p,&out)==GGT_ARGUMENT);
    CHECK(ggt_start_once(&f->c,&f->ops,NULL,&out)==GGT_ARGUMENT);
    CHECK(ggt_start_once(&f->c,&f->ops,&f->p,NULL)==GGT_ARGUMENT);
    CHECK(ggt_start_once(&f->c,&f->ops,&f->p,(struct ggt_receipt *)&f->c)==GGT_ARGUMENT);
    CHECK(ggt_start_once((struct ggt_context *)(uintptr_t)(UINTPTR_MAX-4),&f->ops,&f->p,&out)==GGT_ARGUMENT);
    CHECK(!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    for(unsigned i=0;i<9;i++){
        f=fresh(0);switch(i){case 0:f->ops.guard=NULL;break;case 1:f->ops.seal=NULL;break;case 2:f->ops.read32=NULL;break;case 3:f->ops.write32=NULL;break;case 4:f->ops.barrier=NULL;break;case 5:f->ops.delay_us=NULL;break;case 6:f->ops.read_memory=NULL;break;case 7:f->ops.write_memory=NULL;break;case 8:f->ops.quarantine=NULL;break;}
        CHECK(run(f,&out)==GGT_ARGUMENT&&!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    }
    for(unsigned reg=0;reg<0x24000;reg++)CHECK(ggt_register_allowed(reg,true)==(reg==0x807||reg==0x1f8c3)&&ggt_register_allowed(reg,false)==(reg==0x807||reg==0x201||reg==0x823||reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889));
    for(unsigned off=0;off<32768;off++)CHECK(ggt_artifact_allowed(off)==golden_artifact(off));
    CHECK(!ggt_artifact_allowed(~0u)&&!ggt_artifact_allowed(32768));
    for(unsigned id=0;id<27;id++){
        struct ggt_blob b;CHECK(ggt_blob_get(id,&b));const struct draw171_native_blob *g=golden_blob(id);
        CHECK(b.words==g->gpu_serialized_extent/4&&b.payload_words==g->words&&b.offset==(g->words?g->iova-DRAW171_RING_BASE:0));
        for(unsigned j=0;j<b.words;j++){uint32_t value=0;CHECK(ggt_blob_word(id,j,&value)&&value==(j<g->words?g->data[j]:0));}
        uint32_t unchanged=0x12345678;CHECK(!ggt_blob_word(id,b.words,&unchanged)&&unchanged==0x12345678);
    }
    struct ggt_blob b,previous;memset(&b,0x61,sizeof(b));previous=b;CHECK(!ggt_blob_get(27,&b)&&!memcmp(&b,&previous,sizeof(b))&&!ggt_blob_get(0,NULL));
    f=fresh(0);struct ggt_command cmd,saved;memset(&cmd,0x61,sizeof(cmd));saved=cmd;
    CHECK(ggt_command_build(&f->p,&cmd)&&!memcmp(cmd.word,command,sizeof(command)));cmd=saved;
    CHECK(!ggt_command_build(NULL,&cmd)&&!memcmp(&cmd,&saved,sizeof(cmd))&&!ggt_command_build(&f->p,NULL));
    CHECK(!ggt_command_build(&f->p,(struct ggt_command *)&f->p));
    for(unsigned test=0;test<6;test++){
        struct ggd_plan plan=f->p;
        switch(test){case 0:plan.bootstrap.region[GGP_RING].readonly=false;break;case 1:plan.bootstrap.region[GGP_RING].privileged=true;break;case 2:plan.bootstrap.region[GGP_RING].executable=true;break;case 3:plan.bootstrap.region[GGP_RING].mapped-=4096;break;case 4:plan.bootstrap.region[GGP_RING].iova+=4096;break;case 5:plan.data.iova+=4096;break;}
        CHECK(!ggt_command_build(&plan,&cmd)&&!memcmp(&cmd,&saved,sizeof(cmd)));
    }
    free(f);
    printf("PASS: GPU triangle %u cases/%u assertions; all callback failures, all1632 staged/padded words in capture/commands/verify, full DATA1024 corruptions, dropped1639 CPU writes, dropped pixels, separate EOP6/idle, output/once/quarantine/timeouts/faults. Pure hostile model, NO GPU execution or Metal proof.\n",cases,checks);
}
