#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_compute.h"
static unsigned checks,cases;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"GPU compute line%d\n",__LINE__);abort();}}while(0)
static const uint32_t prefix[20]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0,0x70620002,0xfc010000,0,0x70e60001,0,0x70620002,0xfc010000,0};
#include "native_words.h"
struct fake {
    struct ggk_context c;struct ggk_ops ops;struct ggd_plan p;
    uint32_t ring[8192],scratch[1024],data[1024],reg[0x24000];
    unsigned step,fail,quarantined,sealed,seal_calls,private_ok,nested,trace;
    unsigned reads,writes,mem_reads,mem_writes,drop_command,corrupt_phase,corrupt_mem,corrupt_offset;
    unsigned kept,submitted,fence_reads,fence_writes,drop_fence,counter_reads,wrap;
    unsigned shadow_reads,busy_reads,rptr_delay,busy_delay,bad_rptr,bad_busy,timeout_guard,fault_after;
    unsigned nc_since_guard,max_nc_seen,drop_shader;
    unsigned device_done,device_writes,drop_data,corrupt_data,eop_done,eop_reads,eop_delay,drop_eop,bad_eop,eop_guard;
};
static bool tick(struct fake *f){CHECK(!f->quarantined);return ++f->step!=f->fail;}
static bool guard(void *cookie,enum ggk_phase phase)
{
    struct fake *f=cookie;CHECK(f->c.state==1&&phase>=GGK_SEAL&&phase<=GGK_FINAL);
    CHECK(f->nc_since_guard<=64);if(f->max_nc_seen<f->nc_since_guard)f->max_nc_seen=f->nc_since_guard;
    f->nc_since_guard=0;
    if(f->nested){f->nested=0;struct ggk_receipt r,old;memset(&r,0x61,sizeof(r));old=r;unsigned step=f->step;
        CHECK(ggk_start_once(&f->c,&f->ops,&f->p,&r)==GGK_ALREADY&&step==f->step&&!memcmp(&r,&old,sizeof(r)));}
    if(phase==GGK_WAIT&&f->timeout_guard&&f->shadow_reads>=f->timeout_guard)return false;
    if(phase==GGK_WAIT&&f->eop_guard&&f->eop_reads>=f->eop_guard)return false;
    return tick(f);
}
static bool seal(void *cookie,uint64_t pa)
{struct fake *f=cookie;CHECK(f->c.phase==GGK_SEAL&&!f->seal_calls++);if(!tick(f)||!f->private_ok||pa!=0xaa200000)return false;f->sealed=1;return true;}
static void quarantine(void *cookie)
{struct fake *f=cookie;CHECK(f->c.state==3&&!f->quarantined);f->quarantined=1;}
/* Explicit adversarial GPU MODEL, not an IR3 emulator/hardware proof.
 * Primary native91/32/16 bytes are checked before this modeled SP result.
 * Only these device seams can write DATA; CPU callbacks are ring-only. */
static void device_execute(struct fake *f)
{
    CHECK(!f->device_done&&f->submitted&&f->reg[0x807]==27);f->device_done=1;
    CHECK(!memcmp(f->ring+20,command,sizeof(command))&&!(f->ring[23]&(1u<<20)));
    CHECK(!memcmp(f->ring+4096,indirect,sizeof(indirect)));
    CHECK(!memcmp(f->ring+5120,program,sizeof(program))&&!memcmp(f->ring+6144,ibo,sizeof(ibo)));
    CHECK(program[0]==0&&program[1]==0x200cc001&&program[4]==0x01674000&&program[5]==0xc0260000);
    CHECK(ibo[1]==32&&ibo[4]==0xfc018000&&!ibo[5]);
    for(unsigned id=0;id<32;id++){
        if(!f->drop_shader&&f->drop_data!=id+1)f->data[id]=id;
        ++f->device_writes;
    }
}
/* Adversarially allow an idle/RPTR27 report before the modeled event so the
 * engine must observe DATA0 independently and still require shader results.
 * Real native IB has RB_DONE/WAIT/CACHE_FLUSH/WAIT before WHERE. */
