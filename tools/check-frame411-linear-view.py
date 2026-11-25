#!/usr/bin/env python3
"""Stage a managed, padded backing qualification without publishing GPU targets."""

import argparse
from contextlib import redirect_stdout
from difflib import unified_diff
from importlib import import_module
from io import StringIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-411'
phase = import_module('check-frame410-phase')
REFERENCE = phase.source_manifest('0409')
ADMISSION = BASE/'complete-rebase-batch-admission.json'
NATIVE = BASE/'native-kernel-0409/build-manifest.json'
SOURCE = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
BOARD = Path('bsd/dev/gauguin_ui_trace_board.c')
HEADER = Path('bsd/dev/gauguin_linear_scanout411.h')
MODEL = WORK/'graphics/gauguin-display/LinearScanout411.h'
PATCH = BASE/'411-managed-padded-scanout-0409.patch'
HOST = BASE/'0409-layout-host.json'
COMPILER = Path('/Library/Developer/CommandLineTools/usr/bin')


def exactly(text,before,after):
    require(text.count(before)==1,'linear backing source changed at '+before[:90])
    return text.replace(before,after,1)


def framebuffer(text):
    site = '#include "../../../bsd/dev/gauguin_copy379_probe.h"'
    text = exactly(text,site,site+'\n#include "../../../bsd/dev/gauguin_linear_scanout411.h"'
        '\n#include <IOKit/IOBufferMemoryDescriptor.h>'
        '\n#include <kern/task.h>\n#include <machine/machine_routines.h>')
    site = 'static struct {\n    IOMemoryDescriptor *memory[2];\n    IOMemoryMap *mapping[2];\n} scanout383;'
    allocator = '''
static IOBufferMemoryDescriptor *f411Owner[2];
static bool f411Published, f411Attempted;
static uint32_t f411Physical[2];
static uintptr_t f411Address[2];

extern "C" boolean_t pmap_valid_page(ppnum_t);
extern "C" bool sweet_frame411_padded(void);

static void
prepare411Buffers()
{
    uint32_t script = 0, stats = 0, hz = 0, native = 0, gpu = 0;
    if (!PE_parse_boot_argn("swp", &script, sizeof(script)) || script != 4 ||
        !PE_parse_boot_argn("sweetfb_stats", &stats, sizeof(stats)) || stats != 9 ||
        !PE_parse_boot_argn("sweetfb_hz", &hz, sizeof(hz)) || hz != 60 ||
        !PE_parse_boot_argn("sweetnvt", &native, sizeof(native)) || native ||
        !PE_parse_boot_argn("gpf", &gpu, sizeof(gpu)) || gpu != 5 ||
        __atomic_exchange_n(&f411Attempted, true, __ATOMIC_ACQ_REL))
        return;

    struct Candidate {
        IOBufferMemoryDescriptor *memory[2] = {};
        ~Candidate()
        {
            for (auto &slot : memory)
                OSSafeReleaseNULL(slot);
        }
    } candidate;
    auto &memory = candidate.memory;
    uint64_t physical[2] = {};
    uintptr_t address[2] = {};
    for (unsigned i = 0; i < 2; ++i) {
        memory[i] = IOBufferMemoryDescriptor::inTaskWithPhysicalMask(kernel_task,
            kIODirectionInOut | kIOMemoryPhysicallyContiguous | kIOMapWriteCombineCache,
            F411_SLOT_BYTES, UINT64_C(0xffffffff));
        if (!memory[i] || memory[i]->getLength() != F411_SLOT_BYTES)
            return;
        IOByteCount contiguous = 0;
        physical[i] = memory[i]->getPhysicalSegment(0, &contiguous, kIOMemoryMapperNone);
        address[i] = reinterpret_cast<uintptr_t>(memory[i]->getBytesNoCopy());
        if (!address[i] || !f411_managed_extent(physical[i], contiguous) ||
            (address[i] & (F411_PAGE_BYTES - 1)))
            return;
        for (unsigned offset = 0; offset < F411_SLOT_BYTES; offset += F411_PAGE_BYTES) {
            if (!pmap_valid_page(static_cast<ppnum_t>((physical[i] + offset) >> PAGE_SHIFT)) ||
                ml_vtophys(address[i] + offset) != physical[i] + offset)
                return;
        }
    }
    if (!f411_disjoint(physical[0], physical[1]) || !f411_disjoint(address[0], address[1]))
        return;
    for (unsigned i = 0; i < 2; ++i) {
        f411Owner[i] = memory[i];
        memory[i] = nullptr;
        f411Physical[i] = static_cast<uint32_t>(physical[i]);
        f411Address[i] = address[i];
    }
    __atomic_store_n(&f411Published, true, __ATOMIC_RELEASE);
    IOLog("SWEET F411: two managed linear backings bytes=%u\\n", F411_SLOT_BYTES);
}

extern "C" bool
sweet_fb411_buffers(uint32_t physical[2], uintptr_t address[2])
{
    if (!__atomic_load_n(&f411Published, __ATOMIC_ACQUIRE))
        return false;
    for (unsigned i = 0; i < 2; ++i) {
        physical[i] = f411Physical[i];
        address[i] = f411Address[i];
    }
    return true;
}

'''
    text = exactly(text,site,site+'\n'+allocator)
    site = '        if (fFrameInfo375 && fReadyEvent) attachStage384Worker();'
    text = exactly(text,site,'''        if (fFrameInfo375 && fReadyEvent) {
            prepare411Buffers();
            attachStage384Worker();
        }''')
    source = '''            const uintptr_t dst = (flipDst ? flipDst : fPixels) + (uint64_t)dy * fRowBytes + (uint64_t)dx * 4;
            const uintptr_t first = src + s->offset + (uint64_t)sy * s->bytesPerRow + (uint64_t)sx * 4;'''
    target = '''            uint32_t dstStride = fRowBytes;
            uintptr_t target = flipDst ? flipDst : fPixels;
#if defined(GAUGUIN)
            const bool padded = flipDst && sweet_frame411_padded();
            if (padded) {
                dstStride = F411_RENDER_PITCH;
                target += F411_VIEW_OFFSET;
            }
#endif
            const uintptr_t dst = target + (uint64_t)dy * dstStride + (uint64_t)dx * 4;
            const uintptr_t first = src + s->offset + (uint64_t)sy * s->bytesPerRow + (uint64_t)sx * 4;'''
    text = exactly(text,source,target)
    source = '''            const bool pairedCopy = fastBlank && dx == 0 && dy == 0 && s->memory != fSurface->memory &&
                scan352_copy_supported(dst, first, w, h, fRowBytes, s->bytesPerRow);'''
    target = '''            const bool fullPadded = padded && w == F411_PANEL_WIDTH && h == F411_PANEL_HEIGHT &&
                sx == F411_CROP_X && sy == F411_CROP_Y && s->offset == 0 && s->planeCount == 0 &&
                s->pixelFormat == SWEET_FB_FORMAT_BGRA && s->width == F411_RENDER_WIDTH &&
                s->height == F411_RENDER_HEIGHT && s->bytesPerRow == F411_RENDER_PITCH &&
                s->allocSize == F411_SLOT_BYTES;
            const bool pairedCopy = fastBlank && dx == 0 && dy == 0 && s->memory != fSurface->memory &&
                (padded ? fullPadded : scan352_copy_supported(dst, first, w, h, fRowBytes, s->bytesPerRow));'''
    text = exactly(text,source,target)
    # The centered destination is only eight-byte aligned. The inherited
    # paired-store helper qualifies an aligned packed destination.
    text = exactly(text,'            if (probeLane) {','''            if (padded) {
                for (int32_t y = 0; y < h; ++y)
                    memcpy((void *)(dst + (uint64_t)y * dstStride),
                        (const void *)(first + (uint64_t)y * s->bytesPerRow), F411_PANEL_PITCH);
            } else if (probeLane) {''')
    return text


