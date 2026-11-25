#!/usr/bin/env python3
"""Compile the actual present-stats header with clang++ ASan/UBSan and run host checks."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEADER = ROOT / 'research/tmp/SweetPresentStats.h'
FIXTURE = ROOT / 'tests/fixtures/present_stats_host.cpp'


def header_under_test():
    if 'XNU_SOURCE' in os.environ:
        tree = os.environ['XNU_SOURCE']
        if not tree:
            raise SystemExit('XNU_SOURCE is set but empty')
        return Path(tree) / 'iokit/Kernel/arm/SweetPresentStats.h'
    return DEFAULT_HEADER


def run_checked(argv, env, cwd, timeout):
    result = subprocess.run(argv, env=env, cwd=cwd, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode != 0:
        print(f'FAILED ({result.returncode}): {" ".join(argv)}', file=sys.stderr)
        if result.stdout:
            print(result.stdout, end='', file=sys.stderr)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        raise SystemExit(result.returncode or 1)
    return result


def main():
    header = header_under_test()
    if not header.is_file():
        raise SystemExit(f'present-stats header missing: {header}')
    if not FIXTURE.is_file():
        raise SystemExit(f'present-stats fixture missing: {FIXTURE}')
    compiler = shutil.which('clang++')
    if compiler is None:
        raise SystemExit('clang++ not found on PATH')

    fixture = FIXTURE.read_text(encoding='utf-8')
    if fixture.count('@HEADER@') != 1:
        raise SystemExit('present-stats fixture must contain exactly one @HEADER@')
    source = fixture.replace('@HEADER@', header.read_text(encoding='utf-8'))

    env = dict(os.environ)
    env['ASAN_OPTIONS'] = 'halt_on_error=1:detect_leaks=0'
    env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    with tempfile.TemporaryDirectory(prefix='present-stats-') as directory:
        work = Path(directory)
        cpp = work / 'present_stats_host.cpp'
        exe = work / 'present_stats_host'
        cpp.write_text(source, encoding='utf-8')
        compile_argv = [
            compiler, '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-pedantic', '-fsanitize=address,undefined',
            '-fno-sanitize-recover=all', '-fno-omit-frame-pointer',
            str(cpp), '-pthread', '-o', str(exe),
        ]
        run_checked(compile_argv, env, work, 120)
        result = run_checked([str(exe)], env, work, 60)
        print(f'header: {header}')
        print(result.stdout, end='')


if __name__ == '__main__':
    main()