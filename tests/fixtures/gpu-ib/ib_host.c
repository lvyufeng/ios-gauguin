#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_ib.h"
static unsigned checks,cases;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"GPU IB line%d\n",__LINE__);abort();}}while(0)
static const uint32_t prefix[20]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0,0x70620002,0xfc010000,0,0x70e60001,0,0x70620002,0xfc010000,0};
static const uint32_t command[7]={0x70bf8003,0xfc00c000,0,8,0x70620002,0xfc010000,0};
static const uint32_t indirect[8]={0x703d8003,0xfc018000,0,0x47494231,0x703d8003,0xfc018ffc,0,0x47494232};
struct fake {
    struct ggi_context c;struct ggi_ops ops;struct ggd_plan p;
    uint32_t ring[8192],scratch[1024],data[1024],reg[0x24000];
    unsigned step,fail,quarantined,sealed,seal_calls,private_ok,nested,trace;
    unsigned reads,writes,mem_reads,mem_writes,drop_command,corrupt_phase,corrupt_mem,corrupt_offset;
    unsigned kept,submitted,fence_reads,fence_writes,drop_fence,counter_reads,wrap;
    unsigned shadow_reads,busy_reads,rptr_delay,busy_delay,bad_rptr,bad_busy,timeout_guard,fault_after;
    unsigned device_done,device_writes,drop_data,corrupt_data;
};
static bool tick(struct fake *f){CHECK(!f->quarantined);return ++f->step!=f->fail;}
static bool guard(void *cookie,enum ggi_phase phase)
{
    struct fake *f=cookie;CHECK(f->c.state==1&&phase>=GGI_SEAL&&phase<=GGI_FINAL);
    if(f->nested){f->nested=0;struct ggi_receipt r,old;memset(&r,0x61,sizeof(r));old=r;unsigned step=f->step;
        CHECK(ggi_start_once(&f->c,&f->ops,&f->p,&r)==GGI_ALREADY&&step==f->step&&!memcmp(&r,&old,sizeof(r)));}
    if(phase==GGI_WAIT&&f->timeout_guard&&f->shadow_reads>=f->timeout_guard)return false;
    return tick(f);
}
static bool seal(void *cookie,uint64_t pa)
{struct fake *f=cookie;CHECK(f->c.phase==GGI_SEAL&&!f->seal_calls++);if(!tick(f)||!f->private_ok||pa!=0xaa200000)return false;f->sealed=1;return true;}
static void quarantine(void *cookie)
{struct fake *f=cookie;CHECK(f->c.state==3&&!f->quarantined);f->quarantined=1;}
/* Independent fake device decodes real packet addresses and values. Only
 * this seam writes data; production memory-write callbacks permit ring only. */
