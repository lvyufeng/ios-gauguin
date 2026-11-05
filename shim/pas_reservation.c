#include "pas_reservation.h"

#define PAGE UINT64_C(0x4000)
#define LIMIT UINT64_C(0x100000000)
#define MAX_PAYLOAD UINT64_C(0x20000000)
#define MAX_DT (1024u * 1024u)
#define MAX_DEPTH 16u
#define MAX_NODES 4096u
#define MAX_PROPS 16384u
#define MAX_MAP 64u
#define HEADER 0x2a8u
#define MAX_SEGS 490u
struct range {
    uint64_t start, size;
};
struct adt_view {
    uint64_t base, size;
    uint32_t req_name, req_value, io_name, io_value;
    unsigned chosen, defaults, req, io, base_seen, size_seen, actual, owner, maps, nodes, props;
    struct range map[MAX_MAP];
};
/* Freestanding metadata helpers: volatile byte operations avoid implicit
 * libc memset/memcpy calls and unaligned Device-memory accesses. */
static void clear_metadata(void *p, size_t bytes)
{
    volatile uint8_t *d = p;
    while (bytes--)
        *d++ = 0;
}
static void copy_metadata(void *dst, const void *src, size_t bytes)
{
    volatile uint8_t *d = dst;
    const uint8_t *s = src;
    while (bytes--)
        *d++ = *s++;
}
static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint64_t le64(const uint8_t *p)
{
    return le32(p) | ((uint64_t)le32(p + 4) << 32);
}
static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}
static uint64_t be64(const uint8_t *p)
{
    return ((uint64_t)be32(p) << 32) | be32(p + 4);
}
static void put32(uint8_t *p, uint32_t v)
{
    for (unsigned i = 0; i < 4; ++i)
        p[i] = (uint8_t)(v >> (i * 8));
}
static void put64(uint8_t *p, uint64_t v)
{
    put32(p, (uint32_t)v);
    put32(p + 4, (uint32_t)(v >> 32));
}
static int eq(const uint8_t *p, size_t bytes, const char *s)
{
    size_t i = 0;
    while (i < bytes && s[i] && p[i] == (uint8_t)s[i])
        ++i;
    return i < bytes && !s[i] && !p[i];
}
static int magic(const uint8_t *p, const char *s)
{
    for (unsigned i = 0; i < 8; ++i)
        if (p[i] != (uint8_t)s[i])
            return 0;
    return 1;
}
static int zero(const uint8_t *p, size_t bytes)
{
    while (bytes--)
        if (*p++)
            return 0;
    return 1;
}
static int fits(uint64_t start, uint64_t bytes, uint64_t limit)
{
    return start <= limit && bytes <= limit - start;
}
static int valid(struct range r)
{
    return r.size && fits(r.start, r.size, UINT64_MAX);
}
static int overlap(struct range a, struct range b)
{
    return a.size && b.size && a.start < b.start + b.size && b.start < a.start + a.size;
}
static int inside(struct range a, struct range b)
{
    return a.start >= b.start && fits(a.start - b.start, a.size, b.size);
}
static uint64_t up(uint64_t value, uint64_t align)
{
    return (value + align - 1) & ~(align - 1);
}
static int node_is(const uint8_t *p, size_t bytes, const char *s)
{
    size_t i = 0;
    while (i < bytes && s[i] && p[i] == (uint8_t)s[i])
        ++i;
    return i < bytes && !s[i] && (!p[i] || p[i] == '@');
}
static void name_set(uint8_t *p, const char *name)
{
    unsigned i = 0;
    for (; i < 32 && name[i]; ++i)
        p[i] = (uint8_t)name[i];
    for (; i < 32; ++i)
        p[i] = 0;
}

/* Apple ADT properties use little-endian lengths and4-byte padding. Only
 * metadata is traversed. Recursive depth and aggregate work are hard bounded. */
