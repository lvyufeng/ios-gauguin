#include "gauguin_ui_trace.h"

#define GUT_CLOSED (UINT64_C(1)<<63)

static uint32_t state(const struct gut_core *c)
{return c?__atomic_load_n(&c->state,__ATOMIC_ACQUIRE):GUT_OFF;}
bool gut_enabled(const struct gut_core *c)
{
    uint32_t s=state(c);
    return (s==GUT_ARMED||s==GUT_CAPTURE)&&
        !(__atomic_load_n(&c->gate,__ATOMIC_ACQUIRE)&GUT_CLOSED);
}
/* Control/report metadata alone is serialized. Ordinary record writers never
 * take this lock, and live polling never takes it before the deadline. */
static bool enter(struct gut_core *c,bool producer)
{
    if(__atomic_exchange_n(&c->busy,1,__ATOMIC_ACQUIRE)) {
        if(producer)__atomic_fetch_add(&c->lost,UINT64_C(1),__ATOMIC_RELAXED);
        return false;
    }
    return true;
}
static void leave(struct gut_core *c)
{__atomic_store_n(&c->busy,0,__ATOMIC_RELEASE);}
static void close_capture(struct gut_core *c,uint32_t reason)
{
    __atomic_fetch_or(&c->close_flags,1u<<reason,__ATOMIC_ACQ_REL);
    uint32_t expected=0;
    (void)__atomic_compare_exchange_n(&c->close_reason,&expected,reason,false,
        __ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);
    __atomic_fetch_or(&c->gate,GUT_CLOSED,__ATOMIC_ACQ_REL);
}
static bool in_window(struct gut_core *c,uint64_t now)
{
    uint32_t stop=__atomic_load_n(&c->stop,__ATOMIC_ACQUIRE);
    if(stop)close_capture(c,stop);
    else if(now<c->start)close_capture(c,GUT_CLOCK);
    else if(now>=c->end)close_capture(c,GUT_DEADLINE);
    else return true;
    return false;
}
static uint64_t append(struct gut_core *c,uint32_t kind,uint64_t id,
    uint32_t pid,uint32_t flags,uint64_t a,uint64_t b,uint64_t d)
{
    /* Admission and closure share one atomic word. Every writer admitted
     * before closure publishes its private slot before dropping its reference.
     * Post-close attempts touch no payload. The consumer never waits for an
     * interrupted writer and can retry on its next existing logger tick. */
    uint64_t admission=__atomic_fetch_add(&c->gate,UINT64_C(1),__ATOMIC_ACQ_REL);
    uint64_t seq=0;
    if(!(admission&GUT_CLOSED)) {
        uint64_t now=c->clock(c->cookie);
        if(in_window(c,now)) {
            uint32_t slot=__atomic_fetch_add(&c->reserved,1,__ATOMIC_RELAXED);
            if(slot<c->capacity) {
                seq=(uint64_t)slot+1;
                if(kind==GUT_REPORT)id=seq;
                c->events[slot]=(struct gut_event){seq,now,id,kind,pid,flags,0,a,b,d};
                if(slot+1==c->capacity)close_capture(c,GUT_CAPACITY);
            } else close_capture(c,GUT_CAPACITY);
        }
    }
    __atomic_fetch_sub(&c->gate,UINT64_C(1),__ATOMIC_RELEASE);
    return seq;
}
bool gut_init(struct gut_core *c,struct gut_event *events,uint32_t capacity,uint32_t which,
    uint64_t window,uint64_t (*clock)(void *),void *cookie)
{
    if(!c)return false;
    uint32_t expected=0;
    if(!__atomic_compare_exchange_n(&c->initialized,&expected,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return false;
    if(!events||!capacity||capacity>4096||!which||which>16||!window||!clock)return false;
    c->events=events;c->capacity=capacity;c->which=which;c->window=window;
    c->clock=clock;c->cookie=cookie;
    __atomic_store_n(&c->state,GUT_ARMED,__ATOMIC_RELEASE);return true;
}
uint64_t gut_report(struct gut_core *c,uint64_t begin,uint64_t end,uint32_t status,uint32_t mask)
{
    if(!gut_enabled(c)||!enter(c,true))return 0;
    if(!gut_enabled(c)){leave(c);return 0;}
    uint64_t now=c->clock(c->cookie),id=0;
    bool valid=!status&&mask<1024&&begin&&begin<=end&&end<=now;
    if(valid) {
        bool down=!c->mask&&mask;c->mask=mask;
        if(state(c)==GUT_ARMED&&down&&++c->gestures==c->which) {
            c->start=now;
            if(now>UINT64_MAX-c->window)close_capture(c,GUT_CLOCK);
            else {c->end=now+c->window;__atomic_store_n(&c->state,GUT_CAPTURE,__ATOMIC_RELEASE);}
        }
    }
    if(!valid&&!status)status=UINT32_MAX;
    if(state(c)==GUT_CAPTURE)id=append(c,GUT_REPORT,0,0,status,begin,end,mask);
    leave(c);return id;
}
void gut_record(struct gut_core *c,uint32_t kind,uint64_t id,uint32_t pid,uint32_t flags,
    uint64_t a,uint64_t b,uint64_t d)
{
    if(state(c)!=GUT_CAPTURE)return;
    (void)append(c,kind,id,pid,flags,a,b,d);
}
void gut_stop(struct gut_core *c,uint32_t reason)
{
    if(!gut_enabled(c)||reason<GUT_DEADLINE||reason>GUT_GPU_STOP)return;
    uint32_t expected=0;
    (void)__atomic_compare_exchange_n(&c->stop,&expected,reason,false,__ATOMIC_RELEASE,__ATOMIC_RELAXED);
}
bool gut_read(struct gut_core *c,struct gut_event *out,uint32_t capacity,uint32_t *count,struct gut_meta *meta)
{
    if(!c||!out||!capacity||!count||!meta)return false;
    uint32_t s=state(c);
    uint64_t poll_tick=0;bool checked_clock=false;
    if(s==GUT_OFF)return false;
    /* No producer lock acquisition merely to discover a live capture. */
    if(s==GUT_ARMED&&!__atomic_load_n(&c->stop,__ATOMIC_ACQUIRE)&&
        !(__atomic_load_n(&c->gate,__ATOMIC_ACQUIRE)&GUT_CLOSED))return false;
    if(s==GUT_CAPTURE&&!__atomic_load_n(&c->stop,__ATOMIC_ACQUIRE)&&
        !(__atomic_load_n(&c->gate,__ATOMIC_ACQUIRE)&GUT_CLOSED)) {
        poll_tick=c->clock(c->cookie);checked_clock=true;
        if(poll_tick>=c->start&&poll_tick<c->end)return false;
    }
    if(!enter(c,false))return false;
    s=state(c);
    if(s<GUT_FROZEN) {
        uint32_t stop=__atomic_load_n(&c->stop,__ATOMIC_ACQUIRE);
        if(stop)close_capture(c,stop);
        else if(s==GUT_CAPTURE)(void)in_window(c,checked_clock?poll_tick:c->clock(c->cookie));
        if(__atomic_load_n(&c->gate,__ATOMIC_ACQUIRE)!=GUT_CLOSED){leave(c);return false;}
        /* All pre-close slot writes happen before this acquire. No payload is
         * read until the admitted writer count reaches zero. */
        c->count=__atomic_load_n(&c->reserved,__ATOMIC_RELAXED);
        if(c->count>c->capacity)c->count=c->capacity;
        c->lost_final=__atomic_fetch_or(&c->lost,GUT_CLOSED,__ATOMIC_ACQ_REL)&~GUT_CLOSED;
        c->reason=__atomic_load_n(&c->close_reason,__ATOMIC_ACQUIRE);
        /* A pre-close writer can discover a clock fault or exhaust capacity
         * after another thread closed at the deadline. Never let the first
         * close reason mask evidence that makes the prefix unqualified. */
        uint32_t flags=__atomic_load_n(&c->close_flags,__ATOMIC_ACQUIRE);
        if(flags&(1u<<GUT_CLOCK))c->reason=GUT_CLOCK;
        else if(flags&(1u<<GUT_CAPACITY))c->reason=GUT_CAPACITY;
        __atomic_store_n(&c->state,GUT_FROZEN,__ATOMIC_RELEASE);
    }
    uint32_t n=c->count-c->cursor;if(n>capacity)n=capacity;
    for(uint32_t i=0;i<n;i++)out[i]=c->events[c->cursor+i];
    c->cursor+=n;
    if(c->cursor==c->count)__atomic_store_n(&c->state,GUT_DRAINED,__ATOMIC_RELEASE);
    *count=n;*meta=(struct gut_meta){c->start,c->end,c->lost_final,
        state(c),c->reason,c->count,c->cursor,c->which,c->gestures};
    leave(c);return true;
}
