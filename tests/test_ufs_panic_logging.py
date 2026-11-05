#!/usr/bin/env python3
"""Keep the UFS panic flush path out of interrupt-disabled console I/O."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU_SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = XNU_SOURCE / 'bsd/dev/sweet_ufs.c'

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define MIN(a, b) ((a) < (b) ? (a) : (b))
static bool irq_enabled;
static unsigned console_calls, ring_calls;
static char captured[1024];

static bool ml_get_interrupts_enabled(void) { return irq_enabled; }

static int console_printf(const char *format, ...)
{
    assert(irq_enabled);
    assert(strcmp(format, "%s") == 0);
    console_calls++;
    va_list args;
    va_start(args, format);
    int length = vsnprintf(captured, sizeof(captured), format, args);
    va_end(args);
    assert(length >= 0 && length <= 255);
    return length;
}

static void sweet_log_append(const char *text, int length)
{
    assert(!irq_enabled);
    assert(length > 0 && length <= 255);
    ring_calls++;
    memcpy(captured, text, (size_t)length);
    captured[length] = 0;
}

#define printf console_printf
@FUNCTION@
#undef printf

static void reset(bool enabled)
{
    irq_enabled = enabled;
    console_calls = ring_calls = 0;
    memset(captured, 0, sizeof(captured));
}

static void check_route(bool enabled)
{
    assert(irq_enabled == enabled);
    assert(console_calls == (enabled ? 1u : 0u));
    assert(ring_calls == (enabled ? 0u : 1u));
}

int main(void)
{
    for (unsigned state = 0; state < 2; state++) {
        bool enabled = state != 0;
        reset(enabled);
        sweet_ufs_log("UFS failure %u at %#llx\n", 5u, 0x123456789ULL);
        check_route(enabled);
        assert(strcmp(captured, "UFS failure 5 at 0x123456789\n") == 0);

        reset(enabled);
        sweet_ufs_log("%s", "literal 100% %n %x");
        check_route(enabled);
        assert(strcmp(captured, "literal 100% %n %x") == 0);

        reset(enabled);
        char message[801];
        memset(message, 'x', sizeof(message) - 1);
        message[sizeof(message) - 1] = 0;
        sweet_ufs_log("%s", message);
        check_route(enabled);
        assert(strlen(captured) == 255);
        for (unsigned i = 0; i < 255; i++) {
            assert(captured[i] == 'x');
        }

        reset(enabled);
        sweet_ufs_log("%s", "");
        assert(console_calls == 0 && ring_calls == 0);
        assert(irq_enabled == enabled);
    }
    puts("UFS logging routing, formatting and truncation passed");
    return 0;
}
'''


def function_source(source, name):
    start = source.index('\n' + name + '(')
    end = source.index('\n}\n', start) + 3
    return source[start:end]


def main():
    if not SOURCE.exists():
        print(f'skip UFS panic logging test, source not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    # These functions form the logging and SCSI path reached by panic flush.
    for name, count in {'ufs_scsi_slot': 5, 'sweet_log_write_blocks': 1,
                        'sweet_log_sync_cache': 1, 'sweet_log_flush': 1}.items():
        body = function_source(source, name)
        assert re.search(r'\bprintf\s*\(', body) is None, name
        assert len(re.findall(r'\bsweet_ufs_log\s*\(', body)) == count, name
    helper = 'static void' + function_source(source, 'sweet_ufs_log')
    with tempfile.TemporaryDirectory(prefix='gauguin-ufs-panic-log-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(HARNESS.replace('@FUNCTION@', helper))
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', str(path / 'test.c'), '-o', str(path / 'test')],
                       check=True)
        subprocess.run([str(path / 'test')], check=True)
    print('all eight panic-flush diagnostic call sites use safe logging')


if __name__ == '__main__':
    main()