static int adt_node(const uint8_t *d, size_t bytes, size_t *at, unsigned parent, unsigned depth,
                    struct adt_view *v)
{
    if (depth >= MAX_DEPTH || ++v->nodes > MAX_NODES || !fits(*at, 8, bytes))
        return PAS_BAD_ADT;
    uint32_t np = le32(d + *at), nc = le32(d + *at + 4);
    *at += 8;
    if (np > MAX_PROPS - v->props || nc > MAX_NODES)
        return PAS_BAD_ADT;
    v->props += np;
    size_t first = *at, name_at = 0, name_bytes = 0;
    unsigned names = 0;
    for (uint32_t i = 0; i < np; ++i) {
        if (!fits(*at, 36, bytes))
            return PAS_BAD_ADT;
        uint32_t length = le32(d + *at + 32) & 0x7fffffffu;
        size_t padded = ((size_t)length + 3) & ~(size_t)3;
        if (!fits(*at + 36, padded, bytes))
            return PAS_BAD_ADT;
        unsigned n = 0;
        while (n < 32 && d[*at + n])
            ++n;
        if (n == 32)
            return PAS_BAD_ADT;
        if (eq(d + *at, 32, "name")) {
            if (le32(d + *at + 32) & 0x80000000u)
                return PAS_BAD_ADT;
            if (names) {
                if (name_bytes != length)
                    return PAS_BAD_ADT;
                for (size_t j = 0; j < length; ++j)
                    if (d[name_at + j] != d[*at + 36 + j])
                        return PAS_BAD_ADT;
            }
            ++names;
            name_at = *at + 36;
            name_bytes = length;
        }
        *at += 36 + padded;
    }
    if (!names || !name_bytes || d[name_at + name_bytes - 1])
        return PAS_BAD_ADT;
    unsigned role = 0;
    if (!depth) {
        if (!eq(d + name_at, name_bytes, "device-tree"))
            return PAS_BAD_ADT;
        role = 1;
    } else if (parent == 1 && eq(d + name_at, name_bytes, "chosen")) {
        role = 2;
        ++v->chosen;
    } else if (parent == 1 && eq(d + name_at, name_bytes, "defaults")) {
        role = 3;
        ++v->defaults;
    } else if (parent == 2 && eq(d + name_at, name_bytes, "memory-map"))
        role = 4;
    size_t pos = first;
    for (uint32_t i = 0; i < np; ++i) {
        uint32_t raw = le32(d + pos + 32), length = raw & 0x7fffffffu;
        const uint8_t *p = d + pos, *value = p + 36;
        if (role == 2 && eq(p, 32, "LowPASRequest")) {
            if (raw != PAS_REQUEST_BYTES)
                return PAS_BAD_ADT;
            ++v->req;
            v->req_name = (uint32_t)pos;
            v->req_value = (uint32_t)(pos + 36);
        } else if (role == 2 && eq(p, 32, "LowPASReservation")) {
            ++v->actual;
            ++v->owner;
        } else if (role == 3 && eq(p, 32, "LowPASIOPending")) {
            if (raw != 24 || !zero(value, 24))
                return PAS_BAD_ADT;
            ++v->io;
            v->io_name = (uint32_t)pos;
            v->io_value = (uint32_t)(pos + 36);
        } else if (role == 3 && eq(p, 32, "pmap-io-ranges"))
            ++v->actual;
        else if (role == 2 && eq(p, 32, "dram-base")) {
            if (raw != 8)
                return PAS_BAD_ADT;
            v->base = le64(value);
            ++v->base_seen;
        } else if (role == 2 && eq(p, 32, "dram-size")) {
            if (raw != 8)
                return PAS_BAD_ADT;
            v->size = le64(value);
            ++v->size_seen;
        } else if (role == 4 && length == 16) {
            if (raw != 16 || v->maps == MAX_MAP)
                return PAS_BAD_ADT;
            struct range r = {le64(value), le64(value + 8)};
            if (!valid(r))
                return PAS_BAD_ADT;
            v->map[v->maps++] = r;
        }
        pos += 36 + (((size_t)length + 3) & ~(size_t)3);
    }
    for (uint32_t i = 0; i < nc; ++i) {
        int s = adt_node(d, bytes, at, role, depth + 1, v);
        if (s)
            return s;
    }
    return 0;
}
static int adt_read(const uint8_t *d, size_t bytes, struct adt_view *v)
{
    clear_metadata(v, sizeof(*v));
    size_t at = 0;
    if (!d || bytes > MAX_DT)
        return PAS_BAD_ADT;
    int s = adt_node(d, bytes, &at, 0, 0, v);
    if (s || at != bytes)
        return PAS_BAD_ADT;
    if (v->chosen != 1 || v->base_seen != 1 || v->size_seen != 1)
        return PAS_BAD_ADT;
    if (v->req > 1 || v->io > 1 || v->defaults > 1)
        return PAS_BAD_ADT;
    return 0;
}
static int request(const uint8_t *r, uint64_t payload_bytes, uint64_t *tail)
{
    if (!magic(r, "LPASREQ1") || le32(r + 8) != 1 || le32(r + 12) ||
        le64(r + 24) != PAS_TAIL_BYTES || le64(r + 32) != PAS_REGION_BYTES ||
        le64(r + 40) != PAS_ALIGNMENT || le64(r + 48) != payload_bytes ||
        !zero(r + 56, PAS_REQUEST_BYTES - 56))
        return PAS_BAD_REQUEST;
    *tail = le64(r + 16);
    if ((*tail & (PAGE - 1)) || !fits(*tail, PAS_TAIL_BYTES, payload_bytes) ||
        *tail + PAS_TAIL_BYTES != payload_bytes)
        return PAS_BAD_REQUEST;
    return 0;
}

