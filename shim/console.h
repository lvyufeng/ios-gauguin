#pragma once
#include <stdint.h>

/*
 * Framebuffer defaults: sweet's ABL cont splash (1080x2400 a8r8g8b8 at
 * 0x9c000000). con_init() replaces them with the phone's actual
 * /reserved-memory/cont_splash_region and /chosen framebuffer geometry, so
 * boards with a different layout (gauguin: 0xa0000000) need no rebuild.
 */
#define FB_BASE		0x9c000000UL
#define FB_W		1080
#define FB_H		2400
#define FB_STRIDE	(FB_W * 4)	/* a8r8g8b8 */

extern uint64_t con_fb_base;
extern uint32_t con_w, con_h, con_stride;

/* Use the framebuffer described by the live FDT (falls back to the defaults). */
void con_init(uintptr_t fdt);

#define RED	0xffff0000U
#define BLUE	0xff0000a0U
#define WHITE	0xffffffffU
#define YELLOW	0xffffff00U
#define GREEN	0xff00ff00U

extern volatile uint32_t *con_fb;

void con_clear(uint32_t bg);
void con_skip(void);
void con_str(const char *label, const char *s);
void con_hex(const char *label, uint64_t v);
/* label, then "a=xxxxxxxx b=xxxxxxxx" style pairs of 32-bit values */
void con_hex2(const char *label, const char *a, uint32_t va, const char *b, uint32_t vb);
