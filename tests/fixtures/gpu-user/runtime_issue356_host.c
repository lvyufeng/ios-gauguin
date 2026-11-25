/* Run the actual acknowledgement sequence against typed, in-memory callbacks. */
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include "gauguin_gpu_runtime.h"

struct fixture {
    uint32_t ring[8192];
    uint32_t wptr, shadow, eop, fence_off, busy_reads;
    unsigned guards, effects, writes, doorbells, delays, quarantines;
    unsigned fail_guard, poison_effect, expire_effect;
    uint64_t tick, transcript;
    bool poisoned, stopped;
};

static void effect(struct fixture *f, uint32_t kind, uint32_t address, uint32_t value)
{
    assert(!f->stopped);
    const uint32_t fields[] = {kind,address,value};
    for (unsigned i=0; i<sizeof(fields)/sizeof(*fields); ++i) {
        f->transcript ^= fields[i];
        f->transcript *= UINT64_C(1099511628211);
    }
    ++f->effects;
    if (f->effects==f->poison_effect) f->poisoned=true;
    if (f->effects==f->expire_effect) f->tick+=UINT64_C(2000000000);
}

static bool healthy(void *p)
{
    struct fixture *f=p;
    assert(!f->stopped);
    ++f->guards;
    return !f->poisoned && f->guards!=f->fail_guard;
}

static uint64_t nanos(void *p)
{
    struct fixture *f=p;
    return f->tick+=100;
}

static bool read_reg(void *p,uint32_t reg,uint32_t *value)
{
    struct fixture *f=p;
    switch (reg) {
    case 0x201: case 0x823: case 0x23b0c: *value=0; break;
    case 0x807: *value=f->wptr; break;
    case 0x23b13:
        assert(f->fence_off==1);
        *value=f->busy_reads!=0;
        if (f->busy_reads) --f->busy_reads;
        break;
    default: assert(false); return false;
    }
    effect(f,1,reg,*value);
    return true;
}

static bool write_reg(void *p,uint32_t reg,uint32_t value)
{
    struct fixture *f=p;
    assert(!f->poisoned && f->tick<UINT64_C(2000000000));
    ++f->writes;
    if (reg==0x1f8c3) {
        assert(value<=1);
        f->fence_off=value;
    } else {
        assert(reg==0x807 && f->fence_off==1);
        if (f->doorbells) assert(f->wptr==value);
        f->wptr=value;
        ++f->doorbells;
    }
    effect(f,2,reg,value);
    return true;
}

static bool memory(void *p,enum ggr_memory region,uint32_t offset,uint32_t *value)
{
    struct fixture *f=p;
    assert(!(offset&3));
    if (region==GGR_RING) *value=f->ring[offset/4];
    else {
        assert(!offset && (region==GGR_SHADOW || region==GGR_COMPLETION));
        *value=region==GGR_SHADOW?f->shadow:f->eop;
    }
    effect(f,3+region,offset,*value);
    return true;
}

static bool word(void *p,uint32_t offset,uint32_t value)
{
    struct fixture *f=p;
    assert(!f->poisoned && f->tick<UINT64_C(2000000000) && offset<32768 && !(offset&3));
    f->ring[offset/4]=value;
    effect(f,8,offset,value);
    return true;
}

static bool span(void *p,uint32_t offset,const uint32_t *values,uint32_t count,bool verify)
{
    struct fixture *f=p;
    assert(values && count && count<=GGR_RING_PACKET_WORDS && !(offset&3));
    for (uint32_t i=0; i<count; ++i) {
        uint32_t at=(offset+4*i)%32768;
        if (verify) assert(f->ring[at/4]==values[i]);
        else if (!word(p,at,values[i])) return false;
    }
    return true;
}

static bool barrier(void *p) {effect(p,9,0,0); return true;}
static bool delay(void *p,uint32_t value)
{
    struct fixture *f=p;
    assert(!f->poisoned && f->tick<UINT64_C(2000000000) && value==10);
    ++f->delays;
    effect(f,10,0,value);
    f->tick+=10000;
    return true;
}
static void quarantine(void *p)
{
    struct fixture *f=p;
    assert(!f->stopped);
    f->stopped=true;
    ++f->quarantines;
}

static void init(struct fixture *f,struct ggr_context *c,unsigned reissues)
{
    memset(f,0,sizeof(*f));
    memset(c,0,sizeof(*c));
    f->wptr=f->shadow=20;
    struct ggr_ops ops={.cookie=f,.healthy=healthy,.nanoseconds=nanos,.read_reg=read_reg,
        .write_reg=write_reg,.read_memory=memory,.write_ring=word,.barrier=barrier,.delay_us=delay,
        .quarantine=quarantine,.ring_span=span};
    assert(ggr_open(c,&ops,0xfc010000u,0xfc018000u)==GGR_OK);
    f->busy_reads=reissues;
    f->transcript=UINT64_C(14695981039346656037);
    f->guards=f->effects=0;
}

static enum ggr_error issue(struct ggr_context *c,uint32_t *fence)
{
    const uint64_t addr[]={GGR_VA_START};
    const uint32_t words[]={8};
    return ggr_issue(c,addr,words,1,fence);
}

static void failed_issue(struct fixture *f,struct ggr_context *c)
{
    uint32_t fence=0xdeadbeef;
    assert(issue(c,&fence)!=GGR_OK && fence==0xdeadbeef);
    assert(f->quarantines==1 && c->state==GGR_FAILED);
    unsigned before=f->effects;
    assert(issue(c,&fence)==GGR_UNAVAILABLE && f->effects==before);
}

int main(void)
{
    for (unsigned reissues=0; reissues<=2; reissues+=2) {
        struct fixture f;
        struct ggr_context c;
        init(&f,&c,reissues);
        uint32_t fence=0;
        assert(issue(&c,&fence)==GGR_OK && fence==1 && c.completed==0 && c.state==GGR_BUSY);
        assert(f.doorbells==1+reissues && f.delays==reissues && f.writes==3+reissues && !f.fence_off);
        const unsigned guards=f.guards, effects=f.effects;
        printf("%u %u %u %u %" PRIu64 "\n",reissues,guards,effects,f.writes,f.transcript);
        assert(issue(&c,&fence)==GGR_UNAVAILABLE && f.effects==effects);
        assert(ggr_poll(&c)==GGR_PENDING && c.completed==0);
        f.eop=1;
        f.shadow=f.wptr;
        assert(ggr_poll(&c)==GGR_OK && c.completed==1 && c.state==GGR_READY);
        for (unsigned i=1; i<=guards; ++i) {
            init(&f,&c,reissues);
            f.fail_guard=i;
            failed_issue(&f,&c);
        }
        /* Poison or expire each acknowledgement-side effect after the first
         * doorbell, including the final fence-off clear. */
        init(&f,&c,reissues);
        f.poison_effect=effects-1;
        failed_issue(&f,&c);
        for (unsigned i=effects-(3+4*reissues); i<=effects; ++i) {
            init(&f,&c,reissues);
            f.poison_effect=i;
            failed_issue(&f,&c);
            init(&f,&c,reissues);
            f.expire_effect=i;
            failed_issue(&f,&c);
        }
    }
    struct fixture f;
    struct ggr_context c;
    init(&f,&c,200);
    uint32_t fence=0;
    assert(issue(&c,&fence)==GGR_TIMEOUT && !fence && f.doorbells==201 && f.delays==200 && f.quarantines==1);
    return 0;
}
