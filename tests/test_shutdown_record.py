#!/usr/bin/env python3
"""Exercise the actual early shutdown recorder and optional reboot control."""
import os
from pathlib import Path
import re
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
#include <setjmp.h>

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define FALSE 0
#define THREAD_NULL NULL
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define PZERO 0
#define RB_AUTOBOOT 0
typedef int boolean_t;
typedef int wait_result_t;
struct proc { int p_pid; char p_comm[32]; } process;
static struct proc *process_ptr = &process;
static void *thread = (void *)(uintptr_t)1;
static bool irq_enabled = true, nested_flush;
static unsigned appends, flushes, irq_changes, proc_reads;
static char lines[2][256];

static size_t test_strlcpy(char *dest, const char *src, size_t size)
{
    size_t length = strlen(src);
    if (size) {
        size_t copied = MIN(length, size - 1);
        memcpy(dest, src, copied);
        dest[copied] = 0;
    }
    return length;
}
#undef strlcpy
#define strlcpy test_strlcpy
static void *current_thread(void) { return thread; }
static struct proc *current_proc(void) { proc_reads++; return process_ptr; }
static uint64_t mach_absolute_time(void) { return 123456789; }
static boolean_t ml_get_interrupts_enabled(void) { return irq_enabled; }
static boolean_t ml_set_interrupts_enabled(boolean_t enabled)
{
    boolean_t previous = irq_enabled;
    irq_enabled = enabled;
    irq_changes++;
    return previous;
}
static void sweet_log_append(const char *text, int length)
{
    assert(appends < 2 && length > 0 && length <= 255);
    memcpy(lines[appends], text, (size_t)length);
    lines[appends++][length] = 0;
}
void sweet_record_shutdown(unsigned, unsigned, unsigned, uintptr_t);
static void sweet_log_flush_panic(void)
{
    assert(!irq_enabled);
    assert(appends == flushes + 1); /* the record precedes every flush */
    flushes++;
    if (nested_flush) {
        nested_flush = false;
        sweet_record_shutdown(1, 99, 99, 99);
        sweet_record_shutdown(0, 99, 99, 99);
        assert(appends == 1 && flushes == 1);
    }
}
@RECORDER@

static int timer_seconds, timer_normal;
static bool normal_present;
static unsigned timer_prints, sleeps, reboots, panics;
static int sweet_log_chan, hz = 100;
static jmp_buf panic_return;
static bool PE_parse_boot_argn(const char *name, void *value, int size)
{
    assert(size == sizeof(int));
    if (strcmp(name, "sweetreboot") == 0) {
        *(int *)value = timer_seconds;
        return true;
    }
    assert(strcmp(name, "sweetrebootnormal") == 0);
    if (normal_present) { *(int *)value = timer_normal; }
    return normal_present;
}
static int timer_printf(const char *format, int seconds)
{
    assert(strcmp(format, "SWEET: debug reboot in %d s\n") == 0);
    assert(seconds == timer_seconds);
    timer_prints++;
    return 0;
}
static int tsleep(void *channel, int priority, const char *reason, int ticks)
{
    assert(channel == &sweet_log_chan && priority == PZERO);
    assert(strcmp(reason, "sweetreboot") == 0 && ticks == hz * timer_seconds);
    sleeps++;
    return 0;
}
static int reboot_kernel(int options, char *message)
{
    assert(options == RB_AUTOBOOT && message == NULL);
    reboots++;
    return 0;
}
static void panic(const char *format, int seconds)
{
    assert(strcmp(format, "SWEET: debug reboot timer (%d s)") == 0);
    assert(seconds == timer_seconds);
    panics++;
    longjmp(panic_return, 1);
}
#define printf timer_printf
@TIMER@
#undef printf

