#!/usr/bin/env python3
"""Exercise actual UFS descriptor setup and takeover against fake host registers.

Model the cache-line writeback/DMA completion interleaving that corrupted OCS
with adjacent slots. The old 0/1 layout is an explicit failing control.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = CACHE / 'bsd/dev/sweet_ufs.c'

HARNESS = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#undef bzero
#define bzero(p, n) memset((p), 0, (n))
@DEFINITIONS@
#define CACHE_LINE_BYTES (1u << MMU_CLINE)
static _Alignas(64) uint8_t dma[DMA_SIZE];
static struct { uintptr_t dma; uint64_t dma_pa; uint8_t lun; } su;
static uint32_t regs[0x100 / 4];
static unsigned writes;
static uint32_t ufs_rd(unsigned reg) { return regs[reg / 4]; }
static void ufs_wr(unsigned reg, uint32_t value)
{
    writes++;
    regs[reg / 4] = value;
}
static int quiet_printf(const char *format, ...) { (void)format; return 0; }
#define printf quiet_printf
@TAKEOVER@
#undef printf

/* The production preparation body, stopping before cache maintenance/MMIO. */
static void prepare(const uint8_t *cdb, unsigned cdb_len, uint32_t len,
    bool write, uintptr_t data_pa, unsigned slot)
{
@PREPARE@
    (void)bit;
    (void)bounce_off;
}

static void reset_host(unsigned count)
{
    memset(regs, 0, sizeof(regs));
    regs[REG_CAP / 4] = CAP_64AS | (count - 1);
    regs[REG_HCE / 4] = 1;
    regs[REG_HCS / 4] = HCS_DP | HCS_UTRLRDY;
    su.dma = (uintptr_t)dma;
    su.dma_pa = 0x184724000ULL;
    su.lun = 0;
    writes = 0;
}

/* A cached write to peer races with the device's successful victim OCS.
 * Cleaning the peer's entire line must not reintroduce victim OCS=0xf. */
static uint32_t race_ocs(unsigned victim, unsigned peer)
{
    uint8_t ram[32 * sizeof(struct utrd)] = {0};
    uint8_t cached_line[CACHE_LINE_BYTES];
    size_t victim_ocs = victim * sizeof(struct utrd) + offsetof(struct utrd, dw2);
    size_t peer_ocs = peer * sizeof(struct utrd) + offsetof(struct utrd, dw2);
    size_t line = peer_ocs & ~(size_t)(CACHE_LINE_BYTES - 1);
    uint32_t invalid = 0xf, completed = 0, observed;
    memcpy(ram + victim_ocs, &invalid, sizeof(invalid));
    memcpy(cached_line, ram + line, sizeof(cached_line));
    memcpy(cached_line + peer_ocs - line, &invalid, sizeof(invalid));
    memcpy(ram + victim_ocs, &completed, sizeof(completed));
    memcpy(ram + line, cached_line, sizeof(cached_line));
    memcpy(&observed, ram + victim_ocs, sizeof(observed));
    return observed;
}

int main(void)
{
    const unsigned slots[] = {UFS_SLOT_MAIN, UFS_SLOT_LOG, UFS_SLOT_MARK};
    const unsigned ucd_offsets[] = {DMA_UCD, DMA_UCD_LOG, DMA_UCD_MARK};
    assert(sizeof(struct utrd) == 32 && CACHE_LINE_BYTES == 64);
    assert(DMA_UTRL % CACHE_LINE_BYTES == 0);
    assert(race_ocs(0, 1) == 0xf); /* old layout loses DMA completion */
    assert(race_ocs(1, 0) == 0xf);
    for (unsigned i = 0; i < 3; i++) {
        size_t start = DMA_UTRL + slots[i] * sizeof(struct utrd);
        assert(start % CACHE_LINE_BYTES == 0);
        assert(start + sizeof(struct utrd) <= DMA_UCD);
        for (unsigned j = 0; j < 3; j++) {
            if (i != j) {
                assert(slots[i] != slots[j]);
                assert(race_ocs(slots[i], slots[j]) == 0);
            }
        }
    }

    /* Every undersized CAP is rejected before changing host registers. */
    for (unsigned count = 1; count <= UFS_SLOT_MARK; count++) {
        reset_host(count);
        assert(ufs_take_over_host() == ENXIO && writes == 0);
    }
    for (unsigned count = UFS_SLOT_MARK + 1; count <= 32; count++) {
        reset_host(count);
        assert(ufs_take_over_host() == 0 && writes > 0);
        assert(regs[REG_UTRLBA / 4] == (uint32_t)su.dma_pa);
        assert(regs[REG_UTRLBAU / 4] == (uint32_t)(su.dma_pa >> 32));
        assert(regs[REG_UTRLRSR / 4] == 1);
    }
    reset_host(32);
    regs[REG_CAP / 4] &= ~CAP_64AS;
    assert(ufs_take_over_host() == ENXIO && writes == 0);
    su.dma_pa = 0x90000000;
    assert(ufs_take_over_host() == 0);
    reset_host(32);
    regs[REG_UTRLDBR / 4] = 1;
    assert(ufs_take_over_host() == EBUSY && writes == 0);

    reset_host(32);
    const uint8_t cdb[] = {0x28, 0, 0, 0, 0x12, 0x34, 0, 0, 1, 0};
    for (unsigned i = 0; i < 3; i++) {
        prepare(cdb, sizeof(cdb), UFS_BLOCK, false, su.dma_pa + DMA_BOUNCE, slots[i]);
        const struct utrd *desc = (const void *)(dma + DMA_UTRL + slots[i] * sizeof(*desc));
        const struct ucd *command = (const void *)(dma + ucd_offsets[i]);
        assert(desc->dw2 == 0xf);
        assert(desc->ucdba == (uint32_t)(su.dma_pa + ucd_offsets[i]));
        assert(desc->ucdbau == (uint32_t)(su.dma_pa >> 32));
        assert(command->cmd[3] == slots[i]);
        assert(memcmp(command->cmd + 16, cdb, sizeof(cdb)) == 0);
    }
    /* Keep MAIN outstanding while LOG issues more than the old 32-tag cycle. */
    for (unsigned i = 0; i < 96; i++) {
        prepare(cdb, sizeof(cdb), 0, false, 0, UFS_SLOT_LOG);
        const struct ucd *main = (const void *)(dma + DMA_UCD);
        const struct ucd *log = (const void *)(dma + DMA_UCD_LOG);
        assert(main->cmd[3] == UFS_SLOT_MAIN);
        assert(log->cmd[3] == UFS_SLOT_LOG && log->cmd[3] != main->cmd[3]);
    }
    puts("UFS cache-line isolation, descriptor tags and CAP guards passed");
    return 0;
}
'''


def main():
    if not SOURCE.exists():
        print(f'skip UFS descriptor test, source not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    definitions = '\n'.join(re.findall(
        r'^#define (?:REG_\w+|HCS_\w+|CAP_\w+|UFS_SLOT_\w+|DMA_\w+|'
        r'UFS_BLOCK|BOUNCE_SIZE|PRDT_CHUNK|PRDT_MAX)\s+[^\n]+', source, re.M))
    for name in ('utrd', 'ucd'):
        start = source.index('struct ' + name + ' {')
        end = source.index('\n};', start) + 3
        definitions += '\n' + source[start:end]
    proc_reg = (CACHE / 'osfmk/arm64/proc_reg.h').read_text()
    sweet = proc_reg.split('#elif defined (SWEET)', 1)[1].split('#elif', 1)[0]
    definitions += '\n' + re.search(r'^#define MMU_CLINE\s+\d+', sweet, re.M)[0]
    start = source.index('static int\nufs_take_over_host(void)')
    end = source.index('\n}\n', start) + 3
    takeover = source[start:end]
    start = source.index('\nufs_scsi_slot(')
    start = source.index('\n{\n', start) + 3
    end = source.index('\n\tif (su.cache)', start)
    prepare = source[start:end]
    harness = HARNESS.replace('@DEFINITIONS@', definitions).replace(
        '@TAKEOVER@', takeover).replace('@PREPARE@', prepare)
    with tempfile.TemporaryDirectory(prefix='gauguin-ufs-descriptors-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(harness)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', str(path / 'test.c'), '-o', str(path / 'test')],
                       check=True)
        subprocess.run([str(path / 'test')], check=True)


if __name__ == '__main__':
    main()
