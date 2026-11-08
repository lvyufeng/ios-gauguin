/* Hostile MODEL of one fixed three-submit GPU session. No IR3 emulation.
 * Only the modeled DEVICE writes DATA. Frozen independent native references
 * admit every CPU ring write. Pixel oracle uses integer geometry separately
 *from the engine's native semantic table. No physical GPU/Metal claim. */
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_varying.h"
#include "native_words.h"
#include "pixel_vectors173.h"
static uint64_t checks,cases;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"GPU varying line%d\n",__LINE__);abort();}}while(0)
static const uint32_t prefix[20]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0,0x70620002,0xfc010000,0,0x70e60001,0,0x70620002,0xfc010000,0};
static const uint32_t command[7]={0x70bf8003,0xfc00c000,0,203,0x70620002,0xfc010000,0};
static uint32_t stage_offsets[1632],stage_values[3][1632];
static unsigned stage_count;
static uint32_t pixel(unsigned job,unsigned index)
{return reference_preferred[job][index];}
static uint32_t rounding_choice(unsigned job,unsigned index,unsigned choice)
{
    uint32_t lo=reference_lower[job][index],hi=reference_upper[job][index],value=0;
    for(unsigned c=0;c<4;c++)value|=(((choice&(1u<<c)?hi:lo)>>(8*c))&255u)<<(8*c);
    return value;
}
static bool declared(unsigned job,unsigned index,uint32_t value)
{
    uint32_t lo=reference_lower[job][index],hi=reference_upper[job][index];
    for(unsigned c=0;c<4;c++)if(((value>>(8*c))&255u)<((lo>>(8*c))&255u)||((value>>(8*c))&255u)>((hi>>(8*c))&255u))return false;
    return true;
}
static uint32_t expected_data(unsigned job,unsigned index)
{return index<256?pixel(job,index):index==768?16*job+6:0;}
static bool artifact(unsigned off)
{
    if(off&3)return false;
    for(unsigned id=0;id<27;id++){
        const struct varying173_native_blob *b=&varying173_blobs[0][id];
        if(b->words&&off>=b->iova-0xfc008000u&&off-(b->iova-0xfc008000u)<b->gpu_serialized_extent)return true;
    }
    return false;
}
static void init_golden(void)
{
    for(unsigned job=0;job<3;job++){
        unsigned count=0;
        for(unsigned id=0;id<27;id++){
            const struct varying173_native_blob *b=&varying173_blobs[job][id];
            if(!b->words)continue;
            for(unsigned i=0;i<b->gpu_serialized_extent/4;i++){
                CHECK(count<1632);unsigned off=b->iova-0xfc008000u+4*i;
                if(!job)stage_offsets[count]=off;else CHECK(stage_offsets[count]==off);
                stage_values[job][count++]=i<b->words?b->data[i]:0;
            }
        }
        CHECK(count==1632);stage_count=count;
    }
    CHECK(stage_count==1632);
    CHECK(reference_preferred[0][0]==0xff400808u&&reference_preferred[2][255]==0xff400000u);
}
struct job_model {
    unsigned kept,submitted,fence_reads,fence_writes,drop_fence,counter_reads,wrap;
    unsigned shadow_reads,busy_reads,rptr_delay,busy_delay,bad_rptr,bad_busy,fault_after;
    unsigned mem_writes,device_done,device_writes,eop_done,eop_reads,eop_delay;
    unsigned drop_eop,bad_eop,intermediate,regress,idle_control_pending,skip_draw;
};
struct fake {
    struct ggv_context c;struct ggv_ops ops;struct ggd_plan p;
    uint32_t ring[8192],scratch[1024],data[1024],reg[0x24000],produced[3][256];
    struct job_model j[3];
    unsigned step,fail,quarantined,sealed,seal_calls,private_ok,nested,trace;
    unsigned reads,writes,mem_reads,mem_writes,drop_command,corrupt_phase,corrupt_mem,corrupt_offset,corrupt_job;
    unsigned nc_since_guard,max_nc_seen,drop_pixel,drop_pixel_job,corrupt_data,corrupt_data_job;
    unsigned timeout_guard,timeout_job,eop_guard,eop_guard_job;
    unsigned mutation_kind,mutation_job,mutation_phase,mutation_done;
    unsigned between_job,between_mem,between_offset,between_done,between_set;uint32_t between_value;
};
static bool tick(struct fake *f)
{CHECK(!f->quarantined);return ++f->step!=f->fail;}
static bool guard(void *cookie,unsigned job,enum ggv_phase phase)
{
    struct fake *f=cookie;CHECK(f->c.state==1&&job<3&&f->c.job==job&&phase>=GGV_SEAL&&phase<=GGV_FINAL&&f->c.phase==(unsigned)phase);
    CHECK(f->nc_since_guard<=64);if(f->max_nc_seen<f->nc_since_guard)f->max_nc_seen=f->nc_since_guard;f->nc_since_guard=0;
    if(f->nested){f->nested=0;struct ggv_receipt out,old;memset(&out,0x61,sizeof(out));old=out;unsigned steps=f->step;
        CHECK(ggv_start_once(&f->c,&f->ops,&f->p,&out)==GGV_ALREADY&&f->step==steps&&!memcmp(&out,&old,sizeof(out)));}
    if(f->between_job==job+1&&phase==GGV_CAPTURE&&!f->between_done){
        f->between_done=1;CHECK(f->between_offset<4096&&!(f->between_offset&3));
        if(f->between_mem==GGV_DATA){if(f->between_set)f->data[f->between_offset/4]=f->between_value;else f->data[f->between_offset/4]^=1;}
        else if(f->between_mem==GGV_RING)f->ring[f->between_offset/4]^=1;
        else f->scratch[0]^=1;
    }
    if(job==f->timeout_job&&phase==GGV_WAIT&&f->timeout_guard&&f->j[job].shadow_reads>=f->timeout_guard)return false;
    if(job==f->eop_guard_job&&phase==GGV_WAIT&&f->eop_guard&&f->j[job].eop_reads>=f->eop_guard)return false;
    if(!tick(f))return false;
    if(f->mutation_kind&&job==f->mutation_job&&phase==(enum ggv_phase)f->mutation_phase&&!f->mutation_done){
        f->mutation_done=1;
        switch(f->mutation_kind){
        case 1:f->c.job=~0u;break;case 2:f->c.phase=~0u;break;case 3:f->c.state=2;break;
        case 4:f->c.ops.cookie=NULL;break;case 5:f->c.command.word[1]^=4096;break;case 6:f->c.work.completed_jobs^=1;break;
        default:CHECK(false);
        }
    }
    return true;
}
static bool seal(void *cookie,uint64_t pa)
{struct fake *f=cookie;CHECK(!f->c.job&&f->c.phase==GGV_SEAL&&!f->seal_calls++);if(!tick(f)||!f->private_ok||pa!=0xaa200000)return false;f->sealed=1;return true;}
static void quarantine(void *cookie)
{struct fake *f=cookie;CHECK(f&&f->c.state==3&&!f->quarantined);f->quarantined=1;}
static void root_and_artifacts(struct fake *f,unsigned job)
{
    CHECK(!memcmp(f->ring,prefix,sizeof(prefix)));
    for(unsigned j=0;j<=job;j++)CHECK(!memcmp(f->ring+20+7*j,command,sizeof(command)));
    for(unsigned i=0;i<1632;i++)CHECK(f->ring[stage_offsets[i]/4]==stage_values[job][i]);
}
static void device_execute(struct fake *f,unsigned job)
{
    struct job_model *m=&f->j[job];CHECK(!m->device_done&&m->submitted&&f->reg[0x807]==27+7*job);m->device_done=1;
    CHECK(f->c.work.completed_jobs==job&&f->c.work.job[job].artifact_checked==1632&&m->mem_writes==1639);root_and_artifacts(f,job);
    if(job)CHECK(f->j[job-1].eop_done&&f->c.work.job[job-1].complete);
    for(unsigned i=0;i<256;i++){
        if(!m->skip_draw&&!(f->drop_pixel_job==job&&f->drop_pixel==i+1))f->data[i]=f->produced[job][i];
        ++m->device_writes;
    }
}
static void device_eop(struct fake *f,unsigned job)
{
    struct job_model *m=&f->j[job];CHECK(m->device_done&&!m->eop_done&&f->reg[0x807]==27+7*job);
    const uint32_t *ib=varying173_blobs[job][0].data;unsigned events=0;
    for(unsigned i=0;i+4<203;i++)if(ib[i]==0x70460004u){
        CHECK(!(ib[i+1]&0xc0000000u)&&ib[i+2]==0xfc018c00u&&!ib[i+3]&&ib[i+4]==16*job+(++events));
    }
    CHECK(events==6);f->data[768]=m->bad_eop?m->bad_eop:16*job+6;m->device_writes+=6;m->eop_done=1;
    if(f->corrupt_data&&f->corrupt_data_job==job){CHECK(f->corrupt_data<=1024);f->data[f->corrupt_data-1]^=1;}
}
static bool read32(void *cookie,uint32_t reg,uint32_t *out)
{
    struct fake *f=cookie;unsigned job=f->c.job;CHECK(f->sealed&&job<3&&out&&ggv_register_allowed(reg,false));struct job_model *m=&f->j[job];
    if(!tick(f))return false;++f->reads;*out=f->reg[reg];
    if(reg==0x23b13){*out=m->fence_reads++<m->drop_fence?3:2;if(!(*out&1)){m->submitted=1;if(!m->device_done)device_execute(f,job);}}
    if(reg==0x23b0c&&f->c.phase==GGV_WAIT)*out=m->bad_busy?~0u:m->busy_reads++<m->busy_delay?0x80800000u:0x80000000u;
    if(reg==0x823&&((m->fault_after==1&&f->c.phase==GGV_WAIT)||(m->fault_after==2&&f->c.phase==GGV_VERIFY)))*out=1;
    if(reg==0x1f888||reg==0x1f889){unsigned n=m->counter_reads++;*out=!m->wrap?(reg==0x1f889?1u:0x12345678u):n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:reg==0x1f889?2u:0x20u;}
    if(f->trace&&f->c.phase>=GGV_SUBMIT&&(reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889))printf("R %u %05x %08x\n",job,reg,*out);
    return true;
}
static bool write32(void *cookie,uint32_t reg,uint32_t value)
{
    struct fake *f=cookie;unsigned job=f->c.job;CHECK(f->sealed&&job<3&&f->c.phase==GGV_SUBMIT&&ggv_register_allowed(reg,true));struct job_model *m=&f->j[job];
    CHECK(m->mem_writes==1639&&f->c.work.job[job].commands_checked==7&&f->c.work.job[job].artifact_checked==1632);root_and_artifacts(f,job);
    if(!tick(f))return false;++f->writes;
    if(reg==0x1f8c3){CHECK(value<=1);m->kept=value;}else{CHECK(value==27+7*job&&m->kept);++m->fence_writes;}
    f->reg[reg]=value;if(f->trace)printf("W %u %05x %08x\n",job,reg,value);return true;
}
static bool barrier(void *cookie)
{struct fake *f=cookie;if(!tick(f))return false;if(f->trace&&f->c.phase==GGV_SUBMIT)puts("B");if(f->trace&&f->c.phase==GGV_WAIT)puts("I");return true;}
static bool delay_us(void *cookie,unsigned us)
{struct fake *f=cookie;CHECK(f->c.job<3&&us==10&&f->c.phase==GGV_SUBMIT&&f->j[f->c.job].kept);return tick(f);}
static bool read_memory(void *cookie,enum ggv_memory mem,uint32_t off,uint32_t *out)
{
    struct fake *f=cookie;unsigned job=f->c.job;CHECK(f->sealed&&job<3&&out&&!(off&3));struct job_model *m=&f->j[job];
    unsigned start=20+7*job,end=start+7;bool ring=mem==GGV_RING&&(off<4*end||artifact(off));
    bool data=mem==GGV_DATA&&off<4096,scratch=mem==GGV_SCRATCH&&off==0;
    CHECK((f->c.phase==GGV_CAPTURE&&(ring||data||scratch))||
      (f->c.phase==GGV_COMMANDS&&ring&&off>=4*start)||
      (f->c.phase==GGV_WAIT&&(scratch||(data&&(off==3072||off==3076))))||
      (f->c.phase==GGV_VERIFY&&(ring||data)));
    if(!tick(f))return false;++f->mem_reads;CHECK(++f->nc_since_guard<=64);
    if(f->c.phase==GGV_WAIT&&scratch){
        CHECK(m->submitted&&!m->kept&&m->device_done);m->idle_control_pending=1;
        if(m->shadow_reads++>=m->rptr_delay)f->scratch[0]=end;
        if(m->bad_rptr)f->scratch[0]=m->bad_rptr;
    }
    if(f->c.phase==GGV_WAIT&&data&&off==3072){
        if(m->idle_control_pending)m->idle_control_pending=0;
        else{
            unsigned poll=m->eop_reads++;
            if(poll>=m->eop_delay&&!m->eop_done&&!m->drop_eop)device_eop(f,job);
            else if(m->regress)f->data[768]=poll?job?16*(job-1)+6:0:16*job+1;
            else if(m->intermediate)f->data[768]=16*job+(poll<5?poll+1:5);
        }
    }
    *out=mem==GGV_RING?f->ring[off/4]:mem==GGV_DATA?f->data[off/4]:f->scratch[0];
    if(f->corrupt_job==job&&f->corrupt_phase==f->c.phase&&f->corrupt_mem==(unsigned)mem&&f->corrupt_offset==off)*out^=1;
    return true;
}
static bool write_memory(void *cookie,enum ggv_memory mem,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;unsigned job=f->c.job;CHECK(f->sealed&&job<3&&f->c.phase==GGV_COMMANDS&&mem==GGV_RING&&!(off&3));struct job_model *m=&f->j[job];
    unsigned n=m->mem_writes;CHECK(n<1639&&off==(n<1632?stage_offsets[n]:4*(20+7*job+n-1632))&&value==(n<1632?stage_values[job][n]:command[n-1632]));
    if(!tick(f))return false;++m->mem_writes;++f->mem_writes;CHECK(++f->nc_since_guard<=64);
    if(f->mem_writes!=f->drop_command)f->ring[off/4]=value;
    if(f->trace)printf("N %u %u %u %08x\n",job,mem,off/4,value);return true;
}
static struct fake *fresh(unsigned scenario)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan m;struct ggp_plan p;
    CHECK(ggm_plan_build(0xaa200000,&m)&&ggp_plan_build(&m,&p)&&ggd_plan_build(&p,&f->p));
    f->ops=(struct ggv_ops){f,guard,seal,read32,write32,barrier,delay_us,read_memory,write_memory,quarantine};f->private_ok=1;
    memset(f->ring,0xaa,sizeof(f->ring));memcpy(f->ring,prefix,sizeof(prefix));
    for(unsigned i=0;i<1024;i++)f->scratch[i]=0xd5432100u+i;f->scratch[0]=20;
    f->reg[0x807]=20;f->reg[0x23b0c]=0x71000000;
    for(unsigned j=0;j<3;j++)for(unsigned i=0;i<256;i++)f->produced[j][i]=pixel(j,i);
    for(unsigned j=0;j<3;j++){
        f->j[j].drop_fence=scenario==1?1:scenario==2?100:scenario==3?199:0;f->j[j].wrap=scenario==4;
        f->j[j].rptr_delay=scenario==1?2:0;f->j[j].busy_delay=scenario==1?2:0;f->j[j].eop_delay=scenario==1?2:0;
    }
    return f;
}
static enum ggv_result run(struct fake *f,struct ggv_receipt *out)
{return ggv_start_once(&f->c,&f->ops,&f->p,out);}
static void once(struct fake *f)
{struct ggv_receipt out,old;memset(&out,0x61,sizeof(out));old=out;unsigned steps=f->step;CHECK(run(f,&out)==GGV_ALREADY&&f->step==steps&&!memcmp(&out,&old,sizeof(out)));}
static void untouched(struct fake *f)
{
    CHECK(!memcmp(f->ring,prefix,sizeof(prefix)));
    for(unsigned i=41;i<8192;i++)if(!artifact(i*4))CHECK(f->ring[i]==0xaaaaaaaa);
    for(unsigned i=1;i<1024;i++)CHECK(f->scratch[i]==0xd5432100u+i);
}
static void good(struct fake *f)
{
    struct ggv_receipt out;CHECK(run(f,&out)==GGV_OK&&f->c.state==2&&f->c.phase==GGV_DONE&&f->c.job==2&&!f->quarantined);++cases;
    CHECK(out.sealed&&out.complete&&out.requests_retained&&out.completed_jobs==3&&f->seal_calls==1&&f->mem_writes==4917);
    for(unsigned j=0;j<3;j++){
        struct ggv_job_receipt *r=&out.job[j];struct job_model *m=&f->j[j];
        CHECK(r->complete&&r->prefix_checked==20+7*j&&r->clean_checked==7&&r->commands_written==7&&r->commands_checked==7);
        CHECK(r->artifact_before_checked==1632&&r->artifact_written==1632&&r->artifact_checked==1632&&r->artifact_after_checked==1632);
        for(unsigned id=0;id<27;id++){
            unsigned size=varying173_blobs[j][id].gpu_serialized_extent/4;
            CHECK(r->blob_before_checked[id]==size&&r->blob_written[id]==size&&r->blob_checked[id]==size&&r->blob_after_checked[id]==size);
        }
        CHECK(r->data_before_checked==1024&&r->data_after_checked==1024&&r->pixels_checked==256&&r->foreground_checked==256&&r->background_checked==0&&r->unchanged_checked==767&&r->eop_checked==1);
        CHECK(r->eop_complete==1&&r->eop_value==16*j+6&&r->eop_polls==m->eop_delay+1&&r->ring_after_checked==27+7*j&&m->device_writes==262&&r->eop_progress==6);
        CHECK(r->max_nc_batch_words==64&&f->max_nc_seen<=64&&r->initial_wptr==20+7*j&&r->initial_shadow==20+7*j&&r->rptr==27+7*j&&!(r->busy&(1u<<23)));
        CHECK(r->writes==3+m->drop_fence&&r->fence_checks==m->drop_fence+1&&r->fence_slow==(m->drop_fence>=100));
        CHECK(r->counter_before_valid&&r->counter_after_valid==r->fence_slow&&r->counter_before==(m->wrap?UINT64_C(0x200000010):UINT64_C(0x112345678)));
        CHECK(r->submit_attempted&&r->keepalive_set_attempted&&r->keepalive_clear_attempted&&!m->kept&&r->wait_samples==r->idle_polls&&!r->wait_control_hi);
    }
    for(unsigned i=0;i<1024;i++)CHECK(f->data[i]==(i<256?f->produced[2][i]:expected_data(2,i)));untouched(f);once(f);
}
static void stopped(struct fake *f,enum ggv_result result)
{struct ggv_receipt out,old;memset(&out,0x61,sizeof(out));old=out;enum ggv_result actual=run(f,&out);if(actual!=result)fprintf(stderr,"expected%d actual%d job%u phase%u diag %x/%x/%x\n",result,actual,f->c.job,f->c.phase,f->c.diagnostic.reg,f->c.diagnostic.expected,f->c.diagnostic.actual);CHECK(actual==result&&f->c.state==3&&f->quarantined&&!memcmp(&out,&old,sizeof(out)));++cases;untouched(f);once(f);}
int main(int argc,char **argv)
{
    init_golden();
    if(argc==2){unsigned scenario=(unsigned)strtoul(argv[1],NULL,10);CHECK(scenario<5);struct fake *f=fresh(scenario);f->trace=1;good(f);free(f);return 0;}CHECK(argc==1);
    for(unsigned s=0;s<5;s++){
        struct fake *f=fresh(s);f->nested=1;good(f);unsigned steps=f->step;free(f);
        if(s<2)for(unsigned i=1;i<=steps;i++){
            f=fresh(s);f->fail=i;struct ggv_receipt out,old;memset(&out,0x61,sizeof(out));old=out;
            CHECK(run(f,&out)!=GGV_OK&&f->c.state==3&&f->quarantined&&f->step==i&&!memcmp(&out,&old,sizeof(out)));++cases;untouched(f);once(f);free(f);
        }
        printf("GPU varying scenario%u: all3jobs/27slots/1632 padded words/pixels256/EOP6,22,38; %u callback boundaries PASS%s\n",s,steps,s<2?" (all injected)":"");fflush(stdout);
    }
    for(unsigned j=0;j<3;j++){
        for(unsigned phase=GGV_CAPTURE;phase<=GGV_VERIFY;phase++){
            if(phase!=GGV_CAPTURE&&phase!=GGV_COMMANDS&&phase!=GGV_VERIFY)continue;
            for(unsigned off=(phase==GGV_COMMANDS?4*(20+7*j):0);off<4*(27+7*j);off+=4){struct fake *f=fresh(0);f->corrupt_job=j;f->corrupt_phase=phase;f->corrupt_mem=GGV_RING;f->corrupt_offset=off;stopped(f,GGV_MEMORY_ERROR);free(f);}
            for(unsigned i=0;i<1632;i++){struct fake *f=fresh(0);f->corrupt_job=j;f->corrupt_phase=phase;f->corrupt_mem=GGV_RING;f->corrupt_offset=stage_offsets[i];stopped(f,GGV_MEMORY_ERROR);free(f);}
            if(phase!=GGV_COMMANDS)for(unsigned off=0;off<4096;off+=4){struct fake *f=fresh(0);f->corrupt_job=j;f->corrupt_phase=phase;f->corrupt_mem=GGV_DATA;f->corrupt_offset=off;stopped(f,GGV_MEMORY_ERROR);free(f);}
        }
        for(unsigned i=1;i<=1639;i++){
            struct fake *f=fresh(0);f->drop_command=j*1639+i;
            bool same=j&&i<=1632&&stage_values[j][i-1]==stage_values[j-1][i-1];
            if(same)good(f);else{stopped(f,GGV_MEMORY_ERROR);CHECK(!f->j[j].submitted&&!f->j[j].device_writes);}
            free(f);
        }
        for(unsigned i=1;i<=1024;i++){struct fake *f=fresh(0);f->corrupt_data_job=j;f->corrupt_data=i;if(i<=256&&declared(j,i-1,pixel(j,i-1)^1u))good(f);else stopped(f,GGV_MEMORY_ERROR);CHECK(f->j[j].device_writes==262);free(f);}
        for(unsigned i=1;i<=256;i++){struct fake *f=fresh(0);f->drop_pixel_job=j;f->drop_pixel=i;if(j&&declared(j,i-1,pixel(j-1,i-1)))good(f);else stopped(f,GGV_MEMORY_ERROR);free(f);}
        {struct fake *f=fresh(0);f->j[j].skip_draw=1;stopped(f,GGV_MEMORY_ERROR);CHECK(f->j[j].eop_done&&f->data[768]==16*j+6);free(f);}
        {struct fake *f=fresh(0);f->j[j].drop_eop=1;stopped(f,GGV_TIMEOUT);CHECK(f->j[j].eop_reads==1024&&f->scratch[0]==27+7*j&&f->j[j].device_writes==256&&!f->c.work.job[j].eop_complete);free(f);}
        for(unsigned delay=1;delay<=1023;delay=delay==1?2:delay==2?1023:1024){struct fake *f=fresh(0);f->j[j].eop_delay=delay;good(f);free(f);}
        {struct fake *f=fresh(0);f->j[j].eop_delay=6;f->j[j].intermediate=1;good(f);free(f);}
        {struct fake *f=fresh(0);f->j[j].drop_eop=1;f->j[j].regress=1;stopped(f,GGV_MEMORY_ERROR);free(f);}
        {const unsigned wrong[]={~0u,7u,16*j+7,0x0cf49802u,16*((j+1)%3)+6};for(unsigned i=0;i<5;i++){
            struct fake *f=fresh(0);f->j[j].bad_eop=wrong[i];stopped(f,GGV_MEMORY_ERROR);CHECK(!f->c.work.job[j].eop_complete);free(f);
        }}
        {struct fake *f=fresh(0);f->j[j].drop_eop=1;f->eop_guard_job=j;f->eop_guard=3;stopped(f,GGV_GUARD);free(f);}
        for(unsigned phase=GGV_CAPTURE;phase<=GGV_VERIFY;phase++)for(unsigned mutation=1;mutation<=6;mutation++){
            struct fake *f=fresh(0);f->mutation_job=j;f->mutation_phase=phase;f->mutation_kind=mutation;stopped(f,GGV_GUARD);CHECK(f->mutation_done);free(f);
        }
        for(unsigned fault=1;fault<=2;fault++){struct fake *f=fresh(0);f->j[j].fault_after=fault;stopped(f,GGV_FAULT);free(f);}
        {struct fake *f=fresh(0);f->j[j].bad_rptr=8192;stopped(f,GGV_MEMORY_ERROR);free(f);}
        {struct fake *f=fresh(0);f->j[j].bad_busy=1;stopped(f,GGV_FAULT);free(f);}
        {struct fake *f=fresh(0);f->j[j].drop_fence=200;stopped(f,GGV_TIMEOUT);CHECK(f->j[j].fence_reads==200&&f->j[j].fence_writes==201&&f->j[j].kept&&!f->j[j].submitted);free(f);}
        for(unsigned busy=0;busy<2;busy++){struct fake *f=fresh(0);if(busy)f->j[j].busy_delay=~0u;else f->j[j].rptr_delay=~0u;f->timeout_job=j;f->timeout_guard=3;stopped(f,GGV_GUARD);free(f);}
        printf("GPU varying job%u: native/data corruptions, all1639 silent write drops (identical previous bytes harmless), dropped256 pixels, stale/intermediate/regressing/future EOP, mutable context quarantine PASS\n",j);fflush(stdout);
    }
    for(unsigned j=1;j<3;j++)for(unsigned off=0;off<4096;off+=4){struct fake *f=fresh(0);f->between_job=j+1;f->between_mem=GGV_DATA;f->between_offset=off;stopped(f,GGV_MEMORY_ERROR);CHECK(!f->j[j].mem_writes&&!f->j[j].submitted);free(f);}
    /* Exact previous OBSERVATION, even when drift is a legal prior result. */
    for(unsigned j=1;j<3;j++)for(unsigned i=0;i<256;i++){
        struct fake *f=fresh(0);f->between_job=j+1;f->between_mem=GGV_DATA;f->between_offset=4*i;f->between_set=1;
        uint32_t old=pixel(j-1,i);f->between_value=old==reference_lower[j-1][i]?reference_upper[j-1][i]:reference_lower[j-1][i];
        CHECK(f->between_value!=old&&declared(j-1,i,f->between_value));stopped(f,GGV_MEMORY_ERROR);CHECK(!f->j[j].mem_writes&&!f->j[j].submitted);free(f);
    }
    for(unsigned job=0;job<3;job++)for(unsigned i=0;i<256;i++){
        for(unsigned choice=0;choice<(job==2?2u:8u);choice++){
            struct fake *f=fresh(0);f->produced[job][i]=rounding_choice(job,i,job==2?choice*4:choice);CHECK(declared(job,i,f->produced[job][i]));good(f);free(f);
        }
        for(unsigned c=0;c<4;c++){
            unsigned lo=(reference_lower[job][i]>>(8*c))&255u,hi=(reference_upper[job][i]>>(8*c))&255u;
            uint32_t value=(pixel(job,i)&~(255u<<(8*c)))|((lo?lo-1:hi+1)<<(8*c));
            CHECK(!declared(job,i,value));struct fake *f=fresh(0);f->produced[job][i]=value;stopped(f,GGV_MEMORY_ERROR);free(f);
            for(unsigned byte=0;byte<256;byte++){
                value=(pixel(job,i)&~(255u<<(8*c)))|(byte<<(8*c));CHECK(ggv_pixel_allowed(job,i,value)==(lo<=byte&&byte<=hi));
            }
        }
    }
    for(unsigned scenario=0;scenario<5;scenario++)for(unsigned mode=0;mode<8;mode++){
        struct fake *f=fresh(scenario);for(unsigned j=0;j<3;j++)for(unsigned i=0;i<256;i++)f->produced[j][i]=rounding_choice(j,i,(mode+i+2*j)&7);good(f);free(f);
    }
    printf("GPU varying: all declared pixel quantization choices, all256 channel bytes, exact prior legal-choice drift refusal PASS\n");fflush(stdout);
    for(unsigned mutation=1;mutation<=6;mutation++)for(unsigned phase=GGV_SEAL;phase<=GGV_FINAL;phase+=GGV_FINAL-GGV_SEAL){
        struct fake *f=fresh(0);f->mutation_job=phase==GGV_FINAL?2:0;f->mutation_phase=phase;f->mutation_kind=mutation;stopped(f,GGV_GUARD);free(f);
    }
    struct fake *f=fresh(0);f->private_ok=0;stopped(f,GGV_OWNER);CHECK(!f->reads&&!f->mem_reads&&!f->writes);free(f);
    for(unsigned bit=0;bit<32;bit++){
        if(GGQ_RBBM_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x201]=1u<<bit;stopped(f,GGV_FAULT);free(f);}
        if(GGQ_CP_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x823]=1u<<bit;stopped(f,GGV_FAULT);free(f);}
    }
    f=fresh(0);f->reg[0x807]=19;stopped(f,GGV_DIRTY_STATE);free(f);
    f=fresh(0);f->scratch[0]=19;stopped(f,GGV_MEMORY_ERROR);free(f);
    f=fresh(0);f->reg[0x23b0c]|=1u<<23;stopped(f,GGV_FAULT);free(f);
    f=fresh(0);f->j[0].rptr_delay=~0u;stopped(f,GGV_TIMEOUT);CHECK(f->j[0].shadow_reads==200000);free(f);
    f=fresh(0);struct ggv_receipt out,old;memset(&out,0x61,sizeof(out));old=out;
    CHECK(ggv_start_once(NULL,&f->ops,&f->p,&out)==GGV_ARGUMENT&&ggv_start_once(&f->c,NULL,&f->p,&out)==GGV_ARGUMENT&&ggv_start_once(&f->c,&f->ops,NULL,&out)==GGV_ARGUMENT&&ggv_start_once(&f->c,&f->ops,&f->p,NULL)==GGV_ARGUMENT);
    CHECK(ggv_start_once(&f->c,&f->ops,&f->p,(struct ggv_receipt *)&f->c)==GGV_ARGUMENT);
    CHECK(ggv_start_once((struct ggv_context *)(uintptr_t)(UINTPTR_MAX-4),&f->ops,&f->p,&out)==GGV_ARGUMENT);
    CHECK(!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    for(unsigned i=0;i<9;i++){
        f=fresh(0);switch(i){case 0:f->ops.guard=NULL;break;case 1:f->ops.seal=NULL;break;case 2:f->ops.read32=NULL;break;case 3:f->ops.write32=NULL;break;case 4:f->ops.barrier=NULL;break;case 5:f->ops.delay_us=NULL;break;case 6:f->ops.read_memory=NULL;break;case 7:f->ops.write_memory=NULL;break;case 8:f->ops.quarantine=NULL;break;}
        CHECK(run(f,&out)==GGV_ARGUMENT&&!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    }
    for(unsigned reg=0;reg<0x24000;reg++)CHECK(ggv_register_allowed(reg,true)==(reg==0x807||reg==0x1f8c3)&&ggv_register_allowed(reg,false)==(reg==0x807||reg==0x201||reg==0x823||reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889));
    for(unsigned off=0;off<32768;off++)CHECK(ggv_artifact_allowed(off)==artifact(off));
    CHECK(!ggv_artifact_allowed(~0u)&&!ggv_artifact_allowed(32768));
    for(unsigned j=0;j<3;j++){
        CHECK(ggv_expected_eop(j)==16*j+6);
        for(unsigned i=0;i<1024;i++){uint32_t value=~0u;CHECK(ggv_data_expected(j,i,&value)&&value==expected_data(j,i));}
        for(unsigned value=0;value<64;value++)CHECK(ggv_control_allowed(j,value)==(value==(j?16*(j-1)+6:0)||(value>16*j&&value<=16*j+6)));
        for(unsigned id=0;id<27;id++){
            struct ggv_blob b;CHECK(ggv_blob_get(j,id,&b));const struct varying173_native_blob *g=&varying173_blobs[j][id];
            CHECK(b.words==g->gpu_serialized_extent/4&&b.payload_words==g->words&&b.offset==(g->words?g->iova-0xfc008000u:0));
            for(unsigned k=0;k<b.words;k++){uint32_t value=0;CHECK(ggv_blob_word(j,id,k,&value)&&value==(k<g->words?g->data[k]:0));}
            uint32_t v=0x12345678;CHECK(!ggv_blob_word(j,id,b.words,&v)&&v==0x12345678);
        }
    }
    uint32_t v=0x12345678;struct ggv_blob b,savedb;memset(&b,0x61,sizeof(b));savedb=b;
    CHECK(!ggv_blob_get(3,0,&b)&&!memcmp(&b,&savedb,sizeof(b))&&!ggv_blob_get(0,27,&b)&&!ggv_blob_get(0,0,NULL)&&!ggv_blob_word(3,0,0,&v)&&!ggv_data_expected(3,0,&v)&&!ggv_data_expected(0,1024,&v)&&v==0x12345678&&!ggv_control_allowed(3,6)&&!ggv_expected_eop(3)&&!ggv_pixel_allowed(3,0,0)&&!ggv_pixel_allowed(0,256,0));
    f=fresh(0);struct ggv_command cmd,saved;memset(&cmd,0x61,sizeof(cmd));saved=cmd;
    CHECK(ggv_command_build(&f->p,&cmd)&&!memcmp(cmd.word,command,sizeof(command)));cmd=saved;
    CHECK(!ggv_command_build(NULL,&cmd)&&!memcmp(&cmd,&saved,sizeof(cmd))&&!ggv_command_build(&f->p,NULL)&&!ggv_command_build(&f->p,(struct ggv_command *)&f->p));
    for(unsigned test=0;test<6;test++){
        struct ggd_plan p=f->p;switch(test){case 0:p.bootstrap.region[GGP_RING].readonly=false;break;case 1:p.bootstrap.region[GGP_RING].privileged=true;break;case 2:p.bootstrap.region[GGP_RING].executable=true;break;case 3:p.bootstrap.region[GGP_RING].mapped-=4096;break;case 4:p.bootstrap.region[GGP_RING].iova+=4096;break;case 5:p.data.iova+=4096;break;}
        CHECK(!ggv_command_build(&p,&cmd)&&!memcmp(&cmd,&saved,sizeof(cmd)));
    }
    free(f);
    printf("PASS: GPU varying %" PRIu64 " cases/%" PRIu64 " assertions; three native jobs/one seal; all callback failures and native/data corruption boundaries,4917 silent CPU write drops,768 missing pixel controls (identical prior values harmless), exact observed previous DATA guards, all declared rounding choices and exhaustive byte bounds, independent stale/intermediate/true EOP, context mutation quarantine. Explicit hostile MODEL, NO GPU or Metal execution.\n",cases,checks);
    return 0;
}