static void timer_case(int seconds, bool present, int normal)
{
    timer_seconds = seconds;
    normal_present = present;
    timer_normal = normal;
    timer_prints = sleeps = reboots = panics = 0;
    if (setjmp(panic_return) == 0) { sweet_reboot_thread(NULL, 0); }
    if (seconds <= 0) {
        assert(timer_prints == 0 && sleeps == 0 && reboots == 0 && panics == 0);
    } else {
        assert(timer_prints == 1 && sleeps == 1);
        bool normal_reboot = present && normal == 1;
        assert(reboots == (normal_reboot ? 1u : 0u));
        assert(panics == (normal_reboot ? 0u : 1u));
    }
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    process.p_pid = 42;
    strcpy(process.p_comm, "launchd");
    if (strcmp(argv[1], "timer") == 0) {
        timer_case(0, false, 0);
        timer_case(-1, true, 1);
        timer_case(15, false, 0);
        timer_case(15, true, 0);
        timer_case(15, true, 1);
        timer_case(15, true, 2);
        puts("normal reboot control is opt-in; default panic and disabled timer preserved");
        return 0;
    }
    if (strcmp(argv[1], "irq-off") == 0) { irq_enabled = false; }
    if (strcmp(argv[1], "no-proc") == 0) { process_ptr = NULL; }
    if (strcmp(argv[1], "no-thread") == 0) { thread = NULL; }
    if (strcmp(argv[1], "name-bound") == 0) {
        memset(process.p_comm, 'N', sizeof(process.p_comm));
    }
    if (strcmp(argv[1], "recursive") == 0) { nested_flush = true; }
    if (strcmp(argv[1], "invalid-stage") == 0) {
        sweet_record_shutdown(2, 99, 99, 99);
        assert(appends == 0 && flushes == 0 && irq_changes == 0);
    }
    bool initial_irq = irq_enabled;
    sweet_record_shutdown(0, 0x404, 0x55, 0xabcdef);
    assert(appends == 1 && flushes == 1 && irq_changes == 2);
    assert(irq_enabled == initial_irq);
    assert(strstr(lines[0], "stage=reboot_kernel") != NULL);
    assert(strstr(lines[0], "howto=0x404 details=0x55 at=123456789 caller=0xabcdef") != NULL);
    assert(strstr(lines[0], initial_irq ? "irq=1" : "irq=0") != NULL);
    if (process_ptr == NULL || thread == NULL) {
        assert(strstr(lines[0], "pid=-1 proc=<none>") != NULL);
    } else if (strcmp(argv[1], "name-bound") == 0) {
        char expected[64] = "proc=";
        memset(expected + 5, 'N', sizeof(process.p_comm));
        strcpy(expected + 5 + sizeof(process.p_comm), " howto=");
        assert(strstr(lines[0], expected) != NULL);
    } else {
        assert(strstr(lines[0], "pid=42 proc=launchd") != NULL);
    }
    assert(proc_reads == (thread == NULL ? 0u : 1u));
    sweet_record_shutdown(0, 0x999, 0x999, 0x999);
    assert(appends == 1 && flushes == 1 && irq_changes == 2);
    sweet_record_shutdown(1, 7, 0xaa, 0xfedcba);
    assert(appends == 2 && flushes == 2 && irq_changes == 4);
    assert(irq_enabled == initial_irq);
    assert(strstr(lines[1], "stage=platform") != NULL);
    assert(strstr(lines[1], "type=0x7 details=0xaa") != NULL);
    assert(strstr(lines[1], "caller=0xfedcba") != NULL);
    sweet_record_shutdown(1, 0x999, 0x999, 0x999);
    assert(appends == 2 && flushes == 2 && irq_changes == 4);
    puts(argv[1]);
    return 0;
}
'''


def function(source, name):
    start = source.index('\n' + name + '(')
    end = source.index('\n}\n', start) + 3
    return source[start:end]


def main():
    ufs_path = SOURCE / 'bsd/dev/sweet_ufs.c'
    if not ufs_path.exists():
        print(f'skip shutdown record test, source not staged at {SOURCE}')
        return
    ufs = ufs_path.read_text()
    recorder = 'void' + function(ufs, 'sweet_record_shutdown')
    assert re.search(r'\b(?:printf|proc_find|proc_name|proc_selfname)\s*\(', recorder) is None
    timer = 'static void' + function(ufs, 'sweet_reboot_thread')
    kernel = function((SOURCE / 'bsd/kern/kern_shutdown.c').read_text(), 'reboot_kernel')
    assert kernel.index('\tsweet_record_shutdown(0,') < kernel.index('\tif (')
    assert kernel.index('\tsweet_record_shutdown(0,') < kernel.index('lck_mtx_lock(')
    platform = function((SOURCE / 'iokit/Kernel/IOPlatformExpert.cpp').read_text(),
                        'PEHaltRestartInternal')
    hook = platform.index('\t\tsweet_record_shutdown(1,')
    assert hook < platform.index('IOService::getPMRootDomain()')
    assert hook < platform.index('handlePlatformHaltRestart(')
    for terminal_type in ('kPEHaltCPU', 'kPERestartCPU', 'kPEUPSDelayHaltCPU'):
        assert terminal_type in platform[:hook]
    assert 'SWEET: platform restart requested' not in platform
    harness = HARNESS.replace('@RECORDER@', recorder).replace('@TIMER@', timer)
    with tempfile.TemporaryDirectory(prefix='gauguin-shutdown-record-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(harness)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', str(path / 'test.c'), '-o', str(path / 'test')],
                       check=True)
        for case in ('normal', 'irq-off', 'no-proc', 'no-thread', 'name-bound',
                     'recursive', 'invalid-stage', 'timer'):
            subprocess.run([str(path / 'test'), case], check=True)
    print('early hooks, bounded metadata, IRQ restore and recursion guards passed')


if __name__ == '__main__':
    main()
