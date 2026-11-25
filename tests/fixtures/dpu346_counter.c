#include "gauguin_scanout345.h"
#include <assert.h>

int main(void)
{
    const struct scan345_geometry missing = {0};
    const struct scan345_geometry active = {1182, 4910, 32, 2431, 37824, 2874623};
    struct scan345_geometry drift = active;
    ++drift.start;
    ++drift.end;
    struct scan345_status status = {0};

    assert(!scan345_counter_can_arm(&status, &active, &active));
    assert(!scan345_counter_readable(&status));
    status.enable = 1;
    assert(scan345_counter_readable(&status));
    assert(!scan345_counter_can_arm(&status, &missing, &active));
    assert(!scan345_counter_can_arm(&status, &active, &drift));
    assert(!scan345_counter_can_arm(&status, &missing, &missing));
    assert(scan345_counter_can_arm(&status, &active, &active));
    for (uint32_t claimed = 1; claimed <= 3; ++claimed) {
        status.count = claimed;
        assert(!scan345_counter_can_arm(&status, &active, &active));
        assert(scan345_counter_readable(&status) == (claimed == 3));
    }
    status.count = UINT32_C(0x80000000);
    assert(!scan345_counter_can_arm(&status, &active, &active));
    assert(!scan345_counter_readable(&status));
    return 0;
}
