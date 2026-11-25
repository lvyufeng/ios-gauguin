/* Appended to the existing actual-runtime fixture. Only ROOT ring protocol
 * is decoded; no IB execution or GPU emulation is introduced. */
enum event_kind { REG_READ,REG_WRITE,BARRIER,DELAY };
struct protocol_event { uint32_t kind,reg,value; };
static struct protocol_event events[128];
static unsigned event_count;
static bool tracing;
static unsigned span_writes,span_verifies,write_words,verify_words;
static unsigned fail_write,fail_verify;
enum ring_step { WRITE_SPAN,RING_BARRIER,VERIFY_SPAN,RING_STEPS };
enum ring_fault { NO_FAULT,CALLBACK_FAILURE,HEALTH_FAILURE,DEADLINE_EXPIRED };
static enum ring_step fault_step;
static enum ring_fault fault;
static unsigned ring_checks[RING_STEPS],first_mmio_write_checks,retries_left;
static bool preparing_ring;

static void event(enum event_kind kind,uint32_t reg,uint32_t value)
{
    if(!tracing)return;
    assert(event_count<128);events[event_count++]=(struct protocol_event){kind,reg,value};
}
static bool trace_read(void *p,uint32_t reg,uint32_t *value)
{
    bool ok=read_reg(p,reg,value);
    if(ok&&reg==0x23b13&&retries_left){*value=1;--retries_left;}
    if(ok)event(REG_READ,reg,*value);
    return ok;
}
static bool trace_write(void *p,uint32_t reg,uint32_t value)
{
    struct model *m=p;
    if(!first_mmio_write_checks)first_mmio_write_checks=m->checks;
    event(REG_WRITE,reg,value);
    /* A retry writes the same WPTR; it does not fetch a second packet. */
    if(reg==0x807&&value==m->wptr){++m->writes;return true;}
    return write_reg(p,reg,value);
}
static bool finish_step(struct model *m,enum ring_step step)
{
    if(step!=fault_step)return true;
    if(fault==HEALTH_FAILURE)m->poison=true;
    if(fault==DEADLINE_EXPIRED)m->ns=UINT64_C(30000000000);
    return fault!=CALLBACK_FAILURE;
}
static bool trace_barrier(void *p)
{
    event(BARRIER,0,0);
    if(!barrier(p))return false;
    if(!preparing_ring)return true;
    ring_checks[RING_BARRIER]=((struct model *)p)->checks;
    return finish_step(p,RING_BARRIER);
}
static bool trace_delay(void *p,uint32_t us)
{event(DELAY,0,us);return delay_us(p,us);}
static bool model_span(void *p,uint32_t off,const uint32_t *packet,uint32_t n,bool verify)
{
    assert(packet&&n&&n<=GGR_RING_PACKET_WORDS&&!(off&3)&&off<32768);
    CHECK(n>=12&&(n-8)%4==0);
    for(uint32_t i=0;i<(n-8)/4;i++){
        CHECK(packet[4*i]==0x70bf8003u);
        CHECK(packet[4*i+1]==GGR_VA_START+65536u*i);
        CHECK(!packet[4*i+2]&&packet[4*i+3]==4+i);
    }
    enum ring_step step=verify?VERIFY_SPAN:WRITE_SPAN;
    ring_checks[step]=((struct model *)p)->checks;
    preparing_ring=!verify;
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
    return finish_step(p,step);
}
static void reset_trace(void)
{
    memset(events,0,sizeof(events));event_count=0;tracing=true;
    span_writes=span_verifies=write_words=verify_words=0;
    fail_write=fail_verify=UINT32_MAX;
    memset(ring_checks,0,sizeof(ring_checks));
    first_mmio_write_checks=retries_left=0;
    fault=NO_FAULT;fault_step=WRITE_SPAN;preparing_ring=false;
}
static void prepare(struct model *m,struct ggr_context *c,bool batch,uint32_t start)
{
    tracing=false;init(m,c);reset_trace();
    c->ops.read_reg=trace_read;c->ops.write_reg=trace_write;
    c->ops.barrier=trace_barrier;c->ops.delay_us=trace_delay;
    c->ops.ring_span=batch?model_span:NULL;
    m->wptr=m->shadow=m->old_wptr=c->wptr=start;
}
static void no_doorbell(void)
{
    for(unsigned i=0;i<event_count;i++)CHECK(events[i].kind!=REG_WRITE);
}
static void compare(uint32_t start,uint32_t ibs)
{
    struct model a,b;struct ggr_context ca,cb;uint32_t fa=0,fb=0;
    prepare(&a,&ca,false,start);unsigned a_start=a.checks;
    CHECK(submit(&ca,ibs,&fa)==GGR_OK);unsigned a_checks=a.checks-a_start;
    struct protocol_event before[128];memcpy(before,events,sizeof(before));unsigned count=event_count;
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
static enum ggr_error issue_packet(struct ggr_context *c,uint32_t count,uint32_t *fence)
{
    uint64_t a[GGR_MAX_COMMANDS];uint32_t w[GGR_MAX_COMMANDS];
    for(uint32_t i=0;i<count;i++){a[i]=GGR_VA_START+65536ull*i;w[i]=4+i;}
    return ggr_issue(c,a,w,count,fence);
}
static void compare_issued(uint32_t start,uint32_t ibs,bool span,unsigned retries)
{
    struct model a,b;struct ggr_context ca,cb;uint32_t fa=0,fb=0;
    prepare(&a,&ca,span,start);retries_left=retries;
    CHECK(submit(&ca,ibs,&fa)==GGR_OK&&!retries_left);
    struct protocol_event before[128];memcpy(before,events,sizeof(before));
    unsigned count=event_count,mmio_before=first_mmio_write_checks;
    unsigned checks_before[RING_STEPS];memcpy(checks_before,ring_checks,sizeof(checks_before));
    prepare(&b,&cb,span,start);retries_left=retries;
    CHECK(issue_packet(&cb,ibs,&fb)==GGR_OK&&fb==1&&!retries_left);
    CHECK(cb.state==GGR_BUSY&&cb.submitted==fb&&cb.completed==0&&cb.wptr==start);
    CHECK(ggr_poll(&cb)==GGR_OK&&cb.state==GGR_READY);
    CHECK(count==event_count&&!memcmp(before,events,count*sizeof(*events)));
    CHECK(!memcmp(a.ring,b.ring,sizeof(a.ring)));
    CHECK(fa==fb&&ca.wptr==cb.wptr&&ca.submitted==cb.submitted&&ca.completed==cb.completed);
    CHECK(ca.polls==cb.polls&&a.writes==b.writes&&!a.quarantines&&!b.quarantines);
    unsigned saved=span?2:0;
    unsigned saved_before_enable=saved;
#ifdef GGR_SHARE_DOORBELL_GUARDS
    if(span){saved+=2;++saved_before_enable;}
#endif
    CHECK(a.checks==b.checks+saved&&mmio_before==first_mmio_write_checks+saved_before_enable);
    if(span){
        CHECK(ring_checks[WRITE_SPAN]==checks_before[WRITE_SPAN]);
        CHECK(ring_checks[RING_BARRIER]==ring_checks[WRITE_SPAN]+1);
        CHECK(ring_checks[RING_BARRIER]+1==checks_before[RING_BARRIER]);
        CHECK(ring_checks[VERIFY_SPAN]==ring_checks[RING_BARRIER]+1);
        CHECK(ring_checks[VERIFY_SPAN]+2==checks_before[VERIFY_SPAN]);
#ifdef GGR_SHARE_DOORBELL_GUARDS
        CHECK(first_mmio_write_checks==ring_checks[VERIFY_SPAN]+1);
#else
        CHECK(first_mmio_write_checks==ring_checks[VERIFY_SPAN]+2);
#endif
    }
}
static void test_shared_guards(void)
{
    compare_issued(20,1,true,0);
    compare_issued(8180,3,true,3);
    compare_issued(8191,GGR_MAX_COMMANDS,true,0);
    compare_issued(8191,3,false,0);

    struct model m;struct ggr_context c;uint32_t fence;
    for(enum ring_step step=WRITE_SPAN;step<RING_STEPS;step++){
        for(enum ring_fault inject=CALLBACK_FAILURE;inject<=DEADLINE_EXPIRED;inject++){
            prepare(&m,&c,true,8191);fence=0xdeadbeef;
            fault=inject;fault_step=step;
            CHECK(issue_packet(&c,3,&fence)==GGR_IO&&fence==0xdeadbeef);
            CHECK(ring_checks[step]&&c.state==GGR_FAILED&&m.quarantines==1);
            for(unsigned later=step+1;later<RING_STEPS;later++)CHECK(!ring_checks[later]);
            CHECK(!c.submitted&&!c.completed&&!m.decoded_fence);no_doorbell();
        }
    }
    prepare(&m,&c,true,20);unsigned first=m.checks;
    CHECK(issue_packet(&c,3,&fence)==GGR_OK);
    unsigned boundaries=m.checks-first,first_write=first_mmio_write_checks-first;
#ifdef GGR_SHARE_DOORBELL_GUARDS
    CHECK(boundaries==12);
#else
    CHECK(boundaries==14);
#endif
    for(unsigned at=1;at<=boundaries;at++){
        prepare(&m,&c,true,20);m.fail_at=m.checks+at;fence=0xdeadbeef;
        CHECK(issue_packet(&c,3,&fence)==GGR_IO&&fence==0xdeadbeef);
        CHECK(m.quarantines==1&&c.state==GGR_FAILED&&!c.completed);
        if(at<=first_write)no_doorbell();
#ifdef GGR_SHARE_DOORBELL_GUARDS
        if(at==first_write+1) {
            CHECK(!c.submitted&&!m.decoded_fence);
            for(unsigned j=0;j<event_count;j++)
                if(events[j].kind==REG_WRITE)CHECK(events[j].reg==0x1f8c3&&events[j].value==1);
        }
#endif
        unsigned writes=m.writes;
        CHECK(issue_packet(&c,3,&fence)==GGR_UNAVAILABLE&&m.writes==writes&&m.quarantines==1);
    }
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
    prepare(&m,&c,true,8191);fault=DEADLINE_EXPIRED;fence=0xdeadbeef;
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
    test_shared_guards();
    printf("PASS: %u additional ring-span assertions; identical protocol; wrap, retry, deadline and failure checks; no IB/GPU emulation\n",cases-retained);
}
