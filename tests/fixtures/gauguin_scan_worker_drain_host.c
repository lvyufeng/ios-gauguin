#include "gauguin_page_flip.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

enum { F344_POLL_US = 1200, NSEC_PER_MSEC = 1000000, NSEC_PER_USEC = 1000 };
static struct { bool stop_requested; } scan382;
static struct { uint64_t end; } frames;
static struct { uint32_t frame; } scan;
struct scan351_position { uint32_t frame; };
static uint64_t now, rearm_at;
static bool capture_active, scan351_published, route_valid, owned;
#ifdef SUSTAINED417
#include "gauguin_sustain417.h"
static bool sustained417;
#endif
static unsigned scan_call, polls, outcome, stops;
static const char *stopped_for;

static uint64_t mach_absolute_time(void) { return now; }
static bool frame_active(void) { return capture_active; }
static void nanoseconds_to_absolutetime(uint64_t ns, uint64_t *ticks) { *ticks = ns; }
static void clock_interval_to_deadline(uint64_t n, uint64_t unit, uint64_t *deadline)
{
    *deadline = now + n * unit;
}
static bool scan351_position(struct scan351_position *p)
{
    p->frame = scan.frame;
    return route_valid;
}
static void thread_call_enter_delayed(unsigned call, uint64_t deadline)
{
    assert(call == scan_call);
    rearm_at = deadline;
}
bool sweet_frame382_active(void) { return owned; }
unsigned sweet_fb382_poll(uint32_t scan_number)
{
    assert(scan_number == scan.frame && scan382.stop_requested && scan351_published);
    ++polls;
    return outcome;
}
static void scan_stop(const char *reason)
{
    ++stops;
    stopped_for = reason;
    scan351_published = false;
}

static void report(const char *format, ...) { (void)format; }
#define printf report
#include "scan_worker_drain416.inc"
#undef printf

static void reset(void)
{
    memset(&scan416, 0, sizeof(scan416));
    scan382.stop_requested = false;
    now = 1;
    rearm_at = 0;
    frames.end = 45000ULL * NSEC_PER_MSEC;
    scan.frame = 42;
    capture_active = scan351_published = route_valid = owned = true;
    polls = stops = 0;
    outcome = F382_DRAIN_WAIT;
    stopped_for = NULL;
#ifdef SUSTAINED417
    sustained417 = false;
#endif
}

int main(void)
{
    reset();
    capture_active = false;
    struct scan351_position p;
    assert(sweet_frame382_ending() && scan382_position(&p) && p.frame == scan.frame);
    scan_finish("deadline");
    assert(polls == 1 && !stops && rearm_at == now + F344_POLL_US * NSEC_PER_USEC);
    now = rearm_at;
    outcome = F382_DRAIN_DONE;
    scan_finish(scan416.reason);
    assert(polls == 2 && stops == 1 && !scan382_position(&p));

    reset();
    scan_finish("route");
    assert(polls == 1 && !stops && sweet_frame382_ending() && !strcmp(scan416.reason, "route"));
    now += F382_DRAIN_MS * NSEC_PER_MSEC;
    scan_finish(scan416.reason);
    assert(polls == 1 && stops == 1 && !strcmp(stopped_for, "route"));

    reset();
    for (unsigned i = 0; i <= F382_DRAIN_POLLS; ++i)
        scan_finish("deadline");
    assert(polls == F382_DRAIN_POLLS && stops == 1);

    reset();
    outcome = F382_DRAIN_QUARANTINED;
    scan_finish("deadline");
    assert(polls == 1 && stops == 1 && !rearm_at && !scan351_published);

    reset();
    owned = false;
    scan_finish("deadline");
    assert(!polls && stops == 1 && !rearm_at && !scan382.stop_requested);

    reset();
    assert(!sweet_frame382_ending());
    now = frames.end - F382_DRAIN_MS * NSEC_PER_MSEC;
    route_valid = false;
    assert(sweet_frame382_ending() && !scan382_position(&p));
#ifdef SUSTAINED417
    reset();
    sustained417 = true;
    capture_active = false;
    assert(sweet_frame382_copy_limit() == F417_FLIP_LIMIT);
    assert(sweet_frame351_window() && !sweet_frame382_ending());
    now = frames.end - F382_DRAIN_MS * NSEC_PER_MSEC;
    assert(sweet_frame351_window() && sweet_frame382_ending());
    now = frames.end;
    assert(!sweet_frame351_window() && sweet_frame382_ending());
    scan_finish("deadline");
    assert(polls == 1 && !stops);
    puts("9");
#else
    puts("6");
#endif
}
