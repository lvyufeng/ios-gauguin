#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { Z_WAITOK = 1, Z_ZERO = 2, SCAN358_FRAME_CAPACITY = 20480,
       SCAN358_PROBE_FIRST_LINE = 1728, SCAN358_PROBE_LIMIT = 1024,
       GUT_ARMED = 1, GUT_CAPTURE = 2, VM_PROT_READ = 1, VM_PROT_WRITE = 2,
       F344_GCC_PAGE = 1, F344_DISPCC_PA = 2, F344_MDP_PA = 3, F344_INTF_PAGE = 4,
       F344_PAGE = 16384, F344_INTF_OFF = 0x3000, F345_STARTUP_MS = 800 };
#define NSEC_PER_SEC UINT64_C(1000000000)
#define NSEC_PER_MSEC UINT64_C(1000000)
struct gut_event { uint64_t tick; };
struct mock_trace { unsigned state; };
typedef unsigned vm_prot_t;
typedef void (*thread_call_t)(void);
static struct gut_event storage[SCAN358_FRAME_CAPACITY];
static uint32_t map_words[F344_PAGE / sizeof(uint32_t)];
static struct mock_trace frames;
static struct { uint32_t numer, denom; } frame_timebase = {625, 12};
static struct {
    bool counter_opt_in, counter_readonly, crc_blanking, crc_preserve_idle_data, crc_blocked;
    uint64_t startup_end;
} scan;
static const volatile uint32_t *scan_gcc, *scan_disp, *scan_mdp;
static volatile uint32_t *scan_intf;
static thread_call_t scan_call;

static bool scan351_enabled, scan352_enabled, scan357_enabled;
static bool sweet_script_wake_mode, sweet_motion_mode;
static uint32_t stats, script_mode, physical_mode, refresh_hz, capture_capacity;
static unsigned arm_count, legacy_count, maps, poll_starts;
static bool desktop_enabled;
static const uint64_t now = 1;

static bool PE_parse_boot_argn(const char *name, void *out, size_t size)
{
    assert(size == sizeof(uint32_t));
    uint32_t value;
    if (!strcmp(name, "swp"))
        value = script_mode;
    else if (!strcmp(name, "sweetnvt"))
        value = physical_mode;
    else if (!strcmp(name, "sweetfb_hz"))
        value = refresh_hz;
    else {
        assert(!strcmp(name, "sweetfb_stats"));
        value = stats;
    }
    memcpy(out, &value, size);
    return true;
}

static bool sweet_metal_desktop_enabled(void) { return desktop_enabled; }
static void sweet_script_arm(void) { ++arm_count; }
static void sweet_swipe_arm(void) { ++legacy_count; }
static void nanoseconds_to_absolutetime(uint64_t ns, uint64_t *out) { *out = ns; }
static void clock_timebase_info(void *out) { assert(out == &frame_timebase); }

static struct gut_event *kalloc_data(size_t bytes, unsigned flags)
{
    assert(bytes <= sizeof(storage) && flags == (Z_WAITOK | Z_ZERO));
    return storage;
}

static void kfree_data(struct gut_event *events, size_t bytes)
{
    assert(events == storage && bytes <= sizeof(storage));
}

static bool gut_init_frames(struct mock_trace *state, struct gut_event *events,
                            uint32_t cap, uint64_t window, uint64_t tick)
{
    assert(events == storage && window == 45 * NSEC_PER_SEC && tick == now);
    state->state = GUT_ARMED;
    capture_capacity = cap;
    return true;
}

static uint64_t mach_absolute_time(void) { return now; }

static bool gut_report(struct mock_trace *trace, uint64_t begin, uint64_t end, unsigned pid, unsigned kind)
{
    assert(trace == &frames && trace->state == GUT_ARMED);
    assert(begin == now && end == now && pid == 0 && kind == 1);
    trace->state = GUT_CAPTURE;
    return true;
}

static uintptr_t ml_io_map_with_prot(unsigned page, unsigned bytes, vm_prot_t prot)
{
    assert(++maps == page && bytes == F344_PAGE);
    const bool writable = page == F344_INTF_PAGE && (!scan.counter_readonly || scan.crc_blanking);
    assert(prot == (VM_PROT_READ | (writable ? VM_PROT_WRITE : 0)));
    return (uintptr_t)map_words;
}

static void clock_interval_to_deadline(unsigned count, uint64_t unit, uint64_t *deadline)
{
    assert(count == F345_STARTUP_MS && unit == NSEC_PER_MSEC);
    *deadline = now + count * unit;
}

static void scan_poll(void) {}
static thread_call_t thread_call_allocate(thread_call_t call, const void *arg)
{
    assert(call == scan_poll && !arg);
    return call;
}

static void thread_call_enter(thread_call_t call)
{
    assert(call == scan_poll);
    ++poll_starts;
}

static void scan_stop(const char *cause)
{
    (void)cause;
    assert(false);
}

static int quiet_printf(const char *format, ...) { (void)format; return 0; }
#define printf quiet_printf
/* MODE_IMPLEMENTATIONS */
#undef printf

int main(void)
{
    unsigned cases = 0;
    for (stats = 1; stats <= 10; ++stats) {
        for (script_mode = 0; script_mode < 6; ++script_mode) {
            for (physical_mode = 0; physical_mode <= 1; ++physical_mode) {
                for (unsigned desktop = 0; desktop <= 1; ++desktop) {
                    for (refresh_hz = 60; refresh_hz <= 120; refresh_hz += 60) {
                        desktop_enabled = desktop;
                        arm_count = legacy_count = 0;
                        sweet_script_wake_mode = sweet_motion_mode = false;
                        touch_init_mode();
                        assert(arm_count == (!physical_mode && script_mode >= 2 && script_mode <= 4));
                        assert(legacy_count == (!physical_mode && script_mode == 1));
                        assert(sweet_script_wake_mode == (!physical_mode && (script_mode == 3 || script_mode == 4)));
                        assert(sweet_motion_mode == (!physical_mode && script_mode == 4));
                        bool eligible = stats >= 2 && stats <= 9 && desktop_enabled && !physical_mode &&
                                        (stats < 4 || refresh_hz == 60);
                        frames.state = 0;
                        frame_init_before();
                        assert(frames.state == (eligible && script_mode == 3 ? GUT_ARMED : 0));
                        frames.state = 0;
                        frame_init_after();
                        const bool expected = eligible && (script_mode == 3 || script_mode == 4);
                        assert(frames.state == (expected ? GUT_ARMED : 0));
                        if (expected) {
                            assert(capture_capacity == (stats == 9 ? 20480u : 16384u));
                            assert(scan.crc_blanking == (stats >= 5));
                            assert(scan357_enabled == (stats == 9));
                        }
                        maps = poll_starts = 0;
                        sweet_frame344_prepare();
                        sweet_frame344_prepare();
                        assert(frames.state == (expected ? GUT_CAPTURE : 0));
                        assert(maps == (expected ? 4 : 0));
                        assert(poll_starts == (expected ? 1 : 0));
                        ++cases;
                    }
                }
            }
        }
    }
    printf("%u gate and prepare combinations passed\n", cases);
    return 0;
}
