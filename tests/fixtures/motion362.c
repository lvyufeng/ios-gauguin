#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

struct sweet_hid_touch_snapshot {
    unsigned active_mask, x[1], y[1];
};

#define NSEC_PER_MSEC 1000000ULL
static unsigned calls, fail_at, releases, empty_releases;
static uint64_t tick, scheduled;
static bool display_on;
static const void *sweet_script_call = &scheduled;

static uint32_t sweet_fb_display_state(void) { return display_on ? 1 : 2; }
static uint64_t mach_absolute_time(void) { return tick; }
static void clock_interval_to_deadline(unsigned ms, uint64_t units, uint64_t *end)
{
    *end = tick + ms * units;
}

static void thread_call_enter_delayed(const void *call, uint64_t due)
{
    assert(call == sweet_script_call && !scheduled && due > tick);
    scheduled = due;
}

static int sweet_hid_touch_frame(const struct sweet_hid_touch_snapshot *snapshot)
{
    unsigned step = calls++;
    assert(calls <= 163);
    tick += 2000;
    if (snapshot->active_mask) {
        assert(step <= 160 && snapshot->y[0] == 1200);
        assert(snapshot->x[0] == 900 - 720 * step / 160);
    } else {
        ++releases;
        if (!snapshot->x[0] && !snapshot->y[0])
            ++empty_releases;
        else
            assert(step == 161 && snapshot->x[0] == 180 && snapshot->y[0] == 1200);
    }
    return calls == fail_at ? 1 : 0;
}

/* MOTION_IMPLEMENTATION */

static void arm(unsigned failure)
{
    assert(!sweet_motion_armed);
    sweet_motion_mode = true;
    sweet_motion_step = 0;
    calls = releases = empty_releases = 0;
    tick = NSEC_PER_MSEC;
    fail_at = failure;
    display_on = true;
    if (sweet_motion_mode)
        sweet_motion_arm();
    assert(scheduled == tick + 2500 * NSEC_PER_MSEC);
    assert(sweet_motion_limit - sweet_motion_due == 2400 * NSEC_PER_MSEC);
}

static void fire(void)
{
    assert(sweet_motion_armed && scheduled);
    tick = scheduled;
    scheduled = 0;
    sweet_motion_fire(tick);
}

static void finish(void)
{
    for (unsigned i = 0; sweet_motion_armed && i < 163; ++i)
        fire();
    assert(!sweet_motion_armed && !scheduled);
}

int main(void)
{
    arm(0);
    finish();
    assert(calls == 162 && releases == 1 && !empty_releases);
    for (unsigned i = 1; i < SWEET_MOTION_REPORTS; ++i)
        assert(sweet_motion_samples[i].entered - sweet_motion_samples[i - 1].returned == 10 * NSEC_PER_MSEC);

    arm(0);
    scheduled = sweet_motion_limit;
    finish();
    assert(!calls);

    arm(0);
    fire();
    display_on = false;
    finish();
    assert(calls == 2 && releases == 1 && empty_releases == 1);

    arm(9);
    finish();
    assert(calls == 10 && releases == 1 && empty_releases == 1);

    arm(162);
    finish();
    assert(calls == 163 && releases == 2 && empty_releases == 1);
    return 0;
}
