#!/usr/bin/env python3
"""Link the bounded Spotlight workload over the exact 0419 renderer."""

from importlib import import_module
from pathlib import Path

from frame366_scope import MAIN, WORK, load, require, sha


previous = import_module('build-frame425')
BASE = WORK / 'research/tmp/frame-426'
PATCH = WORK / 'xnu/patches/0308-gauguin-diagnose-reproducible-spotlight-input.patch'
PARENT = previous.PARENT
MANIFEST = BASE / 'native-kernel/build-manifest.json'
TOUCH = MAIN / 'research/tmp/gauguin-frame417-sustained-60-worktree-20261124/research/tmp/frame-417/native-kernel/build-manifest.json'
KDEBUG = MAIN / 'research/tmp/gauguin-frame401-render-ownership-worktree-20261123/research/tmp/frame-404/native-kernel/build-manifest.json'
UNITS = {'gauguin_ui_trace_board':PARENT,'sweet_touch':TOUCH,'kdebug':KDEBUG}


def native():
    link = load(MANIFEST)
    require(link['state'] == '0426-native-ARM64-linked' and link['inputs_unchanged']
            and link['baseline_reproduced_except_uuid'] and sha(link['kernel']) == link['kernel_sha256']
            and all(link['input_pins'][str(p)] == sha(p) for p in (PARENT,PATCH,TOUCH,KDEBUG))
            and {Path(name).stem for name in link['object_replacements'].values()} == set(UNITS),
            'Spotlight trial changed the renderer or unrelated objects')
    return link


def build():
    budget = load(previous.BASE / 'total-batch-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == 2_500_000_000
            and budget['current_accounted_bytes'] + budget['planned_batch_bytes'] <= budget['limit_bytes'],
            'complete diagnostics batch is not admitted')
    previous.REFERENCE.phase.native()
    import_module('build-frame347').link_scanout(PARENT,MANIFEST.parent,parent_trial='0419',trial='0426',
        patches=(PATCH,),extra_units=tuple((name,receipt,'compile-' + name) for name,receipt in UNITS.items()),
        recompile_scanout=False,compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    return {key:native()[key] for key in ('kernel_sha256','kernel_bytes','identity')}


if __name__ == '__main__':
    print(build())
