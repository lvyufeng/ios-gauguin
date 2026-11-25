/* Root-to-compositor readiness, protected by the driver's existing GPU lock. MIT. */
#ifndef GAUGUIN_METAL_BOOTSTRAP_H
#define GAUGUIN_METAL_BOOTSTRAP_H
#include <stdint.h>
#include <stdbool.h>
#define GGR_BOOTSTRAP_SELECTOR 0x7cu
#define GGR_BOOTSTRAP_VERSION 1u
#define GGR_BOOTSTRAP_MIN_JOBS 8u
#define GGR_BOOTSTRAP_MAX_JOBS 64u
struct ggr_bootstrap {
    uint32_t version, checks, fence, reserved;
    uint64_t epoch;
};
struct ggr_bootstrap_state {
    uint64_t epoch;
    uint32_t jobs, fence;
    bool armed, ready, failed;
};
static inline void ggr_bootstrap_fail(struct ggr_bootstrap_state *s)
{ s->ready=false; s->armed=false; s->failed=true; }
static inline bool ggr_bootstrap_begin(struct ggr_bootstrap_state *s)
{
    if(s->epoch==UINT64_MAX){ggr_bootstrap_fail(s);return false;}
    s->epoch++;s->jobs=s->fence=0;s->armed=s->ready=s->failed=false;return true;
}
static inline bool ggr_bootstrap_arm(struct ggr_bootstrap_state *s,uint32_t jobs,uint32_t fence)
{
    if(s->armed){ggr_bootstrap_fail(s);return false;}
    if(!s->epoch||s->failed||s->ready||jobs<GGR_BOOTSTRAP_MIN_JOBS||
       jobs>GGR_BOOTSTRAP_MAX_JOBS||!fence)return false;
    s->jobs=jobs;s->fence=fence;s->armed=true;return true;
}
static inline void ggr_bootstrap_close(struct ggr_bootstrap_state *s,bool clean,uint32_t jobs,uint32_t fence)
{
    s->ready=clean&&s->armed&&!s->failed&&s->epoch&&jobs==s->jobs&&fence==s->fence;
    s->armed=false;
    if(!clean)s->failed=true;
}
#if defined(__cplusplus)
static_assert(sizeof(ggr_bootstrap)==24,"root readiness wire size");
#else
_Static_assert(sizeof(struct ggr_bootstrap)==24,"root readiness wire size");
#endif
#endif
