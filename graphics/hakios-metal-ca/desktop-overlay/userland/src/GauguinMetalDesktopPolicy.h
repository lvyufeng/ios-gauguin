/* Experimental 20H392 compositor contract; no kernel authority. MIT. */
#ifndef GAUGUIN_METAL_DESKTOP_POLICY_H
#define GAUGUIN_METAL_DESKTOP_POLICY_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Existing kernel pilot authorization additionally requires its protected
 * launchd proxy identity and the released root GPU owner. This parser cannot
 * grant either. Reject duplicate/conflicting selectors rather than using a
 * different mode from the kernel. */
static inline bool gauguin_desktop_boot(const char *args)
{
    const char *keys[] = {"sweeteagl=", "gmt=", "sweet_dyld_probe="};
    const char values[] = {'2', '2', '1'};
    unsigned counts[3] = {0, 0, 0};
    if (!args || strstr(args, "metal_m2v")) return false;
    for (const char *p = args; *p;) {
        p += strspn(p, " \t");
        size_t n = strcspn(p, " \t");
        if (!n) break;
        for (size_t i = 0; i < 3; i++) {
            size_t k = strlen(keys[i]);
            if (n >= k && !memcmp(p, keys[i], k)) {
                if (++counts[i] != 1 || n != k + 1 || p[k] != values[i]) return false;
            }
        }
        p += n;
    }
    return counts[0] == 1 && counts[1] == 1 && counts[2] == 1;
}

static inline bool gauguin_desktop_identity(unsigned long uid, unsigned long euid,
                                           const char *name, const char *version)
{
    return uid == 501 && euid == 501 && name && !strcmp(name, "backboardd") &&
           version && !strcmp(version, "20H392");
}

/* This single current-system caller makes an immediate decoded-image upload.
 * The desktop experiment snapshots its input, as upstream does; it does not
 * implement later CPU/GPU aliasing. Other callers must still be refused.
 * The return offset includes the BL instruction's four bytes. ASLR is removed
 * against the actual image header; the image UUID and path must also match. */
static inline bool gauguin_desktop_upload_site(const char *path,
                                              const unsigned char uuid[16],
                                              uintptr_t return_offset)
{
    static const unsigned char expected[16] = {
        0x9e,0x40,0xb2,0xeb,0x26,0x0c,0x3a,0xf1,
        0xae,0x45,0xa1,0xa5,0x51,0xa8,0xc1,0xb9
    };
    return path && !strcmp(path, "/System/Library/Frameworks/QuartzCore.framework/QuartzCore") &&
           uuid && !memcmp(uuid, expected, sizeof(expected)) && return_offset == 0x200390;
}

static inline bool gauguin_desktop_upload_bounds(uintptr_t bytes, size_t length,
                                                uint64_t options)
{
    return bytes && length && length <= (64ULL << 20) &&
           length <= UINTPTR_MAX - bytes && options == 0;
}
#endif
