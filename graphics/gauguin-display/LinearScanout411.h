#ifndef GAUGUIN_LINEAR_SCANOUT_411_H
#define GAUGUIN_LINEAR_SCANOUT_411_H

#include <stdbool.h>
#include <stdint.h>

enum {
    F411_RENDER_WIDTH = 1125,
    F411_RENDER_HEIGHT = 2436,
    F411_RENDER_PITCH = 4608,
    F411_PANEL_WIDTH = 1080,
    F411_PANEL_HEIGHT = 2400,
    F411_PANEL_PITCH = 4320,
    F411_CROP_X = 22,
    F411_CROP_Y = 18,
    F411_SOURCE_XY = (F411_CROP_Y << 16) | F411_CROP_X,
    F411_VIEW_OFFSET = F411_CROP_Y * F411_RENDER_PITCH + F411_CROP_X * 4,
    F411_PAGE_BYTES = 0x4000,
    F411_SLOT_BYTES = 0xab8000
};

static inline bool
f411_managed_extent(uint64_t base, uint64_t contiguous)
{
    return base && !(base & (F411_PAGE_BYTES - 1)) && contiguous >= F411_SLOT_BYTES &&
        base <= UINT64_C(0x100000000) - F411_SLOT_BYTES &&
        (base >= UINT64_C(0xa2400000) || base <= UINT64_C(0xa0000000) - F411_SLOT_BYTES);
}

static inline bool
f411_disjoint(uint64_t first, uint64_t second)
{
    return first <= second ? second - first >= F411_SLOT_BYTES : first - second >= F411_SLOT_BYTES;
}

static inline uint32_t
f411_pitch(bool padded, unsigned slot)
{
    return padded && slot ? F411_RENDER_PITCH : F411_PANEL_PITCH;
}

static inline uint32_t
f411_source_xy(bool padded, unsigned slot)
{
    return padded && slot ? F411_SOURCE_XY : 0;
}

#endif
