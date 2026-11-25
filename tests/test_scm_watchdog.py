#!/usr/bin/env python3
"""Run the real shim SCM logic with a scripted monitor replacing only SMC.

The host executable cannot issue firmware calls. It checks the input registers
at every mocked SMC, then supplies responses to the unmodified control flow.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent

HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct exchange { uint64_t input[7], output[7]; };
static struct exchange script[80];
static unsigned script_count, calls, delay_count, delay_total, announce_count;
static uint32_t announced[4];

static void reset(void)
{
    memset(script, 0, sizeof(script));
    memset(announced, 0, sizeof(announced));
    script_count = calls = delay_count = delay_total = announce_count = 0;
}

static void expect_call(uint32_t fn, uint32_t arg, int32_t status, uint64_t value)
{
    assert(script_count < 80);
    struct exchange *e = &script[script_count++];
    e->input[0] = fn;
    e->input[1] = 1;
    e->input[2] = arg;
    e->output[0] = (uint64_t)(int64_t)status;
    e->output[1] = value;
}

static void mock_smc(uint64_t *x0, uint64_t *x1, uint64_t *x2, uint64_t *x3,
    uint64_t *x4, uint64_t *x5, uint64_t *x6)
{
    uint64_t *regs[] = { x0, x1, x2, x3, x4, x5, x6 };
    assert(calls < script_count);
    struct exchange *e = &script[calls++];
    for (unsigned i = 0; i < 7; i++) {
        assert(*regs[i] == e->input[i]);
        *regs[i] = e->output[i];
    }
}

static void delay_ms(unsigned ms)
{
    assert(ms == 30);
    delay_count++;
    delay_total += ms;
}
static void con_hex2(const char *tag, const char *a, uint64_t av,
    const char *b, uint64_t bv)
{
    (void)tag; (void)a; (void)av; (void)b; (void)bv;
}
static void loader_announce(uintptr_t dtb, const char *label, uint32_t value)
{
    assert(dtb == 0x1234);
    const char *labels[] = { "scmstep=", "scmabi=", "scmrc=", "scmret=" };
    assert(announce_count < 4);
    assert(strcmp(label, labels[announce_count]) == 0);
    announced[announce_count++] = value;
}

@IMPLEMENTATION@

static void check_probe(uint32_t step, uint32_t abi, int32_t status, uint32_t value)
{
    disable_secure_watchdog(0x1234);
    assert(calls == script_count && announce_count == 4);
    assert(announced[0] == step && announced[1] == abi);
    assert(announced[2] == (uint32_t)status && announced[3] == value);
}

int main(void)
{
    /* ABI64, successful availability and disable, preserve service result. */
    reset();
    expect_call(0xc2000601, 0x82000601, 0, 1);
    expect_call(0x42000601, 0x02000107, 0, 1);
    expect_call(0x42000107, 1, 0, 0x5a);
    check_probe(3, 64, 0, 0x5a);

    /* ABI32 fallback must omit the SMC64 bit from subsequent calls. */
    reset();
    expect_call(0xc2000601, 0x82000601, -1, 0);
    expect_call(0x82000601, 0x82000601, 0, 1);
    expect_call(0x02000601, 0x02000107, 0, 1);
    expect_call(0x02000107, 1, 0, 0);
    check_probe(3, 32, 0, 0);

    /* A zero availability result is unsupported even with transport success. */
    reset();
    expect_call(0xc2000601, 0x82000601, 0, 0);
    expect_call(0x82000601, 0x82000601, 0, 0);
    check_probe(1, 0, 0, 0);
    reset();
    expect_call(0xc2000601, 0x82000601, -1, 0);
    expect_call(0x82000601, 0x82000601, -2, 0x55);
    check_probe(1, 0, -2, 0x55);

    /* Never issue the mutating disable call after either query failure. */
    reset();
    expect_call(0xc2000601, 0x82000601, 0, 1);
    expect_call(0x42000601, 0x02000107, 0, 0);
    check_probe(2, 64, 0, 0);
    reset();
    expect_call(0xc2000601, 0x82000601, 0, 1);
    expect_call(0x42000601, 0x02000107, -1, 1);
    check_probe(2, 64, -1, 1);
    reset();
    expect_call(0xc2000601, 0x82000601, 0, 1);
    expect_call(0x42000601, 0x02000107, 0, 1);
    expect_call(0x42000107, 1, -2, 0x55);
    check_probe(3, 64, -2, 0x55);
    reset();
    expect_call(0xc2000601, 0x82000601, 0, 1);
    expect_call(0x42000601, 0x02000107, 0, 1);
    expect_call(0x42000107, 1, -2, (uint64_t)(int64_t)-4);
    check_probe(3, 64, -2, (uint32_t)-4);

    /* Busy retries reset argument registers after firmware clobbers them. */
    reset();
    expect_call(0x42000107, 1, -12, 0x55);
    for (unsigned i = 2; i < 7; i++) script[0].output[i] = 0x100 + i;
    expect_call(0x42000107, 1, 0, 0x66);
    struct scm_result result = scm_call_one(0x42000107, 1);
    assert(result.status == 0 && result.value == 0x66);
    assert(calls == 2 && delay_count == 1 && delay_total == 30);
    reset();
    for (unsigned i = 0; i < 8; i++) expect_call(0x42000107, 1, -12, i);
    result = scm_call_one(0x42000107, 1);
    assert((int32_t)result.status == -12 && result.value == 7);
    assert(calls == 8 && delay_count == 7 && delay_total == 210);

    /* Interrupted calls retain all returned registers, including x6. */
    reset();
    expect_call(0x42000107, 1, 1, 0x123);
    for (unsigned i = 2; i < 7; i++) script[0].output[i] = 0x200 + i;
    expect_call(0, 0, 0, 0x987);
    memcpy(script[1].input, script[0].output, sizeof(script[1].input));
    result = scm_call_one(0x42000107, 1);
    assert(result.status == 0 && result.value == 0x987);
    assert(calls == 2 && delay_count == 0);
    reset();
    for (unsigned i = 0; i < 64; i++) {
        expect_call(0x42000107, 1, 1, i);
        for (unsigned r = 2; r < 7; r++) script[i].output[r] = 0x300 + i + r;
        if (i) memcpy(script[i].input, script[i - 1].output, sizeof(script[i].input));
    }
    result = scm_call_one(0x42000107, 1);
    assert(result.status == 1 && result.value == 63);
    assert(calls == 64 && delay_count == 0);
    puts("all SCM protocol, capability, status and retry-bound checks passed");
    return 0;
}
'''


def main():
    source = (ROOT / 'shim/shim.c').read_text()
    start = source.index('struct scm_result {')
    end = source.index('static void __attribute__((noreturn)) reset(', start)
    implementation = source[start:end]
    implementation, count = re.subn(
        r'register uint64_t (x[0-6]) __asm__\("\1"\)',
        r'uint64_t \1', implementation)
    assert count == 7, 'SCM input register declarations changed'
    implementation, count = re.subn(
        r'__asm__ volatile\("smc #0".*?"memory"\);',
        'mock_smc(&x0, &x1, &x2, &x3, &x4, &x5, &x6);',
        implementation, flags=re.DOTALL)
    assert count == 1 and '__asm__' not in implementation
    with tempfile.TemporaryDirectory(prefix='gauguin-scm-test-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(HARNESS.replace('@IMPLEMENTATION@', implementation))
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', str(path / 'test.c'), '-o', str(path / 'test')],
                       check=True)
        subprocess.run([str(path / 'test')], check=True)


if __name__ == '__main__':
    main()