def board(text):
    header = '#include "gauguin_blank352.h"'
    text = exactly(text,header,header+'\n#include "gauguin_linear_scanout411.h"')
    text = exactly(text,'''    volatile uint32_t *source, *flush;
    bool enabled;
} scan382;''',
'''    volatile uint32_t *source, *pitch, *sourceXY, *flush;
    bool enabled, padded;
} scan382;

extern bool sweet_fb411_buffers(uint32_t [2], uintptr_t [2]);''')
    text = exactly(text,'static bool scan382_live_route(void)','static bool scan382_live_route(uint32_t pitch, uint32_t sourceXY)')
    text = exactly(text,'pipe[0x70 / 4] == 0 && pipe[0x24 / 4] == 4320 &&',
                         'pipe[0x70 / 4] == 0 && pipe[0x24 / 4] == pitch && pipe[0x08 / 4] == sourceXY &&')
    text = exactly(text,'if (!scan382_route(s) || !scan382_live_route() ||',
                         'if (!scan382_route(s) || !scan382_live_route(F411_PANEL_PITCH, 0) ||')
    start = text.index('    uintptr_t slots[2];\n    if (!sweet_fb383_map(')
    end = text.index('    const vm_offset_t vig = scan382_map_registers',start)
    text = text[:start]+'''    uintptr_t slots[2];
    uint32_t physical[2];
    const bool padded = sweet_fb411_buffers(physical, slots);
    const uint64_t bytes = padded ? F411_SLOT_BYTES : slot;
    if (!padded) {
        if (!sweet_fb383_map((uint32_t)start, (uint32_t)slot, slots)) {
            printf("SWEET F383 MAP: allocation-failed\\n");
            return false;
        }
        physical[0] = (uint32_t)start;
        physical[1] = (uint32_t)(start + slot);
    }
    for (unsigned i = F382_FIRST; i <= F382_SECOND; ++i) {
        scan382.address[i] = physical[i - 1];
        scan382.map[i] = slots[i - 1];
        if (ml_vtophys(scan382.map[i]) != scan382.address[i] ||
            ml_vtophys(scan382.map[i] + bytes - 1) != (uint64_t)scan382.address[i] + bytes - 1) {
            if (!padded) sweet_fb383_discard();
            printf("SWEET F383 MAP: translation-mismatch\\n");
            return false;
        }
    }
    printf("SWEET F383 MAP: %s\\n", padded ? "two-private-managed-linear-slots" : "two-private-IOKit-WC-slots");
'''+text[end:]
    text = exactly(text,'''    scan382.source = (volatile uint32_t *)(vig + 0x1014);
    scan382.flush = (volatile uint32_t *)(ctl + 0x2018);
    if (*scan382.source != scan382.address[F382_FRONT] || *scan382.flush)''',
'''    scan382.source = (volatile uint32_t *)(vig + 0x1014);
    scan382.pitch = (volatile uint32_t *)(vig + 0x1024);
    scan382.sourceXY = (volatile uint32_t *)(vig + 0x1008);
    scan382.flush = (volatile uint32_t *)(ctl + 0x2018);
    if (*scan382.source != scan382.address[F382_FRONT] || *scan382.pitch != F411_PANEL_PITCH ||
        *scan382.sourceXY || *scan382.flush)''')
    text = exactly(text,'''    printf("SWEET F382 BACKING: first=%08x second=%08x bytes=%d\\n",
        scan382.address[1], scan382.address[2], F382_SLOT_BYTES);
    __atomic_store_n(&scan382.enabled, true, __ATOMIC_RELEASE);''',
'''    printf("SWEET F382 BACKING: first=%08x second=%08x bytes=%u\\n",
        scan382.address[1], scan382.address[2], (unsigned)bytes);
    scan382.padded = padded;
    __atomic_store_n(&scan382.enabled, true, __ATOMIC_RELEASE);''')
    text = exactly(text,'''bool sweet_frame382_ending(void)''',
'''bool sweet_frame411_padded(void)
{
    return sweet_frame382_active() && scan382.padded;
}

bool sweet_frame382_ending(void)''')
    text = exactly(text,'''    if (!scan382_live_route() || *scan382.source != scan382.address[front] || *scan382.flush)''',
'''    const uint32_t oldPitch = f411_pitch(scan382.padded, front);
    const uint32_t nextPitch = f411_pitch(scan382.padded, next);
    const uint32_t oldXY = f411_source_xy(scan382.padded, front);
    const uint32_t nextXY = f411_source_xy(scan382.padded, next);
    if (!scan382_live_route(oldPitch, oldXY) || *scan382.source != scan382.address[front] || *scan382.flush)''')
    text = exactly(text,'''    ++scan382.requests;
    *scan382.source = scan382.address[next];''',
'''    ++scan382.requests;
    if (oldPitch != nextPitch) *scan382.pitch = nextPitch;
    if (oldXY != nextXY) *scan382.sourceXY = nextXY;
    *scan382.source = scan382.address[next];''')
    text = exactly(text,'''    const uint32_t source = *scan382.source;
    ml_set_interrupts_enabled(interrupts);
    if (flush != 1 || source != scan382.address[next] ||''',
'''    const uint32_t source = *scan382.source;
    const uint32_t pitch = *scan382.pitch;
    const uint32_t sourceXY = *scan382.sourceXY;
    ml_set_interrupts_enabled(interrupts);
    if (flush != 1 || source != scan382.address[next] || pitch != nextPitch || sourceXY != nextXY ||''')
    text = exactly(text,'''    if (source != scan382.address[next] || flush & ~1u || !scan382_live_route())''',
'''    if (source != scan382.address[next] || flush & ~1u ||
        !scan382_live_route(f411_pitch(scan382.padded, next), f411_source_xy(scan382.padded, next)))''')
    return text


