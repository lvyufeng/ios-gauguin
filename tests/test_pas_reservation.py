#!/usr/bin/env python3
"""Exercise the real loader and PAS metadata parser; no device access."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / 'tests/pas_reservation'


def main():
    with tempfile.TemporaryDirectory(prefix='pas-reservation-') as temporary:
        out = Path(temporary)
        env = dict(os.environ, PAS_TEST_OUT=str(out))
        subprocess.run([sys.executable, str(FIXTURES / 'make_cases.py')],
                       env=env, check=True, timeout=60)
        flags = shlex.split(os.environ.get('CC', 'cc')) + [
            '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I' + str(ROOT / 'shim')]
        runtime = out / 'runtime'
        subprocess.run(flags + [str(FIXTURES / 'test_runtime.c'),
                               str(ROOT / 'shim/pas_reservation.c'), '-o', str(runtime)],
                       check=True, timeout=60)
        cases = json.loads((out / 'cases.json').read_text())
        for case in cases:
            subprocess.run([str(runtime), case['path']], check=True, timeout=10)

        # Execute actual loader C; replace only privileged instructions, linker
        # image bounds, and final branch/stop with host-controlled boundaries.
        source = (ROOT / 'shim/loader.c').read_text()
        source = source.replace('extern const uint8_t _head[], _end[];',
                                'extern const uint8_t *test_image_start, *test_image_end;')
        source = source.replace('(uintptr_t)_head', '(uintptr_t)test_image_start')
        source = source.replace('(uintptr_t)_end', '(uintptr_t)test_image_end')
        source = source.replace('__asm__ volatile("wfe" ::: "memory");', 'test_stop();')
        source = source.replace('__asm__ volatile("dsb sy; ic iallu; dsb sy; isb" ::: "memory");', '')
        source = source.replace('((xnu_entry_t)entry_pa)(ba_pa);',
                                '(void)entry_pa; test_jump(ba_pa);')
        host = out / 'loader.c'
        host.write_text('#include <stdint.h>\n'
                        'extern void test_stop(void) __attribute__((noreturn));\n'
                        'extern void test_jump(uint64_t) __attribute__((noreturn));\n' + source)
        loader = out / 'loader'
        subprocess.run(flags + [str(FIXTURES / 'test_loader.c'), str(host),
                               str(ROOT / 'shim/pas_reservation.c'), '-o', str(loader)],
                       check=True, timeout=60)
        default = next(c['path'] for c in cases if c['name'] == 'default')
        subprocess.run([str(loader), default], check=True, timeout=30)
        print(f'{len(cases)} PAS metadata cases and actual loader passed ASan/UBSan')


if __name__ == '__main__':
    main()
