/* SPDX-License-Identifier: MIT
 * Exercise the production identity reader against caller-owned CA assets.
 * This verifies stage/name separation and malformed-container rejection only.
 */
#include <stdio.h>
#include <stdlib.h>
#include "GauguinCAVariant.h"

static unsigned checks;
static void require(bool ok, const char *what) {
    if (!ok) { fprintf(stderr, "identity fixture failed: %s\n", what); exit(2); }
    checks++;
}
static void rejected(const uint8_t *bytes, size_t size) {
    struct gauguin_ca_variant v;
    require(!gauguin_ca_variant_read(bytes, size, &v), "malformed input accepted");
}
int main(int argc, char **argv) {
    require(argc == 2, "one caller-owned functions file required");
    FILE *f = fopen(argv[1], "rb"); require(f != NULL, "input open");
    require(!fseek(f, 0, SEEK_END), "input seek"); long count = ftell(f);
    require(count > 88 && count < 32 * 1024 * 1024, "bounded input");
    rewind(f); uint8_t *bytes = malloc((size_t)count); require(bytes != NULL, "input allocation");
    require(fread(bytes, 1, (size_t)count, f) == (size_t)count && !fclose(f), "input read");
    unsigned libraries = 0;
    for (size_t at = 0; at + 88 <= (size_t)count; at++) {
        if (memcmp(bytes + at, "MTLB", 4)) continue;
        uint64_t size = gauguin_ca_le(bytes + at + 16, 8);
        require(size <= (size_t)count - at, "bounded sublibrary");
        struct gauguin_ca_variant v;
        require(gauguin_ca_variant_read(bytes + at, size, &v), "actual variant rejected");
        require(gauguin_ca_variant_matches(&v, v.name, v.type == 0), "same identity rejected");
        require(!gauguin_ca_variant_matches(&v, v.name, v.type != 0), "wrong stage accepted");
        require(!gauguin_ca_variant_matches(&v, "fixed_frag_lpf_cpf", false), "LPH variant accepted as LPF");
        require(!gauguin_ca_variant_matches(&v, NULL, false), "nil identity accepted");
        require(!strncmp(v.name, v.type ? "fixed_frag_lph_" : "fixed_vert_lph_", 15), "unexpected image function precision");
        uint8_t *bad = malloc(size); require(bad != NULL, "mutation allocation");
        for (size_t j = 0; j < 88; j++) rejected(bytes + at, j);
        rejected(bytes + at, size - 1);
        const size_t offsets[] = {24, 32, 72, 80};
        for (unsigned j = 0; j < sizeof(offsets) / sizeof(offsets[0]); j++) {
            memcpy(bad, bytes + at, size); memset(bad + offsets[j], 0xff, 8); rejected(bad, size);
        }
        memcpy(bad, bytes + at, size);
        size_t list = (size_t)gauguin_ca_le(bad + 24, 8); bad[list] = 2; rejected(bad, size);
        size_t end = list + 4 + (size_t)gauguin_ca_le(bad + list + 4, 4);
        for (size_t q = list + 8; q + 6 < end;) {
            size_t length = (size_t)gauguin_ca_le(bytes + at + q + 4, 2);
            memcpy(bad, bytes + at, size);
            if (!memcmp(bad + q, "NAME", 4)) {
                bad[q + 6 + length - 1] = 'x'; rejected(bad, size);
                memcpy(bad, bytes + at, size); bad[q + 6] = 0; rejected(bad, size);
            } else if (!memcmp(bad + q, "TYPE", 4)) {
                bad[q + 6] = 2; rejected(bad, size);
            } else if (!memcmp(bad + q, "OFFT", 4)) {
                memset(bad + q + 6 + 16, 0xff, 8); rejected(bad, size);
            } else if (!memcmp(bad + q, "MDSZ", 4)) {
                memset(bad + q + 6, 0xff, 8); rejected(bad, size);
            }
            memcpy(bad, bytes + at, size); memset(bad + q + 4, 0xff, 2); rejected(bad, size);
            q += 6 + length;
        }
        memcpy(bad, bytes + at, size);
        size_t module = (size_t)((const uint8_t *)v.module - (bytes + at));
        memset(bad + module + 8, 0xff, 4); rejected(bad, size);
        memcpy(bad, bytes + at, size); bad[end - 1] = 0; rejected(bad, size);
        free(bad); libraries++; at += size - 1;
    }
    require(libraries == 451, "image-owned variant count changed"); free(bytes);
    printf("{\"state\":\"variant-identity-and-bounds-checked\",\"libraries\":%u,\"checks\":%u,\"GPU_jobs\":0}\n", libraries, checks);
    return 0;
}
