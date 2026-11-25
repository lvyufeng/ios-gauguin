#ifndef GAUGUIN_COMPLETION_HINT_406_H
#define GAUGUIN_COMPLETION_HINT_406_H

#include "gauguin_probe358.h"
#include "gauguin_page_flip.h"

enum { SCAN406_STAGE_LINES = 960 };

static inline bool
scan406_probe_line(uint32_t line, uint32_t end)
{
    return line < end && end - line >= F382_CUTOFF_GUARD_LINES + SCAN406_STAGE_LINES;
}

/* The completion hint shares the original request slot and total quota.
 * A matching queued request can use the new deadline without another poll. */
static inline bool
scan406_offer(struct scan358_probe_slot *slot, uint32_t frame, uint64_t ticket, uint32_t fence)
{
    const uint32_t step = frame - slot->request.frame;
    if (!ticket || !fence || fence <= slot->last_raw_fence ||
        (slot->sent && step >= UINT32_C(0x80000000))) return false;

    if (slot->request.ticket && !step) {
        if (slot->request.ticket != ticket) return false;
        slot->request.raw_eop = true;
    } else {
        if (slot->sent >= SCAN358_PROBE_LIMIT) return false;
        slot->request.ticket = ticket;
        slot->request.frame = frame;
        slot->request.retried = false;
        slot->request.raw_eop = true;
        ++slot->sent;
    }
    slot->retry_ticket = 0;
    slot->last_raw_fence = fence;
    return true;
}

static inline bool
scan406_still_timely(const struct scan358_request *request, const struct scan351_position *position,
    const struct scan351_slot *blank)
{
    if (!request->raw_eop) return scan358_still_timely(request, position, blank);
    return request->ticket && position->frame == request->frame &&
        scan406_probe_line(position->line, position->end) &&
        (!blank->attempts || blank->frame != position->frame);
}

#ifdef __cplusplus
extern "C" {
#endif
bool sweet_fb406_request_raw_probe(uint32_t frame, uint64_t ticket, uint32_t fence);
#ifdef __cplusplus
}
#endif

#endif