def host():
    original = load(REFERENCE)
    source = Path(original['source'])
    require((source/SOURCE).read_text().count('                workUs = 7200;')==1,
            '0411 must retain the 0409 compositor work duration')
    assets = [(SOURCE,framebuffer((source/SOURCE).read_text())),
              (BOARD,board((source/BOARD).read_text())),(HEADER,MODEL.read_text())]
    lines = []
    for relative,content in assets:
        p = source/relative
        before = p.read_text().splitlines(keepends=True) if p.exists() else []
        lines.extend(unified_diff(before,content.splitlines(keepends=True),
            'a/'+str(relative) if p.exists() else '/dev/null','b/'+str(relative)))
    PATCH.write_text(''.join(lines))
    fixture = WORK/'tests/fixtures/gauguin_direct_scanout_host.cpp'
    sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    with TemporaryDirectory(prefix='0411-host-',dir=BASE) as folder:
        binary = Path(folder)/'layout'
        subprocess.run([str(COMPILER/'clang++'),'-isysroot',sdk,'-std=c++20','-Wall',
            '-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(fixture),
            '-o',str(binary)],check=True,timeout=60)
        subprocess.run([str(binary)],check=True,timeout=20)
    return dict(state='0411-linear-view-offline-source-checked',device_commands=0,patch_sha256=sha(PATCH),
        input_pins={str(p):sha(p) for p in (REFERENCE,source/SOURCE,source/BOARD,MODEL,fixture,PATCH)})


def native():
    budget = load(ADMISSION)
    require(budget['admitted'] and budget['planned_batch_bytes']==447_000_000 and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            '0411 full rebase and trial batch exceeds storage')
    proof = load(HOST)
    require(not proof['device_commands'] and all(sha(path)==digest for path,digest in proof['input_pins'].items()),
            '0411 offline inputs differ')
    donor = phase.source_manifest('0408')
    with redirect_stdout(StringIO()):
        import_module('build-frame347').link_scanout(REFERENCE,NATIVE.parent,parent_trial='0409',trial='0411',
            patches=(PATCH,),extra_units=(('SweetFramebuffer',donor,'compile-SweetFramebuffer'),
                ('gauguin_ui_trace_board',donor,'compile-gauguin_ui_trace_board')),
            recompile_scanout=False,compiler_bin=COMPILER)
    result = load(NATIVE)
    return {key:result[key] for key in ('state','identity','kernel_sha256','kernel_bytes','object_replacements',
                                       'baseline_reproduced_except_uuid','inputs_unchanged')}


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stage',choices=('host','native'))
    print(json.dumps(globals()[cli.parse_args().stage](),indent=2))
