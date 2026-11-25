#include "gauguin_scanout345.h"
#include <assert.h>

int main(void)
{
    const uint32_t idle = UINT32_C(0x01000000);
    assert(scan350_idle_pair(idle,idle,1));
    assert(scan350_idle_pair(idle,idle,(uint32_t)0-UINT32_MAX));
    assert(!scan350_idle_pair(0,idle,1));
    assert(!scan350_idle_pair(idle,0,1));
    assert(!scan350_idle_pair(idle,idle,0));
    assert(!scan350_idle_pair(idle,idle,2));
    const uint32_t active_or_busy[] = {
        UINT32_C(0x01000001),UINT32_C(0x01000100),UINT32_C(0x01000200),
        UINT32_C(0x01000400),UINT32_C(0x81000000)
    };
    for (unsigned i = 0; i < sizeof(active_or_busy)/sizeof(active_or_busy[0]); ++i) {
        assert(!scan350_idle_pair(active_or_busy[i],active_or_busy[i],1));
        assert(!scan350_idle_pair(idle,active_or_busy[i],1));
    }
}
