#!/usr/bin/env python3
"""Build a read-only Adreno aperture check for the two physically scanned boot slots."""

import argparse
from contextlib import redirect_stdout
from difflib import unified_diff
from importlib import import_module
from io import StringIO
import json
from pathlib import Path

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/shared-scanout'
P413 = MAIN/'research/tmp/gauguin-reserved-linear-backing-worktree-20261124'
INPUT = P413/'research/tmp/reserved-linear/native-kernel-0409/build-manifest.json'
ADMISSION = P413/'research/tmp/frame-413/offline-next-shared-backing-admission.json'
GPU_DONOR = (MAIN/'research/tmp/gauguin-frame406-completion-hint-worktree-20261124'
             /'research/tmp/frame-407/native-kernel/build-manifest.json')
COMPILER = Path('/Library/Developer/CommandLineTools/usr/bin')
PATCH = BASE/'shared-readonly-aperture.patch'
KERNEL = BASE/'native-kernel/build-manifest.json'
SOURCE = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
GPU = SOURCE.with_name('GauguinGPU.cpp')
BOARD = Path('bsd/dev/gauguin_ui_trace_board.c')
HELPER = r'''extern "C" bool sweet_fb414_reserved_descriptors(IOMemoryDescriptor *[2], uint32_t [2]);

/* Called under the native GPU lock, between completed submits. The display
 * service publishes these two descriptors only after both boot-owned slots
 * have latched. This test never issues GPU work or exposes a client handle. */
static bool probeBootScanout414()
{
    static bool attempted;
    if (attempted || !gPtes || !sweet_gpu_runtime_ready()) return true;
    IOMemoryDescriptor *memory[2] = {};
    uint32_t physical[2] = {};
    if (!sweet_fb414_reserved_descriptors(memory, physical)) return true;
    attempted = true;

    constexpr uint64_t slotBytes = F411_SLOT_BYTES;
    constexpr uint64_t pageBytes = 4096;
    constexpr uint64_t readOnlyLeaf = 0xec3;
    for (unsigned slot = 0; slot < 2; ++slot) {
        if (!memory[slot] || memory[slot]->getLength() != slotBytes) {
            IOLog("SWEET F414 GPU MAP: refused-extent\n");
            return true;
        }
        for (uint64_t offset = 0; offset < slotBytes; offset += pageBytes) {
            IOByteCount contiguous = 0;
            const uint64_t pa = memory[slot]->getPhysicalSegment(offset, &contiguous, kIOMemoryMapperNone);
            if (pa != physical[slot] + offset || contiguous < pageBytes) {
                IOLog("SWEET F414 GPU MAP: refused-physical-segment\n");
                return true;
            }
        }
    }

    uint64_t address[2] = {reserveAddress(slotBytes), 0};
    if (address[0]) address[1] = reserveAddress(slotBytes);
    if (!address[1]) {
        if (address[0]) releaseAddress(address[0], slotBytes);
        IOLog("SWEET F414 GPU MAP: refused-aperture\n");
        return true;
    }
    for (unsigned slot = 0; slot < 2; ++slot) memory[slot]->retain();

    // Retain both descriptors and VA ranges on a bad leaf or failed sync.
    // Neither allocation can be repurposed while translation is uncertain.
    for (unsigned slot = 0; slot < 2; ++slot) {
        for (uint64_t offset = 0; offset < slotBytes; offset += pageBytes) {
            if (*leafAt(address[slot] + offset)) {
                sweet_gpu_runtime_stop();
                IOLog("SWEET F414 GPU MAP: quarantined-stale-leaf\n");
                return false;
            }
        }
    }
    for (unsigned slot = 0; slot < 2; ++slot)
        for (uint64_t offset = 0; offset < slotBytes; offset += pageBytes)
            *leafAt(address[slot] + offset) = (physical[slot] + offset) | readOnlyLeaf;

    memoryBarrier();
    if (!sweet_gpu_runtime_sync()) {
        sweet_gpu_runtime_stop();
        IOLog("SWEET F414 GPU MAP: quarantined-publication\n");
        return false;
    }
    for (unsigned slot = 0; slot < 2; ++slot) {
        for (uint64_t offset = 0; offset < slotBytes; offset += pageBytes) {
            if (*leafAt(address[slot] + offset) != ((physical[slot] + offset) | readOnlyLeaf)) {
                sweet_gpu_runtime_stop();
                IOLog("SWEET F414 GPU MAP: quarantined-readback\n");
                return false;
            }
        }
    }
    for (unsigned slot = 0; slot < 2; ++slot)
        for (uint64_t offset = 0; offset < slotBytes; offset += pageBytes)
            *leafAt(address[slot] + offset) = 0;

    memoryBarrier();
    if (!sweet_gpu_runtime_sync()) {
        sweet_gpu_runtime_stop();
        IOLog("SWEET F414 GPU MAP: quarantined-removal\n");
        return false;
    }
    for (unsigned slot = 0; slot < 2; ++slot) {
        releaseAddress(address[slot], slotBytes);
        memory[slot]->release();
    }
    IOLog("SWEET F414 GPU MAP: published-and-removed read-only pages=%u per-slot=%u\n",
          static_cast<unsigned>(2 * slotBytes / pageBytes), static_cast<unsigned>(slotBytes / pageBytes));
    return true;
}

'''


