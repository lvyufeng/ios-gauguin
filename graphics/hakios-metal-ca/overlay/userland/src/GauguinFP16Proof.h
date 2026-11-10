/* SPDX-License-Identifier: MIT
 * Exact binary16 result of the root probe's dyadic test expressions. A matching
 * hash is a scoped probe receipt, not an Apple GPU-family certification.
 */
#ifndef GAUGUIN_FP16_PROOF_H
#define GAUGUIN_FP16_PROOF_H
#include <stdint.h>

static uint16_t gauguin_fp16_expected(unsigned x, unsigned channel, uint32_t seed)
{
    static const uint16_t colors[4][4] = {
        {0x3400, 0x3600, 0x3900, 0x3a00},
        {0x3600, 0x0000, 0x3600, 0x3a00},
        {0x0000, 0x3a00, 0x3000, 0x3a00},
        {0x3500, 0x3900, 0x3b00, 0x3a00},
    };
    return colors[((x / 16) + (seed & 3)) & 3][channel];
}

static uint64_t gauguin_fp16_expected_hash(uint32_t seed)
{
    uint64_t hash = UINT64_C(14695981039346656037);
    for (unsigned y = 0; y < 64; y++) for (unsigned x = 0; x < 64; x++) {
        for (unsigned channel = 0; channel < 4; channel++) {
            uint16_t value = gauguin_fp16_expected(x, channel, seed);
            hash = (hash ^ (uint8_t)value) * UINT64_C(1099511628211);
            hash = (hash ^ (uint8_t)(value >> 8)) * UINT64_C(1099511628211);
        }
    }
    return hash;
}
#endif
