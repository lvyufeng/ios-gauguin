#include "gauguin_blank351.h"
#include <assert.h>

int main(void)
{
    const uint32_t limit = scan351_end(0,0,462);
    assert(limit == 4878);
    assert(scan351_end(0x80000000u,462u*4760+1,462)==4728);
    assert(scan351_end(0x80000000u,0,462)==0);
    assert(!scan351_can_copy(2431,limit));
    assert(scan351_can_copy(2480,limit));
    assert(scan351_can_copy(2878,limit));
    assert(!scan351_can_copy(2879,limit));
    assert(!scan351_can_copy(2480,4400)); /* prefetch removes the budget */

    struct scan351_slot slot = {0};
    struct scan351_position pos = {100,UINT32_MAX,2320,limit};
    assert(!scan351_can_take(&slot,&pos) && scan351_delay_lines(&slot,&pos)==160);
    pos.line = 2480;
    assert(scan351_can_take(&slot,&pos) && scan351_delay_lines(&slot,&pos)==0);
    scan351_take(&slot,&pos);
    assert(slot.attempts==1 && slot.attempted_at==100);
    pos.tick = 110;
    assert(scan351_can_take(&slot,&pos));
    scan351_take(&slot,&pos);
    assert(!scan351_can_take(&slot,&pos) && scan351_delay_lines(&slot,&pos)==4910);
    pos.frame = 0;
    assert(scan351_can_take(&slot,&pos));
    scan351_take(&slot,&pos);
    assert(slot.attempts==1);
    slot.done = true;
    assert(!scan351_can_take(&slot,&pos));
}
