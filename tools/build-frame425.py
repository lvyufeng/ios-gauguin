#!/usr/bin/env python3
"""Link passive native submit and completion observations over 0419."""

from importlib import import_module
from pathlib import Path

from frame366_scope import WORK, load, require, sha


BASE = WORK / 'research/tmp/frame-425'
PATCH = WORK / 'xnu/patches/0307-gauguin-observe-submit-and-completion-passively.patch'
REFERENCE = import_module('prepare-frame423')
PARENT = REFERENCE.KERNEL
MANIFEST = BASE / 'native-kernel/build-manifest.json'
UNITS = ('GauguinGPU','gauguin_ui_trace_board')


def native():
    parent = REFERENCE.phase.native()
    candidate = load(MANIFEST)
    require(candidate['state'] == '0425-native-ARM64-linked' and candidate['inputs_unchanged']
            and candidate['baseline_reproduced_except_uuid']
            and sha(parent['kernel']) == parent['kernel_sha256']
            and sha(candidate['kernel']) == candidate['kernel_sha256']
            and all(candidate['input_pins'][str(path)] == sha(path) for path in (PARENT,PATCH))
            and {Path(name).stem for name in candidate['object_replacements'].values()} == set(UNITS),
            'passive observation differs beyond the two linked diagnostics')
    return candidate


def build():
    budget = load(BASE / 'total-batch-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == 2_500_000_000
            and budget['current_accounted_bytes'] + budget['planned_batch_bytes'] <= budget['limit_bytes'],
            'complete diagnostics batch is not admitted')
    import_module('build-frame347').link_scanout(PARENT, MANIFEST.parent, parent_trial='0419', trial='0425',
        patches=(PATCH,), extra_units=tuple((name,PARENT,'compile-' + name) for name in UNITS),
        recompile_scanout=False, compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    return {key:native()[key] for key in ('kernel_sha256','kernel_bytes','identity')}


if __name__ == '__main__':
    print(build())
