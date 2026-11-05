#!/usr/bin/env python3
"""Exercise the actual secure diagnostic reader against fake physical memory.

The sampler accepts one observed SRAM window plus a bounded DRAM window. These
checks guard mapping and header bounds, ring wrap, one-second scheduling, and
suppression of unchanged text. No device or firmware access is performed.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU_SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = XNU_SOURCE / 'iokit/Kernel/arm/SweetWatchdog.cpp'

HARNESS = r'''
#include <cassert>
#include <cstdarg>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#define GAUGUIN 1
#define NSEC_PER_SEC 1000000000u
using vm_offset_t = uintptr_t;
using vm_size_t = size_t;
using thread_call_param_t = void *;
using thread_call_t = void *;

static uint32_t imem[0x418 / 4];
alignas(4096) static uint8_t tzdata[0x3000];
alignas(4096) static uint8_t hypdata[0x2000];
static unsigned map_calls, schedules;
static uint32_t fail_physical;
static bool fail_allocation;
static int enabled_arg;
static uint64_t now_ticks, next_deadline;
static std::vector<std::string> messages;

static uint64_t mach_absolute_time()
{
    return now_ticks;
}

static vm_offset_t ml_io_map(vm_offset_t physical, vm_size_t size)
{
    map_calls++;
    if (physical == fail_physical) {
        return 0;
    }
    if (physical == 0x146aa720 && size == sizeof(imem)) {
        return reinterpret_cast<vm_offset_t>(imem);
    }
    if ((physical == 0x14696000 || physical == 0x80910000) && size == sizeof(tzdata)) {
        return reinterpret_cast<vm_offset_t>(tzdata);
    }
    if (physical == 0x80920000 && size == sizeof(hypdata)) {
        return reinterpret_cast<vm_offset_t>(hypdata);
    }
    assert(false && "unexpected or unvalidated physical mapping");
    return 0;
}

static bool PE_parse_boot_argn(const char *key, void *value, size_t size)
{
    assert(std::strcmp(key, "sweettzsample") == 0 && size == sizeof(int));
    *static_cast<int *>(value) = enabled_arg;
    return true;
}

static void IOLog(const char *format, ...)
{
    char line[1024];
    va_list args;
    va_start(args, format);
    int length = std::vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    assert(length > 0 && length < 256);
    messages.emplace_back(line);
}

static void clock_interval_to_deadline(unsigned interval, unsigned scale, uint64_t *result)
{
    assert(interval == 1 && scale == NSEC_PER_SEC);
    *result = now_ticks + 19200000;
}

static thread_call_t thread_call_allocate(void (*callback)(void *, void *), void *arg)
{
    assert(callback && arg == nullptr);
    if (fail_allocation) {
        return nullptr;
    }
    return reinterpret_cast<void *>(1);
}

static void thread_call_enter_delayed(thread_call_t call, uint64_t deadline)
{
    assert(call && deadline == now_ticks + 19200000);
    next_deadline = deadline;
    schedules++;
}

@IMPLEMENTATION@

static void write32(uint8_t *buffer, unsigned offset, uint32_t value)
{
    std::memcpy(buffer + offset, &value, sizeof(value));
}

static void fixture()
{
    std::memset(imem, 0, sizeof(imem));
    std::memset(tzdata, 0, sizeof(tzdata));
    std::memset(hypdata, 0, sizeof(hypdata));
    sweet_tz_buffer = {};
    sweet_hyp_buffer = {};
    sweet_secure_diag_call = nullptr;
    sweet_secure_diag_imem = nullptr;
    sweet_secure_diag_round = map_calls = schedules = 0;
    now_ticks = 192000000;
    next_deadline = fail_physical = 0;
    fail_allocation = false;
    messages.clear();
    enabled_arg = 1;

    imem[0] = 0x14696000;
    imem[0x410 / 4] = 0x80920000;
    imem[0x414 / 4] = sizeof(hypdata);
    write32(tzdata, 0, 0x747a6461);
    write32(tzdata, 4, 0x90001);
    write32(tzdata, 8, 8);
    write32(tzdata, 20, 40);
    write32(tzdata, 28, 512);
    write32(tzdata, 32, 512);
    write32(tzdata, 508, 64u << 16);
    std::memcpy(tzdata + 512, "bounded TZ log %n", 17);

    write32(hypdata, 0, 0x6879706d);
    write32(hypdata, 4, 8);
    write32(hypdata, 8, 128);
    write32(hypdata, 12, 128u << 16);
    write32(hypdata, 16, sizeof(hypdata) - 128);
    write32(hypdata, 20, 7);
    std::memcpy(hypdata + 128, "bounded HYP log", 15);
}

static unsigned logged(const char *needle)
{
    unsigned count = 0;
    for (const auto &line : messages) {
        if (line.find(needle) != std::string::npos) {
            count++;
        }
    }
    return count;
}

static void sample()
{
    now_ticks = next_deadline;
    sweet_secure_diag_sample(nullptr, nullptr);
}

static void expect_invalid_headers()
{
    sweet_secure_diag_start();
    sample();
    assert(sweet_tz_buffer.stopped && sweet_hyp_buffer.stopped);
    assert(schedules == 1 && logged("sampling finished after 1 rounds"));
}

int main()
{
    /* Only the exact observed SRAM allocation is accepted. */
    assert(sweet_diag_phys_range(0x14696000, 0x3000));
    assert(!sweet_diag_phys_range(0x14695000, 0x3000));
    assert(!sweet_diag_phys_range(0x14697000, 0x3000));
    assert(!sweet_diag_phys_range(0x14696000, 0x2fff));
    assert(!sweet_diag_phys_range(0x14696000, 0x3001));
    assert(!sweet_diag_phys_range(0x17c10000, 0x1000));
    assert(sweet_diag_phys_range(0x80000000, 40));
    assert(sweet_diag_phys_range(0xbbaf0000, 0x10000));
    assert(!sweet_diag_phys_range(0x80910004, 0x3000));
    assert(!sweet_diag_phys_range(0x80910000, 0x10001));
    assert(!sweet_diag_phys_range(0xbbb00000, 40));
    assert(!sweet_diag_phys_range(0xfffff000, 0x1000));
    assert(!sweet_diag_region(UINT32_MAX, 1, 0x3000));
    assert(!sweet_diag_region(40, UINT32_MAX, 0x3000));

    for (int disabled : {0, 2}) {
        fixture();
        enabled_arg = disabled;
        sweet_secure_diag_start();
        assert(map_calls == 0 && schedules == 0);
    }

    fixture();
    sweet_secure_diag_start();
    assert(map_calls == 1 && schedules == 1);
    sweet_secure_diag_start();
    assert(map_calls == 1 && schedules == 1);
    sample();
    assert(map_calls == 3 && schedules == 2);
    assert(!sweet_tz_buffer.stopped && !sweet_hyp_buffer.stopped);
    assert(logged("s2_faults=7") && logged("bounded TZ log %n"));
    assert(logged("bounded HYP log"));

    /* Unchanged buffers are quiet. Counter changes need no repeated text. */
    messages.clear();
    sample();
    assert(messages.empty());
    write32(hypdata, 20, 9);
    sample();
    assert(logged("s2_faults=9") == 1 && logged(" tail ") == 0);
    messages.clear();
    sample();
    assert(messages.empty());
    write32(hypdata, 12, 129u << 16);
    sample();
    assert(logged("HYP round=5") && logged("HYP tail "));
    messages.clear();
    for (unsigned round = 6; round <= 9; round++) {
        sample();
    }
    assert(messages.empty());
    sample();
    assert(logged("TZ round=10") == 1 && logged("HYP round=10") == 1);
    assert(logged(" tail ") == 0);
    while (sweet_secure_diag_round < 300) {
        sample();
    }
    assert(SWEET_DIAG_ROUNDS == 300 && schedules == 300 && map_calls == 3);
    assert(logged("sampling finished after 300 rounds") == 1);

    /* A wrapped ring joins its physical end to its beginning. */
    fixture();
    std::memset(tzdata + 512, 'A', 512);
    std::memcpy(tzdata + 512 + 509, "END", 3);
    std::memcpy(tzdata + 512, "BEGIN", 5);
    write32(tzdata, 508, (5u << 16) | 1u);
    sweet_secure_diag_start();
    sample();
    assert(logged("ENDBEGIN") && logged("TZ tail ") == 2);

    for (uint32_t physical : {0x17c10000u, 0x80910004u, 0x14695000u, 0x14697000u}) {
        fixture();
        imem[0] = physical;
        sweet_secure_diag_start();
        sample();
        assert(sweet_tz_buffer.stopped && map_calls == 2);
    }
    fixture();
    imem[0] = 0x80910000;
    sweet_secure_diag_start();
    sample();
    assert(!sweet_tz_buffer.stopped && sweet_tz_buffer.physical == 0x80910000);

    fixture();
    imem[0x414 / 4] = 0x10001;
    sweet_secure_diag_start();
    sample();
    assert(sweet_hyp_buffer.stopped && map_calls == 2);

    fixture();
    write32(tzdata, 20, UINT32_MAX);
    write32(hypdata, 8, UINT32_MAX);
    expect_invalid_headers();
    fixture();
    write32(tzdata, 4, 0x90002);
    write32(hypdata, 0, 0x68797064);
    expect_invalid_headers();
    fixture();
    write32(tzdata, 508, 512u << 16);
    write32(hypdata, 12, 0xffff0000);
    expect_invalid_headers();
    for (uint32_t cpus : {0u, 9u}) {
        fixture();
        write32(tzdata, 8, cpus);
        write32(hypdata, 4, cpus);
        expect_invalid_headers();
    }

    fixture();
    sweet_secure_diag_start();
    sample();
    imem[0] = 0x80930000;
    sample();
    assert(sweet_tz_buffer.stopped && map_calls == 3);
    assert(logged("firmware buffer moved"));

    fixture();
    fail_physical = 0x146aa720;
    sweet_secure_diag_start();
    assert(map_calls == 1 && schedules == 0 && logged("IMEM mapping failed"));
    fixture();
    fail_allocation = true;
    sweet_secure_diag_start();
    assert(map_calls == 1 && schedules == 0 && logged("callout allocation failed"));
    fixture();
    fail_physical = 0x14696000;
    sweet_secure_diag_start();
    sample();
    assert(sweet_tz_buffer.stopped && !sweet_hyp_buffer.stopped);
    assert(logged("TZ stopped: mapping failed"));

    std::puts("secure diagnostic SRAM/bounds, ring, counter, quiet and scheduling checks passed");
}
'''


def main():
    if not SOURCE.exists():
        print(f'skip secure diagnostic test, source not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    start = source.index('#define SWEET_DIAG_IMEM_PA ')
    end = source.index('\nvoid\nsweet_wdt_thread_start(void)', start)
    implementation = source[start:end]
    with tempfile.TemporaryDirectory(prefix='gauguin-secure-diag-') as directory:
        path = Path(directory)
        (path / 'test.cpp').write_text(HARNESS.replace('@IMPLEMENTATION@', implementation))
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall',
                        '-Wextra', '-Werror', str(path / 'test.cpp'),
                        '-o', str(path / 'test')], check=True)
        subprocess.run([str(path / 'test')], check=True)


if __name__ == '__main__':
    main()
