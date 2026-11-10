#include <assert.h>
#include <stdio.h>
#include "gauguin_scan_timing.h"

#define MS UINT64_C(1000000)

struct fixture {
    uint64_t time, start;
    uint32_t rate, origin;
    unsigned mapped, maps, reads[3], sleeps, crosses;
    int fail_map, gate_region;
    bool gate_late, counters_off, stopped, unstable, stalled_clock, bad_line;
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
    };
    struct gscan_result r;
    gauguin_scan_run(mode, &ops, &r);
    assert(f->mapped == 0 && f->sleeps <= 160);
    return r;
}

int main(void)
{
    struct fixture f = fresh(60);
    assert(run(&f, 0).status == GSCAN_DISABLED && f.maps == 0);
    assert(run(&f, 4).status == GSCAN_BAD_MODE && f.maps == 0);
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
    puts("Actual scan core passed 16 scenarios including wrap, boundary, drift and access guards.");
}
