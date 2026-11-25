#!/usr/bin/env python3
"""Link the independent display deadline timeline over exact 0418."""

from importlib import import_module
from pathlib import Path

from frame366_scope import MAIN, WORK, load, require, sha


BASE = WORK / 'research/tmp/frame-419'
SOURCE_WORK = MAIN / 'research/tmp/gauguin-frame417-sustained-60-worktree-20261124'
P417 = SOURCE_WORK / 'research/tmp/frame-417'
P418 = SOURCE_WORK / 'research/tmp/frame-418'
PARENT = P418 / 'native-kernel/build-manifest.json'
GPU = MAIN / 'research/tmp/frame-415-write-probe/timed/native-kernel/build-manifest.json'
BOARD = P417 / 'native-kernel/build-manifest.json'
PATCH = WORK / 'xnu/patches/0304-gauguin-trace-deadlines-independently.patch'
MANIFEST = BASE / 'native-kernel/build-manifest.json'
BATCH = 1_450_000_000
UNITS = ('SweetFramebuffer', 'gauguin_ui_trace_board', 'GauguinGPU')


def native():
    parent = load(PARENT)
    require(parent['state'] == '0418-native-ARM64-linked'
            and parent['kernel_sha256'] == sha(parent['kernel'])
            == 'c478f2ca58b11ecdd0cb5d36215eaf52f0dfcdc890d943eac3eb61c7bc494e19',
            '0418 linked identity differs')
    link = load(MANIFEST)
    require(link['state'] == '0419-native-ARM64-linked' and link['inputs_unchanged']
            and link['baseline_reproduced_except_uuid'] and sha(link['kernel']) == link['kernel_sha256']
            and all(link['input_pins'][str(path)] == sha(path) for path in (PARENT, GPU, BOARD, PATCH))
            and set(UNITS) == {Path(name).stem for name in link['object_replacements'].values()},
            '0419 is not the exact three-object deadline timeline')
    return link


def build():
    budget = load(BASE / 'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == BATCH
            and budget['limit_bytes'] == 200_000_000_000
            and budget['current_accounted_bytes'] + BATCH <= budget['limit_bytes'],
            '0419 whole build and trial batch is not admitted')
    import_module('build-frame347').link_scanout(
        PARENT, MANIFEST.parent, parent_trial='0418', trial='0419', patches=(PATCH,),
        extra_units=tuple((name, receipt, 'compile-' + name)
                          for name, receipt in zip(UNITS, (PARENT, BOARD, GPU), strict=True)),
        recompile_scanout=False, compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    native()


if __name__ == '__main__':
    build()