static void device_execute(struct fake *f)
{
    CHECK(!f->device_done&&f->submitted&&f->reg[0x807]==27);f->device_done=1;
    CHECK(f->ring[20]==0x70bf8003&&f->ring[21]==0xfc00c000&&!f->ring[22]&&f->ring[23]==8&&!(f->ring[23]&(1u<<20)));
    for(unsigned n=0;n<2;n++){
        const uint32_t *p=f->ring+4096+4*n;CHECK(p[0]==0x703d8003);
        uint64_t addr=(uint64_t)p[1]|((uint64_t)p[2]<<32);CHECK(addr>=0xfc018000&&addr<=0xfc018ffc&&!(addr&3));
        if(f->drop_data!=n+1)f->data[(addr-0xfc018000)/4]=p[3];++f->device_writes;
    }
    if(f->corrupt_data){CHECK(f->corrupt_data<=1024);f->data[f->corrupt_data-1]^=1;}
}
static bool read32(void *cookie,uint32_t reg,uint32_t *out)
{
    struct fake *f=cookie;CHECK(f->sealed&&out&&ggi_register_allowed(reg,false));if(!tick(f))return false;++f->reads;*out=f->reg[reg];
    if(reg==0x23b13){*out=f->fence_reads++<f->drop_fence?3:2;if(!(*out&1)){f->submitted=1;if(!f->device_done)device_execute(f);}}
    if(reg==0x23b0c&&f->c.phase==GGI_WAIT)*out=f->bad_busy?0xffffffff:f->busy_reads++<f->busy_delay?0x80800000:0x80000000;
    if(reg==0x823&&((f->fault_after==1&&f->c.phase==GGI_WAIT)||(f->fault_after==2&&f->c.phase==GGI_VERIFY)))*out=1;
    if(reg==0x1f888||reg==0x1f889){unsigned n=f->counter_reads++;*out=!f->wrap?(reg==0x1f889?1u:0x12345678u):n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:reg==0x1f889?2u:0x20u;}
    if(f->trace&&f->c.phase>=GGI_SUBMIT&&(reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889))printf("R %05x %08x\n",reg,*out);
    return true;
}
static bool write32(void *cookie,uint32_t reg,uint32_t value)
{
    struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGI_SUBMIT&&ggi_register_allowed(reg,true));
    CHECK(f->mem_writes==15&&f->c.work.commands_checked==7&&f->c.work.ib_checked==8&&!memcmp(f->ring,prefix,sizeof(prefix))&&!memcmp(f->ring+20,command,sizeof(command))&&!memcmp(f->ring+4096,indirect,sizeof(indirect)));
    if(!tick(f))return false;++f->writes;if(reg==0x1f8c3){CHECK(value<=1);f->kept=value;}else{CHECK(value==27&&f->kept);++f->fence_writes;}
    f->reg[reg]=value;if(f->trace)printf("W %05x %08x\n",reg,value);return true;
}
static bool barrier(void *cookie)
{struct fake *f=cookie;if(!tick(f))return false;if(f->trace&&f->c.phase==GGI_SUBMIT)puts("B");if(f->trace&&f->c.phase==GGI_WAIT)puts("I");return true;}
static bool delay_us(void *cookie,unsigned us)
{struct fake *f=cookie;CHECK(us==10&&f->c.phase==GGI_SUBMIT&&f->kept);if(!tick(f))return false;if(f->trace)printf("D %u\n",us);return true;}
static bool read_memory(void *cookie,enum ggi_memory mem,uint32_t off,uint32_t *out)
{
    struct fake *f=cookie;CHECK(f->sealed&&out&&!(off&3));
    CHECK((mem==GGI_RING&&((f->c.phase==GGI_CAPTURE&&off<108)||(f->c.phase==GGI_COMMANDS&&off>=80&&off<108)||(f->c.phase==GGI_VERIFY&&off<108)))||
        (mem==GGI_SCRATCH&&off==0&&(f->c.phase==GGI_CAPTURE||f->c.phase==GGI_WAIT))||
        (mem==GGI_DATA&&off<4096&&(f->c.phase==GGI_CAPTURE||f->c.phase==GGI_VERIFY))||
        (mem==GGI_IB&&off<32&&(f->c.phase==GGI_CAPTURE||f->c.phase==GGI_COMMANDS||f->c.phase==GGI_VERIFY)));
    if(!tick(f))return false;++f->mem_reads;
    if(f->c.phase==GGI_WAIT){CHECK(f->submitted&&!f->kept&&f->device_done&&f->reg[0x807]==27);
        if(f->shadow_reads++>=f->rptr_delay)f->scratch[0]=27;if(f->bad_rptr)f->scratch[0]=f->bad_rptr;
        if(f->trace)printf("P %08x\n",f->scratch[0]);}
    *out=mem==GGI_RING?f->ring[off/4]:mem==GGI_IB?f->ring[4096+off/4]:mem==GGI_SCRATCH?f->scratch[off/4]:f->data[off/4];
    if(f->corrupt_phase==f->c.phase&&f->corrupt_mem==(unsigned)mem&&f->corrupt_offset==off)*out^=1;
    return true;
}
static bool write_memory(void *cookie,enum ggi_memory mem,uint32_t off,uint32_t value)
{
    struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGI_COMMANDS&&f->mem_writes<15);
    bool ib=f->mem_writes<8;unsigned n=ib?f->mem_writes:f->mem_writes-8;
    CHECK(mem==(ib?GGI_IB:GGI_RING)&&off==(ib?4*n:80+4*n)&&value==(ib?indirect[n]:command[n]));
    if(!tick(f))return false;++f->mem_writes;if(f->mem_writes!=f->drop_command)f->ring[(ib?4096:0)+off/4]=value;
    if(f->trace)printf(ib?"J %u %08x\n":"C %u %08x\n",off/4,value);return true;
}
static struct fake *fresh(unsigned scenario)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan m;struct ggp_plan p;
    CHECK(ggm_plan_build(0xaa200000,&m)&&ggp_plan_build(&m,&p)&&ggd_plan_build(&p,&f->p));
    f->ops=(struct ggi_ops){f,guard,seal,read32,write32,barrier,delay_us,read_memory,write_memory,quarantine};f->private_ok=1;
    memset(f->ring,0xaa,sizeof(f->ring));memcpy(f->ring,prefix,sizeof(prefix));
    for(unsigned i=0;i<1024;i++)f->scratch[i]=0xd5432100u+i;f->scratch[0]=20;
    f->reg[0x807]=20;f->reg[0x23b0c]=0x71000000;
    f->drop_fence=scenario==1?1:scenario==2?100:scenario==3?199:0;f->wrap=scenario==4;
    f->rptr_delay=scenario==1?2:0;f->busy_delay=scenario==1?2:0;return f;
}
static enum ggi_result run(struct fake *f,struct ggi_receipt *out)
{return ggi_start_once(&f->c,&f->ops,&f->p,out);}
static void once(struct fake *f)
{struct ggi_receipt r,old;memset(&r,0x61,sizeof(r));old=r;unsigned step=f->step;CHECK(run(f,&r)==GGI_ALREADY&&step==f->step&&!memcmp(&r,&old,sizeof(r)));}
static void untouched(struct fake *f)
{CHECK(!memcmp(f->ring,prefix,sizeof(prefix)));for(unsigned i=27;i<8192;i++)if(i<4096||i>=4104)CHECK(f->ring[i]==0xaaaaaaaa);for(unsigned i=1;i<1024;i++)CHECK(f->scratch[i]==0xd5432100u+i);}
static void good(struct fake *f)
{
    struct ggi_receipt r;CHECK(run(f,&r)==GGI_OK&&f->c.state==2&&f->c.phase==GGI_DONE&&!f->quarantined);++cases;
    CHECK(r.sealed&&r.complete&&r.requests_retained&&r.prefix_checked==20&&r.clean_checked==7&&r.commands_written==7&&r.commands_checked==7&&r.ib_clean_checked==8&&r.ib_written==8&&r.ib_checked==8&&r.ib_after_checked==8);
    CHECK(r.initial_wptr==20&&r.initial_shadow==20&&r.rptr==27&&!(r.busy&(1u<<23))&&r.writes==3+f->drop_fence&&r.reads==f->reads);
    CHECK(r.data_before_checked==1024&&r.data_after_checked==1024&&r.edge_checked==2&&r.unchanged_checked==1022&&r.ring_after_checked==27);
    CHECK(f->device_writes==2&&r.fence_checks==f->drop_fence+1&&r.fence_slow==(f->drop_fence>=100)&&r.counter_before_valid&&r.counter_after_valid==r.fence_slow);
    CHECK(r.counter_before==(f->wrap?UINT64_C(0x200000010):UINT64_C(0x112345678)));
    CHECK(r.submit_attempted&&r.keepalive_set_attempted&&r.keepalive_clear_attempted&&!f->kept);
    for(unsigned i=0;i<1024;i++)CHECK(f->data[i]==(i==0?0x47494231u:i==1023?0x47494232u:0));
    untouched(f);once(f);
}
static void stopped(struct fake *f,enum ggi_result result)
{struct ggi_receipt r,old;memset(&r,0x61,sizeof(r));old=r;CHECK(run(f,&r)==result&&f->c.state==3&&f->quarantined&&!memcmp(&r,&old,sizeof(r)));++cases;untouched(f);once(f);}
int main(int argc,char **argv)
{
    if(argc==2){unsigned s=(unsigned)strtoul(argv[1],NULL,10);CHECK(s<5);struct fake *f=fresh(s);f->trace=1;good(f);free(f);return 0;}CHECK(argc==1);
    for(unsigned s=0;s<5;s++){
        struct fake *f=fresh(s);f->nested=1;good(f);unsigned steps=f->step;free(f);
        if(s<2)for(unsigned i=1;i<=steps;i++){
            f=fresh(s);f->fail=i;struct ggi_receipt r,old;memset(&r,0x61,sizeof(r));old=r;
            CHECK(run(f,&r)!=GGI_OK&&f->c.state==3&&f->quarantined&&f->step==i&&!memcmp(&r,&old,sizeof(r)));++cases;untouched(f);once(f);free(f);
        }
        printf("GPU IB scenario%u: native27/2edge/1022unchanged and%u boundaries PASS%s\n",s,steps,s<2?" (all injected)":"");
    }
    for(unsigned phase=GGI_CAPTURE;phase<=GGI_VERIFY;phase++){
        if(phase!=GGI_CAPTURE&&phase!=GGI_COMMANDS&&phase!=GGI_VERIFY)continue;
        unsigned start=phase==GGI_COMMANDS?20:0;
        for(unsigned i=start;i<27;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGI_RING;f->corrupt_offset=4*i;stopped(f,GGI_MEMORY_ERROR);free(f);}
        for(unsigned i=0;i<8;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGI_IB;f->corrupt_offset=4*i;stopped(f,GGI_MEMORY_ERROR);free(f);}
        if(phase!=GGI_COMMANDS)for(unsigned i=0;i<1024;i++){struct fake *f=fresh(0);f->corrupt_phase=phase;f->corrupt_mem=GGI_DATA;f->corrupt_offset=4*i;stopped(f,GGI_MEMORY_ERROR);free(f);}
    }
    for(unsigned i=1;i<=15;i++){struct fake *f=fresh(0);f->drop_command=i;stopped(f,GGI_MEMORY_ERROR);CHECK(!f->writes&&!f->device_writes);free(f);}
    for(unsigned i=1;i<=1024;i++){struct fake *f=fresh(0);f->corrupt_data=i;stopped(f,GGI_MEMORY_ERROR);CHECK(f->device_writes==2);free(f);}
    for(unsigned i=1;i<=2;i++){struct fake *f=fresh(0);f->drop_data=i;stopped(f,GGI_MEMORY_ERROR);free(f);}
    struct fake *f=fresh(0);f->private_ok=0;stopped(f,GGI_OWNER);CHECK(!f->reads&&!f->mem_reads&&!f->writes);free(f);
    f=fresh(0);f->p.bootstrap.owner_pa+=0x100000;stopped(f,GGI_OWNER);free(f);
    for(unsigned bit=0;bit<32;bit++){
        if(GGQ_RBBM_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x201]=1u<<bit;stopped(f,GGI_FAULT);free(f);}
        if(GGQ_CP_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x823]=1u<<bit;stopped(f,GGI_FAULT);free(f);}
    }
    for(unsigned i=1;i<=2;i++){f=fresh(0);f->fault_after=i;stopped(f,GGI_FAULT);free(f);}
    f=fresh(0);f->reg[0x807]=19;stopped(f,GGI_DIRTY_STATE);free(f);
    f=fresh(0);f->scratch[0]=19;stopped(f,GGI_MEMORY_ERROR);free(f);
    f=fresh(0);f->reg[0x23b0c]|=1u<<23;stopped(f,GGI_FAULT);free(f);
    f=fresh(0);f->bad_rptr=8192;stopped(f,GGI_MEMORY_ERROR);free(f);
    f=fresh(0);f->bad_busy=1;stopped(f,GGI_FAULT);free(f);
    f=fresh(0);f->drop_fence=200;stopped(f,GGI_TIMEOUT);CHECK(f->fence_reads==200&&f->fence_writes==201&&f->kept&&!f->submitted);free(f);
    f=fresh(0);f->rptr_delay=~0u;stopped(f,GGI_TIMEOUT);CHECK(f->shadow_reads==200000);free(f);
    for(unsigned busy=0;busy<2;busy++){f=fresh(0);if(busy)f->busy_delay=~0u;else f->rptr_delay=~0u;f->timeout_guard=3;stopped(f,GGI_GUARD);free(f);}
    f=fresh(0);struct ggi_receipt out,old;memset(&out,0x61,sizeof(out));old=out;
    CHECK(ggi_start_once(NULL,&f->ops,&f->p,&out)==GGI_ARGUMENT);
    CHECK(ggi_start_once(&f->c,NULL,&f->p,&out)==GGI_ARGUMENT);
    CHECK(ggi_start_once(&f->c,&f->ops,NULL,&out)==GGI_ARGUMENT);
    CHECK(ggi_start_once(&f->c,&f->ops,&f->p,NULL)==GGI_ARGUMENT);
    CHECK(ggi_start_once(&f->c,&f->ops,&f->p,(struct ggi_receipt *)&f->c)==GGI_ARGUMENT);
    CHECK(ggi_start_once((struct ggi_context *)(uintptr_t)(UINTPTR_MAX-4),&f->ops,&f->p,&out)==GGI_ARGUMENT);
    CHECK(!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    for(unsigned i=0;i<9;i++){
        f=fresh(0);switch(i){case 0:f->ops.guard=NULL;break;case 1:f->ops.seal=NULL;break;case 2:f->ops.read32=NULL;break;case 3:f->ops.write32=NULL;break;case 4:f->ops.barrier=NULL;break;case 5:f->ops.delay_us=NULL;break;case 6:f->ops.read_memory=NULL;break;case 7:f->ops.write_memory=NULL;break;case 8:f->ops.quarantine=NULL;break;}
        CHECK(run(f,&out)==GGI_ARGUMENT&&!f->step&&!f->c.state&&!memcmp(&out,&old,sizeof(out)));free(f);
    }
    for(unsigned r=0;r<0x24000;r++)CHECK(ggi_register_allowed(r,true)==(r==0x807||r==0x1f8c3)&&ggi_register_allowed(r,false)==(r==0x807||r==0x201||r==0x823||r==0x23b13||r==0x23b0c||r==0x1f888||r==0x1f889));
    CHECK(!ggi_register_allowed(~0u,true)&&!ggi_register_allowed(~0u,false));
    printf("PASS: GPU IB %u cases/%u assertions; exact native7word ring/8word IB, all pre/post data/ring corruption and callback failures, device-only2edge writes/1022preserved, output/once/quarantine/timeout/fault checks; pure model, no live GPU or rendering proof\n",cases,checks);
}
