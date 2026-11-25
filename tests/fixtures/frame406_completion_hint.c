#include <assert.h>

#include "gauguin_completion_hint406.h"

int main(void)
{
    struct scan358_probe_slot slot = {0};
    const uint64_t first = (UINT64_C(41) << 32) | 3;
    const uint64_t second = first + (UINT64_C(1) << 32);
    assert(scan358_offer(&slot, 100, first));
    assert(!scan406_offer(&slot, 100, second, 41));
    assert(scan406_offer(&slot, 100, first, 40));
    assert(slot.sent == 1 && slot.request.raw_eop && !slot.retry_ticket);
    const struct scan358_request request = scan358_take(&slot);
    assert(!scan406_offer(&slot, 100, first, 40));
    assert(!scan358_allow_lock_retry(&slot, &request));
    assert(!scan358_offer(&slot, 100, first));
    assert(!scan406_offer(&slot, 99, second, 41));

    struct scan351_position position = {0};
    struct scan351_slot blank = {0};
    position.frame = 100;
    position.end = SCAN351_TOTAL - SCAN351_END_GUARD;
    position.line = position.end - F382_CUTOFF_GUARD_LINES - SCAN406_STAGE_LINES;
    assert(!scan358_still_timely(&request, &position, &blank));
    assert(scan406_still_timely(&request, &position, &blank));
    ++position.line;
    assert(!scan406_still_timely(&request, &position, &blank));
    position.line = 1300;
    assert(scan406_still_timely(&request, &position, &blank));
    blank.attempts = 1;
    blank.frame = 100;
    assert(!scan406_still_timely(&request, &position, &blank));
    blank.attempts = 0;
    ++position.frame;
    assert(!scan406_still_timely(&request, &position, &blank));

    assert(scan358_offer(&slot, 101, second));
    const struct scan358_request normal = scan358_take(&slot);
    assert(!normal.raw_eop && scan358_allow_lock_retry(&slot, &normal));
    assert(scan406_offer(&slot, 101, second, 41));
    assert(slot.sent == 3 && slot.request.raw_eop && !slot.retry_ticket);
    scan358_take(&slot);
    slot.sent = SCAN358_PROBE_LIMIT;
    assert(!scan406_offer(&slot, 102, second, 42));
    assert(!scan406_offer(&slot, 102, 0, 43));

    slot = (struct scan358_probe_slot){0};
    assert(scan406_offer(&slot, UINT32_MAX, first, 40));
    scan358_take(&slot);
    assert(scan406_offer(&slot, 0, second, 41));
    assert(!scan406_offer(&slot, UINT32_MAX, second, 42));
}
