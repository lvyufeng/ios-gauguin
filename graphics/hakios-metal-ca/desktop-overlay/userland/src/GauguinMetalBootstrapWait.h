/* Finite first-device wait before Metal can cache a nil device. MIT. */
#ifndef GAUGUIN_METAL_BOOTSTRAP_WAIT_H
#define GAUGUIN_METAL_BOOTSTRAP_WAIT_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define GAUGUIN_METAL_OPEN_BUDGET_NS UINT64_C(35000000000)
#define GAUGUIN_METAL_OPEN_STEP_NS UINT64_C(100000000)
#define GAUGUIN_METAL_OPEN_ATTEMPTS 351u
enum gauguin_metal_wait_reason { GMW_READY=0,GMW_TIMEOUT,GMW_CLOCK,GMW_SLEEP,GMW_ATTEMPTS,GMW_ARGUMENT };
struct gauguin_metal_wait_result { enum gauguin_metal_wait_reason reason;uint32_t attempts;uint64_t elapsed_ns; };
struct gauguin_metal_wait_ops {
    void *cookie;
    bool (*clock)(void *,uint64_t *);
    bool (*sleep)(void *,uint64_t);
    void *(*open)(void *);
    void (*close)(void *,void *);
};
static inline void *gauguin_metal_wait_open(const struct gauguin_metal_wait_ops *ops,
                                           struct gauguin_metal_wait_result *result)
{
    if(!result)return NULL;
    *result=(struct gauguin_metal_wait_result){GMW_ARGUMENT,0,0};
    if(!ops||!ops->clock||!ops->sleep||!ops->open||!ops->close)return NULL;
    uint64_t start=0,last=0,now=0;
    if(!ops->clock(ops->cookie,&start)){result->reason=GMW_CLOCK;return NULL;}
    last=start;
    for(unsigned n=0;n<GAUGUIN_METAL_OPEN_ATTEMPTS;n++) {
        if(!ops->clock(ops->cookie,&now)||now<last){result->reason=GMW_CLOCK;return NULL;}
        result->elapsed_ns=now-start;
        if(now-start>GAUGUIN_METAL_OPEN_BUDGET_NS){result->reason=GMW_TIMEOUT;return NULL;}
        result->attempts++;
        void *device=ops->open(ops->cookie);
        uint64_t end=0;
        if(!ops->clock(ops->cookie,&end)||end<now) {
            if(device)ops->close(ops->cookie,device);
            result->reason=GMW_CLOCK;return NULL;
        }
        result->elapsed_ns=end-start;last=end;
        if(result->elapsed_ns>GAUGUIN_METAL_OPEN_BUDGET_NS) {
            if(device)ops->close(ops->cookie,device);
            result->reason=GMW_TIMEOUT;return NULL;
        }
        if(device){result->reason=GMW_READY;return device;}
        if(result->elapsed_ns==GAUGUIN_METAL_OPEN_BUDGET_NS){result->reason=GMW_TIMEOUT;return NULL;}
        if(n+1==GAUGUIN_METAL_OPEN_ATTEMPTS){result->reason=GMW_ATTEMPTS;return NULL;}
        uint64_t left=GAUGUIN_METAL_OPEN_BUDGET_NS-result->elapsed_ns;
        uint64_t pause=left<GAUGUIN_METAL_OPEN_STEP_NS?left:GAUGUIN_METAL_OPEN_STEP_NS;
        if(!ops->sleep(ops->cookie,pause)){result->reason=GMW_SLEEP;return NULL;}
    }
    result->reason=GMW_ATTEMPTS;return NULL;
}
#endif