static void device_eop(struct fake *f)
{
    CHECK(f->device_done&&!f->eop_done&&f->reg[0x807]==27);
    CHECK(indirect[69]==0x70460004&&indirect[70]==0x16&&indirect[71]==0xfc018000&&indirect[73]==1);
    CHECK(indirect[81]==0x70460004&&indirect[82]==4&&indirect[83]==0xfc018000&&indirect[85]==2);
    f->data[0]=1;f->data[0]=f->bad_eop?f->bad_eop:2;f->device_writes+=2;f->eop_done=1;
    if(f->corrupt_data){CHECK(f->corrupt_data<=1024);f->data[f->corrupt_data-1]^=1;}
}
static bool read32(void *cookie,uint32_t reg,uint32_t *out)
{
    struct fake *f=cookie;CHECK(f->sealed&&out&&ggk_register_allowed(reg,false));if(!tick(f))return false;++f->reads;*out=f->reg[reg];
    if(reg==0x23b13){*out=f->fence_reads++<f->drop_fence?3:2;if(!(*out&1)){f->submitted=1;if(!f->device_done)device_execute(f);}}
    if(reg==0x23b0c&&f->c.phase==GGK_WAIT)*out=f->bad_busy?0xffffffff:f->busy_reads++<f->busy_delay?0x80800000:0x80000000;
    if(reg==0x823&&((f->fault_after==1&&f->c.phase==GGK_WAIT)||(f->fault_after==2&&f->c.phase==GGK_VERIFY)))*out=1;
    if(reg==0x1f888||reg==0x1f889){unsigned n=f->counter_reads++;*out=!f->wrap?(reg==0x1f889?1u:0x12345678u):n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:reg==0x1f889?2u:0x20u;}
    if(f->trace&&f->c.phase>=GGK_SUBMIT&&(reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889))printf("R %05x %08x\n",reg,*out);
    return true;
}
static bool write32(void *cookie,uint32_t reg,uint32_t value)
{
    struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGK_SUBMIT&&ggk_register_allowed(reg,true));
    CHECK(f->mem_writes==146&&f->c.work.commands_checked==7&&f->c.work.ib_checked==91&&f->c.work.program_checked==32&&f->c.work.ibo_checked==16);
    CHECK(!memcmp(f->ring,prefix,sizeof(prefix))&&!memcmp(f->ring+20,command,sizeof(command))&&!memcmp(f->ring+4096,indirect,sizeof(indirect)));
    CHECK(!memcmp(f->ring+5120,program,sizeof(program))&&!memcmp(f->ring+6144,ibo,sizeof(ibo)));
    if(!tick(f))return false;++f->writes;if(reg==0x1f8c3){CHECK(value<=1);f->kept=value;}else{CHECK(value==27&&f->kept);++f->fence_writes;}
    f->reg[reg]=value;if(f->trace)printf("W %05x %08x\n",reg,value);return true;
}
static bool barrier(void *cookie)
{struct fake *f=cookie;if(!tick(f))return false;if(f->trace&&f->c.phase==GGK_SUBMIT)puts("B");if(f->trace&&f->c.phase==GGK_WAIT)puts("I");return true;}
static bool delay_us(void *cookie,unsigned us)
{struct fake *f=cookie;CHECK(us==10&&f->c.phase==GGK_SUBMIT&&f->kept);if(!tick(f))return false;if(f->trace)printf("D %u\n",us);return true;}
static bool read_memory(void *cookie,enum ggk_memory mem,uint32_t off,uint32_t *out)
{
    struct fake *f=cookie;CHECK(f->sealed&&out&&!(off&3));
    CHECK((mem==GGK_RING&&((f->c.phase==GGK_CAPTURE&&off<108)||(f->c.phase==GGK_COMMANDS&&off>=80&&off<108)||(f->c.phase==GGK_VERIFY&&off<108)))||
        (mem==GGK_SCRATCH&&off==0&&(f->c.phase==GGK_CAPTURE||f->c.phase==GGK_WAIT))||
        (mem==GGK_DATA&&off<4096&&(f->c.phase==GGK_CAPTURE||f->c.phase==GGK_VERIFY||(f->c.phase==GGK_WAIT&&off==0)))||
        ((mem==GGK_IB||mem==GGK_PROGRAM||mem==GGK_IBO)&&(f->c.phase==GGK_CAPTURE||f->c.phase==GGK_COMMANDS||f->c.phase==GGK_VERIFY)&&
          off<4*(mem==GGK_IB?91u:mem==GGK_PROGRAM?32u:16u)));
    if(!tick(f))return false;++f->mem_reads;CHECK(++f->nc_since_guard<=64);
    if(f->c.phase==GGK_WAIT&&mem==GGK_SCRATCH){CHECK(f->submitted&&!f->kept&&f->device_done&&f->reg[0x807]==27);
        if(f->shadow_reads++>=f->rptr_delay)f->scratch[0]=27;if(f->bad_rptr)f->scratch[0]=f->bad_rptr;
        if(f->trace)printf("P %08x\n",f->scratch[0]);}
    if(f->c.phase==GGK_WAIT&&mem==GGK_DATA){
        CHECK(f->device_done&&f->scratch[0]==27&&!f->kept&&off==0);
        if(f->eop_reads++>=f->eop_delay&&!f->drop_eop&&!f->eop_done)device_eop(f);
    }
    *out=mem==GGK_RING?f->ring[off/4]:mem==GGK_IB?f->ring[4096+off/4]:mem==GGK_PROGRAM?f->ring[5120+off/4]:mem==GGK_IBO?f->ring[6144+off/4]:mem==GGK_SCRATCH?f->scratch[off/4]:f->data[off/4];
    if(f->corrupt_phase==f->c.phase&&f->corrupt_mem==(unsigned)mem&&f->corrupt_offset==off)*out^=1;
    if(f->trace&&f->c.phase==GGK_WAIT&&mem==GGK_DATA)printf("E %08x\n",*out);
    return true;
}
static bool write_memory(void *cookie,enum ggk_memory mem,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGK_COMMANDS&&f->mem_writes<146);
    unsigned total=f->mem_writes,n=total<32?total:total<48?total-32:total<139?total-48:total-139;
    enum ggk_memory expected=total<32?GGK_PROGRAM:total<48?GGK_IBO:total<139?GGK_IB:GGK_RING;
    const uint32_t *values=expected==GGK_PROGRAM?program:expected==GGK_IBO?ibo:expected==GGK_IB?indirect:command;
    unsigned base=expected==GGK_PROGRAM?5120:expected==GGK_IBO?6144:expected==GGK_IB?4096:0;
    CHECK(mem==expected&&off==(expected==GGK_RING?80+4*n:4*n)&&value==values[n]);
    if(!tick(f))return false;++f->mem_writes;CHECK(++f->nc_since_guard<=64);
    if(f->mem_writes!=f->drop_command)f->ring[base+off/4]=value;
    if(f->trace)printf("N %u %u %08x\n",mem,off/4,value);return true;
}

