#!/usr/bin/env python3
"""Link the 60 Hz display drain against the exact 0415 kernel."""

from importlib import import_module
from pathlib import Path

from frame366_scope import MAIN, WORK, load, require, sha


BASE = WORK / 'research/tmp/frame-416'
PARENT = MAIN / 'research/tmp/frame-415-write-probe/timed/native-kernel/build-manifest.json'
PATCH = WORK / 'xnu/patches/0301-gauguin-drain-owned-scanout-on-stop.patch'
MANIFEST = BASE / 'native-kernel/build-manifest.json'
BATCH = 800_000_000
UNITS = {'SweetFramebuffer', 'gauguin_ui_trace_board'}


def build():
    budget = load(BASE / 'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == BATCH
            and budget['limit_bytes'] == 200_000_000_000
            and budget['current_accounted_bytes'] + BATCH <= budget['limit_bytes'],
            'complete 0416 build and preview batch is not admitted')
    old = load(PARENT)
    require(old['state'] == '0415-native-ARM64-linked' and
            sha(old['kernel']) == old['kernel_sha256'], '0415 linked parent differs')
    import_module('build-frame347').link_scanout(
        PARENT, MANIFEST.parent, parent_trial='0415', trial='0416', patches=(PATCH,),
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    candidate = load(MANIFEST)
    require({Path(path).stem for path in candidate['object_replacements'].values()} == UNITS,
            '0416 changed a kernel unit outside the display drain')


if __name__ == '__main__':
    build()
