#!/usr/bin/env python3
"""Exercise the actual marker flush function against a fake SCSI target.

The former WRITE(10) command always addressed device LBA zero. These checks
decode every submitted command and exercise bounds, failures and a mark
published while the previous version is in flight.
"""
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
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define UFS_BLOCK 4096u
#define SWEET_LOG_BLOCKS 1025u
#define SWEET_MARK_BLOCKS 64u
#define DMA_MARK 0u
@SLOT_DEFINITION@
#define TRUE 1
typedef uintptr_t addr64_t;
static struct {
    bool ready, writable;
    uint64_t first_block, nblocks, dma_pa;
    uintptr_t dma;
} su;
static unsigned sweet_mark_lock;
static uint8_t bounce[UFS_BLOCK];
static uint8_t sweet_mark_ram[SWEET_MARK_BLOCKS * UFS_BLOCK];
static uint32_t sweet_mark_dirty[SWEET_MARK_BLOCKS / 32];
static unsigned calls;
static uint64_t addresses[SWEET_MARK_BLOCKS];
static bool fail_write, publish_during_write;

static void lck_mtx_lock(unsigned *lock) { assert(!*lock); *lock = 1; }
static void lck_mtx_unlock(unsigned *lock) { assert(*lock); *lock = 0; }
static void clean_dcache64(addr64_t pa, uint32_t length, int physical)
{
    assert(pa == su.dma_pa && length == UFS_BLOCK && physical);
}
static int ufs_scsi_slot(const uint8_t *cdb, unsigned cdb_len, uint32_t len,
    bool write, uintptr_t pa, unsigned slot)
{
    assert(cdb_len == 10 && cdb[0] == 0x2a);
    assert(cdb[1] == 0 && cdb[6] == 0 && cdb[7] == 0);
    assert(cdb[8] == 1 && cdb[9] == 0);
    assert(len == UFS_BLOCK && write && pa == su.dma_pa);
    assert(slot == UFS_SLOT_MARK && sweet_mark_lock == 1);
    uint64_t lba = (uint32_t)cdb[2] << 24 | (uint32_t)cdb[3] << 16 |
        (uint32_t)cdb[4] << 8 | cdb[5];
    assert(calls < SWEET_MARK_BLOCKS);
    addresses[calls++] = lba;
    assert(lba != 0 && lba >= su.first_block);
    assert(lba - su.first_block < su.nblocks);
    if (publish_during_write) {
        publish_during_write = false;
        sweet_mark_ram[0] = 0x77;
        __atomic_fetch_or(&sweet_mark_dirty[0], 1u, __ATOMIC_RELEASE);
    }
    return fail_write ? 5 : 0;
}

@FUNCTION@

static void reset(void)
{
    memset(&su, 0, sizeof(su));
    memset(sweet_mark_dirty, 0, sizeof(sweet_mark_dirty));
    memset(sweet_mark_ram, 0, sizeof(sweet_mark_ram));
    su.ready = su.writable = true;
    su.first_block = 0x2c1000;
    su.nblocks = 28056571;
    su.dma = (uintptr_t)bounce;
    su.dma_pa = 0x184720000;
    calls = 0;
    fail_write = publish_during_write = false;
}
static void expect_rejected(void)
{
    sweet_mark_dirty[0] = 1;
    assert(sweet_log_mark_flush() == 0 && calls == 0);
    assert(sweet_mark_dirty[0] == 1 && sweet_mark_lock == 0);
}
int main(void)
{
    reset();
    sweet_mark_dirty[0] = sweet_mark_dirty[1] = UINT32_MAX;
    assert(sweet_log_mark_flush() == SWEET_MARK_BLOCKS);
    assert(calls == SWEET_MARK_BLOCKS);
    uint64_t base = su.first_block + su.nblocks - 1025 - 64;
    for (unsigned i = 0; i < SWEET_MARK_BLOCKS; i++) {
        assert(addresses[i] == base + i);
    }
    assert(!sweet_mark_dirty[0] && !sweet_mark_dirty[1]);
    calls = 0;
    assert(sweet_log_mark_flush() == 0 && calls == 0);

    reset(); su.ready = false; expect_rejected();
    reset(); su.writable = false; expect_rejected();
    reset(); su.nblocks = 0; expect_rejected();
    reset(); su.nblocks = 1088; expect_rejected();
    reset(); su.first_block = 0; expect_rejected();
    reset(); su.first_block = (uint64_t)UINT32_MAX + 1; expect_rejected();
    reset(); su.nblocks = UINT64_MAX; expect_rejected();
    reset(); su.first_block = UINT64_MAX - 10; expect_rejected();
    reset(); su.first_block = UINT32_MAX - 100; expect_rejected();

    reset();
    su.nblocks = 1089;
    su.first_block = (uint64_t)UINT32_MAX - su.nblocks + 1;
    sweet_mark_dirty[0] = 1;
    sweet_mark_dirty[1] = 1u << 31;
    assert(sweet_log_mark_flush() == 2);
    assert(addresses[0] == su.first_block);
    assert(addresses[1] == (uint64_t)UINT32_MAX - 1025);

    reset();
    sweet_mark_dirty[0] = 1;
    fail_write = true;
    assert(sweet_log_mark_flush() == 0 && calls == 1);
    assert(sweet_mark_dirty[0] == 1);
    fail_write = false;
    calls = 0;
    assert(sweet_log_mark_flush() == 1 && calls == 1);
    assert(sweet_mark_dirty[0] == 0);

    reset();
    sweet_mark_ram[0] = 0x22;
    sweet_mark_dirty[0] = 1;
    publish_during_write = true;
    assert(sweet_log_mark_flush() == 1 && calls == 1);
    assert(bounce[0] == 0x22 && sweet_mark_dirty[0] == 1);
    calls = 0;
    assert(sweet_log_mark_flush() == 1 && calls == 1);
    assert(bounce[0] == 0x77 && sweet_mark_dirty[0] == 0);
    puts("all marker write bounds/retry/concurrent-update checks passed");
    return 0;
}
'''


def main():
    if not SOURCE.exists():
        print(f'skip marker write test, source not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    start = source.index('static uint32_t\nsweet_log_mark_flush(void)\n{')
    end = source.index('\nstatic int\nsweet_log_flush(', start)
    function = source[start:end]
    slot_definition = re.search(r'^#define UFS_SLOT_MARK\s+[^\n]+', source, re.M)[0]
    with tempfile.TemporaryDirectory(prefix='gauguin-mark-writes-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(HARNESS.replace('@FUNCTION@', function).replace(
            '@SLOT_DEFINITION@', slot_definition))
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', str(path / 'test.c'), '-o', str(path / 'test')],
                       check=True)
        subprocess.run([str(path / 'test')], check=True)


if __name__ == '__main__':
    main()
