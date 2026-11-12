#!/usr/bin/env python3
"""Compile actual GPU submit body with the shared C ABI and CPU-only seams."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(source):
    marker = 'GauguinGPUUserClient::submit('
    assert source.count(marker) == 1
    start = source.rfind('\n', 0, source.index(marker)) + 1
    opening = source.index('{', source.index(marker))
    depth = 0
    for at in range(opening, len(source)):
        if source[at] == '{':
            depth += 1
        elif source[at] == '}':
            depth -= 1
            if not depth:
                return source[start:at + 1]
    raise ValueError('unclosed GPU submit method')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    source_root = args.candidate_root.resolve()
    source = source_root / 'iokit/Kernel/arm/GauguinGPU.cpp'
    runtime = source_root / 'bsd/dev/gauguin_gpu_runtime.c'
    header = source_root / 'bsd/dev/gauguin_gpu_runtime.h'
    fixture = repo / 'tests/fixtures/gpu-user/async_submit_host.cpp'
    out = args.out.resolve()
    assert out.is_relative_to(repo / 'research/tmp') and not out.exists()
    inputs = [Path(__file__).resolve(), source, runtime, header, fixture]
    pins = {str(p): sha(p) for p in inputs}
    model = fixture.read_text()
    assert model.count('/* INSERT_REAL_SUBMIT_METHOD */') == 1
    out.mkdir(parents=True)
    composite = out / 'submit-host.cpp'
    composite.write_text(model.replace('/* INSERT_REAL_SUBMIT_METHOD */',
                                       extract(source.read_text())))
    binary = out / 'submit-host'
    runtime_object = out / 'runtime.o'
    sanitizer = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    compile_commands = [
        ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
         *sanitizer, '-I', str(header.parent), '-c', str(runtime),
         '-o', str(runtime_object)],
        ['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
         *sanitizer, '-I', str(header.parent), str(composite),
         str(runtime_object), '-o', str(binary)],
    ]
    with (out / 'compile.log').open('x') as stream:
        for command in compile_commands:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                           check=True, env=env)
    with (out / 'run.log').open('x') as stream:
        subprocess.run([str(binary)], stdout=stream, stderr=subprocess.STDOUT,
                       check=True, env=env, timeout=30)
    log = (out / 'run.log').read_text()
    assert 'real async-submit escrow/fence/failure/sync assertions' in log
    assert all(sha(Path(path)) == digest for path, digest in pins.items())
    result = {'state': 'passed-actual-user-client-submit-CPU-host',
              'input_pins': pins, 'inputs_unchanged': True,
              'composite_sha256': sha(composite),
              'run_log_sha256': sha(out / 'run.log'),
              'sanitizer': 'address,undefined', 'device_commands': 0,
              'hardware_qualified': False,
              'scope': 'actual submit body and shared C ABI under CPU-only seams'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'},
                     indent=2))


if __name__ == '__main__':
    main()
