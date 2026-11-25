#!/usr/bin/env python3
"""Link the bounded sustained 60 Hz profile over the exact 0416 overlay."""

from importlib import import_module
from pathlib import Path

from frame366_scope import MAIN, WORK, load, require, sha


BASE = WORK / 'research/tmp/frame-417'
P416 = MAIN / 'research/tmp/gauguin-frame416-display-drain-worktree-20261124/research/tmp/frame-416'
PARENT = P416 / 'native-kernel/build-manifest.json'
TOUCH = (MAIN / 'research/tmp/gauguin-frame402-stock-cpu-opp-worktree-20261124'
         / 'research/tmp/frame-402/native-kernel/build-manifest.json')
PATCH = WORK / 'xnu/patches/0302-gauguin-sustain-60-display-workload.patch'
MANIFEST = BASE / 'native-kernel/build-manifest.json'
BATCH = 1_400_000_000
UNITS = {'SweetFramebuffer', 'gauguin_ui_trace_board', 'sweet_touch'}


def build():
    budget = load(BASE / 'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == BATCH
            and budget['limit_bytes'] == 200_000_000_000
            and budget['current_accounted_bytes'] + BATCH <= budget['limit_bytes'],
            'complete 0417 build and test batch is not admitted')
    old = load(PARENT)
    require(old['state'] == '0416-native-ARM64-linked' and
            sha(old['kernel']) == old['kernel_sha256'], '0416 parent differs')
    import_module('build-frame347').link_scanout(
        PARENT, MANIFEST.parent, parent_trial='0416', trial='0417', patches=(PATCH,),
        extra_units=(('sweet_touch', TOUCH, 'compile-sweet_touch'),),
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    candidate = load(MANIFEST)
    require({Path(path).stem for path in candidate['object_replacements'].values()} == UNITS,
            '0417 changed a kernel unit outside display and test input')


if __name__ == '__main__':
    build()