size_t pas_fdt_header_size(const uint8_t *fdt)
{
    if (!fdt || be32(fdt) != 0xd00dfeed)
        return 0;
    uint32_t size = be32(fdt + 4);
    return size >= 40 && size <= MAX_DT ? size : 0;
}
/* Reject a reservation intersecting selected backing or actual high load
 * destinations. The initrd reservation exception is handled separately. */
static int excluded(const struct pas_context *c, const struct pas_plan *p, struct range r)
{
    if (!valid(r))
        return PAS_BAD_FDT;
    if (c->payload_bytes && overlap(r, (struct range){c->payload_pa, c->payload_bytes}))
        return PAS_OVERLAP;
    if (!c->payload)
        return 0;
    if (overlap(r, (struct range){p->pa, p->bytes}))
        return PAS_OVERLAP;
    const uint8_t *d = c->payload;
    uint32_t n = le32(d + 12);
    for (uint32_t i = 0; i < n; ++i) {
        const uint8_t *s = d + HEADER + 32 * i;
        struct range load = {le64(d + 56) + le64(s) - le64(d + 16), le64(s + 8)};
        if (overlap(r, load))
            return PAS_OVERLAP;
    }
    uint64_t adt_pa = le64(d + 56) + le64(d + 48) - le64(d + 16);
    uint64_t end = up(adt_pa + p->adt_bytes, PAGE) + PAGE;
    return overlap(r, (struct range){adt_pa, end - adt_pa}) ? PAS_OVERLAP : 0;
}
struct fnode {
    uint32_t kind, ac, sc, ranges, reg_count, size_count, ac_seen, sc_seen, child_seen;
    size_t reg, reg_bytes;
};
static int fdt_validate(const struct pas_context *c, struct pas_plan *p)
{
    const uint8_t *d = c->fdt;
    size_t bytes = c->fdt_bytes;
    if (bytes < 40 || pas_fdt_header_size(d) != bytes || be32(d + 20) != 17 || be32(d + 24) > 17)
        return PAS_BAD_FDT;
    uint32_t so = be32(d + 8), strings = be32(d + 12), reserve = be32(d + 16), sn = be32(d + 32),
             st = be32(d + 36);
    if ((so & 3) || (reserve & 7) || so < 40 || strings < 40 || reserve < 40 ||
        !fits(so, st, bytes) || !fits(strings, sn, bytes) ||
        overlap((struct range){so, st}, (struct range){strings, sn}))
        return PAS_BAD_FDT;
    size_t rpos = reserve;
    unsigned reserved = 0;
    for (;;) {
        if (++reserved > 128 || !fits(rpos, 16, bytes))
            return PAS_BAD_FDT;
        struct range r = {be64(d + rpos), be64(d + rpos + 8)};
        rpos += 16;
        if (!r.start && !r.size)
            break;
        if (!valid(r))
            return PAS_BAD_FDT;
        struct range input = {c->payload_pa, c->payload_bytes};
        if (c->payload_bytes && overlap(r, input)) {
            /* Only an EXACT /chosen initrd reservation is attributable to the
             * inherited input. Broader/page-rounded/partial claims are ambiguous. */
            if (r.start != input.start || r.size != input.size ||
                ++p->exact_initrd_reservations > 1)
                return PAS_AMBIGUOUS;
        } else {
            int status = excluded(c, p, r);
            if (status)
                return status;
        }
    }
    if (overlap((struct range){reserve, rpos - reserve}, (struct range){so, st}) ||
        overlap((struct range){reserve, rpos - reserve}, (struct range){strings, sn}))
        return PAS_BAD_FDT;
    struct fnode stack[MAX_DEPTH];
    unsigned depth = 0, nodes = 0, props = 0, chosen = 0, resroot = 0, banks = 0;
    unsigned start_seen = 0, end_seen = 0, in_ram = 0, compatible = 0, compatible_seen = 0,
             root_seen = 0, gauguin = 0, sm7225 = 0;
    uint64_t initrd_start = 0, initrd_end = 0;
    size_t at = so, end = so + st;
    for (;;) {
        if (!fits(at, 4, end))
            return PAS_BAD_FDT;
        uint32_t token = be32(d + at);
        at += 4;
        if (token == 1) {
            if (depth == MAX_DEPTH || ++nodes > MAX_NODES)
                return PAS_BAD_FDT;
            size_t name = at;
            while (at < end && at - name < 256 && d[at])
                ++at;
            if (at == end || at - name == 256)
                return PAS_BAD_FDT;
            size_t len = at - name + 1;
            at = (at + 4) & ~(size_t)3;
            if (at > end)
                return PAS_BAD_FDT;
            struct fnode f;
            clear_metadata(&f, sizeof f);
            f.ac = 2;
            f.sc = 2;
            if (depth)
                stack[depth - 1].child_seen = 1;
            if (!depth) {
                if (root_seen++ || len != 1)
                    return PAS_BAD_FDT;
                f.kind = 1;
            } else if (depth == 1) {
                if (eq(d + name, len, "chosen")) {
                    f.kind = 2;
                    ++chosen;
                } else if (node_is(d + name, len, "memory"))
                    f.kind = 3;
                else if (eq(d + name, len, "reserved-memory")) {
                    f.kind = 4;
                    ++resroot;
                }
            } else if (depth == 2 && stack[depth - 1].kind == 4)
                f.kind = 5;
            else if (depth > 2 && stack[depth - 1].kind == 5)
                return PAS_BAD_FDT;
            copy_metadata(&stack[depth++], &f, sizeof f);
        } else if (token == 2) {
            if (!depth)
                return PAS_BAD_FDT;
            struct fnode *f = &stack[--depth];
            if ((f->kind == 1 || f->kind == 4) &&
                (f->ac != 2 || f->sc != 2 || f->ac_seen != 1 || f->sc_seen != 1))
                return PAS_BAD_FDT;
            if (f->kind == 4 && f->ranges != 1)
                return PAS_BAD_FDT;
            if (f->kind == 3 || f->kind == 5) {
                if (f->size_count > 1 || f->reg_count > 1 || (f->kind == 3 && f->reg_count != 1))
                    return PAS_BAD_FDT;
                if (f->reg_count) {
                    if (!f->reg_bytes || (f->reg_bytes % 16))
                        return PAS_BAD_FDT;
                    for (size_t off = 0; off < f->reg_bytes; off += 16) {
                        struct range r = {be64(d + f->reg + off), be64(d + f->reg + off + 8)};
                        if (!valid(r))
                            return PAS_BAD_FDT;
                        if (f->kind == 3) {
                            if (++banks > 32)
                                return PAS_BAD_FDT;
                            if (inside((struct range){c->payload_pa, c->payload_bytes}, r))
                                ++in_ram;
                        } else {
                            if (++p->fixed_reservations > 128)
                                return PAS_BAD_FDT;
                            int status = excluded(c, p, r);
                            if (status)
                                return status;
                        }
                    }
                } else if (f->size_count) {
                    if (++p->dynamic_pools > 128)
                        return PAS_BAD_FDT;
                } else
                    return PAS_BAD_FDT;
            }
        } else if (token == 3) {
            if (!depth || ++props > MAX_PROPS || !fits(at, 8, end))
                return PAS_BAD_FDT;
            uint32_t len = be32(d + at), no = be32(d + at + 4);
            at += 8;
            if (no >= sn || !fits(at, len, end))
                return PAS_BAD_FDT;
            size_t stop = strings + no;
            while (stop < strings + sn && stop - (strings + no) < 128 && d[stop])
                ++stop;
            if (stop == strings + sn || stop - (strings + no) == 128)
                return PAS_BAD_FDT;
            const uint8_t *name = d + strings + no;
            size_t nl = stop - (strings + no) + 1;
            struct fnode *f = &stack[depth - 1];
            if (f->child_seen)
                return PAS_BAD_FDT;
            if (eq(name, nl, "#address-cells")) {
                if (len != 4 || ++f->ac_seen != 1)
                    return PAS_BAD_FDT;
                f->ac = be32(d + at);
            } else if (eq(name, nl, "#size-cells")) {
                if (len != 4 || ++f->sc_seen != 1)
                    return PAS_BAD_FDT;
                f->sc = be32(d + at);
            } else if (f->kind == 4 && eq(name, nl, "ranges")) {
                if (len)
                    return PAS_BAD_FDT;
                ++f->ranges;
            } else if ((f->kind == 3 || f->kind == 5) && eq(name, nl, "reg")) {
                ++f->reg_count;
                f->reg = at;
                f->reg_bytes = len;
            } else if (f->kind == 5 && eq(name, nl, "size")) {
                if (len != 8 || !be64(d + at))
                    return PAS_BAD_FDT;
                ++f->size_count;
            } else if (f->kind == 2 &&
                       (eq(name, nl, "linux,initrd-start") || eq(name, nl, "linux,initrd-end"))) {
                if (len != 4 && len != 8)
                    return PAS_BAD_FDT;
                uint64_t value = len == 8 ? be64(d + at) : be32(d + at);
                if (eq(name, nl, "linux,initrd-start")) {
                    ++start_seen;
                    initrd_start = value;
                } else {
                    ++end_seen;
                    initrd_end = value;
                }
            } else if (f->kind == 1 && eq(name, nl, "compatible")) {
                if (++compatible_seen != 1)
                    return PAS_BAD_FDT;
                size_t pos = 0;
                while (pos < len) {
                    size_t finish = pos;
                    while (finish < len && d[at + finish])
                        ++finish;
                    if (finish == len)
                        return PAS_BAD_FDT;
                    /* Stock recovery uses lagoon. Our qualified wrapper uses
                     * the gauguin/SM7225 pair; SM7225 alone is insufficient. */
                    if (eq(d + at + pos, finish - pos + 1, "qcom,lagoon"))
                        compatible = 1;
                    if (eq(d + at + pos, finish - pos + 1, "xiaomi,gauguin"))
                        gauguin = 1;
                    if (eq(d + at + pos, finish - pos + 1, "qcom,sm7225"))
                        sm7225 = 1;
                    pos = finish + 1;
                }
            }
            at += ((size_t)len + 3) & ~(size_t)3;
            if (at > end)
                return PAS_BAD_FDT;
        } else if (token == 4)
            continue;
        else if (token == 9) {
            if (depth || !root_seen || at != end || chosen != 1 || resroot != 1 ||
                start_seen != 1 || end_seen != 1 || !(compatible || (gauguin && sm7225)) || !banks ||
                (c->payload_bytes && in_ram != 1))
                return PAS_BAD_FDT;
            if (initrd_end <= initrd_start || initrd_end - initrd_start > MAX_PAYLOAD)
                return PAS_BAD_FDT;
            if (c->payload_bytes &&
                (initrd_start != c->payload_pa || initrd_end != c->payload_pa + c->payload_bytes))
                return PAS_BAD_FDT;
            p->payload_pa = initrd_start;
            p->payload_bytes = initrd_end - initrd_start;
            return 0;
        } else
            return PAS_BAD_FDT;
    }
}

