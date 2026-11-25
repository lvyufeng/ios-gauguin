#include <assert.h>
#include <stdio.h>

#include "DisplayWriter401.h"

int main(void)
{
    struct display401_writer active = {0};
    const uint64_t ticket = UINT64_C(17)<<32 | 41;
    const uint64_t later = ticket + (UINT64_C(1)<<32);

    assert(!display401_publish(&active,7,41,4,ticket));
    assert(!display401_publish(&active,7,41,5,0));
    assert(display401_publish(&active,7,41,4,0));
    assert(!display401_publish(&active,8,41,8,0));
    assert(!display401_claim(&active,6,ticket,4));
    assert(!display401_claim(&active,7,ticket+1,4));
    assert(!display401_claim(&active,7,ticket,8));
    assert(display401_claim(&active,7,ticket,4));
    assert(!display401_claim(&active,7,later,4));

    assert(!display401_seal(&active,7,42,4));
    assert(!display401_seal(&active,7,41,8));
    assert(!display401_seal(&active,8,41,4));
    assert(display401_seal(&active,7,41,4)==ticket);
    assert(!display401_claim(&active,7,later,4));
    assert(!display401_seal(&active,7,41,4));

    assert(display401_publish(&active,8,41,8,0));
    assert(!display401_seal(&active,8,41,8));
    assert(!display401_claim(&active,8,later,8));
    assert(display401_publish(&active,9,41,12,0));
    assert(!display401_claim(&active,9,41,12));
    assert(display401_claim(&active,9,later,12));
    assert(display401_seal(&active,9,41,12)==later);
    puts("exact busy writer ticket and pre-issue ownership seal passed");
}
