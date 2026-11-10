#!/usr/bin/env python3
"""Exercise the actual diagnostic WRITE(10) entry against a mock UFS controller."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

HARNESS = r"""
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_scan_log_guard.h"
#include "gauguin_scan_timing.h"

#define UFS_BLOCK 4096u
#define SWEET_LOG_BLOCKS 1025u
#define UFS_RESERVED_TAIL_BLOCKS 1089u
#define UFS_SLOT_MARK 4u
#define DMA_MARK 4096u
#define TRUE true
#define bzero(p,n) memset((p),0,(n))
typedef uint64_t addr64_t;

static uint8_t dma[8192];
static unsigned writes, syncs, cleans, depth;
static bool poisoned, transfer_fails;
static int sweet_dma_owner_lock;
static struct {
    uintptr_t dma;
    uint64_t dma_pa, first_block, nblocks, fs_nblocks;
    bool ready, writable;
} su;

static void lck_mtx_lock(int *lock) {
    assert(lock == &sweet_dma_owner_lock && depth == 0); depth++;
}
static void lck_mtx_unlock(int *lock) {
    assert(lock == &sweet_dma_owner_lock && depth == 1); depth--;
}
static bool ufs_dma_available(void) { return !poisoned; }
static void clean_dcache64(addr64_t pa, uint32_t count, bool physical) {
    assert(depth == 1 && pa == su.dma_pa + DMA_MARK && count == UFS_BLOCK && physical);
    cleans++;
}
static int ufs_scsi_slot(const uint8_t *cdb, unsigned size, uint32_t bytes,
                        bool write, uintptr_t pa, unsigned slot) {
    assert(depth == 1 && cleans == writes + 1 && write && size == 10 && cdb[0] == 0x2a);
    assert(bytes == UFS_BLOCK && pa == su.dma_pa + DMA_MARK && slot == UFS_SLOT_MARK);
    uint64_t lba = (uint64_t)cdb[2] << 24 | (uint64_t)cdb[3] << 16 |
                   (uint64_t)cdb[4] << 8 | cdb[5];
    assert(lba == 30943225 && cdb[7] == 0 && cdb[8] == 1);
    assert((lba - su.first_block) * UFS_BLOCK == 114915512320ull);
    writes++;
    return transfer_fails ? ETIMEDOUT : 0;
}
static int sweet_log_sync_cache(void) {
    assert(depth == 1 && writes == syncs + 1); syncs++; return 0;
}

@RECORD@

