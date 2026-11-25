#!/usr/bin/env python3
"""Qualify the padded DPU view using the shim-owned low address slots."""

import argparse
from contextlib import redirect_stdout
from difflib import unified_diff
from importlib import import_module
from io import StringIO
import json
from pathlib import Path

from frame366_scope import MAIN, WORK, load, require, sha

layout = import_module('check-frame411-linear-view')
phase = import_module('check-frame410-phase')
BASE = WORK/'research/tmp/reserved-linear'
ADMISSION = MAIN/'research/tmp/gauguin-frame412-stock-gpu-ceiling-worktree-20261124/research/tmp/frame-412/offline-reserved-backing-batch.json'
SHIM = BASE/'shim-native/result.json'
SOURCE, BOARD, HEADER = layout.SOURCE, layout.BOARD, layout.HEADER
replace = layout.exactly


def framebuffer(source):
    source = layout.framebuffer(source)
    begin = source.index('static IOBufferMemoryDescriptor *f411Owner[2];')
    end = source.index('/* The private descriptors are never published as IOSurfaces.',begin)
    source = source[:begin] + 'extern "C" bool sweet_frame411_padded(void);\n\n' + source[end:]
    source = replace(source,'''#include <IOKit/IOBufferMemoryDescriptor.h>
#include <kern/task.h>
#include <machine/machine_routines.h>
''','')
    source = replace(source,'''        if (fFrameInfo375 && fReadyEvent) {
            prepare411Buffers();
            attachStage384Worker();
        }''','''        if (fFrameInfo375 && fReadyEvent) attachStage384Worker();''')
    return replace(source,'    if (bytes != F382_SLOT_BYTES || scanout383.memory[0] || scanout383.memory[1])',
        '''    if ((bytes != F382_SLOT_BYTES && bytes != F411_SLOT_BYTES) ||
        scanout383.memory[0] || scanout383.memory[1])''')


def board(source):
    source = layout.board(source)
    source = replace(source,'\nextern bool sweet_fb411_buffers(uint32_t [2], uintptr_t [2]);\n','')
    source = replace(source,'''    const uint64_t start = owner[0], slot = owner[1], payload = owner[2], length = owner[3];
''','''    const uint64_t start = owner[0], slot = owner[1], payload = owner[2], length = owner[3];
    const bool padded = slot == F411_SLOT_BYTES;
''')
    source = replace(source,'        slot != F382_SLOT_BYTES || (start & (F344_PAGE - 1)) || start < payload ||',
                          '        (!padded && slot != F382_SLOT_BYTES) || (start & (F344_PAGE - 1)) || start < payload ||')
    begin = source.index('    uintptr_t slots[2];',source.index('static bool scan382_prepare('))
    end = source.index('    const vm_offset_t vig =',begin)
    source = source[:begin]+'''    uintptr_t slots[2];
    if (!sweet_fb383_map((uint32_t)start, (uint32_t)slot, slots)) {
        printf("SWEET F383 MAP: allocation-failed\\n");
        return false;
    }
    for (unsigned i = F382_FIRST; i <= F382_SECOND; ++i) {
        scan382.address[i] = (uint32_t)(start + (i - 1) * slot);
        scan382.map[i] = slots[i - 1];
        for (uint64_t offset = 0; offset < slot; offset += F344_PAGE) {
            if (ml_vtophys(scan382.map[i] + offset) != (uint64_t)scan382.address[i] + offset) {
                sweet_fb383_discard();
                printf("SWEET F383 MAP: translation-mismatch\\n");
                return false;
            }
        }
    }
    printf("SWEET F383 MAP: %s\\n", padded ? "two-private-reserved-linear-slots" : "two-private-IOKit-WC-slots");
'''+source[end:]
    return replace(source,'scan382.address[1], scan382.address[2], (unsigned)bytes);',
                          'scan382.address[1], scan382.address[2], (unsigned)slot);')


def selected(control):
    if control=='0409':
        return phase.source_manifest('0409')
    return ADMISSION.parent/'native-kernel-stock-scope/build-manifest.json'


def source_patch(control):
    parent = selected(control)
    source = Path(load(parent)['source'])
    geometry = layout.MODEL.read_text()
    first = geometry.index('static inline bool\nf411_managed_extent')
    end = geometry.index('static inline uint32_t\nf411_pitch',first)
    geometry = geometry[:first]+geometry[end:]
    assets = [(SOURCE,framebuffer((source/SOURCE).read_text())),
              (BOARD,board((source/BOARD).read_text())),(HEADER,geometry)]
    patch = BASE/f'reserved-linear-{control}.patch'
    lines = []
    for relative,content in assets:
        file = source/relative
        before = file.read_text().splitlines(keepends=True) if file.exists() else []
        lines.extend(unified_diff(before,content.splitlines(keepends=True),
            'a/'+str(relative) if file.exists() else '/dev/null','b/'+str(relative)))
    patch.write_text(''.join(lines))
    return patch


def shim():
    if not SHIM.is_file():
        import_module('prepare-frame382').shim_image(SHIM.parent,state='reserved-linear-arm64-shim-linked')
    receipt = load(SHIM)
    image = Path(receipt['binary'])
    require(receipt['state']=='reserved-linear-arm64-shim-linked' and sha(image)==receipt['binary_sha256'] and
            all(sha(path)==digest for path,digest in receipt['input_pins'].items()),'reserved shim receipts differ')
    control = import_module('prepare-frame388').SHIM.parent
    before = {path.name:sha(path) for path in control.glob('*.o')}
    after = {path.name:sha(path) for path in SHIM.parent.glob('*.o')}
    require(before.keys()==after.keys() and {key for key in before if before[key]!=after[key]}=={'pas_reservation.o'},
            'reserved scanout shim changed units other than PAS padding admission')
    return dict(image=str(image),sha256=sha(image),bytes=image.stat().st_size)


def build(control):
    budget = load(ADMISSION)
    require(budget['admitted'] and budget['planned_batch_bytes']==310_000_000 and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            'reserved backing and concurrent runtime batch exceeds the project limit')
    parent = selected(control)
    donor = phase.source_manifest('0408')
    patch = source_patch(control)
    output = BASE/f'native-kernel-{control}'
    with redirect_stdout(StringIO()):
        import_module('build-frame347').link_scanout(parent,output,parent_trial=control,trial='0413',
            patches=(patch,),extra_units=(('SweetFramebuffer',donor,'compile-SweetFramebuffer'),
              ('gauguin_ui_trace_board',donor,'compile-gauguin_ui_trace_board')),
            recompile_scanout=False,compiler_bin=layout.COMPILER)
    manifest = output/'build-manifest.json'
    evidence = load(manifest)
    require(evidence['inputs_unchanged'] and evidence['baseline_reproduced_except_uuid'] and
            {Path(path).stem for path in evidence['object_replacements'].values()}==
                {'SweetFramebuffer','gauguin_ui_trace_board'},'reserved scanout native units differ')
    return {key:evidence[key] for key in ('identity','kernel_sha256','kernel_bytes','object_replacements')}


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=('shim','build'))
    cli.add_argument('--control',choices=('0409','0412'),default='0409')
    args = cli.parse_args()
    print(json.dumps(shim() if args.step=='shim' else build(args.control),indent=2))