int pas_initrd(const uint8_t *fdt, size_t bytes, uint64_t *start, uint64_t *end)
{
    if (!fdt || !start || !end)
        return PAS_BAD_INPUT;
    struct pas_context c;
    clear_metadata(&c, sizeof c);
    c.fdt = fdt;
    c.fdt_bytes = bytes;
    struct pas_plan p;
    clear_metadata(&p, sizeof p);
    int status = fdt_validate(&c, &p);
    if (status)
        return status;
    /* Before the loader can dereference even the payload magic, a second
     * metadata-only pass must prove RAM containment and reservations. No
     * payload pointer is installed, so excluded() cannot inspect its header. */
    c.payload_pa = p.payload_pa;
    c.payload_bytes = p.payload_bytes;
    struct range input = {c.payload_pa, c.payload_bytes};
    struct range original_fdt = {(uintptr_t)fdt, bytes};
    if (!valid(original_fdt) || overlap(input, original_fdt))
        return PAS_OVERLAP;
    clear_metadata(&p, sizeof p);
    status = fdt_validate(&c, &p);
    if (status)
        return status;
    *start = p.payload_pa;
    *end = p.payload_pa + p.payload_bytes;
    return 0;
}

int pas_prepare(const struct pas_context *c, struct pas_plan *out)
{
    if (!c || !out || !c->payload || !c->fdt || c->payload_bytes < HEADER ||
        c->payload_bytes > MAX_PAYLOAD)
        return PAS_BAD_INPUT;
    const uint8_t *d = c->payload;
    if (!magic(d, "SWEETXNU") || le32(d + 8) != 1)
        return PAS_BAD_PAYLOAD;
    uint64_t ao = le64(d + 32), az = le64(d + 40);
    if (ao < HEADER || (ao & 7) || !az || az > MAX_DT || !fits(ao, az, c->payload_bytes))
        return PAS_BAD_PAYLOAD;
    struct adt_view v;
    int status = adt_read(d + ao, (size_t)az, &v);
    if (status)
        return status;
    int enabled = v.req || v.io;
    if (v.actual || (enabled && (v.req != 1 || v.io != 1 || v.defaults != 1 || v.actual)))
        return PAS_BAD_REQUEST;
    struct pas_plan p;
    clear_metadata(&p, sizeof p);
    p.adt_offset = (uint32_t)ao;
    p.adt_bytes = (uint32_t)az;
    p.request_name = v.req_name;
    p.request_value = v.req_value;
    p.io_name = v.io_name;
    p.io_value = v.io_value;
    if (enabled) {
        status = request(d + ao + v.req_value, c->payload_bytes, &p.tail_offset);
        if (status)
            return status;
        if (!fits(ao, up(az, 8), p.tail_offset))
            return PAS_BAD_PAYLOAD;
    } else if (!fits(ao, up(az, 8), c->payload_bytes))
        return PAS_BAD_PAYLOAD;
    struct range input = {c->payload_pa, c->payload_bytes}, fdt = {c->fdt_pa, c->fdt_bytes},
                 shim = {c->shim_pa, c->shim_bytes};
    if (!valid(input) || !valid(fdt) || !valid(shim) || (c->payload_pa & 7) ||
        overlap(input, fdt) || overlap(input, shim) || overlap(fdt, shim))
        return PAS_OVERLAP;
    if (enabled) {
        uint64_t tail_pa = input.start + p.tail_offset;
        if (tail_pa > UINT64_MAX - (PAS_ALIGNMENT - 1))
            return PAS_RANGE;
        p.pa = up(tail_pa, PAS_ALIGNMENT);
        p.bytes = PAS_REGION_BYTES;
        if (!inside((struct range){p.pa, p.bytes}, (struct range){tail_pa, PAS_TAIL_BYTES}) ||
            !fits(p.pa, p.bytes, LIMIT))
            return PAS_RANGE;
    }
    p.managed_pa = le64(d + 56);
    p.managed_bytes = le64(d + 64);
    struct range managed = {p.managed_pa, p.managed_bytes};
    if (!valid(managed) || (p.managed_pa & 0x1ffffff) || (p.managed_bytes & (PAGE - 1)) ||
        v.base != managed.start || v.size != managed.size || overlap(input, managed) ||
        overlap((struct range){p.pa, p.bytes}, managed))
        return PAS_RANGE;
    uint64_t vb = le64(d + 16), ke = le64(d + 48), entry = le64(d + 24);
    uint32_t n = le32(d + 12);
    if (!n || n > MAX_SEGS || (entry & 3) || (vb & 0x1ffffff) || (ke & (PAGE - 1)) || ke < vb ||
        !fits(HEADER, 32u * n, ao))
        return PAS_BAD_PAYLOAD;
    uint64_t last = vb;
    unsigned entry_seen = 0;
    for (uint32_t i = 0; i < n; ++i) {
        const uint8_t *s = d + HEADER + 32 * i;
        uint64_t va = le64(s), vm = le64(s + 8), off = le64(s + 16), sz = le64(s + 24);
        if (!vm || ((va | vm | off) & 7) || va < last || !fits(va, vm, UINT64_MAX) || va < vb ||
            !fits(va - vb, vm, managed.size) || sz > UINT64_MAX - 7 || up(sz, 8) > vm ||
            off < HEADER + 32u * n || !fits(off, up(sz, 8), ao))
            return PAS_BAD_PAYLOAD;
        for (uint32_t j = 0; j < i; ++j) {
            const uint8_t *old = d + HEADER + 32 * j;
            if (overlap((struct range){off, up(sz, 8)},
                        (struct range){le64(old + 16), up(le64(old + 24), 8)}))
                return PAS_BAD_PAYLOAD;
        }
        struct range dest = {managed.start + va - vb, vm};
        if (overlap(dest, fdt) || overlap(dest, shim))
            return PAS_OVERLAP;
        if (sz && entry >= va && entry - va < sz)
            ++entry_seen;
        last = va + vm;
    }
    if (ke < last || entry_seen != 1 || !fits(ke - vb, az, managed.size))
        return PAS_BAD_PAYLOAD;
    uint64_t ap = managed.start + ke - vb;
    if (ap + az > UINT64_MAX - (PAGE - 1))
        return PAS_RANGE;
    uint64_t ba = up(ap + az, PAGE);
    if (!fits(ba, PAGE, managed.start + managed.size) ||
        overlap((struct range){ap, ba + PAGE - ap}, fdt) ||
        overlap((struct range){ap, ba + PAGE - ap}, shim))
        return PAS_OVERLAP;
    for (unsigned i = 0; i < v.maps; ++i)
        if (overlap(v.map[i], (struct range){p.pa, p.bytes}))
            return PAS_OVERLAP;
    p.payload_pa = input.start;
    p.payload_bytes = input.size;
    p.fdt_pa = fdt.start;
    p.fdt_bytes = fdt.size;
    p.shim_pa = shim.start;
    p.shim_bytes = shim.size;
    if (!enabled)
        return PAS_DISABLED;
    status = fdt_validate(c, &p);
    if (status)
        return status;
    copy_metadata(out, &p, sizeof p);
    return PAS_READY;
}

