#include "gauguin_scanout345.h"
#include <assert.h>

int main(void)
{
    struct scan345_geometry geometry = {462, 4910, 32, 2431, 0x39c0, 0x1124ff};
    assert(scan349_timing(&geometry));
    geometry.vtotal = 2455;
    assert(!scan349_timing(&geometry));
    assert(!scan349_line(2751) && scan349_line(2752));
    assert(scan349_line(4479) && !scan349_line(4480));

    struct scan349_read a = {1000, 1012, 2752, 0xfedcba98};
    struct scan349_read b = {24000, 24017, 4479, 0x12345678};
    uint32_t lines;
    uint64_t signatures, ticks;
    assert(scan349_pack(&a, &b, &lines, &signatures, &ticks));
    assert(lines == (2752 | (4479 << 13)));
    assert(signatures == UINT64_C(0xfedcba9812345678));
    assert(ticks == ((UINT64_C(23000) << 40) | (UINT64_C(12) << 20) | 17));
    assert(!scan349_pack(&b, &a, &lines, &signatures, &ticks));
    b.line = a.line;
    assert(!scan349_pack(&a, &b, &lines, &signatures, &ticks));
    b.line = 2800;
    b.start = a.end;
    assert(!scan349_pack(&a, &b, &lines, &signatures, &ticks));
    b.start = a.start + (UINT64_C(1) << 20);
    b.end = b.start + 1;
    assert(!scan349_pack(&a, &b, &lines, &signatures, &ticks));
}
