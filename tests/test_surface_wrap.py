#!/usr/bin/env python3
"""Run production IOSurface wrapping and cleanup with fallible IOKit seams."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TREE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source197-codex'))
SOURCE = TREE / 'iokit/Kernel/arm/SweetSurface.cpp'
FIXTURE = ROOT / 'tests/fixtures/surface_wrap_host.cpp'


def main():
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, FIXTURE)}
    source = SOURCE.read_text()

    def extract(signature):
        start = source.index(signature)
        return source[start:source.index('\n}\n', start) + 3]

    methods = '\n'.join(extract(s) for s in (
        'void\nSweetSurface::free()',
        'uintptr_t\nSweetSurface::kernelAddress()',
        'IOReturn\nIOSurfaceRootUserClient::wrapImage('))
    fixture = FIXTURE.read_text()
    assert fixture.count('@METHODS@') == 1
    with tempfile.TemporaryDirectory(prefix='surface-wrap-') as directory:
        directory = Path(directory)
        unit = directory / 'test.cpp'
        unit.write_text(fixture.replace('@METHODS@', methods))
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run([os.environ.get('CXX', 'clang++'), '-std=c++17',
                        '-Wall', '-Wextra', '-Werror', '-pedantic',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-O1', '-g', str(unit), '-o', str(directory / 'test')],
                       env=env, check=True)
        subprocess.run([str(directory / 'test')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
