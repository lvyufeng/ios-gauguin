#!/usr/bin/env python3
"""Observed bit31 request: old production guard RED, new guard preserves real holds."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile

from test_present_lifetime import unit

ROOT = Path(__file__).resolve().parents[1]
TREE = Path(os.environ['XNU_SOURCE'])
REFERENCE = Path(os.environ['SWAP_METADATA_REFERENCE'])
BLOCK = ROOT / 'tests/fixtures/swap_metadata_host.cpp'


def main():
    files = [Path(__file__), BLOCK, ROOT / 'tests/test_present_lifetime.py', ROOT / 'tests/fixtures/present_lifetime_host.cpp']
    files += [tree / 'iokit/Kernel/arm' / name for tree in [REFERENCE, TREE] for name in ['SweetFramebuffer.cpp', 'SweetSurface.cpp']]
    pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    marker = '    std::printf("PASS held presentation checks='
    with tempfile.TemporaryDirectory(prefix='swap-metadata-') as directory:
        for name, tree in [('baseline', REFERENCE), ('candidate', TREE)]:
            text = unit(tree)
            assert text.count(marker) == 1
            text = text.replace(marker, BLOCK.read_text() + marker)
            cpp = Path(directory) / (name + '.cpp')
            cpp.write_text(text)
            exe = cpp.with_suffix('')
            subprocess.run(['clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-function', '-Wno-unused-variable', '-pedantic', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', str(cpp), '-pthread', '-o', str(exe)], env=env, check=True)
            result = subprocess.run([str(exe)], env=env, text=True, capture_output=True, timeout=30)
            if name == 'baseline':
                assert result.returncode == 42 and result.stderr == 'FAIL background update bit31 rejected a valid low-layer handoff\n', (result.returncode, result.stdout, result.stderr)
                print('Baseline functional RED: actual0291 guard rejects observed background update before holding its low-layer surface')
            else:
                assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
                print(result.stdout, end='')
                print('PASS 32 low-layer/background combinations, 54 unknown-bit cases, raw request preservation, partial unwind and owner/lifetime checks; host seams only')
    assert pins == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


if __name__ == '__main__':
    main()
