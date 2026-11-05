#!/usr/bin/env python3
"""Exercise real touch entry points with hardware and thread creation mocked."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
@BOARD@
#define KERN_SUCCESS 0
typedef void (*thread_continue_t)(void *, int);
typedef void *thread_t;
static struct { bool started, thread_started; int irq_hint; } st;
static bool mode_present, enable_present, fail_create;
static int selected_mode, selected_enable;
static unsigned creates, hardware_ops, inline_probes, taps, deallocations;

static bool PE_parse_boot_argn(const char *name, void *value, int size)
{
    assert(size == sizeof(int));
    if (strcmp(name, "sweettouchmode") == 0) {
        if (mode_present) { *(int *)value = selected_mode; }
        return mode_present;
    }
    if (strcmp(name, "sweettouch") == 0) {
        if (enable_present) { *(int *)value = selected_enable; }
        return enable_present;
    }
    assert(strcmp(name, "sweettouchirq") == 0);
    return false;
}
static int quiet_printf(const char *format, ...) { (void)format; return 0; }
static void touch_bringup(void) { hardware_ops++; inline_probes++; }
static void touch_bringup_thread(void *arg, int result)
{
    (void)arg; (void)result;
    assert(!"The harness must never execute the experimental thread");
}
static void sweet_fb_mark(uint32_t colour) { (void)colour; hardware_ops++; }
static void sweet_log_mark(const char *text) { (void)text; }
void sweet_tap_arm(void) { taps++; }
static int kernel_thread_start(thread_continue_t function, void *arg, thread_t *thread)
{
    assert(function == touch_bringup_thread && arg == NULL);
    creates++;
    *thread = (void *)(uintptr_t)1;
    return fail_create ? 5 : KERN_SUCCESS;
}
static void thread_deallocate(thread_t thread)
{
    assert(thread == (void *)(uintptr_t)1);
    deallocations++;
}
#define printf quiet_printf
#define TOUCH_MARK(text) sweet_log_mark(text)
@START@
@INIT@
#undef printf

static void reset(void)
{
    memset(&st, 0, sizeof(st));
    mode_present = enable_present = fail_create = false;
    selected_mode = selected_enable = 0;
    creates = hardware_ops = inline_probes = taps = deallocations = 0;
}
static void expect_idle(void)
{
    assert(creates == 0 && hardware_ops == 0 && inline_probes == 0);
}

int main(void)
{
    reset();
    sweet_touch_init();
#if defined(GAUGUIN)
    expect_idle();
    assert(taps == 0 && !st.thread_started);
    reset();
    sweet_touch_start_at_init(); /* framebuffer/direct entry also stays idle */
    expect_idle();
    assert(!st.thread_started);
#else
    assert(creates == 1 && deallocations == 1 && inline_probes == 0);
#endif
    for (int mode = 0; mode <= 3; mode++) {
        reset(); mode_present = true; selected_mode = mode;
        sweet_touch_init();
        if (mode == 1) {
            assert(creates == 1 && deallocations == 1 && st.thread_started);
            assert(hardware_ops == 1 && inline_probes == 0);
            sweet_touch_init();
            assert(creates == 1); /* repeated init does not create another thread */
        } else {
            expect_idle();
            assert(taps == (mode == 3 ? 1u : 0u));
        }
    }
    reset(); enable_present = true; selected_enable = 0;
    mode_present = true; selected_mode = 1;
    sweet_touch_init();
    expect_idle();
    reset(); mode_present = true; selected_mode = 1; fail_create = true;
    sweet_touch_init();
    assert(creates == 1 && deallocations == 0 && inline_probes == 1);
    puts("touch defaults and explicit modes preserve entry-point behavior");
    return 0;
}
'''


def function(source, name):
    start = source.index('\n' + name + '(')
    end = source.index('\n}\n', start) + 3
    return 'void' + source[start:end]


def main():
    path = SOURCE / 'bsd/dev/sweet_touch.c'
    if not path.exists():
        print(f'skip touch gate test, source not staged at {SOURCE}')
        return
    source = path.read_text()
    start = source.index('#if defined(GAUGUIN)')
    end = source.index('\n#endif', start) + len('\n#endif')
    board = source[start:end]
    assert 'sparse GCC walk' not in source
    assert 'page < 0x19000' not in source
    assert 'a read cannot hang' not in source
    harness = HARNESS.replace('@BOARD@', board).replace(
        '@START@', function(source, 'sweet_touch_start_at_init')).replace(
        '@INIT@', function(source, 'sweet_touch_init'))
    with tempfile.TemporaryDirectory(prefix='gauguin-touch-gate-') as directory:
        build = Path(directory)
        (build / 'test.c').write_text(harness)
        for board_flags in (['-DGAUGUIN=1'], []):
            subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                            '-Werror', *board_flags, str(build / 'test.c'),
                            '-o', str(build / 'test')], check=True)
            subprocess.run([str(build / 'test')], check=True)
    print('GAUGUIN defaults perform no hardware operations or probe-thread creation')


if __name__ == '__main__':
    main()
