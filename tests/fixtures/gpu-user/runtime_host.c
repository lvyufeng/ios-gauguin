/* Executes the real runtime against typed register/memory seams. The model
 * decodes the ROOT ring only; it neither executes an IB nor emulates a GPU. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_gpu_runtime.h"
static unsigned cases;
#define CHECK(x) do { ++cases;assert(x); } while(0)
struct model {
    uint32_t ring[8192],wptr,shadow,eop,quarantines,writes,checks,fail_at;
    uint32_t old_wptr,decoded_ibs,decoded_fence;
    uint32_t rbbm,cp,busy;
    uint64_t ns;
    bool no_eop,no_shadow,stopped,mutate_ring,timeout;
};
static bool healthy(void *p)
{struct model *m=p;++m->checks;return !m->stopped&&m->checks!=m->fail_at;}
static uint64_t time_ns(void *p)
{struct model *m=p;m->ns+=m->timeout?100000000:100;return m->ns;}
static uint32_t ring_word(struct model *m,uint32_t i)
{return m->ring[i%8192];}
static bool read_reg(void *p,uint32_t r,uint32_t *v)
{
    struct model *m=p;assert(!m->stopped);
    if(r==0x807)*v=m->wptr;
    else if(r==0x201)*v=m->rbbm;
    else if(r==0x823)*v=m->cp;
    else if(r==0x23b0c)*v=m->busy;
    else if(r==0x23b13)*v=0;
    else assert(false);
    return true;
}
static bool write_reg(void *p,uint32_t r,uint32_t v)
{
    struct model *m=p;assert(!m->stopped);++m->writes;
    if(r==0x1f8c3){assert(v<=1);return true;}
    assert(r==0x807);m->wptr=v;
    uint32_t at=m->old_wptr;
    while(ring_word(m,at)==0x70bf8003u) {
        CHECK(ring_word(m,at+1)>=GGR_VA_START&&ring_word(m,at+1)<GGR_VA_END);
        CHECK(ring_word(m,at+2)==0);CHECK(ring_word(m,at+3)>0);
        ++m->decoded_ibs;at=(at+4)%8192;
    }
    CHECK(ring_word(m,at)==0x70460004u);CHECK(ring_word(m,at+1)==4);
    CHECK(ring_word(m,at+2)==0xfc018000u);CHECK(ring_word(m,at+3)==0);
    m->decoded_fence=ring_word(m,at+4);at=(at+5)%8192;
    CHECK(ring_word(m,at)==0x70620002u);CHECK(ring_word(m,at+1)==0xfc010000u);
    CHECK(ring_word(m,at+2)==0);CHECK((at+3)%8192==v);
    if(!m->no_eop)m->eop=m->decoded_fence;
    if(!m->no_shadow)m->shadow=v;
    m->old_wptr=v;return true;
}
static bool read_memory(void *p,enum ggr_memory k,uint32_t off,uint32_t *v)
{
    struct model *m=p;assert(!m->stopped);
    if(k==GGR_RING){assert(off<32768&&!(off&3));*v=m->ring[off/4]^(m->mutate_ring?1:0);}
    else if(k==GGR_SHADOW){assert(!off);*v=m->shadow;}
    else {assert(k==GGR_COMPLETION&&!off);*v=m->eop;}
    return true;
}
static bool write_ring(void *p,uint32_t off,uint32_t v)
{struct model *m=p;assert(!m->stopped&&off<32768&&!(off&3));++m->writes;m->ring[off/4]=v;return true;}
static bool barrier(void *p)
{assert(!((struct model *)p)->stopped);return true;}
static bool delay_us(void *p,uint32_t n)
{assert(!((struct model *)p)->stopped&&n==10);((struct model *)p)->ns+=10000;return true;}
static void quarantine(void *p)
{struct model *m=p;assert(!m->stopped);m->stopped=true;++m->quarantines;}
static void init(struct model *m,struct ggr_context *c)
{
    memset(m,0,sizeof(*m));memset(c,0,sizeof(*c));m->wptr=m->shadow=m->old_wptr=20;
    struct ggr_ops o={.cookie=m,.healthy=healthy,.nanoseconds=time_ns,
        .read_reg=read_reg,.write_reg=write_reg,.read_memory=read_memory,
        .write_ring=write_ring,.barrier=barrier,.delay_us=delay_us,.quarantine=quarantine};
    CHECK(ggr_open(c,&o,0xfc010000u,0xfc018000u)==GGR_OK);
}
static enum ggr_error submit(struct ggr_context *c,uint32_t count,uint32_t *fence)
{
    uint64_t a[GGR_MAX_COMMANDS];uint32_t w[GGR_MAX_COMMANDS];
    for(uint32_t i=0;i<GGR_MAX_COMMANDS;i++){a[i]=GGR_VA_START+65536ull*i;w[i]=4+i;}
    return ggr_submit(c,a,w,count,fence);
}
int main(void)
{
    const uint32_t selectors[]={9,0x40,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x4a,0x4b,0x4c,0x7e};
    const uint32_t sizes[]={8,24,16,24,24,4,72,32,12,12,4,24,40};
    for(uint32_t s=0;s<256;s++) {
        size_t expected=0;
        for(size_t i=0;i<sizeof(selectors)/sizeof(*selectors);i++)if(selectors[i]==s)expected=sizes[i];
        CHECK(ggr_request_size(s)==expected);
    }
    struct ggr_submit_cmd cmd={.type=1,.size=16};
    CHECK(ggr_command_range(&cmd,16));CHECK(!ggr_command_range(&cmd,15));
    cmd.submit_offset=4;CHECK(!ggr_command_range(&cmd,16));CHECK(ggr_command_range(&cmd,20));
    cmd.submit_offset=UINT32_MAX;CHECK(!ggr_command_range(&cmd,UINT64_MAX));
    cmd.submit_offset=0;cmd.size=0;CHECK(!ggr_command_range(&cmd,UINT64_MAX));
    cmd.size=0x400000;CHECK(!ggr_command_range(&cmd,UINT64_MAX));
    cmd.size=16;cmd.nr_relocs=1;CHECK(!ggr_command_range(&cmd,16));
    cmd.nr_relocs=0;cmd.relocs=1;CHECK(!ggr_command_range(&cmd,16));
    cmd.relocs=0;cmd.pad=1;CHECK(!ggr_command_range(&cmd,16));
    CHECK(!ggr_user_span(0,1));CHECK(!ggr_user_span(1,0));CHECK(!ggr_user_span(UINT64_MAX,1));
    CHECK(!ggr_user_span(UINT64_C(0x8000000000000000),1));CHECK(ggr_user_span(0x10000,4096));
    struct ggr_timespec t={0,0};CHECK(ggr_timeout_valid(&t));
    t.seconds=-1;CHECK(!ggr_timeout_valid(&t));t.seconds=0;t.nanoseconds=1000000000;CHECK(!ggr_timeout_valid(&t));
    struct model m;struct ggr_context c;uint32_t f=0;
    init(&m,&c);CHECK(submit(&c,1,&f)==GGR_OK&&f==1&&c.completed==1&&m.decoded_ibs==1);
    CHECK(submit(&c,3,&f)==GGR_OK&&f==2&&c.completed==2&&m.decoded_ibs==4);
    CHECK(submit(&c,128,&f)==GGR_OK&&f==3&&m.decoded_ibs==132);
    /* Cross the end of the actual 8192-word root ring repeatedly. */
    for(unsigned i=0;i<40;i++)CHECK(submit(&c,128,&f)==GGR_OK&&f==4+i);
    CHECK(!m.quarantines&&m.eop==c.completed&&m.shadow==c.wptr);
    init(&m,&c);uint32_t unchanged=0x12345678;unsigned before=m.writes;
    CHECK(submit(&c,0,&unchanged)==GGR_ARGUMENT&&unchanged==0x12345678&&m.writes==before&&!m.quarantines);
    uint64_t a=GGR_VA_END-4;uint32_t w=2;
    CHECK(ggr_submit(&c,&a,&w,1,&unchanged)==GGR_ARGUMENT&&unchanged==0x12345678&&m.writes==before);
    init(&m,&c);CHECK(submit(&c,2,&f)==GGR_OK);unsigned healthy_calls=m.checks;
    /* Refuse each actual health boundary, requiring no callback after the
     * quarantine and no output fence on every failed submission. */
    for(unsigned at=1;at<=healthy_calls;at++) {
        init(&m,&c);m.fail_at=m.checks+at;f=0xdeadbeef;
        enum ggr_error rc=submit(&c,2,&f);
        if(m.checks>=m.fail_at) {
            CHECK(rc!=GGR_OK&&c.state==GGR_FAILED&&m.quarantines==1&&f==0xdeadbeef);
            before=m.writes;CHECK(submit(&c,2,&f)==GGR_UNAVAILABLE&&m.writes==before&&m.quarantines==1);
        }
    }
    init(&m,&c);m.no_eop=true;f=0xdeadbeef;
    CHECK(submit(&c,1,&f)!=GGR_OK&&m.quarantines==1&&f==0xdeadbeef);
    init(&m,&c);m.no_shadow=true;f=0xdeadbeef;
    CHECK(submit(&c,1,&f)!=GGR_OK&&m.quarantines==1&&f==0xdeadbeef);
    init(&m,&c);m.mutate_ring=true;f=0xdeadbeef;
    CHECK(submit(&c,1,&f)!=GGR_OK&&m.quarantines==1&&f==0xdeadbeef);
    init(&m,&c);m.timeout=true;f=0xdeadbeef;
    CHECK(submit(&c,1,&f)!=GGR_OK&&m.quarantines==1&&f==0xdeadbeef);
    unsigned retained=cases;
    init(&m,&c);before=m.writes;
    CHECK(ggr_check_idle(&c)==GGR_OK&&m.writes==before&&!m.quarantines);
    CHECK(submit(&c,2,&f)==GGR_OK);before=m.writes;m.ns+=UINT64_C(30000000000);
    unsigned start_checks=m.checks;
    CHECK(ggr_check_idle(&c)==GGR_OK&&m.writes==before&&c.completed==1);
    unsigned idle_boundaries=m.checks-start_checks;
    for(unsigned at=1;at<=idle_boundaries;at++) {
        init(&m,&c);m.fail_at=m.checks+at;before=m.writes;
        CHECK(ggr_check_idle(&c)!=GGR_OK&&m.quarantines==1&&c.state==GGR_FAILED&&m.writes==before);
        CHECK(ggr_check_idle(&c)==GGR_UNAVAILABLE&&m.writes==before&&m.quarantines==1);
    }
    for(unsigned fault=0;fault<8;fault++) {
        init(&m,&c);before=m.writes;
        switch(fault) {
        case 0:m.rbbm=1u<<1;break;case 1:m.cp=1;break;
        case 2:m.wptr++;break;case 3:m.shadow++;break;case 4:m.eop++;break;
        case 5:m.busy=1u<<23;break;case 6:m.busy=UINT32_MAX;break;
        case 7:m.ns=UINT64_MAX-100;break;
        }
        CHECK(ggr_check_idle(&c)!=GGR_OK&&m.quarantines==1&&m.writes==before);
    }
    memset(&c,0,sizeof(c));CHECK(ggr_check_idle(&c)==GGR_UNAVAILABLE);
    CHECK(ggr_check_idle(NULL)==GGR_UNAVAILABLE);
    printf("PASS: %u runtime/ABI assertions + %u service-health assertions; real core, typed seams, no IB/GPU emulation\n",retained,cases-retained);
    return 0;
}
