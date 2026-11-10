/* Preserve the qualified root223 -> GLES handoff alongside Metal diagnostics.
 * This userland routing grants no kernel GPU authority. SPDX-License-Identifier: MIT */
#ifndef GAUGUIN_PROBE_BOOT_H
#define GAUGUIN_PROBE_BOOT_H
#include "GauguinMetalProfile.h"
#include <stdint.h>
#include <sys/stat.h>

enum gauguin_probe_route { GAUGUIN_PROBE_REJECT, GAUGUIN_PROBE_METAL, GAUGUIN_PROBE_GLES };
#define GAUGUIN_LEGACY_PROBE_PATH "/usr/libexec/gauguin-metal-probe"
#define GAUGUIN_LEGACY_PROBE_BYTES 115728
static const unsigned char gauguin_legacy_probe_sha256[32] = {
    0x2e,0x11,0x8d,0x96,0x0a,0x21,0x98,0x90,0xd3,0x21,0x5b,0xef,0x81,0xab,0x9a,0xd3,
    0xc7,0x1d,0x2a,0x68,0xbe,0x62,0x24,0x4d,0x87,0x09,0x00,0xda,0xe0,0xe1,0xe2,0xd8,
};

static inline enum gauguin_probe_route gauguin_probe_boot_route(const char *args)
{
    if (gauguin_metal_boot_profile(args)) return GAUGUIN_PROBE_METAL;
    if (!args) return GAUGUIN_PROBE_REJECT;
    unsigned modes = 0;
    for (const char *p = args; *p;) {
        p += strspn(p, " \t");
        size_t n = strcspn(p, " \t");
        if (!n) break;
        /* gmt is exclusive to the diagnostic; never route an ambiguous
         * selector to the GLES worker, including gmt=0 and duplicates. */
        if (n >= 4 && !memcmp(p, "gmt=", 4)) return GAUGUIN_PROBE_REJECT;
        if (n >= 10 && !memcmp(p, "sweeteagl=", 10)) {
            if (++modes != 1 || n != 11 || p[10] != '2') return GAUGUIN_PROBE_REJECT;
        }
        p += n;
    }
    return modes == 1 ? GAUGUIN_PROBE_GLES : GAUGUIN_PROBE_REJECT;
}

static inline bool gauguin_legacy_probe_metadata_ok(const struct stat *st)
{
    return st && S_ISREG(st->st_mode) && (st->st_mode & 07777) == 0755 &&
        st->st_uid == 0 && st->st_gid == 0 && st->st_nlink == 1 &&
        st->st_size == GAUGUIN_LEGACY_PROBE_BYTES;
}
#endif
