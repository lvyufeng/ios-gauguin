/* Separate experimental desktop profile; diagnostic sources stay unchanged. MIT. */
#ifndef GAUGUIN_METAL_PROFILE_H
#define GAUGUIN_METAL_PROFILE_H
#include "GauguinMetalDesktopPolicy.h"
#include "GauguinMetalDesktopClasses.h"
#define GAUGUIN_METAL_MAX_BUFFER_BYTES (64ULL << 20)
#define GAUGUIN_METAL_MAX_CLIENT_BYTES (256ULL << 20)
bool gauguin_metal_profile_admit(void);
void *gauguin_metal_desktop_open(void);
void gauguin_metal_profile_cache(void);
bool gauguin_metal_desktop_upload(const void *return_pc, const void *bytes,
                                 size_t length, uint64_t options);
#endif