def replace(source, before, after):
    require(source.count(before)==1,'unexpected shared scanout insertion at '+before.splitlines()[0])
    return source.replace(before,after,1)


def board(source):
    site = 'bool sweet_frame411_padded(void)'
    source = replace(source,site,'''static uint32_t scanout414Latched;

bool sweet_frame414_reserved_physical(uint32_t physical[2])
{
    if (!sweet_frame382_active() ||
        __atomic_load_n(&scanout414Latched, __ATOMIC_ACQUIRE) != ((1u << F382_FIRST) | (1u << F382_SECOND)))
        return false;
    physical[0] = scan382.address[F382_FIRST];
    physical[1] = scan382.address[F382_SECOND];
    return true;
}

'''+site)
    site = '    return flush ? F382_WAIT : F382_CONFIRMED;'
    return replace(source,site,'''    if (flush) return F382_WAIT;
    if (scan382.padded && next != F382_FRONT)
        __atomic_fetch_or(&scanout414Latched, 1u << next, __ATOMIC_RELEASE);
    return F382_CONFIRMED;''')


def framebuffer(source):
    site = 'extern "C" void\nsweet_fb382_poll(uint32_t frame)'
    return replace(source,site,'''extern "C" bool sweet_frame414_reserved_physical(uint32_t [2]);

extern "C" bool
sweet_fb414_reserved_descriptors(IOMemoryDescriptor *memory[2], uint32_t physical[2])
{
    if (!sweet_frame414_reserved_physical(physical)) return false;
    if (!scanout383.memory[0] || !scanout383.memory[1]) return false;
    memory[0] = scanout383.memory[0];
    memory[1] = scanout383.memory[1];
    return true;
}

'''+site)


def adreno(source):
    site = 'struct gpu_buffer {'
    source = replace(source,site,'#include "../../../bsd/dev/gauguin_linear_scanout411.h"\n\n'+HELPER+site)
    site = '    const uint32_t producerCookie = r->pad;'
    return replace(source,site,'''    if (fCompositor && fAsync && !probeBootScanout414())
        return kIOReturnNotReady;
'''+site)


def build():
    budget = load(ADMISSION)
    require(budget['admitted'] and budget['planned_batch_bytes']==310_000_000 and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            'shared mapping build and existing physical trial exceed storage')
    old = load(INPUT)
    source = Path(old['source'])
    changes = {GPU:adreno, SOURCE:framebuffer, BOARD:board}
    diffs = []
    for relative,transform in changes.items():
        before = (source/relative).read_text()
        after = transform(before)
        diffs.extend(unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
                                  'a/'+str(relative),'b/'+str(relative)))
    PATCH.write_text(''.join(diffs))
    units = (('GauguinGPU',GPU_DONOR),('SweetFramebuffer',INPUT),('gauguin_ui_trace_board',INPUT))
    with redirect_stdout(StringIO()):
        import_module('build-frame347').link_scanout(INPUT,KERNEL.parent,parent_trial='0413',trial='0414',
            patches=(PATCH,),extra_units=tuple((name,manifest,'compile-'+name) for name,manifest in units),
            recompile_scanout=False,compiler_bin=COMPILER)
    result = load(KERNEL)
    require(result['inputs_unchanged'] and result['baseline_reproduced_except_uuid'] and
            {Path(path).stem for path in result['object_replacements'].values()}==set(name for name,_ in units),
            'shared mapping changed unrelated kernel units')
    return {key:result[key] for key in ('identity','kernel_bytes','kernel_sha256','object_replacements')}


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(build(),indent=2))
