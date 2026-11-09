/* Appended to the existing actual-runtime fixture. Only ROOT ring protocol
 * is decoded; no IB execution or GPU emulation is introduced. */
struct reg_event { uint32_t write,reg,value; };
static struct reg_event events[128];
static unsigned event_count;
static bool tracing;
static unsigned span_writes,span_verifies,write_words,verify_words;
static unsigned fail_write,fail_verify;
static bool expire_after_span;

static void event(uint32_t write,uint32_t reg,uint32_t value)
{
    if(!tracing)return;
    assert(event_count<128);events[event_count++]=(struct reg_event){write,reg,value};
}
static bool trace_read(void *p,uint32_t reg,uint32_t *value)
{bool ok=read_reg(p,reg,value);event(0,reg,*value);return ok;}
static bool trace_write(void *p,uint32_t reg,uint32_t value)
{event(1,reg,value);return write_reg(p,reg,value);}
static bool model_span(void *p,uint32_t off,const uint32_t *packet,uint32_t n,bool verify)
{
    assert(packet&&n&&n<=GGR_RING_PACKET_WORDS&&!(off&3)&&off<32768);
    CHECK(n>=12&&(n-8)%4==0);
    for(uint32_t i=0;i<(n-8)/4;i++){
        CHECK(packet[4*i]==0x70bf8003u);
        CHECK(packet[4*i+1]==GGR_VA_START+65536u*i);
        CHECK(!packet[4*i+2]&&packet[4*i+3]==4+i);
    }
    if(verify)++span_verifies;else ++span_writes;
    for(uint32_t i=0;i<n;i++){
        uint32_t at=(off+4*i)%32768;
        if(verify){
            if(i==fail_verify)return false;
            uint32_t value;assert(read_memory(p,GGR_RING,at,&value));++verify_words;
            if(value!=packet[i])return false;
        } else {
            if(i==fail_write)return false;
            assert(write_ring(p,at,packet[i]));++write_words;
        }
    }
    if(expire_after_span)((struct model *)p)->ns=UINT64_C(30000000000);
    return true;
}
static void reset_trace(void)
{
    memset(events,0,sizeof(events));event_count=0;tracing=true;
    span_writes=span_verifies=write_words=verify_words=0;
    fail_write=fail_verify=UINT32_MAX;expire_after_span=false;
}
static void prepare(struct model *m,struct ggr_context *c,bool batch,uint32_t start)
{
    tracing=false;init(m,c);reset_trace();
    c->ops.read_reg=trace_read;c->ops.write_reg=trace_write;
    c->ops.ring_span=batch?model_span:NULL;
    m->wptr=m->shadow=m->old_wptr=c->wptr=start;
}
static void no_doorbell(void)
{
    for(unsigned i=0;i<event_count;i++)CHECK(!events[i].write);
}
static void compare(uint32_t start,uint32_t ibs)
{
    struct model a,b;struct ggr_context ca,cb;uint32_t fa=0,fb=0;
    prepare(&a,&ca,false,start);unsigned a_start=a.checks;
    CHECK(submit(&ca,ibs,&fa)==GGR_OK);unsigned a_checks=a.checks-a_start;
    struct reg_event before[128];memcpy(before,events,sizeof(before));unsigned count=event_count;
    prepare(&b,&cb,true,start);unsigned b_start=b.checks;
    CHECK(submit(&cb,ibs,&fb)==GGR_OK);unsigned b_checks=b.checks-b_start;
    CHECK(count==event_count&&!memcmp(before,events,count*sizeof(*events)));
    CHECK(!memcmp(a.ring,b.ring,sizeof(a.ring)));
    CHECK(fa==fb&&ca.wptr==cb.wptr&&ca.submitted==cb.submitted&&ca.completed==cb.completed);
    CHECK(ca.polls==cb.polls&&a.shadow==b.shadow&&a.eop==b.eop&&a.writes==b.writes);
    CHECK(!a.quarantines&&!b.quarantines);
    CHECK(span_writes==1&&span_verifies==1);
    uint32_t words=4*ibs+8;
    CHECK(write_words==words&&verify_words==words);
    CHECK(a_checks-b_checks==4*words-4); /* Only CPU ring per-word guards removed. */
}
int main(void)
{
    int result=baseline_main();CHECK(result==0);unsigned retained=cases;
    const uint32_t starts[]={0,20,8180,8191},counts[]={1,3,128};
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++)compare(starts[i],counts[j]);
    struct model m;struct ggr_context c;uint32_t fence;
    prepare(&m,&c,true,8180);
    for(unsigned i=0;i<40;i++){
        event_count=0;CHECK(submit(&c,128,&fence)==GGR_OK&&fence==i+1);
        CHECK(m.eop==c.completed&&m.shadow==c.wptr&&!m.quarantines);
    }
    for(unsigned verify=0;verify<2;verify++)for(unsigned word=0;word<20;word++){
        prepare(&m,&c,true,8190);fence=0xdeadbeef;
        if(verify)fail_verify=word;else fail_write=word;
        CHECK(submit(&c,3,&fence)==GGR_IO&&c.state==GGR_FAILED);
        CHECK(m.quarantines==1&&fence==0xdeadbeef&&!m.decoded_fence);
        CHECK(span_writes==1&&span_verifies==verify);
        CHECK(verify?verify_words==word:write_words==word);
        no_doorbell();unsigned writes=m.writes;
        CHECK(submit(&c,3,&fence)==GGR_UNAVAILABLE&&m.writes==writes&&m.quarantines==1);
    }
    prepare(&m,&c,true,8191);m.mutate_ring=true;fence=0xdeadbeef;
    CHECK(submit(&c,1,&fence)==GGR_IO&&fence==0xdeadbeef);no_doorbell();
    prepare(&m,&c,true,8191);expire_after_span=true;fence=0xdeadbeef;
    CHECK(submit(&c,1,&fence)==GGR_IO&&fence==0xdeadbeef);
    CHECK(span_writes==1&&!span_verifies&&m.quarantines==1);no_doorbell();
    prepare(&m,&c,true,20);unsigned first=m.checks;
    CHECK(submit(&c,3,&fence)==GGR_OK);unsigned boundaries=m.checks-first;
    for(unsigned at=1;at<=boundaries;at++){
        prepare(&m,&c,true,20);m.fail_at=m.checks+at;fence=0xdeadbeef;
        CHECK(submit(&c,3,&fence)!=GGR_OK&&fence==0xdeadbeef);
        CHECK(m.quarantines==1&&c.state==GGR_FAILED);
        if(!span_writes)no_doorbell();
        unsigned writes=m.writes;
        CHECK(submit(&c,3,&fence)==GGR_UNAVAILABLE&&m.writes==writes&&m.quarantines==1);
    }
    printf("PASS: %u additional ring-span assertions; exact ROOT packets/register trace, wrap, partial/verify/deadline/boundary failures; no IB/GPU emulation\n",cases-retained);
}
