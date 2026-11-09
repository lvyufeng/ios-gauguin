#!/usr/bin/env python3
"""Execute real IOSurface create against fallible VM seams; old code must fail functionally."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TREE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source217-codex'))
REL = 'iokit/Kernel/arm/SweetSurface.cpp'
FIXTURE = ROOT / 'tests/fixtures/surface_create_host.cpp'


def unit(source):
    def method(signature):
        start = source.index(signature)
        return source[start:source.index('\n}\n', start) + 3]
    methods = [method(signature) for signature in (
        'void\nSweetSurface::free()', 'uintptr_t\nSweetSurface::kernelAddress()',
        'IOMemoryMap *\nSweetSurface::mapPixelsInTask(',
        'static uint32_t\nsweet_dict_u32(', 'static uint32_t\nsweet_div_up(',
        'static uint32_t\nsweet_row_bytes(', 'static IOReturn\nsweet_surface_layout(')]
    for signature in ('static bool\nsweet_surface_client_numbers(',
                      'static bool\nsweet_surface_client_extent(',
                      'static IOReturn\nsweet_surface_client_layout(',
                      'static IOReturn\nsweet_surface_bind_client('):
        if signature in source:
            methods.append(method(signature))
    methods.append(method('IOReturn\nIOSurfaceRootUserClient::create('))
    fixture = FIXTURE.read_text()
    assert fixture.count('@METHODS@') == 1
    return fixture.replace('@METHODS@', '\n'.join(methods))


def main():
    reference = os.environ.get('SURFACE_CREATE_REFERENCE')
    sources = [('baseline', Path(reference) / REL)] if reference else []
    sources.append(('candidate', TREE / REL))
    paths = [Path(__file__), FIXTURE, *(p for _, p in sources)]
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    with tempfile.TemporaryDirectory(prefix='surface-client-create-') as d:
        directory = Path(d)
        for name, source in sources:
            cpp = directory / (name + '.cpp')
            cpp.write_text(unit(source.read_text()))
            exe = directory / name
            subprocess.run(['clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra',
                            '-Werror', '-pedantic', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', str(cpp), '-o', str(exe)],
                           env=env, check=True)
            result = subprocess.run([str(exe)], env=env, text=True, capture_output=True, timeout=30)
            if name == 'baseline':
                assert result.returncode == 42, (result.returncode, result.stdout, result.stderr)
                assert result.stderr == 'FAIL IOSurfaceCreate ignored caller image storage\n', result.stderr
                print('Baseline functional RED: IOSurfaceCreate substitutes blank storage for caller pixels')
            else:
                assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
                print(result.stdout, end='')
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
