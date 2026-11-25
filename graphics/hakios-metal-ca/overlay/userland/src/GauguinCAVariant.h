/* SPDX-License-Identifier: MIT
 * Identity of one image-owned, pre-specialized CA function. No approximate
 * precision or stage matching; pointers borrow the immutable library bytes.
 */
#ifndef GAUGUIN_CA_VARIANT_H
#define GAUGUIN_CA_VARIANT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct gauguin_ca_variant {
    const char *name;
    unsigned type; /* MTLB: 0 vertex, 1 fragment. */
    const void *module;
    size_t module_size;
};

static uint64_t gauguin_ca_le(const uint8_t *p, size_t n)
{
    uint64_t value = 0;
    for (size_t i = 0; i < n; i++) value |= (uint64_t)p[i] << (8 * i);
    return value;
}

static bool gauguin_ca_variant_read(const void *bytes, size_t size,
                                   struct gauguin_ca_variant *result)
{
    const uint8_t *b = bytes;
    if (b == NULL || result == NULL || size < 88 || memcmp(b, "MTLB", 4) ||
        gauguin_ca_le(b + 16, 8) != size) return false;
    uint64_t list = gauguin_ca_le(b + 24, 8), section = gauguin_ca_le(b + 72, 8);
    uint64_t section_size = gauguin_ca_le(b + 80, 8);
    if (list < 88 || list > size - 8 || section > size || section_size > size - section ||
        gauguin_ca_le(b + list, 4) != 1) return false;
    uint64_t entry = gauguin_ca_le(b + list + 4, 4);
    if (entry < 8 || entry > size - list - 4 || gauguin_ca_le(b + 32, 8) != entry) return false;
    uint64_t q = list + 8, end = list + 4 + entry, offset = 0, module_size = 0;
    const char *name = NULL;
    unsigned type = 0, found = 0;
    bool terminated = false;
    while (q <= end && end - q >= 4) {
        if (!memcmp(b + q, "ENDT", 4)) {
            terminated = q + 4 == end;
            break;
        }
        if (end - q < 6) return false;
        uint64_t length = gauguin_ca_le(b + q + 4, 2);
        if (length > end - q - 6) return false;
        const uint8_t *value = b + q + 6;
        unsigned flag = 0;
        if (!memcmp(b + q, "NAME", 4)) {
            flag = 1;
            if (length < 2 || length > 128 || value[length - 1] || memchr(value, 0, length - 1)) return false;
            for (uint64_t i = 0; i + 1 < length; i++) {
                unsigned char c = value[i];
                if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                      (c >= '0' && c <= '9') || c == '_')) return false;
            }
            name = (const char *)value;
        } else if (!memcmp(b + q, "TYPE", 4)) {
            flag = 2;
            if (length != 1 || value[0] > 1) return false;
            type = value[0];
        } else if (!memcmp(b + q, "OFFT", 4)) {
            flag = 4;
            if (length != 24) return false;
            offset = gauguin_ca_le(value + 16, 8);
        } else if (!memcmp(b + q, "MDSZ", 4)) {
            flag = 8;
            if (length != 8) return false;
            module_size = gauguin_ca_le(value, 8);
        }
        if (flag && (found & flag)) return false;
        found |= flag;
        q += 6 + length;
    }
    if (!terminated || found != 15 || offset > section_size || module_size < 20 ||
        module_size > section_size - offset) return false;
    const uint8_t *module = b + section + offset;
    if (gauguin_ca_le(module, 4) != 0x0b17c0de) return false;
    uint64_t air_offset = gauguin_ca_le(module + 8, 4), air_size = gauguin_ca_le(module + 12, 4);
    if (air_offset < 20 || air_offset > module_size || air_size < 4 || air_size > module_size - air_offset ||
        memcmp(module + air_offset, "BC\xc0\xde", 4)) return false;
    *result = (struct gauguin_ca_variant){name, type, module, (size_t)module_size};
    return true;
}

static bool gauguin_ca_variant_matches(const struct gauguin_ca_variant *variant,
                                      const char *name, bool vertex)
{
    return variant && name && variant->name && variant->type == (vertex ? 0u : 1u) &&
           strcmp(variant->name, name) == 0;
}
#endif