int pas_commit(uint8_t *d, size_t bytes, const struct pas_plan *p)
{
    if (!d || !p || bytes != p->adt_bytes)
        return PAS_BAD_INPUT;
    struct adt_view v;
    int status = adt_read(d, bytes, &v);
    if (status)
        return status;
    if (v.req != 1 || v.io != 1 || v.actual || v.defaults != 1 || v.req_name != p->request_name ||
        v.req_value != p->request_value || v.io_name != p->io_name || v.io_value != p->io_value ||
        v.base != p->managed_pa || v.size != p->managed_bytes)
        return PAS_BAD_ADT;
    uint64_t tail;
    status = request(d + v.req_value, p->payload_bytes, &tail);
    if (status || tail != p->tail_offset)
        return PAS_BAD_REQUEST;
    if (!fits(p->payload_pa, p->payload_bytes, UINT64_MAX) ||
        p->payload_pa + tail > UINT64_MAX - (PAS_ALIGNMENT - 1) ||
        p->pa != up(p->payload_pa + tail, PAS_ALIGNMENT) || p->bytes != PAS_REGION_BYTES ||
        !fits(p->pa, p->bytes, LIMIT) ||
        !inside((struct range){p->pa, p->bytes},
                (struct range){p->payload_pa + tail, PAS_TAIL_BYTES}) ||
        overlap((struct range){p->pa, p->bytes}, (struct range){v.base, v.size}))
        return PAS_RANGE;
    uint8_t *r = d + v.req_value, *io = d + v.io_value;
    put64(r + 64, p->pa);
    put64(r + 72, p->bytes);
    put64(r + 80, p->payload_pa);
    put64(r + 88, p->payload_bytes);
    put64(r + 96, p->fdt_pa);
    put64(r + 104, p->fdt_bytes);
    put64(r + 112, p->shim_pa);
    put64(r + 120, p->shim_bytes);
    for (unsigned i = 0; i < 8; ++i)
        r[i] = (uint8_t)"LPASOWN1"[i];
    put32(r + 12, 1);
    put64(io, p->pa);
    put64(io + 8, p->bytes);
    put32(io + 16, PAS_WIMG);
    put32(io + 20, PAS_SIGNATURE);
    name_set(d + v.req_name, "LowPASReservation");
    name_set(d + v.io_name, "pmap-io-ranges");
    return PAS_READY;
}
