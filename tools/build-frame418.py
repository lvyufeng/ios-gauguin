#!/usr/bin/env python3
"""Link and verify private scanout completion without an active frame trace."""

from importlib import import_module
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, load, require, sha


previous = import_module('prepare-frame417')
BASE = WORK / 'research/tmp/frame-418'
PATCH = WORK / 'xnu/patches/0303-gauguin-keep-stage-completion-after-trace.patch'
MANIFEST = BASE / 'native-kernel/build-manifest.json'
BATCH = 700_000_000


def check_source(manifest):
    source = Path(manifest['source']) / 'iokit/Kernel/arm/SweetFramebuffer.cpp'
    lines = source.read_text().splitlines()
    use, = (index for index, line in enumerate(lines) if '*verifiedFullCopy = frameCopyEnd;' in line)
    finish, = (index for index, line in enumerate(lines) if 'const uint64_t frameCopyEnd =' in line)
    require(lines[finish - 2].strip() == 'if (ordered) __asm__ volatile("dsb sy" ::: "memory");'
            and finish < use, 'private completion is outside the copy store barrier')
    with TemporaryDirectory(prefix='gauguin-copy-completion-') as directory:
        test = Path(directory) / 'completion.cpp'
        test.write_text('''
#include <cassert>
#include <cstdint>

static unsigned calls;
static uint64_t mach_absolute_time() { ++calls; return 1234; }
static uint64_t completion(uint64_t frameCopyBegin, uintptr_t flipDst) {
''' + lines[finish] + '''
    return frameCopyEnd;
}
int main() {
    assert(completion(0, 0) == 0 && calls == 0);
    assert(completion(1, 0) == 1234 && calls == 1);
    assert(completion(0, 1) == 1234 && calls == 2);
    assert(completion(1, 1) == 1234 && calls == 3);
}
''')
        binary = test.with_suffix('')
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', str(test), '-o', str(binary)], check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=10)
    return dict(completion_cases=4, store_barrier_before_completion=True, patch_sha256=sha(PATCH),
                kernel_sha256=manifest['kernel_sha256'], device_commands=0)


def build():
    previous.batch_tools.budget(BASE / 'build-storage-admission.json', BATCH)
    previous.native()
    restored = load(previous.BASE / 'execution/result.json')
    require(restored['independent_restore_verified'] and restored['static_root_comparison_passed'],
            '0417 has no independent restoration')
    if not MANIFEST.exists():
        import_module('build-frame347').link_scanout(
            previous.KERNEL, MANIFEST.parent, parent_trial='0417', trial='0418', patches=(PATCH,),
            recompile_scanout=False, extra_units=(('SweetFramebuffer', previous.KERNEL, 'compile-SweetFramebuffer'),),
            compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    candidate = load(MANIFEST)
    require(candidate['state'] == '0418-native-ARM64-linked'
            and candidate['baseline_reproduced_except_uuid'] and candidate['inputs_unchanged']
            and sha(candidate['kernel']) == candidate['kernel_sha256']
            and candidate['input_pins'][str(previous.KERNEL)] == sha(previous.KERNEL)
            and candidate['input_pins'][str(PATCH)] == sha(PATCH)
            and {Path(path).stem for path in candidate['object_replacements'].values()} == {'SweetFramebuffer'},
            '0418 changed more than the framebuffer completion overlay')
    previous.save(BASE / 'completion-host.json', check_source(candidate))


if __name__ == '__main__':
    build()
