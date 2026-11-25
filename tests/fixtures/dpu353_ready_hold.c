#include <assert.h>
#include "gauguin_ready353.h"

int main(void)
{
    struct scan353_ready ready = {0};
    struct scan351_slot slot = {0};
    struct scan351_position pos = {.tick=1000, .frame=82, .line=3500, .end=4878};
    uint64_t ticket = scan352_ticket(9, 7);
    assert(!scan353_can_take(&ready, &slot, &pos));
    assert(!scan353_mark(&ready, ticket, scan352_ticket(10, 7), 10, 10, 7, 82));
    assert(!scan353_mark(&ready, ticket, ticket, 9, 10, 7, 82));
    assert(!scan353_mark(&ready, ticket, ticket, 9, 9, 8, 82));
    assert(scan353_mark(&ready, ticket, ticket, 9, 9, 7, 82));
    assert(!scan353_mark(&ready, ticket, ticket, 9, 9, 7, 83));
    assert(!scan353_can_take(&ready, &slot, &pos));
    pos.frame++;
    pos.line = 2479;
    assert(!scan353_can_take(&ready, &slot, &pos));
    pos.line = 2480;
    assert(scan353_can_take(&ready, &slot, &pos));
    assert(scan353_carried(&ready, pos.frame));
    scan351_take(&slot, &pos);
    assert(!scan353_can_take(&ready, &slot, &pos));

    ready = (struct scan353_ready){0};  /* released or requeued without its readiness */
    assert(!scan353_can_take(&ready, &slot, &pos));
    assert(!scan353_mark(&ready, ticket, 0, 0, 9, 7, UINT64_MAX));
    assert(scan353_mark(&ready, ticket, ticket, 9, 9, 7, UINT64_MAX));
    assert(!scan353_carried(&ready, pos.frame));

    ready = (struct scan353_ready){0};
    assert(scan353_mark(&ready, ticket, ticket, 9, 9, 7, UINT32_MAX));
    pos.frame = 0;
    assert(scan353_can_take(&ready, &slot, &pos));
    assert(scan353_carried(&ready, pos.frame));
    return 0;
}
