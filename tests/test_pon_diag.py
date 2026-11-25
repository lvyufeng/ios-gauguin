#!/usr/bin/env python3
"""Run the staged PON diagnostic with fake SPMI reads; no hardware access."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))

HARNESS = r'''
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <map>
#include <string>
#include <utility>
#include <vector>

static bool sp_ready = true;
@GUARD@

using Address = std::pair<unsigned, unsigned>;
static std::map<Address, uint8_t> values;
static std::vector<Address> reads;
static std::string log_output;
static int init_result;
static int sweet_spmi_init() { return init_result; }
static int sweet_spmi_read(unsigned sid, unsigned addr, uint8_t *out)
{
    assert(diagnostic_allowed(sid, addr, out) == 0);
    reads.emplace_back(sid, addr);
    auto found = values.find({sid, addr});
    if (found == values.end()) return -1;
    *out = found->second;
    return 0;
}
static void IOLog(const char *format, ...)
{
    char line[256];
    va_list args;
    va_start(args, format);
    int length = std::vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    assert(length > 0 && length < (int)sizeof(line));
    log_output += line;
}

@IMPLEMENTATION@

static void fixture()
{
    reads.clear(); values.clear(); log_output.clear(); init_result = 0;
    values[{0, 0x801}] = 1;
    values[{0, 0x804}] = 8;
    values[{0, 0x805}] = 4;
    values[{2, 0x1604}] = 0xff; // Unknown charger identity stays raw.
    values[{2, 0x1605}] = 0xfe;
    values[{2, 0x1651}] = 0xc2;
    values[{2, 0x1653}] = 0xfb;
}
static void expect_reads(std::vector<unsigned> primary)
{
    std::vector<Address> expected;
    for (unsigned reg : primary) expected.emplace_back(0, reg);
    for (unsigned reg : {0x1604u, 0x1605u, 0x1651u, 0x1653u})
        expected.emplace_back(2, reg);
    assert(reads == expected);
    assert(log_output.find("sid=2 base=0x1600 reg=0x1651 wd-cfg-raw=c2 rc=0") != std::string::npos);
    assert(log_output.find("reg=0x1605 subtype=fe rc=0") != std::string::npos);
}

int main()
{
    // Exhaust the newly admitted peripheral: precisely four bytes on SID2.
    uint8_t byte;
    for (unsigned sid = 0; sid < 16; ++sid) {
        for (unsigned reg = 0x1600; reg < 0x1700; ++reg) {
            bool expected = sid == 2 &&
                (reg == 0x1604 || reg == 0x1605 || reg == 0x1651 || reg == 0x1653);
            assert((diagnostic_allowed(sid, reg, &byte) == 0) == expected);
        }
    }
    assert(diagnostic_allowed(2, 0x1643, &byte) != 0); // Pet command excluded.
    assert(diagnostic_allowed(2, 0x1651, nullptr) != 0);
    assert(diagnostic_allowed(16, 0x1651, &byte) != 0);
    assert(diagnostic_allowed(0, 0x10000, &byte) != 0);
    sp_ready = false;
    assert(diagnostic_allowed(2, 0x1651, &byte) != 0);
    sp_ready = true;

#if defined(GAUGUIN)
    for (uint8_t subtype : {1, 2, 3}) {
        fixture(); values[{0, 0x805}] = subtype;
        sweet_pon_dump();
        expect_reads({0x801,0x804,0x805,0x808,0x809,0x80a,0x80b,0x80c,0x80d,0x80e,0x80f});
    }
    for (uint8_t subtype : {4, 5}) {
        fixture(); values[{0, 0x805}] = subtype;
        values[{0, 0x8c5}] = 2;
        sweet_pon_dump();
        expect_reads({0x801,0x804,0x805,0x8c0,0x8c2,0x8c5,0x8cb,0x8c7,0x8c8,0x8c9,0x8ca});
        assert(log_output.find("reg=0x8c5 poff1=02 rc=0") != std::string::npos);
        assert(log_output.find("reg=0x8c2 warm1=00 rc=-1") != std::string::npos);
    }
    for (uint8_t subtype : {0, 6, 0xff}) {
        fixture(); values[{0, 0x805}] = subtype;
        sweet_pon_dump();
        expect_reads({0x801,0x804,0x805});
        assert(log_output.find("reason layout unavailable") != std::string::npos);
    }
    fixture(); values.erase({0, 0x805});
    sweet_pon_dump();
    expect_reads({0x801,0x804,0x805});
    assert(log_output.find("subtype=00 rc=-1") != std::string::npos);
    fixture(); values.erase({2, 0x1651});
    sweet_pon_dump();
    assert(log_output.find("wd-cfg-raw=00 rc=-1") != std::string::npos);
#else
    fixture();
    for (unsigned reg : {0x1308u,0x1309u,0x1311u,0x1312u}) values[{6,reg}] = 0;
    sweet_pon_dump();
    assert((reads == std::vector<Address>{{6,0x1308},{6,0x1309},{6,0x1311},{6,0x1312}}));
    assert(log_output.find("unverified-legacy sid=6 base=0x1300") != std::string::npos);
#endif
    fixture(); init_result = -1;
    sweet_pon_dump();
    assert(reads.empty() && log_output.find("SPMI unavailable") != std::string::npos);
    puts("PON subtype/failure/legacy and bounded charger allowlist checks passed");
}
'''


def main():
    watchdog = SOURCE / 'iokit/Kernel/arm/SweetWatchdog.cpp'
    if not watchdog.exists():
        print(f'skip PON diagnostic test, source not staged at {SOURCE}')
        return
    source = watchdog.read_text()
    start = source.index('void\nsweet_pon_dump(void)')
    end = source.index('\n/*\n * Watchdog sampler:', start)
    implementation = source[start:end]
    spmi = (SOURCE / 'bsd/dev/sweet_spmi.c').read_text()
    start = spmi.index('int\nsweet_spmi_read(')
    end = spmi.index('\n\tIOLockLock(sp_lock);', start)
    guard = spmi[start:end].replace('sweet_spmi_read(', 'diagnostic_allowed(', 1)
    guard += '\nreturn 0;\n}\n'
    harness = HARNESS.replace('@IMPLEMENTATION@', implementation).replace('@GUARD@', guard)
    with tempfile.TemporaryDirectory(prefix='gauguin-pon-diag-') as directory:
        path = Path(directory)
        (path / 'test.cpp').write_text(harness)
        for board in ('gauguin', 'sweet'):
            flags = ['-DGAUGUIN=1'] if board == 'gauguin' else []
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall',
                            '-Wextra', '-Werror', '-Wno-unused-function', *flags,
                            str(path / 'test.cpp'), '-o', str(path / board)], check=True)
            subprocess.run([str(path / board)], check=True)


if __name__ == '__main__':
    main()