int main(void)
{
    assert(gscan_log_profile(1, 1, 0, 0, 2601));
    assert(gscan_log_profile(1, 3, 0, 0, 2603));
    assert(!gscan_log_profile(0, 1, 0, 0, 2601));
    assert(gscan_log_profile(1, GSCAN_ROUTE_MODE, 0, 0, 2630));
    assert(!gscan_log_profile(1, GSCAN_ROUTE_MODE + 1, 0, 0, 2601));
    assert(!gscan_log_profile(1, 1, 1, 0, 2601));
    assert(!gscan_log_profile(1, 1, 0, 1, 2601));
    assert(!gscan_log_profile(1, 1, 0, 0, 0));
    su.dma = (uintptr_t)dma;
    su.dma_pa = 0x180000000ull;
    su.first_block = 2887680;
    su.nblocks = 28056571;
    su.fs_nblocks = su.nblocks - 1089;
    struct gscan_result r = {
        .status = GSCAN_MEASURED, .stage = GSCAN_INTF,
        .start_ns = 1000000000, .end_ns = 2000000000,
        .frames = 60, .millihz = 60000, .nominal_hz = 60,
    };
    assert(sweet_scan_log_record(0, 1, true, &r) == EPERM);
    assert(sweet_scan_log_record(2601, GSCAN_ROUTE_MODE + 1, true, &r) == EPERM);
    su.writable = true;
    assert(sweet_scan_log_record(2601, 1, true, &r) == EPERM);
    su.writable = false;
    su.ready = true;
    assert(sweet_scan_log_record(2601, 1, true, &r) == EPERM);
    su.ready = false;
    su.first_block++;
    assert(sweet_scan_log_record(2601, 1, true, &r) == EPERM);
    su.first_block--;
    su.nblocks--;
    assert(sweet_scan_log_record(2601, 1, true, &r) == EPERM);
    su.nblocks++;
    su.fs_nblocks++;
    assert(sweet_scan_log_record(2601, 1, true, &r) == EPERM);
    su.fs_nblocks--;
    memset(dma + DMA_MARK, 0x5a, UFS_BLOCK);
    poisoned = true;
    assert(sweet_scan_log_record(2601, 1, false, &r) == EIO);
    assert(dma[DMA_MARK] == 0x5a && writes == 0 && cleans == 0 && syncs == 0);
    poisoned = false;
    assert(sweet_scan_log_record(2603, 3, true, &r) == 0);
    assert(writes == 1 && syncs == 1 && depth == 0);
    const char *record = (const char *)(dma + DMA_MARK);
    assert(strstr(record, "GAUGUIN_SCAN1 run=2603 mode=3 done=1"));
    assert(strstr(record, "millihz=60000 nominal=60\nEND_GAUGUIN_SCAN1 run=2603\n"));
    for (size_t i = strlen(record); i < UFS_BLOCK; ++i)
        assert(record[i] == 0);
    r.route.status = GSCAN_ROUTE_MATCHED;
    r.route.samples = 3;
    r.route.pipe_mask = 1;
    r.route.ctl_mask = 2;
    r.route.framebuffer.address = 0xa0000000;
    r.route.framebuffer.width = 1080;
    r.route.framebuffer.height = 2400;
    r.route.framebuffer.stride = 4320;
    r.route.source[0] = 0xa0000000;
    r.route.interface[1] = 2;
    r.route.stages[1] = 1;
    assert(sweet_scan_log_record(2630, GSCAN_ROUTE_MODE, true, &r) == 0);
    assert(writes == 2 && syncs == 2 && depth == 0);
    assert(strstr(record, "GAUGUIN_SCAN2 run=2630 mode=4 done=1"));
    assert(strstr(record, "route=9 samples=3 frame=0/0 pipe_mask=1 ctl_mask=2 fb=a0000000 geometry=1080/2400/4320"));
    assert(strstr(record, "source=a0000000/00000000/00000000/00000000 interface=00000000/00000002/00000000/00000000"));
    assert(strstr(record, "stages=0/1/0/0 virtual=0/0/0/0\nEND_GAUGUIN_SCAN2 run=2630\n"));
    for (size_t i = strlen(record); i < UFS_BLOCK; ++i)
        assert(record[i] == 0);
    transfer_fails = true;
    assert(sweet_scan_log_record(2601, 1, false, &r) == ETIMEDOUT);
    assert(writes == 3 && syncs == 2 && depth == 0);
    puts("Actual scan receipt writer issued one fixed 4 KiB write, with rejection and timeout controls.");
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    dev = args.source.resolve() / "bsd/dev"
    ufs = (dev / "sweet_ufs.c").read_text()
    begin = ufs.index("static int\nsweet_scan_log_record(")
    record = ufs[begin:ufs.index("\n}\n", begin) + 3]
    init = ufs[ufs.index("sweet_ufs_init(bool scan_log)"):]
    assert init.index("if (scan_log)\n\t\treturn 0;") < init.index("bdevsw_add(")
    bsd = (dev.parent / "kern/bsd_init.c").read_text()
    assert bsd.index("\tsweet_scan_log_diagnostic();") < bsd.index("/* Mount the root file system. */")
    with tempfile.TemporaryDirectory(prefix="gauguin-scan-log-") as directory:
        tmp = Path(directory)
        src, binary = tmp / "record.c", tmp / "record"
        src.write_text(HARNESS.replace("@RECORD@", record))
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", "-I", str(dev), str(src), "-o", str(binary)],
                       check=True, timeout=30)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1:detect_leaks=0", UBSAN_OPTIONS="halt_on_error=1")
        subprocess.run([str(binary)], check=True, timeout=10, env=env)


if __name__ == "__main__":
    main()
