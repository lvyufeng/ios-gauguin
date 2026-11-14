/* Actual collector and policy; explicit failure seams, no device operation. */
#include "SBStackSampler.h"
#include <assert.h>
#include <stdio.h>

static unsigned checks;
#define CHECK(x) do { ++checks; assert(x); } while(0)
struct fake {
    uint64_t now, watch, suspend_cost, state_cost, read_cost;
    uint64_t first_fp, next_override;
    unsigned clocks, regress_at, suspends, states, reads, resumes, length, fail_read;
    int32_t suspend_error, state_error, resume_error;
    bool paused, change_watch, override_next;
    struct sb_stack_registers registers;
};
static uint64_t clock_now(void *p) {
    struct fake *f=p; ++f->clocks;
    if (f->regress_at==f->clocks) f->now-=10000;
    uint64_t value=f->now; f->now+=10; return value;
}
static uint64_t watch_now(void *p) {struct fake *f=p; CHECK(f->paused); return f->watch;}
static int32_t suspend_target(void *p) {
    struct fake *f=p; CHECK(!f->paused); ++f->suspends; f->now+=f->suspend_cost;
    if (f->suspend_error) return f->suspend_error;
    f->paused=true; if(f->change_watch) ++f->watch; return 0;
}
static int32_t state_target(void *p,struct sb_stack_registers *out) {
    struct fake *f=p; CHECK(f->paused); ++f->states; f->now+=f->state_cost;
    if(f->state_error)return f->state_error;
    *out=f->registers; return 0;
}
static int32_t read_target(void *p,uint64_t address,uint64_t *next,uint64_t *lr) {
    struct fake *f=p; CHECK(f->paused); ++f->reads; f->now+=f->read_cost;
    CHECK(address>=f->registers.sp && address+16<=f->registers.sp+SB_STACK_WINDOW_BYTES);
    if(f->reads==f->fail_read)return 7;
    *next=f->override_next?f->next_override:(f->reads>=f->length?0:address+16);
    *lr=UINT64_C(0x180001000)+4*(f->reads-1); return 0;
}
static int32_t resume_target(void *p) {
    struct fake *f=p; CHECK(f->paused); ++f->resumes;
    if(!f->resume_error)f->paused=false; return f->resume_error;
}
static const struct sb_stack_ops ops={clock_now,watch_now,suspend_target,state_target,read_target,resume_target};
static struct sb_stack_target target={1,2,0x8000,0x28000};
static struct fake fresh(void) {
    struct fake f={0}; f.now=SB_STACK_START_US; f.watch=((f.now-1000000)<<2)|2;
    f.registers=(struct sb_stack_registers){0x180001000,0x180002000,0x10000,0x10020};
    f.first_fp=f.registers.fp; f.length=3; return f;
}
static struct sb_stack_result capture(struct fake *f) {
    struct sb_stack_result r; sb_stack_capture(&ops,f,&target,f->watch,&r);
    CHECK(f->suspends==1 && f->resumes==(unsigned)(f->suspend_error==0));
    if(!f->suspend_error && !f->resume_error)CHECK(!f->paused);
    return r;
}
int main(void) {
    struct fake f=fresh(); struct sb_stack_result r=capture(&f);
    CHECK(r.frames==3 && r.stop==SB_STACK_FRAME_END && r.registers_valid);
    CHECK(r.suspend_result==0 && r.state_result==0 && r.read_result==0 && r.resume_result==0);
    CHECK(r.frame_fp[0]==0x10020 && r.frame_lr[2]==0x180001008);
    CHECK(r.resumed_us>=r.held_us && r.held_us>=r.us);

    f=fresh(); f.suspend_error=5; r=capture(&f);
    CHECK(r.stop==SB_STACK_SUSPEND_FAILED && f.states==0 && f.reads==0 && r.resume_result==SB_STACK_NOT_CALLED);
    f=fresh(); f.state_error=6; r=capture(&f);
    CHECK(r.stop==SB_STACK_STATE_FAILED && !r.registers_valid && f.reads==0);
    f=fresh(); f.change_watch=true; r=capture(&f);
    CHECK(r.stop==SB_STACK_STALE_WATCH && f.states==0 && f.reads==0);
    for(unsigned failure=1;failure<=3;++failure) {
        f=fresh(); f.fail_read=failure; r=capture(&f);
        CHECK(r.stop==SB_STACK_READ_FAILED && r.frames==failure-1 && f.reads==failure);
    }
    f=fresh(); f.length=100; r=capture(&f); CHECK(r.frames==SB_STACK_DEPTH && f.reads==SB_STACK_DEPTH && r.stop==SB_STACK_DEPTH_LIMIT);
    uint64_t bad_sp[]={0,0x10001,0x7ff0,0x28000,UINT64_MAX};
    for(unsigned i=0;i<sizeof(bad_sp)/sizeof(*bad_sp);++i) {
        f=fresh(); f.registers.sp=bad_sp[i]; r=capture(&f); CHECK(r.stop==SB_STACK_BAD_REGISTERS && f.reads==0);
    }
    f=fresh(); f.registers.pc=0; r=capture(&f); CHECK(r.stop==SB_STACK_BAD_REGISTERS && f.reads==0);
    f=fresh(); f.registers.fp=0; r=capture(&f); CHECK(r.stop==SB_STACK_FRAME_END && r.frames==0 && r.registers_valid);
    uint64_t bad_fp[]={0x10001,0xfff0,0x20000,0x28000,UINT64_MAX};
    for(unsigned i=0;i<sizeof(bad_fp)/sizeof(*bad_fp);++i) {
        f=fresh(); f.registers.fp=bad_fp[i]; r=capture(&f); CHECK(r.stop==SB_STACK_BAD_FRAME && f.reads==0);
    }
    f=fresh(); f.override_next=true; f.next_override=f.registers.fp; r=capture(&f);
    CHECK(r.stop==SB_STACK_BAD_FRAME && r.frames==1 && f.reads==1);
    f=fresh(); f.override_next=true; f.next_override=UINT64_MAX; r=capture(&f);
    CHECK(r.stop==SB_STACK_BAD_FRAME && r.frames==1 && f.reads==1);
    f=fresh(); f.suspend_cost=2000; r=capture(&f); CHECK(r.stop==SB_STACK_TIME_BUDGET && f.states==0);
    f=fresh(); f.state_cost=2000; r=capture(&f); CHECK(r.stop==SB_STACK_TIME_BUDGET && f.reads==0);
    f=fresh(); f.read_cost=2000; r=capture(&f); CHECK(r.stop==SB_STACK_TIME_BUDGET && r.frames==1);
    f=fresh(); f.regress_at=2; r=capture(&f); CHECK(r.stop==SB_STACK_CLOCK_REGRESSED && f.states==0);

    struct sb_stack_target invalid[]={ {0,2,0x8000,0x28000},{1,1,0x8000,0x28000},
        {1,0,0x8000,0x28000},{1,2,0,0x28000},{1,2,0x8000,0x8000},{1,2,0x8000,0x9000},
        {1,2,0x8000,UINT64_MAX} };
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);++i) {
        f=fresh(); sb_stack_capture(&ops,&f,&invalid[i],f.watch,&r);
        CHECK(r.stop==SB_STACK_SETUP && f.suspends==0 && f.resumes==0);
    }
    struct sb_stack_ops bad_ops=ops; bad_ops.read_frame=NULL;
    f=fresh(); sb_stack_capture(&bad_ops,&f,&target,f.watch,&r); CHECK(f.suspends==0);

    struct sb_stack_policy policy={0}; f=fresh();
    CHECK(sb_stack_due(&policy,f.now,f.watch));
    CHECK(!sb_stack_due(&policy,SB_STACK_START_US-1,f.watch));
    CHECK(!sb_stack_due(&policy,SB_STACK_END_US,f.watch));
    CHECK(!sb_stack_due(&policy,f.now,(f.now<<2)|1));
    CHECK(!sb_stack_due(&policy,f.now,((f.now+1)<<2)|1));
    CHECK(!sb_stack_due(&policy,f.now,0));
    CHECK(!sb_stack_due(&policy,f.now,((f.now-1000000)<<2)|0));
    CHECK(!sb_stack_due(&policy,f.now,((f.now-1000000)<<2)|3));
    policy.attempts=1;policy.last_us=f.now;
    CHECK(!sb_stack_due(&policy,f.now+SB_STACK_PERIOD_US-1,f.watch));
    CHECK(sb_stack_due(&policy,f.now+SB_STACK_PERIOD_US,f.watch));
    CHECK(!sb_stack_due(&policy,f.now-1,f.watch));
    policy.attempts=SB_STACK_MAX_SAMPLES; CHECK(!sb_stack_due(&policy,f.now+SB_STACK_PERIOD_US,f.watch));
    policy=(struct sb_stack_policy){0}; policy.disabled=true; CHECK(!sb_stack_due(&policy,f.now,f.watch));
    policy=(struct sb_stack_policy){0}; f=fresh(); f.resume_error=5;
    uint64_t requested=f.now;
    CHECK(sb_stack_take(&policy,&ops,&f,&target,requested,f.watch,&r));
    CHECK(policy.disabled && policy.attempts==1 && f.resumes==1 && r.resume_result==5 && r.requested_us==requested);
    CHECK(!sb_stack_take(&policy,&ops,&f,&target,requested+SB_STACK_PERIOD_US,f.watch,&r));
    CHECK(f.suspends==1 && f.resumes==1);
    printf("PASS bounded stack collector checks=%u; balanced resume, failure paths, stack bounds and cadence\n",checks);
    return 0;
}
