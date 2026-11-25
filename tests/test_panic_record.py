#!/usr/bin/env python3
"""Exercise the real panic recorder with memory-only logging and IRQ mocks."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU_SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = XNU_SOURCE / 'osfmk/kern/debug.c'

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned long long uint64_t;
typedef bool boolean_t;
#define FALSE false
#define MIN(a, b) ((a) < (b) ? (a) : (b))

static unsigned debug_boot_arg = 0xc, panicDebugging = 1;
static bool irq_enabled = true, reenter;
static unsigned append_calls, flush_calls, irq_calls;
static int append_lengths[8];
static size_t used;
static char captured[2048];

static void invoke_and_check(const char *format, ...);

static void append(const char *text, int length)
{
    assert(length > 0 && length <= 511);
    assert(append_calls < 8);
    append_lengths[append_calls++] = length;
    assert(used + (size_t)length < sizeof(captured));
    memcpy(captured + used, text, (size_t)length);
    used += (size_t)length;
    captured[used] = 0;
}

static boolean_t ml_set_interrupts_enabled(boolean_t enabled)
{
    bool previous = irq_enabled;
    if (irq_calls == 0) {
        assert(enabled == false);
    }
    irq_calls++;
    irq_enabled = enabled;
    return previous;
}

static void flush(void)
{
    assert(!irq_enabled);
    assert(used > 0 && captured[used - 1] == '\n');
    flush_calls++;
    if (reenter) {
        invoke_and_check("nested panic %d", 99);
    }
}

static void (*sweet_log_append)(const char *, int) = append;
static void (*sweet_log_flush_panic)(void) = flush;

@FUNCTION@

static void invoke_and_check(const char *format, ...)
{
    char expected[4096], after[4096];
    va_list arguments, copy;
    va_start(arguments, format);
    va_copy(copy, arguments);
    int expected_length = vsnprintf(expected, sizeof(expected), format, copy);
    va_end(copy);
    sweet_record_panic(format, &arguments, 77, 0xfedcULL, 0x123456UL);
    int actual_length = vsnprintf(after, sizeof(after), format, arguments);
    va_end(arguments);
    assert(actual_length == expected_length);
    assert(strcmp(after, expected) == 0);
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    const char *scenario = argv[1];
    bool initial_irq = strcmp(scenario, "irq-off") != 0;
    irq_enabled = initial_irq;
    reenter = strcmp(scenario, "reentrant") == 0;

    if (strcmp(scenario, "missing-append") == 0) {
        sweet_log_append = NULL;
        invoke_and_check("uncaptured %d", 17);
        assert(append_calls == 0 && flush_calls == 0 && irq_calls == 0);
        sweet_log_append = append;
    }
    if (strcmp(scenario, "missing-flush") == 0) {
        sweet_log_flush_panic = NULL;
    }
    if (strcmp(scenario, "long") == 0) {
        char message[2001];
        memset(message, 'x', sizeof(message) - 1);
        message[sizeof(message) - 1] = 0;
        invoke_and_check("%s suffix-%d", message, 42);
        assert(append_calls == 3 && append_lengths[1] == 511);
        const char *body = strchr(captured + 1, '\n') + 1;
        for (unsigned i = 0; i < 511; i++) {
            assert(body[i] == 'x');
        }
        assert(body[511] == '\n' && body[512] == 0);
    } else {
        invoke_and_check("reason %d %s %#llx", 42, "kept", 0xabcdefULL);
        assert(strstr(captured, "reason 42 kept 0xabcdef\n") != NULL);
        assert(append_calls == 3);
    }

    assert(strstr(captured, "caller=0x123456 reason=77 options=0xfedc debug=0xc hold=1\n") != NULL);
    assert(irq_enabled == initial_irq);
    if (sweet_log_flush_panic != NULL) {
        assert(flush_calls == 1 && irq_calls == 2);
    } else {
        assert(flush_calls == 0 && irq_calls == 0);
    }

    size_t saved_used = used;
    unsigned saved_appends = append_calls;
    unsigned saved_flushes = flush_calls;
    unsigned saved_irq_calls = irq_calls;
    invoke_and_check("later panic %d", 123);
    assert(used == saved_used && append_calls == saved_appends);
    assert(flush_calls == saved_flushes && irq_calls == saved_irq_calls);
    assert(irq_enabled == initial_irq);
    puts(scenario);
    return 0;
}
'''


def main():
    if not SOURCE.exists():
        print(f'skip panic recorder test, source not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    start = source.index('static void\nsweet_record_panic(')
    end = source.index('\n}\n', start) + 3
    function = source[start:end]
    with tempfile.TemporaryDirectory(prefix='gauguin-panic-record-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(HARNESS.replace('@FUNCTION@', function))
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', str(path / 'test.c'), '-o', str(path / 'test')],
                       check=True)
        # Each process gets a fresh copy of the function's first-panic guard.
        for scenario in ('normal', 'long', 'irq-off', 'missing-append',
                         'missing-flush', 'reentrant'):
            subprocess.run([str(path / 'test'), scenario], check=True)
    print('all panic record bounds, varargs, IRQ and first-panic checks passed')


if __name__ == '__main__':
    main()
