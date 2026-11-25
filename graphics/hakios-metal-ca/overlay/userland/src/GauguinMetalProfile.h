/* Diagnostic profile only; this header grants no kernel GPU authority. MIT. */
#ifndef GAUGUIN_METAL_PROFILE_H
#define GAUGUIN_METAL_PROFILE_H
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

#define GAUGUIN_METAL_MAX_BUFFER_BYTES (64ULL << 20)
#define GAUGUIN_METAL_MAX_CLIENT_BYTES (256ULL << 20)
#define GAUGUIN_METAL_PROBE_NAME "gauguin-metal-frontend-probe"

/* A conflicting or duplicate selector is a rejection, even if one value is 1.
 * Parse complete tokens, never substrings such as xgmt=1 or =10. */
static inline bool gauguin_metal_boot_profile(const char *args)
{
    unsigned gpu_modes = 0, frontend_modes = 0;
    if (args == NULL) return false;
    for (const char *p = args; *p;) {
        p += strspn(p, " \t");
        size_t n = strcspn(p, " \t");
        if (!n) break;
        if (n >= 10 && !memcmp(p, "sweeteagl=", 10)) {
            if (++gpu_modes != 1 || n != 11 || p[10] != '1') return false;
        }
        if (n >= 4 && !memcmp(p, "gmt=", 4)) {
            if (++frontend_modes != 1 || n != 5 || p[4] != '1') return false;
        }
        p += n;
    }
    return gpu_modes == 1 && frontend_modes == 1;
}

bool gauguin_metal_profile_admit(void);
void gauguin_metal_profile_cache(void);
#endif
