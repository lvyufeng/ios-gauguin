#!/usr/bin/env python3
"""Model the candidate's actual blanking writes and following-scan readback."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, load, require, sha

build = import_module('check-frame411-linear-view')


def check(manifest=build.NATIVE):
    candidate = load(manifest)
    prefix = Path(candidate['source'])
    board = prefix/build.BOARD
    fixture = WORK/'tests/fixtures/gauguin_padded_scanout_register_host.c'
    contents = board.read_text()
    start = contents.index('unsigned sweet_frame382_issue(')
    end = contents.index('static void scan_report(',start)
    implementation = contents[start:end]
    for order,name in enumerate(('dsb oshst','dsb sy'),1):
        instruction = '__asm__ volatile("'+name+'" ::: "memory");'
        require(implementation.count(instruction)==1,'unexpected backing publication barrier')
        implementation = implementation.replace(instruction,f'barrier({order});')
    sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    with TemporaryDirectory(prefix='scanout-registers-',dir=manifest.parent.parent) as temporary:
        directory = Path(temporary)
        (directory/'frame411_flip_impl.inc').write_text(implementation)
        executable = directory/'flip'
        subprocess.run([str(build.COMPILER/'clang'),'-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(directory),
            '-I'+str(prefix/'bsd/dev'),str(fixture),'-o',str(executable)],check=True,timeout=60)
        subprocess.run([str(executable)],check=True,timeout=20)
    return dict(state='0411-native-flip-geometry-seams-passed',cases=8,device_commands=0,
                input_pins={str(path):sha(path) for path in (manifest,board,fixture)})


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
