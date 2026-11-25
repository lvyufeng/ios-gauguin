#include "gauguin_sustain417.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { NSEC_PER_MSEC = 1000000, NSEC_PER_SEC = 1000000000 };
struct sweet_hid_touch_snapshot {
    unsigned active_mask, x[10], y[10];
};

static unsigned sweet_script_call, display_on, reports, releases, x, y;
static uint64_t now, target;
static bool reject, reject_release;

static void nanoseconds_to_absolutetime(uint64_t ns, uint64_t *ticks) { *ticks = ns; }
static void clock_interval_to_deadline(uint64_t n, uint64_t unit, uint64_t *deadline)
{
    *deadline = now + n * unit;
}

static uint64_t mach_absolute_time(void) { return now; }
static unsigned sweet_fb_display_state(void) { return display_on; }
static void thread_call_enter_delayed(unsigned call, uint64_t at)
{
    assert(call == sweet_script_call && at > now);
    target = at;
}

static int sweet_hid_touch_frame(struct sweet_hid_touch_snapshot *position)
{
    if (!position->active_mask) {
        ++releases;
        return reject_release;
    }
    assert(position->active_mask == 1);
    ++reports;
    x = position->x[0];
    y = position->y[0];
    return reject;
}

static void report(const char *format, ...) { (void)format; }
#define printf report
#include "sustain_motion417.inc"
#undef printf

static void reset(void)
{
    memset(&motion417, 0, sizeof(motion417));
    sweet_continuous_mode = true;
    display_on = 1;
    reports = releases = x = y = 0;
    reject = reject_release = false;
    now = 100;
    motion417_arm();
    assert(sweet_continuous_mode && motion417.armed && target == now + 6ULL * NSEC_PER_SEC);
}

static void fire(uint64_t when)
{
    now = when;
    assert(motion417.armed);
    motion417_fire(now);
}

int main(void)
{
    for (unsigned capture = 0; capture <= 10; ++capture)
        for (unsigned script = 0; script <= 6; ++script)
            for (unsigned physical = 0; physical <= 1; ++physical)
                for (unsigned hz = 0; hz <= 120; ++hz)
                    assert(f417_profile(capture, script, physical, hz) ==
                           (capture == 9 && script == 5 && physical == 0 && hz == 60));
    assert(f417_position(0) == 900 && f417_position(F417_HALF_DRAG) == 180);
    for (unsigned i = 1; i < F417_REPORT_LIMIT; ++i) {
        const unsigned from = f417_position(i - 1), to = f417_position(i);
        assert(to >= 180 && to <= 900);
        assert((i - 1) / F417_HALF_DRAG % 2 ? to > from : to < from);
    }

    reset();
    fire(target - 1);
    assert(!reports && !releases && !motion417.start);
    const uint64_t start = target;
    for (unsigned i = 0; i < F417_REPORT_LIMIT; ++i) {
        assert(target == start + i * motion417.interval);
        fire(target);
        assert(x == f417_position(i) && y == 1200);
    }
    fire(target);
    assert(!motion417.armed && reports == F417_REPORT_LIMIT && releases == 1 &&
           motion417.max_gap == motion417.interval && now - start == 33ULL * NSEC_PER_SEC);

    reset();
    fire(target);
    const uint64_t first = motion417.start;
    fire(target + 3 * motion417.interval + 7);
    assert(reports == 2 && x == f417_position(4) && target == first + 5 * motion417.interval &&
           motion417.max_gap == 4 * motion417.interval + 7);

    reset();
    display_on = 0;
    fire(target);
    assert(!motion417.armed && !reports && !releases);

    reset();
    fire(target);
    display_on = 0;
    fire(target);
    assert(!motion417.armed && reports == 1 && releases == 1);

    reset();
    reject = reject_release = true;
    fire(target);
    assert(!motion417.armed && reports == 1 && releases == 1);
    puts("7");
}
