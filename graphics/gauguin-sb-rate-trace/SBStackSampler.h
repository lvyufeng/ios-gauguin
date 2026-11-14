/* SPDX-License-Identifier: MIT
 * Bounded sampling of an already registered, same-process thread.
 * No allocation, formatting, Objective-C or symbol lookup inside the hold.
 */
#ifndef GAUGUIN_SB_STACK_SAMPLER_H
#define GAUGUIN_SB_STACK_SAMPLER_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#define SB_STACK_DEPTH 16u
#define SB_STACK_MAX_SAMPLES 64u
#define SB_STACK_START_US UINT64_C(220000000)
#define SB_STACK_END_US UINT64_C(270000000)
#define SB_STACK_PERIOD_US UINT64_C(1000000)
#define SB_STACK_MIN_TURN_US UINT64_C(250000)
#define SB_STACK_BUDGET_US UINT64_C(2000)
#define SB_STACK_WINDOW_BYTES UINT64_C(65536)
#define SB_STACK_NOT_CALLED INT32_MIN

enum sb_stack_stop {
    SB_STACK_SETUP=0, SB_STACK_SUSPEND_FAILED, SB_STACK_STALE_WATCH,
    SB_STACK_STATE_FAILED, SB_STACK_BAD_REGISTERS, SB_STACK_FRAME_END,
    SB_STACK_BAD_FRAME, SB_STACK_READ_FAILED, SB_STACK_DEPTH_LIMIT,
    SB_STACK_TIME_BUDGET, SB_STACK_CLOCK_REGRESSED
};
struct sb_stack_registers { uint64_t pc, lr, sp, fp; };
struct sb_stack_target { uintptr_t thread, sampler; uint64_t low, high; };
struct sb_stack_result {
    uint64_t requested_us, us, held_us, resumed_us, expected_watch, stopped_watch;
    struct sb_stack_registers registers;
    uint64_t frame_fp[SB_STACK_DEPTH], frame_lr[SB_STACK_DEPTH];
    int32_t suspend_result, state_result, read_result, resume_result;
    uint32_t stop, frames;
    bool registers_valid;
};
struct sb_stack_ops {
    uint64_t (*clock)(void *);
    uint64_t (*watch)(void *);
    int32_t (*suspend)(void *);
    int32_t (*state)(void *, struct sb_stack_registers *);
    int32_t (*read_frame)(void *, uint64_t, uint64_t *, uint64_t *);
    int32_t (*resume)(void *);
};
struct sb_stack_policy { uint64_t last_us; uint32_t attempts; bool disabled; };

static bool
sb_stack_due(const struct sb_stack_policy *policy, uint64_t now, uint64_t watch)
{
    unsigned phase=(unsigned)(watch&3);
    uint64_t began=watch>>2;
    return !policy->disabled && policy->attempts<SB_STACK_MAX_SAMPLES &&
        now>=SB_STACK_START_US && now<SB_STACK_END_US &&
        (phase==1 || phase==2) && began>0 && began<=now &&
        now-began>=SB_STACK_MIN_TURN_US &&
        (policy->attempts==0 || (now>=policy->last_us && now-policy->last_us>=SB_STACK_PERIOD_US));
}

static bool
sb_stack_target_valid(const struct sb_stack_target *target)
{
    return target->thread && target->sampler && target->thread!=target->sampler &&
        target->low>=4096 && target->high>target->low &&
        target->high-target->low>=16384 && target->high-target->low<=UINT64_C(134217728);
}

static bool
sb_stack_budget_expired(const struct sb_stack_ops *ops, void *context,
                        struct sb_stack_result *result)
{
    uint64_t now=ops->clock(context);
    if (now<result->us) { result->stop=SB_STACK_CLOCK_REGRESSED; return true; }
    if (now-result->us>=SB_STACK_BUDGET_US) { result->stop=SB_STACK_TIME_BUDGET; return true; }
    return false;
}

static void
sb_stack_capture(const struct sb_stack_ops *ops, void *context,
                 const struct sb_stack_target *target, uint64_t watch,
                 struct sb_stack_result *result)
{
    /* Touch/initialize result storage before suspension. */
    memset(result,0,sizeof(*result));
    result->suspend_result=result->state_result=result->read_result=result->resume_result=SB_STACK_NOT_CALLED;
    result->expected_watch=watch;
    result->stop=SB_STACK_SETUP;
    if (!ops || !context || !target || !sb_stack_target_valid(target) ||
        !ops->clock || !ops->watch || !ops->suspend || !ops->state || !ops->read_frame || !ops->resume) return;
    result->us=ops->clock(context);
    result->suspend_result=ops->suspend(context);
    if (result->suspend_result!=0) { result->stop=SB_STACK_SUSPEND_FAILED; return; }

    /* Every path from this point reaches exactly one resume attempt. */
    result->held_us=ops->clock(context);
    result->stopped_watch=ops->watch(context);
    if (result->stopped_watch!=watch) { result->stop=SB_STACK_STALE_WATCH; goto resume; }
    if (sb_stack_budget_expired(ops,context,result)) goto resume;
    result->state_result=ops->state(context,&result->registers);
    if (result->state_result!=0) { result->stop=SB_STACK_STATE_FAILED; goto resume; }
    uint64_t sp=result->registers.sp, fp=result->registers.fp;
    if (!result->registers.pc || (sp&15) || sp<target->low || sp>=target->high) {
        result->stop=SB_STACK_BAD_REGISTERS; goto resume;
    }
    result->registers_valid=true;
    uint64_t limit=target->high-sp>SB_STACK_WINDOW_BYTES ? sp+SB_STACK_WINDOW_BYTES : target->high;
    result->stop=SB_STACK_DEPTH_LIMIT;
    for (unsigned i=0;i<SB_STACK_DEPTH;++i) {
        if (sb_stack_budget_expired(ops,context,result)) break;
        if (!fp) { result->stop=SB_STACK_FRAME_END; break; }
        if ((fp&15) || fp<sp || limit-sp<16 || fp>limit-16) { result->stop=SB_STACK_BAD_FRAME; break; }
        uint64_t next=0, lr=0;
        result->read_result=ops->read_frame(context,fp,&next,&lr);
        if (result->read_result!=0) { result->stop=SB_STACK_READ_FAILED; break; }
        result->frame_fp[i]=fp; result->frame_lr[i]=lr; result->frames=i+1;
        if (!next) { result->stop=SB_STACK_FRAME_END; break; }
        if (next<=fp) { result->stop=SB_STACK_BAD_FRAME; break; }
        fp=next;
    }
resume:
    result->resume_result=ops->resume(context);
    result->resumed_us=ops->clock(context);
}

static bool
sb_stack_take(struct sb_stack_policy *policy, const struct sb_stack_ops *ops,
              void *context, const struct sb_stack_target *target,
              uint64_t now, uint64_t watch, struct sb_stack_result *result)
{
    if (!sb_stack_due(policy,now,watch)) return false;
    policy->last_us=now; ++policy->attempts;
    sb_stack_capture(ops,context,target,watch,result);
    result->requested_us=now;
    if (result->stop==SB_STACK_SETUP ||
        (result->suspend_result==0 && result->resume_result!=0)) policy->disabled=true;
    return true;
}
#endif