static struct fake *fresh(unsigned scenario)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan m;struct ggp_plan p;
    CHECK(ggm_plan_build(0xaa200000,&m)&&ggp_plan_build(&m,&p)&&ggd_plan_build(&p,&f->p));
    f->ops=(struct ggk_ops){f,guard,seal,read32,write32,barrier,delay_us,read_memory,write_memory,quarantine};f->private_ok=1;
    memset(f->ring,0xaa,sizeof(f->ring));memcpy(f->ring,prefix,sizeof(prefix));
    for(unsigned i=0;i<1024;i++)f->scratch[i]=0xd5432100u+i;f->scratch[0]=20;
    f->reg[0x807]=20;f->reg[0x23b0c]=0x71000000;
    f->drop_fence=scenario==1?1:scenario==2?100:scenario==3?199:0;f->wrap=scenario==4;
    f->rptr_delay=scenario==1?2:0;f->busy_delay=scenario==1?2:0;f->eop_delay=scenario==1?2:0;return f;
}
static enum ggk_result run(struct fake *f,struct ggk_receipt *out)
{return ggk_start_once(&f->c,&f->ops,&f->p,out);}
static void once(struct fake *f)
{struct ggk_receipt r,old;memset(&r,0x61,sizeof(r));old=r;unsigned step=f->step;CHECK(run(f,&r)==GGK_ALREADY&&step==f->step&&!memcmp(&r,&old,sizeof(r)));}
static void untouched(struct fake *f)
{
    CHECK(!memcmp(f->ring,prefix,sizeof(prefix)));
    for(unsigned i=27;i<8192;i++)if(!(i>=4096&&i<4187)&&!(i>=5120&&i<5152)&&!(i>=6144&&i<6160))CHECK(f->ring[i]==0xaaaaaaaa);
    for(unsigned i=1;i<1024;i++)CHECK(f->scratch[i]==0xd5432100u+i);
}
static void good(struct fake *f)
{
    struct ggk_receipt r;CHECK(run(f,&r)==GGK_OK&&f->c.state==2&&f->c.phase==GGK_DONE&&!f->quarantined);++cases;
    CHECK(r.sealed&&r.complete&&r.requests_retained&&r.prefix_checked==20&&r.clean_checked==7&&r.commands_written==7&&r.commands_checked==7&&r.ib_clean_checked==91&&r.ib_written==91&&r.ib_checked==91&&r.ib_after_checked==91);
    CHECK(r.initial_wptr==20&&r.initial_shadow==20&&r.rptr==27&&!(r.busy&(1u<<23))&&r.writes==3+f->drop_fence&&r.reads==f->reads);
    CHECK(r.data_before_checked==1024&&r.data_after_checked==1024&&r.invocations_checked==31&&r.unchanged_checked==992&&r.eop_checked==1&&r.eop_complete==1&&r.eop_value==2&&r.eop_polls==f->eop_delay+1&&r.ring_after_checked==27);
    CHECK(r.program_clean_checked==32&&r.program_written==32&&r.program_checked==32&&r.program_after_checked==32);
    CHECK(r.ibo_clean_checked==16&&r.ibo_written==16&&r.ibo_checked==16&&r.ibo_after_checked==16&&r.max_nc_batch_words==64&&f->max_nc_seen<=64);
    CHECK(f->device_writes==34&&r.fence_checks==f->drop_fence+1&&r.fence_slow==(f->drop_fence>=100)&&r.counter_before_valid&&r.counter_after_valid==r.fence_slow);
    CHECK(r.counter_before==(f->wrap?UINT64_C(0x200000010):UINT64_C(0x112345678)));
    CHECK(r.submit_attempted&&r.keepalive_set_attempted&&r.keepalive_clear_attempted&&!f->kept);
    for(unsigned i=0;i<1024;i++)CHECK(f->data[i]==(i==0?2u:i<32?i:0));
    untouched(f);once(f);
}
static void stopped(struct fake *f,enum ggk_result result)
{struct ggk_receipt r,old;memset(&r,0x61,sizeof(r));old=r;CHECK(run(f,&r)==result&&f->c.state==3&&f->quarantined&&!memcmp(&r,&old,sizeof(r)));++cases;untouched(f);once(f);}
int main(int argc,char **argv)
{
    if(argc==2){unsigned s=(unsigned)strtoul(argv[1],NULL,10);CHECK(s<5);struct fake *f=fresh(s);f->trace=1;good(f);free(f);return 0;}CHECK(argc==1);
    for(unsigned s=0;s<5;s++){
        struct fake *f=fresh(s);f->nested=1;good(f);unsigned steps=f->step;free(f);
        if(s<2)for(unsigned i=1;i<=steps;i++){
            f=fresh(s);f->fail=i;struct ggk_receipt r,old;memset(&r,0x61,sizeof(r));old=r;
            CHECK(run(f,&r)!=GGK_OK&&f->c.state==3&&f->quarantined&&f->step==i&&!memcmp(&r,&old,sizeof(r)));++cases;untouched(f);once(f);free(f);
        }
        printf("GPU compute scenario%u: native27/shader31/EOP2/992unchanged and%u boundaries PASS%s\n",s,steps,s<2?" (all injected)":"");
    }
    for(unsigned phase=GGK_CAPTURE;phase<=GGK_VERIFY;phase++){
        if(phase!=GGK_CAPTURE&&phase!=GGK_COMMANDS&&phase!=GGK_VERIFY)continue;
        unsigned start=phase==GGK_COMMANDS?20:0;
        for(unsigned i=start;i<27;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGK_RING;f->corrupt_offset=4*i;stopped(f,GGK_MEMORY_ERROR);free(f);}
        for(unsigned i=0;i<91;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGK_IB;f->corrupt_offset=4*i;stopped(f,GGK_MEMORY_ERROR);free(f);}
        for(unsigned mem=GGK_PROGRAM;mem<=GGK_IBO;mem++)for(unsigned i=0;i<(mem==GGK_PROGRAM?32u:16u);i++){
            struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=mem;f->corrupt_offset=4*i;stopped(f,GGK_MEMORY_ERROR);free(f);
        }
        if(phase!=GGK_COMMANDS)for(unsigned i=0;i<1024;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGK_DATA;f->corrupt_offset=4*i;stopped(f,GGK_MEMORY_ERROR);free(f);}
    }
    for(unsigned i=1;i<=146;i++){struct fake *f=fresh(0);f->drop_command=i;stopped(f,GGK_MEMORY_ERROR);CHECK(!f->writes&&!f->device_writes);free(f);}
    for(unsigned i=1;i<=1024;i++){struct fake *f=fresh(0);f->corrupt_data=i;stopped(f,GGK_MEMORY_ERROR);CHECK(f->device_writes==34);free(f);}
    for(unsigned i=2;i<=32;i++){struct fake *f=fresh(0);f->drop_data=i;stopped(f,GGK_MEMORY_ERROR);free(f);}
    for(unsigned delay=1;delay<=1023;delay=delay==1?2:delay==2?1023:1024){struct fake *f=fresh(0);f->eop_delay=delay;good(f);free(f);}
    {struct fake *f=fresh(0);f->drop_eop=1;stopped(f,GGK_TIMEOUT);CHECK(f->eop_reads==1024&&f->scratch[0]==27&&!f->kept&&f->device_writes==32);free(f);}
    {struct fake *f=fresh(0);f->bad_eop=1;stopped(f,GGK_MEMORY_ERROR);CHECK(f->eop_reads==1&&f->scratch[0]==27);free(f);}
    {struct fake *f=fresh(0);f->drop_eop=1;f->eop_guard=3;stopped(f,GGK_GUARD);free(f);}
    {struct fake *f=fresh(0);f->corrupt_phase=GGK_WAIT;f->corrupt_mem=GGK_DATA;f->corrupt_offset=0;stopped(f,GGK_MEMORY_ERROR);free(f);}
    {struct fake *f=fresh(0);f->drop_shader=1;stopped(f,GGK_MEMORY_ERROR);CHECK(f->eop_done&&f->data[0]==2&&f->scratch[0]==27);free(f);}
    struct fake *f=fresh(0);f->private_ok=0;stopped(f,GGK_OWNER);CHECK(!f->reads&&!f->mem_reads&&!f->writes);free(f);
    f=fresh(0);f->p.bootstrap.owner_pa+=0x100000;stopped(f,GGK_OWNER);free(f);
    for(unsigned bit=0;bit<32;bit++){
        if(GGQ_RBBM_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x201]=1u<<bit;stopped(f,GGK_FAULT);free(f);}
        if(GGQ_CP_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x823]=1u<<bit;stopped(f,GGK_FAULT);free(f);}
    }
    for(unsigned i=1;i<=2;i++){f=fresh(0);f->fault_after=i;stopped(f,GGK_FAULT);free(f);}
    f=fresh(0);f->reg[0x807]=19;stopped(f,GGK_DIRTY_STATE);free(f);
    f=fresh(0);f->scratch[0]=19;stopped(f,GGK_MEMORY_ERROR);free(f);
    f=fresh(0);f->reg[0x23b0c]|=1u<<23;stopped(f,GGK_FAULT);free(f);
    f=fresh(0);f->bad_rptr=8192;stopped(f,GGK_MEMORY_ERROR);free(f);
    f=fresh(0);f->bad_busy=1;stopped(f,GGK_FAULT);free(f);
    f=fresh(0);f->drop_fence=200;stopped(f,GGK_TIMEOUT);CHECK(f->fence_reads==200&&f->fence_writes==201&&f->kept&&!f->submitted);free(f);
    f=fresh(0);f->rptr_delay=~0u;stopped(f,GGK_TIMEOUT);CHECK(f->shadow_reads==200000);free(f);
    for(unsigned busy=0;busy<2;busy++){f=fresh(0);if(busy)f->busy_delay=~0u;else f->rptr_delay=~0u;f->timeout_guard=3;stopped(f,GGK_GUARD);free(f);}
    f=fresh(0);struct ggk_receipt out,old;memset(&out,0x61,sizeof(out));old=out;
    CHECK(ggk_start_once(NULL,&f->ops,&f->p,&out)==GGK_ARGUMENT);
    CHECK(ggk_start_once(&f->c,NULL,&f->p,&out)==GGK_ARGUMENT);
    CHECK(ggk_start_once(&f->c,&f->ops,NULL,&out)==GGK_ARGUMENT);
    CHECK(ggk_start_once(&f->c,&f->ops,&f->p,NULL)==GGK_ARGUMENT);
    CHECK(ggk_start_once(&f->c,&f->ops,&f->p,(struct ggk_receipt *)&f->c)==GGK_ARGUMENT);
    CHECK(ggk_start_once((struct ggk_context *)(uintptr_t)(UINTPTR_MAX-4),&f->ops,&f->p,&out)==GGK_ARGUMENT);
    CHECK(!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    for(unsigned i=0;i<9;i++){
        f=fresh(0);switch(i){case 0:f->ops.guard=NULL;break;case 1:f->ops.seal=NULL;break;case 2:f->ops.read32=NULL;break;case 3:f->ops.write32=NULL;break;case 4:f->ops.barrier=NULL;break;case 5:f->ops.delay_us=NULL;break;case 6:f->ops.read_memory=NULL;break;case 7:f->ops.write_memory=NULL;break;case 8:f->ops.quarantine=NULL;break;}
        CHECK(run(f,&out)==GGK_ARGUMENT&&!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    }
    for(unsigned r=0;r<0x24000;r++)CHECK(ggk_register_allowed(r,true)==(r==0x807||r==0x1f8c3)&&ggk_register_allowed(r,false)==(r==0x807||r==0x201||r==0x823||r==0x23b13||r==0x23b0c||r==0x1f888||r==0x1f889));
    CHECK(!ggk_register_allowed(~0u,true)&&!ggk_register_allowed(~0u,false));
    printf("PASS: GPU compute %u cases/%u assertions; exact native7word ring/91word IB/32word program/16word IBO/noIRQ EOP, all pre/post data/ring corruption and callback failures, device-only31shader+EOP results/992preserved, bounded64word NC, output/once/quarantine/timeout/fault checks; pure model, no live GPU or rendering proof\n",cases,checks);
}
