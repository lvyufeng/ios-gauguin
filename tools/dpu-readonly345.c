/* Static AArch64/Linux recovery probe. Only DRM mode queries and a bounded
 * vblank read. Run from a temporary RAM file. No panel or clock writes. */

typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned long u64;

#define DRM_QUERY(n, t) (0xc0000000u | (u32)sizeof(t) << 16 | 0x6400u | (n))
#define LIMIT 16

struct mode {
    u32 clock;
    u16 width, hstart, hend, htotal, skew;
    u16 height, vstart, vend, vtotal, vscan;
    u32 refresh, flags, type;
    char name[32];
};
struct resources {
    u64 fbs, crtcs, connectors, encoders;
    u32 nfbs, ncrtcs, nconnectors, nencoders;
    u32 minw, maxw, minh, maxh;
};
struct connector {
    u64 encoders, modes, props, values;
    u32 nmodes, nprops, nencoders, encoder, id, type, type_id, connected;
    u32 mmw, mmh, subpixel, padding;
};
struct encoder {
    u32 id, type, crtc, possible_crtcs, clones;
};
struct crtc {
    u64 connectors;
    u32 count, id, fb, x, y, gamma, valid;
    struct mode mode;
};
struct vblank {
    u32 type, seq;
    long sec, usec;
};
_Static_assert(sizeof(struct resources)==64 && sizeof(struct connector)==80 &&
               sizeof(struct encoder)==20 && sizeof(struct crtc)==104 &&
               sizeof(struct vblank)==24, "wrong DRM UAPI layout");

static long call(long nr, long a, long b, long c, long d)
{
    register long x8 __asm__("x8") = nr;
    register long x0 __asm__("x0") = a;
    register long x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c;
    register long x3 __asm__("x3") = d;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2), "r"(x3) : "memory");
    return x0;
}

static void say(const char* text)
{
    u64 n = 0;
    while (text[n]) ++n;
    call(64, 1, (long)text, n, 0);
}

static void number(const char* key, u64 value)
{
    char chars[24];
    u32 i = sizeof(chars)-1;
    chars[i] = 0;
    do {
        chars[--i] = (char)('0' + value % 10);
        value /= 10;
    } while (value);
    say(key);
    say(chars+i);
}

static long query(long fd, u32 cmd, void* args)
{
    return call(29, fd, cmd, (long)args, 0);
}

static int inspect(long fd)
{
    u32 crtcs[LIMIT], connectors[LIMIT];
    struct resources r = {.crtcs=(u64)crtcs, .connectors=(u64)connectors,
                          .ncrtcs=LIMIT, .nconnectors=LIMIT};
    if (query(fd, DRM_QUERY(0xa0, struct resources), &r) || r.ncrtcs > LIMIT || r.nconnectors > LIMIT)
        return 2;
    for (u32 i=0; i<r.nconnectors; ++i) {
        struct mode dummy;
        // A nonzero count avoids the mode-probe side effect of GETCONNECTOR.
        struct connector c = {.id=connectors[i], .nmodes=1, .modes=(u64)&dummy};
        if (query(fd, DRM_QUERY(0xa7, struct connector), &c) || c.type!=16 ||
            c.connected!=1 || !c.encoder) continue;
        struct encoder e = {.id=c.encoder};
        if (query(fd, DRM_QUERY(0xa6, struct encoder), &e) || !e.crtc) continue;
        for (u32 index=0; index<r.ncrtcs; ++index) {
            if (crtcs[index] != e.crtc) continue;
            struct crtc pipe = {.id=e.crtc};
            if (query(fd, DRM_QUERY(0xa1, struct crtc), &pipe) || !pipe.valid) continue;
            number("dsi=",c.type_id); number(" crtc=",index); number(" active=",pipe.valid);
            number(" width=",pipe.mode.width); number(" height=",pipe.mode.height);
            number(" clock_khz=",pipe.mode.clock); number(" htotal=",pipe.mode.htotal);
            number(" vtotal=",pipe.mode.vtotal); number(" refresh=",pipe.mode.refresh);
            say("\n");
            for (u32 n=0; n<14; ++n) {
                struct vblank v = {.type=1u | (index << 1), .seq=1};
                const long ret=query(fd,DRM_QUERY(0x3a,struct vblank),&v);
                if (ret) {
                    number("vblank_errno=", (u64)-ret);
                    say("\n");
                    return 4;
                }
                number("seq=",v.seq); number(" timestamp_us=",(u64)v.sec*1000000+(u64)v.usec);
                say("\n");
            }
            return 0;
        }
    }
    say("no_active_dsi_crtc\n");
    return 3;
}

void _start(void)
{
    const long fd=call(56,-100,(long)"/dev/dri/card0",0x80000,0);
    const int result=fd<0 ? 1 : inspect(fd);
    call(93,result,0,0,0);
    __builtin_unreachable();
}
