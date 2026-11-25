#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gmu_hfi.h"
#include "gauguin_gmu_memory.h"
static unsigned checks;
#define CHECK(c) do {assert(c);++checks;} while(0)
struct fake {
    struct ggh_channel channel;
    uint32_t memory[8192];
    unsigned step,fail,writes,barriers,payload_barrier,payload_read_barrier,index_stores;
    bool nested,ignored_index,drift;
    enum ggh_result nested_result;
};
static bool tick(struct fake *f){return ++f->step!=f->fail;}
static bool guard(void *cookie)
{
    struct fake *f=cookie;
    if(f->nested){
        f->nested=false;uint32_t p=0x100;
        struct ggh_channel old=f->channel;
        f->nested_result=ggh_send(&f->channel,&p,1);
        CHECK(!memcmp(&old,&f->channel,sizeof(old)));
    }
    return tick(f);
}
static bool read_word(void *cookie,uint32_t word,uint32_t *value)
{
    struct fake *f=cookie;CHECK(word<4152);
    if(!tick(f))return false;
    if(word>=56)f->payload_read_barrier=f->barriers;
    *value=f->memory[word];return true;
}
static bool write_word(void *cookie,uint32_t word,uint32_t value)
{
    struct fake *f=cookie;CHECK(word<4152);
    if(!tick(f))return false;
    ++f->writes;
    if(word>=56)f->payload_barrier=f->barriers;
    else {
        CHECK(word==17||word==28||word==40);++f->index_stores;
        if(word==17)CHECK(f->barriers>f->payload_barrier);
        else CHECK(f->barriers>f->payload_read_barrier);
        if(f->ignored_index)return true;
    }
    f->memory[word]=value;return true;
}
static bool barrier(void *cookie)
{
    struct fake *f=cookie;
    if(!tick(f))return false;
    ++f->barriers;
    if(f->drift){++f->memory[17];f->drift=false;}
    return true;
}
static struct ggh_ops ops(struct fake *f)
{return (struct ggh_ops){f,guard,read_word,write_word,barrier};}
static struct fake *fresh(unsigned major,bool bind)
{
    struct fake *f=calloc(1,sizeof(*f));CHECK(f);
    struct ggm_plan p;CHECK(ggm_plan_build(0xaa200000,&p));
    CHECK(ggm_emit_hfi(&p,f->memory,sizeof(f->memory)));
    if(bind){struct ggh_ops o=ops(f);CHECK(ggh_bind(&f->channel,&o,major)==GGH_OK);}
    f->step=f->writes=f->barriers=f->index_stores=f->payload_barrier=0;
    return f;
}
static void fill_rx(struct fake *f,unsigned q,unsigned rd,const uint32_t *p,unsigned n,unsigned major)
{
    unsigned padded=major==2?(n+3)&~3u:n;
    f->memory[6+12*q+10]=rd;f->memory[6+12*q+11]=(rd+padded)%1024;
    for(unsigned i=0;i<padded;i++)f->memory[56+1024*q+(rd+i)%1024]=i<n?p[i]:0xfafafafa;
}
static void quarantined(struct fake *f)
{
    unsigned step=f->step;uint32_t p=0x100,out[4]={1,2,3,4};size_t count=99;
    CHECK(ggh_send(&f->channel,&p,1)==GGH_QUARANTINED);
    CHECK(ggh_receive(&f->channel,1,out,4,&count)==GGH_QUARANTINED);
    struct ggh_ops o=ops(f);CHECK(ggh_bind(&f->channel,&o,1)==GGH_QUARANTINED);
    CHECK(f->step==step&&count==99&&out[0]==1&&out[3]==4);
}
static void happy(void)
{
    for(unsigned major=1;major<=2;major++){
        const uint32_t p[]={0xabc00300,0x12345678,0xdeadbeef};
        struct fake *f=fresh(major,true);unsigned wr=major==1?1022:1020,padded=major==1?3:4;
        f->memory[16]=major==1?10:12;f->memory[17]=wr;f->nested=true;
        CHECK(ggh_send(&f->channel,p,3)==GGH_OK);CHECK(f->nested_result==GGH_BUSY);
        CHECK(f->memory[17]==(wr+padded)%1024);CHECK(f->writes==padded+1&&f->index_stores==1);
        for(unsigned i=0;i<padded;i++)CHECK(f->memory[56+(wr+i)%1024]==(i<3?p[i]:0xfafafafa));
        for(unsigned q=1;q<=2;q++){
            uint32_t rx[]={0xabc3017e,9,0};rx[0]=(rx[0]&~0xff00u)|0x300;
            unsigned rd=major==1?1023:1020;fill_rx(f,q,rd,rx,3,major);
            uint32_t out[5]={5,6,7,8,9};size_t n=99;
            CHECK(ggh_receive(&f->channel,q,out,5,&n)==GGH_OK);
            CHECK(n==3&&!memcmp(out,rx,sizeof(rx))&&out[3]==8&&out[4]==9);
            CHECK(f->memory[6+12*q+10]==(rd+padded)%1024);
        }
        free(f);
        /* Max wire size, wrap and next packet; tests v2 padding255->256. */
        f=fresh(major,true);uint32_t maximum[255];
        for(unsigned i=0;i<255;i++)maximum[i]=i;maximum[0]=0x12f0ff00;
        f->memory[16]=800;f->memory[17]=900;
        CHECK(ggh_send(&f->channel,maximum,255)==GGH_OK);
        unsigned span=major==1?255:256;CHECK(f->memory[17]==(900+span)%1024);
        fill_rx(f,1,900,maximum,255,major);uint32_t out[255];size_t n=0;
        CHECK(ggh_receive(&f->channel,1,out,255,&n)==GGH_OK);
        CHECK(n==255&&!memcmp(out,maximum,sizeof(out)));free(f);
    }
}
static void benign(void)
{
    for(unsigned major=1;major<=2;major++){
        struct fake *f=fresh(major,true);uint32_t old[8192],out[4]={1,2,3,4};size_t n=99;
        memcpy(old,f->memory,sizeof(old));
        CHECK(ggh_receive(&f->channel,1,out,4,&n)==GGH_EMPTY);
        CHECK(!memcmp(old,f->memory,sizeof(old))&&n==99&&out[0]==1&&out[3]==4);
        uint32_t p[4]={0x400,1,2,3};f->memory[16]=major==1?1:4;
        memcpy(old,f->memory,sizeof(old));CHECK(ggh_send(&f->channel,p,4)==GGH_FULL);
        CHECK(!memcmp(old,f->memory,sizeof(old)));
        fill_rx(f,1,0,p,4,major);memcpy(old,f->memory,sizeof(old));
        CHECK(ggh_receive(&f->channel,1,out,3,&n)==GGH_CAPACITY);
        CHECK(!memcmp(old,f->memory,sizeof(old))&&n==99&&out[0]==1);
        unsigned step=f->step;
        CHECK(ggh_send(&f->channel,NULL,1)==GGH_ARGUMENT);
        CHECK(ggh_send(&f->channel,p,0)==GGH_ARGUMENT);
        CHECK(ggh_send(&f->channel,p,256)==GGH_ARGUMENT);
        CHECK(ggh_send(&f->channel,p,3)==GGH_ARGUMENT);
        p[0]=0x10400;CHECK(ggh_send(&f->channel,p,4)==GGH_ARGUMENT);
        CHECK(ggh_send(&f->channel,(void *)(UINTPTR_MAX-1),4)==GGH_ARGUMENT);
        CHECK(ggh_send(&f->channel,(void *)&f->channel,1)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,0,out,4,&n)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,3,out,4,&n)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,NULL,4,&n)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,out,0,&n)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,out,256,&n)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,out,4,NULL)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,out,4,(void *)out)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,(void *)&f->channel,4,&n)==GGH_ARGUMENT);
        CHECK(ggh_receive(&f->channel,1,out,4,(void *)&f->channel)==GGH_ARGUMENT);
        CHECK(f->step==step&&!memcmp(old,f->memory,sizeof(old)));
        free(f);
    }
    struct ggh_channel c={0},old=c;struct fake *f=fresh(1,false);struct ggh_ops o=ops(f);
    CHECK(ggh_bind(NULL,&o,1)==GGH_ARGUMENT);CHECK(ggh_bind(&c,NULL,1)==GGH_ARGUMENT);
    CHECK(ggh_bind(&c,&o,0)==GGH_ARGUMENT);CHECK(ggh_bind(&c,&o,3)==GGH_ARGUMENT);
    o.write=NULL;CHECK(ggh_bind(&c,&o,1)==GGH_ARGUMENT);CHECK(!memcmp(&old,&c,sizeof(c)));
    uint32_t p=0x100;size_t n;CHECK(ggh_send(NULL,&p,1)==GGH_ARGUMENT);
    CHECK(ggh_receive(NULL,1,&p,1,&n)==GGH_ARGUMENT);free(f);
}
static void corrupt(void)
{
    for(unsigned word=0;word<54;word++){
        struct fake *f=fresh(1,false);f->memory[word]^=1;struct ggh_ops o=ops(f);
        CHECK(ggh_bind(&f->channel,&o,1)==GGH_CORRUPT);quarantined(f);free(f);
    }
    for(unsigned i=0;i<10;i++){
        struct fake *f=fresh(1,true);uint32_t p=0x100;
        f->memory[i]^=1;
        CHECK(ggh_send(&f->channel,&p,1)==GGH_CORRUPT);CHECK(f->writes==0);quarantined(f);free(f);
    }
    for(unsigned major=1;major<=2;major++)for(unsigned q=0;q<=2;q++)for(unsigned field=10;field<=11;field++){
        struct fake *f=fresh(major,true);uint32_t p=0x100,out=99;size_t n=99;
        f->memory[6+12*q+field]=1024;
        CHECK((q?ggh_receive(&f->channel,q,&out,1,&n):ggh_send(&f->channel,&p,1))==GGH_CORRUPT);
        CHECK(f->writes==0&&out==99&&n==99);quarantined(f);free(f);
    }
    for(unsigned field=10;field<=11;field++){
        struct fake *f=fresh(2,true);f->memory[6+field]=1;uint32_t p=0x100;
        CHECK(ggh_send(&f->channel,&p,1)==GGH_CORRUPT);quarantined(f);free(f);
    }
    for(unsigned kind=0;kind<2;kind++){
        struct fake *f=fresh(1,true);uint32_t p[]={kind?0x800u:0,1};fill_rx(f,1,0,p,2,1);
        uint32_t out[4]={1,2,3,4};size_t n=99;
        CHECK(ggh_receive(&f->channel,1,out,4,&n)==GGH_CORRUPT);
        CHECK(f->writes==0&&out[0]==1&&out[3]==4&&n==99);quarantined(f);free(f);
    }
    for(unsigned which=0;which<2;which++){
        struct fake *f=fresh(1,true);uint32_t p=0x100;
        f->ignored_index=which==0;f->drift=which==1;
        CHECK(ggh_send(&f->channel,&p,1)==GGH_CORRUPT);quarantined(f);free(f);
    }
}
static enum ggh_result run_operation(struct fake *f,unsigned operation,uint32_t *out,size_t *n)
{
    uint32_t p[]={0x300,0x01234567,0xcafef00d};
    if(operation==0){struct ggh_ops o=ops(f);return ggh_bind(&f->channel,&o,2);}
    if(operation==1)return ggh_send(&f->channel,p,3);
    return ggh_receive(&f->channel,1,out,4,n);
}
static struct fake *prepare(unsigned operation)
{
    struct fake *f=fresh(2,operation!=0);
    if(operation==2){uint32_t p[]={0x10300,0xaabbccdd,0x11223344};fill_rx(f,1,1020,p,3,2);}
    return f;
}
static void faults(void)
{
    for(unsigned operation=0;operation<3;operation++){
        struct fake *f=prepare(operation);uint32_t out[4]={1,2,3,4};size_t n=99;
        CHECK(run_operation(f,operation,out,&n)==GGH_OK);unsigned steps=f->step;free(f);
        for(unsigned fail=1;fail<=steps;fail++){
            f=prepare(operation);f->fail=fail;out[0]=1;out[1]=2;out[2]=3;out[3]=4;n=99;
            CHECK(run_operation(f,operation,out,&n)==GGH_IO);
            CHECK(out[0]==1&&out[1]==2&&out[2]==3&&out[3]==4&&n==99);
            quarantined(f);free(f);
        }
        printf("HFI operation%u fail-every-callback: %u boundaries PASS\n",operation,steps);
    }
}
int main(void){happy();benign();corrupt();faults();printf("GMU HFI: %u checks PASS\n",checks);}
