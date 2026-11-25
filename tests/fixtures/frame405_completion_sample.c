#include <assert.h>
#include <stdint.h>

#include "CompletionSample405.h"

int main(void)
{
    const uint64_t ticket = (UINT64_C(44) << 32) | 3;
    const uint64_t next = ticket + (UINT64_C(1) << 32);
    struct eop405_bracket out = {0};
    struct eop405_state state = {0};

    assert(!eop405_observe(&state,0,11,10,100,104,&out));
    assert(!eop405_observe(&state,ticket,0,0,100,104,&out));
    assert(!eop405_observe(&state,ticket,11,12,100,104,&out));
    assert(eop405_observe(&state,ticket,11,10,100,104,&out));
    assert(out.earliest_tick == 100 && out.latest_tick == 0);
    assert(!eop405_observe(&state,ticket,12,12,105,106,&out));
    assert(!eop405_observe(&state,ticket,11,11,103,106,&out));
    assert(eop405_observe(&state,ticket,11,11,110,113,&out));
    assert(out.earliest_tick == 100 && out.latest_tick == 113);
    assert(!eop405_observe(&state,ticket,11,11,114,118,&out));

    assert(!eop405_observe(&state,next,12,10,120,122,&out));
    assert(eop405_observe(&state,next,12,12,128,130,&out));
    assert(out.earliest_tick == 0 && out.latest_tick == 130);
    assert(!eop405_observe(&state,ticket,11,11,134,135,&out));

    assert(eop405_observe(&state,next+1,13,12,140,142,&out));
    assert(eop405_observe(&state,next+1,13,12,145,146,&out));
    assert(out.earliest_tick == 145 && out.latest_tick == 0);
    assert(eop405_observe(&state,next+1,13,13,152,154,&out));
    assert(out.earliest_tick == 145 && out.latest_tick == 154);
}
