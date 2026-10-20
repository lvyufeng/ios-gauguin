/*
 * Minimal text console on the ABL splash framebuffer. With the MMU off
 * every access is Device memory, so stay aligned (-mstrict-align).
 */
#include "console.h"
#include "fdt.h"
#include "font.h"

#define SCALE		3
#define CH_W		(8 * SCALE)
#define CH_H		(16 * SCALE)
#define MARGIN		24
#define LABEL_COLS	8

volatile uint32_t *con_fb = (volatile uint32_t *)FB_BASE;
uint64_t con_fb_base = FB_BASE;
uint32_t con_w = FB_W, con_h = FB_H, con_stride = FB_STRIDE;
static uint32_t con_bg;
static int row;

void con_init(uintptr_t fdt)
{
	uint64_t base = 0, size = 0;

	/* sweet: /reserved-memory/cont_splash_region (1/1 cells).
	 * Try the 2/2-cells form too: gauguin's base DT describes its
	 * reserved-memory children with the root's 2/2 cells. */
	uintptr_t n = fdt_find(fdt, "/reserved-memory/cont_splash_region");
	if (n && ((fdt_reg2(fdt, n, &base, &size) || fdt_reg1(fdt, n, &base, &size))) &&
	    base && size) {
		con_fb_base = base;
	}
	/* /chosen/framebuffer[@unit]: ABL's splash. sweet writes the geometry as
	 * decimal ASCII, gauguin (framebuffer@a0000000) as raw 32-bit cells. */
	uintptr_t c = fdt_find(fdt, "/chosen/framebuffer");
	if (c) {
		uint64_t fb = 0, sz = 0;
		uint32_t w = 0, h = 0, st = 0;

		if ((fdt_reg2(fdt, c, &fb, &sz) || fdt_reg1(fdt, c, &fb, &sz)) && fb && sz)
			con_fb_base = fb;
		if (!fdt_dec3(fdt, c, "width", &w))
			fdt_u32(fdt, c, "width", &w);
		if (!fdt_dec3(fdt, c, "height", &h))
			fdt_u32(fdt, c, "height", &h);
		if (!fdt_dec3(fdt, c, "stride", &st))
			fdt_u32(fdt, c, "stride", &st);
		if (w && h && st) {
			con_w = w;
			con_h = h;
			con_stride = st;
		}
	}
	if (!con_stride)
		con_stride = con_w * 4;
	con_fb = (volatile uint32_t *)con_fb_base;
}

void con_clear(uint32_t bg)
{
	for (uint32_t y = 0; y < con_h; y++) {
		volatile uint32_t *line = con_fb + y * (con_stride / 4);
		for (uint32_t x = 0; x < con_w; x++)
			line[x] = bg;
	}
	con_bg = bg;
	row = 0;
}

static void put_char(int col, char ch, uint32_t fg)
{
	if (ch < 0x20 || ch > 0x7e)
		ch = '?';
	const unsigned char *g = font8x16[ch - 0x20];
	int x0 = MARGIN + col * CH_W, y0 = MARGIN + row * CH_H;
	if (x0 + CH_W > (int)con_w || y0 + CH_H > (int)con_h)
		return;
	for (int gy = 0; gy < 16; gy++)
		for (int gx = 0; gx < 8; gx++) {
			uint32_t c = (g[gy] & (0x80 >> gx)) ? fg : con_bg;
			for (int sy = 0; sy < SCALE; sy++) {
				volatile uint32_t *p = con_fb + (y0 + gy * SCALE + sy) * (con_stride / 4)
						       + x0 + gx * SCALE;
				for (int sx = 0; sx < SCALE; sx++)
					p[sx] = c;
			}
		}
}

static int put_str(int col, const char *s, uint32_t fg)
{
	while (*s)
		put_char(col++, *s++, fg);
	return col;
}

static void fmt_hex(char *buf, uint64_t v, int digits)
{
	static const char hex[] = "0123456789ABCDEF";
	for (int i = 0; i < digits; i++)
		buf[i] = hex[(v >> (4 * (digits - 1 - i))) & 0xf];
	buf[digits] = 0;
}

void con_skip(void)
{
	row++;
}

void con_str(const char *label, const char *s)
{
	put_str(0, label, YELLOW);
	put_str(LABEL_COLS, s, WHITE);
	row++;
}

void con_hex(const char *label, uint64_t v)
{
	char buf[17];
	fmt_hex(buf, v, 16);
	con_str(label, buf);
}

void con_hex2(const char *label, const char *a, uint32_t va, const char *b, uint32_t vb)
{
	char buf[9];
	int col = put_str(0, label, YELLOW);
	col = col < LABEL_COLS ? LABEL_COLS : col + 1;
	col = put_str(col, a, YELLOW);
	fmt_hex(buf, va, 8);
	col = put_str(col, buf, WHITE);
	if (b) {
		col = put_str(col + 1, b, YELLOW);
		fmt_hex(buf, vb, 8);
		put_str(col, buf, WHITE);
	}
	row++;
}
