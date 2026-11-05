/* The actual candidate body is inserted below; only platform I/O is mocked. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define GAUGUIN 1
#define KERN_SUCCESS 0
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);

static const uint32_t expected_pages[] = {0x152000, 0x145000, 0x12d000};
static const uint32_t expected_reads[] = {0x152008, 0x145004, 0x14500c, 0x145014, 0x12d038};
static const uint32_t observed_values[] = {0x80000180, 0x80000002, 0x20000001, 0, 0xffffffff};
#define FAKE_VA UINT64_C(0xabcd000000000000)
static struct {
    int enabled, thread_error, bad_context, context_after_delay;
    unsigned starts, deallocations, terminations, sleeps, sleep_ms;
    unsigned maps, reads, markers, flushes, fail_map;
    thread_continue_t worker;
    char marker[192], log[8192];
    size_t log_bytes;
} mock;

static int test_printf(const char *format, ...)
{
    char line[256]; va_list args;
    va_start(args, format); int n = vsnprintf(line, sizeof(line), format, args); va_end(args);
    assert(n >= 0 && (size_t)n < sizeof(line));
    assert(mock.log_bytes + (size_t)n + 1 <= sizeof(mock.log));
    memcpy(mock.log + mock.log_bytes, line, (size_t)n + 1); mock.log_bytes += (size_t)n;
    return n;
}
bool PE_parse_boot_argn(const char *key, void *value, size_t bytes)
{
    assert(!strcmp(key, "sweetgpuprobe") && bytes == sizeof(int));
    *(int *)value = mock.enabled; return true;
}
kern_return_t kernel_thread_start(thread_continue_t fn, void *arg, thread_t *thread)
{
    assert(!arg); ++mock.starts;
    if (mock.thread_error) return mock.thread_error;
    mock.worker = fn; *thread = (thread_t)(uintptr_t)1; return 0;
}
void thread_deallocate(thread_t thread)
{ assert(thread == (thread_t)(uintptr_t)1); ++mock.deallocations; }
void thread_terminate_self(void) { ++mock.terminations; }
int ml_get_interrupts_enabled(void) { return mock.bad_context != 1; }
int ml_at_interrupt_context(void) { return mock.bad_context == 2; }
int get_preemption_level(void) { return mock.bad_context == 3; }
void IOSleep(unsigned milliseconds)
{
    assert(milliseconds == 1000 && mock.sleeps < 45 && !mock.maps && !mock.reads);
    ++mock.sleeps; mock.sleep_ms += milliseconds;
    if (mock.sleeps == 45) mock.bad_context = mock.context_after_delay;
}
void sweet_log_mark_sync(const char *line)
{
    assert(!strncmp(line, "SWEET GPU PROBE: ", 17) && strlen(line) < sizeof(mock.marker));
    assert(strstr(mock.log, line)); strcpy(mock.marker, line); ++mock.markers;
}
void sweet_log_flush_now(void) { assert(mock.flushes + 1 == mock.markers); ++mock.flushes; }
static void before_io(const char *phase)
{
    assert(mock.sleeps == 45 && mock.sleep_ms == 45000);
    assert(mock.markers && mock.markers == mock.flushes && strstr(mock.marker, phase));
    assert(!mock.bad_context);
}
vm_offset_t ml_io_map(vm_offset_t physical, vm_size_t size)
{
    before_io("map GCC");
    assert(mock.maps < 3 && physical == expected_pages[mock.maps] && size == 0x1000);
    ++mock.maps;
    if (mock.fail_map == mock.maps) return 0;
    return (vm_offset_t)(FAKE_VA + physical);
}
static uint32_t fake_read(vm_offset_t base, uint32_t offset)
{
    before_io("before read");
    assert(mock.reads < 5 && base >= FAKE_VA);
    assert(base - FAKE_VA + offset == expected_reads[mock.reads]);
    return observed_values[mock.reads++];
}
#define printf test_printf
@SOURCE@
#undef printf

static void reset(void) { memset(&mock, 0, sizeof(mock)); gpu_probe_started = 0; }
static void execute(void)
{
    assert(mock.worker && mock.starts == 1 && mock.deallocations == 1);
    mock.worker(NULL, 0);
    assert(mock.terminations == 1 && mock.markers == mock.flushes);
    assert(!strstr(mock.log, "abcd0000")); /* no fake/kernel mapping address logs */
}
int main(void)
{
    const int disabled[] = {0, -1, 2, 99};
    for (size_t i = 0; i < sizeof(disabled) / sizeof(disabled[0]); ++i) {
        reset(); mock.enabled = disabled[i]; sweet_gpu_probe_init(); sweet_gpu_probe_init();
        assert(!mock.starts && !mock.maps && !mock.reads && !mock.markers && !mock.log_bytes);
    }
    reset(); sweet_gpu_probe_init(); mock.enabled = 1;
    sweet_gpu_probe_init(); sweet_gpu_probe_init();
    assert(!mock.maps && !mock.reads && !mock.sleeps && !mock.markers); /* no inline work */
    execute(); assert(mock.maps == 3 && mock.reads == 5);
    assert(mock.markers == 15 && strstr(mock.log, "complete reads=5"));
    for (unsigned i = 0; i < 5; ++i) {
        char value[32]; snprintf(value, sizeof(value), "raw=%08x", observed_values[i]);
        assert(strstr(mock.log, value));
    }
    sweet_gpu_probe_init(); assert(mock.starts == 1 && mock.reads == 5);
    for (unsigned fail = 1; fail <= 3; ++fail) {
        const unsigned before_failure[] = {0, 1, 4};
        reset(); mock.enabled = 1; mock.fail_map = fail;
        sweet_gpu_probe_init(); execute();
        assert(mock.maps == fail && mock.reads == before_failure[fail - 1]);
        assert(strstr(mock.log, "map failed") && !strstr(mock.log, "complete reads=5"));
    }
    reset(); mock.enabled = 1; mock.thread_error = 5;
    sweet_gpu_probe_init(); sweet_gpu_probe_init();
    assert(mock.starts == 1 && !mock.worker && !mock.deallocations && !mock.terminations);
    assert(!mock.maps && !mock.reads && !mock.markers && !mock.sleeps);
    assert(strstr(mock.log, "no inline fallback"));
    for (int bad = 1; bad <= 3; ++bad) {
        reset(); mock.enabled = 1; mock.bad_context = bad;
        sweet_gpu_probe_init(); execute(); assert(!mock.maps && !mock.reads && !mock.sleeps && !mock.markers);
        reset(); mock.enabled = 1; mock.context_after_delay = bad;
        sweet_gpu_probe_init(); execute(); assert(!mock.maps && !mock.reads && mock.sleeps == 45);
    }
    puts("PASS: actual GPU probe flow; default off, 45s worker, once, thread/map/context failures, exact five reads and persistent phase ordering");
    return 0;
}
