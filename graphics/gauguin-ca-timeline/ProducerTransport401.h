#ifndef GAUGUIN_PRODUCER_TRANSPORT_401_H
#define GAUGUIN_PRODUCER_TRANSPORT_401_H

#include <stdint.h>

enum { GGR_DISPLAY_PRODUCER401 = 0x7d };

struct ggr_display_producer401 {
    uint64_t object;
    uint64_t created_tick;
    uint32_t surface;
    uint32_t cookie;
};

#ifdef __cplusplus
static_assert(sizeof(ggr_display_producer401) == 24, "display producer request");
#else
_Static_assert(sizeof(struct ggr_display_producer401) == 24, "display producer request");
#endif

#endif
