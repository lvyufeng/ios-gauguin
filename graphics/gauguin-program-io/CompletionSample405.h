#ifndef GAUGUIN_COMPLETION_SAMPLE_405_H
#define GAUGUIN_COMPLETION_SAMPLE_405_H

#include <stdbool.h>
#include <stdint.h>

struct eop405_state {
    uint64_t ticket, last_pending_begin, last_read_end;
    uint32_t fence;
    bool reported;
};

struct eop405_bracket {
    uint64_t earliest_tick, latest_tick;
};

/* The word is a GPU end-of-pipe observation only. The caller must have
 * checked the same issued token and permanent mapping on both sides. */
static inline bool
eop405_observe(struct eop405_state *s, uint64_t ticket, uint32_t fence,
    uint32_t observed, uint64_t begin, uint64_t end, struct eop405_bracket *out)
{
    if (!(ticket>>32) || !(uint32_t)ticket || !fence || !begin || end < begin ||
        (observed != fence && observed != fence - 1u)) return false;
    if (ticket != s->ticket) {
        if (fence <= s->fence) return false;
        *s = (struct eop405_state){ticket, 0, 0, fence, false};
    }
    if (fence != s->fence || begin < s->last_read_end || s->reported) return false;
    s->last_read_end = end;
    if (observed != fence) {
        s->last_pending_begin = begin;
        // Keep the lower bound even when guarded completion clears the
        // issued token before the first matching raw sample.
        *out = (struct eop405_bracket){begin, 0};
        return true;
    }
    // A pending load occurred somewhere in its interval. Its begin is
    // the conservative lower bound, even if EOP changed before its end.
    *out = (struct eop405_bracket){s->last_pending_begin, end};
    s->reported = true;
    return true;
}

#endif
