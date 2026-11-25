#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_unsecure.h"
static unsigned checks,cases;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"GPU unsecure line%d\n",__LINE__);abort();}}while(0)
static const uint32_t prefix[15]={0x70c8000b,0x16f,3,0x20000000,0,0,0,2,0xfc014000,0,0,0,0x70620002,0xfc010000,0};
static const uint32_t words[5]={0x70e60001,0,0x70620002,0xfc010000,0};
struct fake {
 struct ggu_context c;struct ggu_ops ops;struct ggp_plan p;
 uint32_t ring[8192],scratch[1024],reg[0x24000];
 unsigned step,fail,quarantined,seal_calls,sealed,private_ok,nested,trace;
 unsigned writes,reads,mem_writes,mem_reads,drop_write,corrupt_read;
 unsigned kept,submitted,fence_reads,fence_writes,drop_fence,delays,counter_reads,wrap;
 unsigned shadow_reads,busy_reads,rptr_delay,busy_delay,bad_rptr,bad_busy,fault_after,timeout_guard;
};
static bool tick(struct fake *f){CHECK(!f->quarantined);return ++f->step!=f->fail;}
static bool guard(void *cookie,enum ggu_phase phase)
{
 struct fake *f=cookie;CHECK(phase>=GGU_SEAL&&phase<=GGU_FINAL&&f->c.state==1);
 if(f->nested){f->nested=0;struct ggu_receipt out,old;memset(&out,0x5a,sizeof(out));old=out;unsigned step=f->step;
  CHECK(ggu_start_once(&f->c,&f->ops,&f->p,&out)==GGU_ALREADY&&f->step==step&&!memcmp(&out,&old,sizeof(out)));}
 if(phase==GGU_WAIT&&f->timeout_guard&&f->shadow_reads>=f->timeout_guard)return false;
 return tick(f);
}
static bool seal(void *cookie,uint64_t pa)
{
 struct fake *f=cookie;CHECK(f->c.phase==GGU_SEAL&&!f->seal_calls++);if(!tick(f))return false;
 if(!f->private_ok||pa!=0xaa200000)return false;f->sealed=1;return true;
}
static void quarantine(void *cookie)
{struct fake *f=cookie;CHECK(f->c.state==3&&!f->quarantined);f->quarantined=1;}
static bool read32(void *cookie,uint32_t reg,uint32_t *out)
{
 struct fake *f=cookie;CHECK(f->sealed&&ggu_register_allowed(reg,false)&&out);if(!tick(f))return false;++f->reads;*out=f->reg[reg];
 if(reg==0x23b13){*out=f->fence_reads++<f->drop_fence?3:2;if(!(*out&1))f->submitted=1;}
 if(reg==0x23b0c&&f->c.phase==GGU_WAIT)*out=f->bad_busy?0xffffffff:f->busy_reads++<f->busy_delay?0x80800000:0x80000000;
 if(reg==0x823&&f->fault_after&&f->c.phase==GGU_WAIT)*out=1;
 if(reg==0x1f888||reg==0x1f889){unsigned n=f->counter_reads++;
  *out=!f->wrap?(reg==0x1f889?1u:0x12345678u):n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:reg==0x1f889?2u:0x20u;}
 if(f->trace&&f->c.phase>=GGU_SUBMIT&&(reg==0x23b13||reg==0x23b0c||reg==0x1f888||reg==0x1f889))printf("R %05x %08x\n",reg,*out);
 return true;
}
static bool write32(void *cookie,uint32_t reg,uint32_t value)
{
 struct fake *f=cookie;CHECK(f->sealed&&f->c.phase==GGU_SUBMIT&&ggu_register_allowed(reg,true)&&f->mem_writes==5);
 CHECK(f->c.work.commands_checked==5&&!memcmp(f->ring,prefix,sizeof(prefix))&&!memcmp(f->ring+15,words,sizeof(words)));
 if(!tick(f))return false;++f->writes;
 if(reg==0x1f8c3){CHECK(value<=1);f->kept=value;}
 else{CHECK(value==20&&f->kept);++f->fence_writes;}
 f->reg[reg]=value;if(f->trace)printf("W %05x %08x\n",reg,value);return true;
}
static bool barrier(void *cookie)
{struct fake *f=cookie;if(!tick(f))return false;if(f->trace&&f->c.phase==GGU_SUBMIT)puts("B");if(f->trace&&f->c.phase==GGU_WAIT)puts("I");return true;}
static bool delay_us(void *cookie,unsigned us)
{struct fake *f=cookie;CHECK(us==10&&f->c.phase==GGU_SUBMIT&&f->kept);if(!tick(f))return false;++f->delays;if(f->trace)printf("D %u\n",us);return true;}
static bool read_memory(void *cookie,enum ggq_memory mem,uint32_t off,uint32_t *out)
{
 struct fake *f=cookie;CHECK(f->sealed&&out&&!(off&3));
 CHECK((mem==GGQ_RING&&((f->c.phase==GGU_CAPTURE&&off<80)||(f->c.phase==GGU_COMMANDS&&off>=60&&off<80)))||
       (mem==GGQ_SCRATCH&&off==0&&(f->c.phase==GGU_CAPTURE||f->c.phase==GGU_WAIT)));
 if(!tick(f))return false;++f->mem_reads;
 if(f->c.phase==GGU_WAIT){CHECK(mem==GGQ_SCRATCH&&f->submitted&&!f->kept&&f->reg[0x807]==20);
  /* Independent fake-device publication, never a production CPU shadow store. */
  if(f->shadow_reads++>=f->rptr_delay)f->scratch[0]=20;
  if(f->bad_rptr)f->scratch[0]=f->bad_rptr;
  if(f->trace)printf("P %08x\n",f->scratch[0]);}
 *out=mem==GGQ_RING?f->ring[off/4]:f->scratch[off/4];if(f->mem_reads==f->corrupt_read)*out^=1;return true;
}
static bool write_memory(void *cookie,enum ggq_memory mem,uint32_t off,uint32_t value)
{
 struct fake *f=cookie;CHECK(f->sealed&&mem==GGQ_RING&&f->c.phase==GGU_COMMANDS&&off==60+4*f->mem_writes&&f->mem_writes<5&&value==words[f->mem_writes]);
 if(!tick(f))return false;++f->mem_writes;if(f->mem_writes!=f->drop_write)f->ring[off/4]=value;
 if(f->trace)printf("C %u %08x\n",off/4,value);return true;
}
static struct fake *fresh(unsigned scenario)
{
 struct fake *f=calloc(1,sizeof(*f));CHECK(f);struct ggm_plan g;CHECK(ggm_plan_build(0xaa200000,&g)&&ggp_plan_build(&g,&f->p));
 f->ops=(struct ggu_ops){f,guard,seal,read32,write32,barrier,delay_us,read_memory,write_memory,quarantine};f->private_ok=1;
 memset(f->ring,0xaa,sizeof(f->ring));memcpy(f->ring,prefix,sizeof(prefix));
 for(unsigned i=0;i<1024;i++)f->scratch[i]=0xd5432100u+i;f->scratch[0]=15;
 f->reg[0x807]=15;f->reg[0x23b0c]=0x71000000;
 f->drop_fence=scenario==1?1:scenario==2?100:scenario==3?199:0;f->wrap=scenario==4;
 f->rptr_delay=scenario==1?2:0;f->busy_delay=scenario==1?2:0;return f;
}
static enum ggu_result run(struct fake *f,struct ggu_receipt *out)
{return ggu_start_once(&f->c,&f->ops,&f->p,out);}
static void once(struct fake *f)
{struct ggu_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned step=f->step;CHECK(run(f,&out)==GGU_ALREADY&&f->step==step&&!memcmp(&old,&out,sizeof(out)));}
static void untouched(struct fake *f)
{CHECK(!memcmp(f->ring,prefix,sizeof(prefix)));for(unsigned i=20;i<8192;i++)CHECK(f->ring[i]==0xaaaaaaaa);for(unsigned i=1;i<1024;i++)CHECK(f->scratch[i]==0xd5432100u+i);}
static void good(struct fake *f)
{
 struct ggu_receipt out;CHECK(run(f,&out)==GGU_OK&&f->c.state==2&&f->c.phase==GGU_DONE&&!f->quarantined);++cases;
 CHECK(out.sealed==1&&out.requests_retained==1&&out.complete==1&&out.prefix_checked==15&&out.clean_checked==5&&out.commands_written==5&&out.commands_checked==5);
 CHECK(out.initial_wptr==15&&out.initial_shadow==15&&out.initial_busy==0x71000000&&out.rptr==20&&!(out.busy&(1<<23)));
 CHECK(out.submit_attempted&&out.keepalive_set_attempted&&out.keepalive_clear_attempted&&!f->kept);
 CHECK(f->writes==3+f->drop_fence&&f->mem_writes==5&&out.writes==f->writes&&out.reads==f->reads);
 CHECK(out.fence_checks==f->drop_fence+1&&out.fence_status==2&&out.fence_slow==(f->drop_fence>=100)&&out.counter_before_valid&&out.counter_after_valid==out.fence_slow);
 CHECK(out.counter_before==(f->wrap?UINT64_C(0x200000010):UINT64_C(0x112345678)));
 CHECK(!memcmp(f->ring+15,words,sizeof(words)));untouched(f);once(f);
}
static void stopped(struct fake *f,enum ggu_result want)
{struct ggu_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;CHECK(run(f,&out)==want&&f->c.state==3&&f->quarantined&&!memcmp(&out,&old,sizeof(out)));++cases;untouched(f);once(f);}
int main(int argc,char **argv)
{
 if(argc==2){unsigned s=(unsigned)strtoul(argv[1],NULL,10);CHECK(s<5);struct fake *f=fresh(s);f->trace=1;good(f);free(f);return 0;}CHECK(argc==1);
 for(unsigned s=0;s<5;s++){
  struct fake *f=fresh(s);f->nested=1;good(f);unsigned steps=f->step;free(f);
  if(s<2)for(unsigned i=1;i<=steps;i++){
   f=fresh(s);f->fail=i;struct ggu_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
   CHECK(run(f,&out)!=GGU_OK&&f->step==i&&f->quarantined&&f->c.state==3&&!memcmp(&out,&old,sizeof(out)));++cases;untouched(f);once(f);free(f);
  }
  printf("GPU unsecure scenario%u: native append and%u boundaries PASS%s\n",s,steps,s<2?" (all injected)":"");
 }
 struct fake *f=fresh(0);f->private_ok=0;stopped(f,GGU_OWNER);CHECK(!f->mem_reads&&!f->mem_writes&&!f->reads&&!f->writes);free(f);
 f=fresh(0);f->p.owner_pa+=0x100000;stopped(f,GGU_OWNER);free(f);
 for(unsigned i=0;i<15;i++){f=fresh(0);f->ring[i]^=1;struct ggu_receipt out;CHECK(run(f,&out)==GGU_MEMORY_ERROR&&!f->mem_writes&&!f->writes&&f->quarantined);++cases;free(f);}
 for(unsigned i=15;i<20;i++){f=fresh(0);f->ring[i]^=1;stopped(f,GGU_MEMORY_ERROR);CHECK(!f->mem_writes&&!f->writes);free(f);}
 for(unsigned i=1;i<=5;i++){f=fresh(0);f->drop_write=i;stopped(f,GGU_MEMORY_ERROR);CHECK(!f->writes&&!f->submitted);free(f);}
 for(unsigned i=1;i<=26;i++){f=fresh(0);f->corrupt_read=i;stopped(f,GGU_MEMORY_ERROR);CHECK(!f->writes);free(f);}
 for(unsigned i=0;i<2;i++)for(unsigned value=0;value<3;value++){
  f=fresh(0);uint32_t v=value==0?0:value==1?14:0xffffffff;if(i)f->scratch[0]=v;else f->reg[0x807]=v;
  struct ggu_receipt out;CHECK(run(f,&out)==(i?GGU_MEMORY_ERROR:GGU_DIRTY_STATE)&&!f->mem_writes&&f->quarantined);++cases;free(f);
 }
 f=fresh(0);f->reg[0x23b0c]|=1<<23;stopped(f,GGU_FAULT);CHECK(!f->mem_writes);free(f);
 for(unsigned bit=0;bit<32;bit++){
  if(GGQ_RBBM_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x201]=1u<<bit;stopped(f,GGU_FAULT);free(f);}
  if(GGQ_CP_ERRORS&(1u<<bit)){f=fresh(0);f->reg[0x823]=1u<<bit;stopped(f,GGU_FAULT);free(f);}
 }
 f=fresh(0);f->fault_after=1;stopped(f,GGU_FAULT);CHECK(f->submitted&&!f->shadow_reads);free(f);
 f=fresh(0);f->bad_rptr=8192;stopped(f,GGU_MEMORY_ERROR);free(f);
 f=fresh(0);f->bad_busy=1;stopped(f,GGU_FAULT);free(f);
 f=fresh(0);f->drop_fence=200;stopped(f,GGU_TIMEOUT);CHECK(f->kept&&!f->submitted&&f->fence_reads==200&&f->fence_writes==201&&!f->c.work.keepalive_clear_attempted);free(f);
 f=fresh(0);f->rptr_delay=~0u;stopped(f,GGU_TIMEOUT);CHECK(f->shadow_reads==200000&&!f->busy_reads);free(f);
 f=fresh(0);f->rptr_delay=~0u;f->timeout_guard=3;stopped(f,GGU_GUARD);CHECK(f->shadow_reads==3);free(f);
 f=fresh(0);f->busy_delay=~0u;f->timeout_guard=3;stopped(f,GGU_GUARD);CHECK(f->shadow_reads==3);free(f);
 for(unsigned r=0;r<0x24000;r++){
  bool write=r==0x807||r==0x1f8c3,read=r==0x807||r==0x201||r==0x823||r==0x23b13||r==0x23b0c||r==0x1f888||r==0x1f889;
  CHECK(ggu_register_allowed(r,true)==write&&ggu_register_allowed(r,false)==read);
 }
 CHECK(!ggu_register_allowed(~0u,true)&&!ggu_register_allowed(~0u,false));
 f=fresh(0);struct ggu_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;
 CHECK(ggu_start_once(NULL,&f->ops,&f->p,&out)==GGU_ARGUMENT);
 CHECK(ggu_start_once(&f->c,NULL,&f->p,&out)==GGU_ARGUMENT);
 CHECK(ggu_start_once(&f->c,&f->ops,NULL,&out)==GGU_ARGUMENT);
 CHECK(ggu_start_once(&f->c,&f->ops,&f->p,NULL)==GGU_ARGUMENT);
 CHECK(ggu_start_once(&f->c,&f->ops,&f->p,(struct ggu_receipt *)&f->c)==GGU_ARGUMENT);
 CHECK(ggu_start_once(&f->c,(struct ggu_ops *)&f->c,&f->p,&out)==GGU_ARGUMENT);
 CHECK(ggu_start_once((struct ggu_context *)(UINTPTR_MAX-16),&f->ops,&f->p,&out)==GGU_ARGUMENT);
 CHECK(!f->c.state&&!f->step&&!memcmp(&out,&old,sizeof(out)));free(f);
 for(unsigned i=0;i<9;i++){
  f=fresh(0);switch(i){case 0:f->ops.guard=NULL;break;case 1:f->ops.seal=NULL;break;case 2:f->ops.read32=NULL;break;case 3:f->ops.write32=NULL;break;case 4:f->ops.barrier=NULL;break;case 5:f->ops.delay_us=NULL;break;case 6:f->ops.read_memory=NULL;break;case 7:f->ops.write_memory=NULL;break;case 8:f->ops.quarantine=NULL;break;}
  CHECK(run(f,&out)==GGU_ARGUMENT&&!f->c.state&&!f->step&&!memcmp(&out,&old,sizeof(out)));free(f);
 }
 printf("PASS GPU unsecure: %u cases, %u assertions; native5word append only, no CPU shadow store or hardware proof\n",cases,checks);return 0;
}
