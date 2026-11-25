/* SPDX-License-Identifier: MIT */
#ifndef GAUGUIN_SB_CALLBACK_WATCH_H
#define GAUGUIN_SB_CALLBACK_WATCH_H

#include "SBStackSampler.h"

#define SB_CALLBACK_POLL_US UINT64_C(20000)
#define SB_CALLBACK_MIN_US UINT64_C(35000)
#define SB_CALLBACK_MAX_SAMPLES 8u
#define SB_CALLBACK_MAX_ROWS 8192u

static inline bool sb_callback_window(uint64_t now)
{
    return now>=SB_STACK_START_US && now<SB_STACK_END_US;
}

static inline uint64_t sb_callback_watch(uint64_t ident, uint64_t start)
{
    if (!ident || ident>UINT32_MAX || !sb_callback_window(start)) return 0;
    return (ident<<32)|start;
}

static inline bool sb_callback_take(struct sb_stack_policy *policy, uint32_t *last_ident,
                                   const struct sb_stack_ops *ops, void *context,
                                   const struct sb_stack_target *target, uint64_t now, uint64_t watch,
                                   struct sb_stack_result *result)
{
    const uint32_t ident=(uint32_t)(watch>>32), start=(uint32_t)watch;
    if (policy->disabled || policy->attempts>=SB_CALLBACK_MAX_SAMPLES || ident<=*last_ident ||
        !sb_callback_window(now) || !sb_callback_window(start) || now<start ||
        now-start<SB_CALLBACK_MIN_US ||
        (policy->attempts && (now<policy->last_us || now-policy->last_us<SB_CALLBACK_POLL_US))) return false;
    *last_ident=ident;
    sb_stack_attempt(policy,ops,context,target,now,watch,result);
    return true;
}
#endif
