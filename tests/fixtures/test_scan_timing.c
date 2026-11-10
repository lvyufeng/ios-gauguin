#include <assert.h>
#include <stdio.h>
#include "gauguin_scan_timing.h"

#define MS UINT64_C(1000000)
#define FB UINT32_C(0xa0000000)

enum route_variant {
    ROUTE_VIG, ROUTE_DMA2, ROUTE_BAD_FB, ROUTE_UNSTAGED, ROUTE_OTHER_PIPE,
    ROUTE_VIRTUAL, ROUTE_TWO_CTLS, ROUTE_TWO_PIPES, ROUTE_NO_PIPE,
    ROUTE_BAD_STRIDE, ROUTE_PENDING, ROUTE_CHANGED, ROUTE_GATED, ROUTE_CROSSED,
    ROUTE_SPLIT_INTERFACE,
};

struct fixture {
    uint64_t time, start;
    uint32_t rate, origin;
    unsigned mapped, maps, reads[GSCAN_REGION_COUNT], sleeps, crosses, route_frames;
    int fail_map, gate_region;
    bool gate_late, counters_off, stopped, unstable, stalled_clock, bad_line;
    enum route_variant variant;
};

static bool map(void *context, enum gscan_region region)
{
    struct fixture *f = context;
    assert(f->mapped == (unsigned)region);
    ++f->maps;
    if ((int)region == f->fail_map)
        return false;
    ++f->mapped;
    return true;
}

static void unmap(void *context, enum gscan_region region)
{
    struct fixture *f = context;
    assert(f->mapped == (unsigned)region + 1);
    --f->mapped;
}

static uint32_t read_word(void *context, enum gscan_region region, uint32_t offset)
{
    struct fixture *f = context;
    assert(f->mapped > (unsigned)region);
    unsigned ordinal = f->reads[region]++;
    if (f->mapped == GSCAN_REGION_COUNT) {
        if (region == GSCAN_GCC)
            return f->variant == ROUTE_GATED ? 0x80000001 : 1;
        if (region == GSCAN_DISP_CC)
            return 1;
        if (region == GSCAN_INTF) {
            if (offset == 0x3800)
                return 1;
            if (offset == 0x38a8)
                return 3;
            assert(offset == 0x38ac);
            unsigned extra = f->variant == ROUTE_CROSSED ? f->route_frames++ : 0;
            return f->origin + (uint32_t)((f->time - f->start) * f->rate / (1000 * MS)) + extra;
        }
        if (region == GSCAN_CTL) {
            unsigned ctl = (offset - 0x2000) / 0x200;
            unsigned field = (offset - 0x2000) % 0x200;
            assert(ctl < GSCAN_CTLS && field <= 0xf4);
            if (field == 0xf4)
                return ctl == 1 ? (f->variant == ROUTE_SPLIT_INTERFACE ? 3 : 2)
                    : (ctl == 0 && f->variant == ROUTE_TWO_CTLS ? 2 : 0);
            if (ctl != 1)
                return 0;
            if (field == 0x18)
                return f->variant == ROUTE_PENDING;
            if (field == 0x70 && f->variant == ROUTE_DMA2)
                return 1;
            if (field == 0xa0 && f->variant == ROUTE_VIRTUAL)
                return 1;
            if (field == 0 && f->variant != ROUTE_DMA2 && f->variant != ROUTE_UNSTAGED)
                return f->variant == ROUTE_OTHER_PIPE ? (1U << 18) | 1 : 1;
            return 0;
        }
        assert(region >= GSCAN_VIG && (offset & ~0x3000u) <= 0x38);
        bool source = f->variant == ROUTE_DMA2 ? region == GSCAN_DMA2 : region == GSCAN_VIG;
        if (f->variant == ROUTE_TWO_PIPES && region == GSCAN_DMA2)
            source = true;
        if (!source || f->variant == ROUTE_NO_PIPE)
            return 0;
        switch (offset & 0xfff) {
        case 0: return (2400U << 16) | 1080;
        case 0x14: return FB;
        case 0x24: return f->variant == ROUTE_BAD_STRIDE ? 4096 : 4320;
        case 0x30: return f->variant == ROUTE_CHANGED && f->sleeps >= 128 ? 0x601 : 0x600;
        default: return 0;
        }
    }
    static const uint32_t offsets[][5] = {
        {0x300c, 0x301c, 0x3070},
        {0x104c, 0x1010, 0x100c, 0x1028},
        {0x3800, 0x38a8, 0x38ac, 0x38b0, 0x38ac},
    };
    static const unsigned counts[] = {3, 4, 5};
    assert(offset == offsets[region][ordinal % counts[region]]);
    if ((int)region == f->gate_region && (!f->gate_late || f->sleeps >= 5))
        return 0x80000001;
    if (region != GSCAN_INTF)
        return 1;
    if (offset == 0x3800)
        return 1;
    if (offset == 0x38a8)
        return f->counters_off ? 0 : 3;
    if (f->stopped)
        return offset == 0x38b0 ? 17 : f->origin;
    uint64_t elapsed = f->time - f->start;
    uint64_t scaled = elapsed * f->rate;
    if (f->unstable && elapsed > 500 * MS)
        scaled += (elapsed - 500 * MS) * 60;
    if (offset == 0x38b0)
        return f->bad_line ? UINT32_MAX : (uint32_t)((scaled % (1000 * MS)) * 2465 / (1000 * MS));
    if (f->sleeps == 20 && ordinal % 5 == 4) {
        ++f->crosses;
        return f->origin + (uint32_t)(scaled / (1000 * MS)) + 1;
    }
    return f->origin + (uint32_t)(scaled / (1000 * MS));
}

static uint64_t now(void *context)
{
    struct fixture *f = context;
    return f->time;
}

