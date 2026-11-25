#include "gauguin_scanout345.h"
#include <assert.h>

int main(void)
{
    assert(scan345_branch_on(2));
    assert(scan345_branch_on(1));
    assert(!scan345_branch_on(UINT32_C(0x80000001)));
    // The GCC value observed on iOS and on the active recovery display.
    assert(scan345_gcc_ahb_accessible(UINT32_C(0x8000000b)));
    assert(!scan345_branch_on(UINT32_C(0x8000000b)));
    assert(!scan345_gcc_ahb_accessible(UINT32_C(0x80000001)));
    assert(!scan345_gcc_ahb_accessible(UINT32_C(0x80000002)));
    assert(!scan345_gcc_ahb_accessible(UINT32_MAX));
    assert(scan345_branch_on(UINT32_C(0x00000001)));
    assert(scan345_branch_on(UINT32_C(0x00000221)));

    const uint32_t htotal = 1182, skew = 501, first_line = 32;
    struct scan345_status status = {
        .hsync = htotal << 16 | 12,
        .period = htotal * 4910,
        .start = htotal * first_line + skew,
        .end = htotal * (first_line + 2400) + skew - 1
    };
    struct scan345_geometry active, drift;
    assert(scan345_timing(&status, &active));
    assert(active.htotal == htotal && active.vtotal == 4910);
    assert(active.first == first_line && active.last == first_line + 2399);
    assert(!scan345_crc_line(&active, first_line + 127));
    assert(scan345_crc_line(&active, first_line + 128));
    assert(scan345_crc_line(&active, first_line + 1535));
    assert(!scan345_crc_line(&active, first_line + 1536));
    status.start += 1;
    status.end += 1;
    assert(scan345_timing(&status, &drift));
    assert(!scan345_same_timing(&active, &drift));
    status.end += 1;
    assert(!scan345_timing(&status, &drift));
    status.end -= 1;
    status.period += 1;
    assert(!scan345_timing(&status, &drift));

    assert(scan345_edge_60(16598000, 1200000, 320, 4910));
    assert(!scan345_edge_60(8333000, 1200000, 320, 4910));
    assert(!scan345_edge_60(16598000, 3300000, 320, 4910));
    assert(!scan345_edge_60(16598000, 1200000, 2000, 4910));
    return 0;
}
