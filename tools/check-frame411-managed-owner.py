#!/usr/bin/env python3
"""Exercise the actual ARM64 candidate's owner construction and refusal paths."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, load, require, sha

build = import_module('check-frame411-linear-view')


def check():
    manifest = build.NATIVE
    native = load(manifest)
    source = Path(native['source'])/build.SOURCE
    fixture = WORK/'tests/fixtures/gauguin_managed_scanout_host.cpp'
    header = Path(native['source'])/build.HEADER
    require(native['state']=='0411-native-ARM64-linked' and native['input_pins'][str(build.PATCH)]==sha(build.PATCH),
            '0411 compiled backing source differs')
    text = source.read_text()
    begin = text.index('static IOBufferMemoryDescriptor *f411Owner[2];')
    end = text.index('/* The private descriptors are never published as IOSurfaces.',begin)
    sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    with TemporaryDirectory(prefix='0411-owner-',dir=build.BASE) as temporary:
        directory = Path(temporary)
        (directory/'LinearScanout411.h').write_bytes(header.read_bytes())
        (directory/'managed_impl.inc').write_text(text[begin:end])
        binary = directory/'owner'
        subprocess.run([str(build.COMPILER/'clang++'),'-isysroot',sdk,'-std=c++20','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(directory),str(fixture),'-o',str(binary)],
            check=True,timeout=60)
        subprocess.run([str(binary)],check=True,timeout=20)
    return dict(state='0411-actual-managed-allocation-owner-checked',allocation_fault_boundaries=9,
        malformed_scope_cases=1,success_with_duplicate_request=1,device_commands=0,
        input_pins={str(path):sha(path) for path in (manifest,source,header,fixture)})


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
