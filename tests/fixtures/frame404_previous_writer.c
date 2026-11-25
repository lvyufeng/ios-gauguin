#include <assert.h>

#include "DisplayWriter401.h"
#include "DisplayPrevious404.h"

int main(void)
{
    struct display401_writer writer = {0};
    uint64_t fresh = (UINT64_C(17)<<32) | 41;

    assert(display401_publish(&writer,5,41,4,0));
    assert(display404_previous_allowed(&writer,41,4));
    display404_previous_claimed(&writer,41,4);
    assert(!display401_claim(&writer,5,fresh,4));
    assert(!display401_seal(&writer,5,41,4));

    assert(display401_publish(&writer,6,41,8,0));
    assert(display401_claim(&writer,6,fresh,8));
    assert(!display404_previous_allowed(&writer,41,8));
    assert(display404_previous_allowed(&writer,41,4));
    assert(display404_previous_allowed(&writer,42,8));
    display404_previous_claimed(&writer,42,8);
    assert(display401_seal(&writer,6,41,8)==fresh);

    assert(display401_publish(&writer,7,41,12,0));
    assert(display404_previous_allowed(&writer,42,12));
    display404_previous_claimed(&writer,42,12);
    assert(display401_claim(&writer,7,fresh,12));
    /* The same exact certificate is returned on the native success or
     * error path. A failed submission uses the existing cancel function. */
    assert(display401_seal(&writer,7,41,12)==fresh);
    assert(display401_seal(&writer,7,41,12)==0);
}