static void sleep(void *context, unsigned ms)
{
    struct fixture *f = context;
    assert(ms == 8);
    ++f->sleeps;
    f->time += f->stalled_clock ? 0 : ms * MS;
}

static struct fixture fresh(uint32_t rate)
{
    return (struct fixture){
        .start = 1000 * MS, .time = 1000 * MS, .rate = rate, .origin = UINT32_MAX - 15,
        .fail_map = -1, .gate_region = -1,
    };
}

static struct gscan_result run(struct fixture *f, unsigned mode)
{
    const struct gscan_ops ops = {
        .context = f, .map = map, .unmap = unmap,
        .read = read_word, .now_ns = now, .sleep_ms = sleep,
        .framebuffer = {f->variant == ROUTE_BAD_FB ? 0 : FB, 1080, 2400, 4320},
    };
    struct gscan_result r;
    gauguin_scan_run(mode, &ops, &r);
    assert(f->mapped == 0 && f->sleeps <= 176);
    return r;
}

int main(void)
{
    struct fixture f = fresh(60);
    assert(run(&f, 0).status == GSCAN_DISABLED && f.maps == 0);
    assert(run(&f, 5).status == GSCAN_BAD_MODE && f.maps == 0);
    assert(run(&f, 1).status == GSCAN_GCC_READY && f.maps == 1 && !f.reads[GSCAN_DISP_CC]);
    f = fresh(60);
    assert(run(&f, 2).status == GSCAN_DISP_READY && f.maps == 2 && !f.reads[GSCAN_INTF]);

    for (uint32_t rate = 30; rate <= 120; rate += 30) {
        f = fresh(rate);
        struct gscan_result r = run(&f, 3);
        assert(r.status == GSCAN_MEASURED && r.crossed == 1 && f.crosses == 1);
        assert(r.samples == 125 && r.frames == rate && r.last_frame < r.first_frame);
        assert(r.millihz == rate * 1000 && r.nominal_hz == (rate >= 60 ? rate : 0));
    }

    f = fresh(60);
    f.fail_map = GSCAN_DISP_CC;
    assert(run(&f, 3).status == GSCAN_MAP_FAILED && f.maps == 2 && !f.reads[GSCAN_INTF]);
    f = fresh(60);
    f.gate_region = GSCAN_GCC;
    assert(run(&f, 3).status == GSCAN_CLOCK_GATED && f.maps == 1 && !f.reads[GSCAN_DISP_CC]);
    f = fresh(60);
    f.gate_region = GSCAN_DISP_CC;
    f.gate_late = true;
    assert(run(&f, 3).status == GSCAN_CLOCK_GATED && f.reads[GSCAN_INTF] == 25);
    f = fresh(60);
    f.counters_off = true;
    assert(run(&f, 3).status == GSCAN_COUNTERS_DISABLED && f.reads[GSCAN_INTF] == 2);
    f = fresh(60);
    f.stopped = true;
    assert(run(&f, 3).status == GSCAN_INSUFFICIENT);
    f = fresh(60);
    f.unstable = true;
    assert(run(&f, 3).status == GSCAN_UNSTABLE);
    f = fresh(60);
    f.bad_line = true;
    assert(run(&f, 3).status == GSCAN_BAD_SAMPLE);
    f = fresh(60);
    f.stalled_clock = true;
    assert(run(&f, 3).status == GSCAN_BAD_SAMPLE);

    static const enum gscan_route_status expected[] = {
        GSCAN_ROUTE_MATCHED, GSCAN_ROUTE_MATCHED, GSCAN_ROUTE_BAD_FRAMEBUFFER,
        GSCAN_ROUTE_NOT_STAGED, GSCAN_ROUTE_NOT_STAGED, GSCAN_ROUTE_NOT_STAGED,
        GSCAN_ROUTE_AMBIGUOUS, GSCAN_ROUTE_AMBIGUOUS, GSCAN_ROUTE_NO_MATCH,
        GSCAN_ROUTE_LAYOUT, GSCAN_ROUTE_LAYOUT, GSCAN_ROUTE_UNSTABLE,
        GSCAN_ROUTE_SCAN_LOST, GSCAN_ROUTE_UNSTABLE, GSCAN_ROUTE_AMBIGUOUS,
    };
    for (unsigned i = 0; i < sizeof(expected) / sizeof(expected[0]); ++i) {
        f = fresh(60);
        f.variant = (enum route_variant)i;
        struct gscan_result r = run(&f, GSCAN_ROUTE_MODE);
        if (r.route.status != expected[i])
            fprintf(stderr, "route case %u: got %u, expected %u\n", i, r.route.status, expected[i]);
        assert(r.status == GSCAN_MEASURED && r.route.status == expected[i]);
        if (r.route.status == GSCAN_ROUTE_MATCHED) {
            unsigned mask = i == ROUTE_VIG ? 1 : 8;
            assert(r.route.samples == 3 && r.route.pipe_mask == mask && r.route.ctl_mask == 2);
            assert(r.route.stages[1] == mask && r.route.virtual_stages[1] == 0);
        }
    }
    f = fresh(60);
    f.fail_map = GSCAN_DMA01;
    assert(run(&f, GSCAN_ROUTE_MODE).route.status == GSCAN_ROUTE_MAP_FAILED);
    assert(!f.reads[GSCAN_CTL] && !f.reads[GSCAN_VIG] && !f.reads[GSCAN_DMA2]);
    f = fresh(60);
    f.counters_off = true;
    assert(run(&f, GSCAN_ROUTE_MODE).route.status == GSCAN_ROUTE_NOT_RUN && f.maps == 3);
    puts("Actual scan core passed 16 cadence and 17 route scenarios.");
}
