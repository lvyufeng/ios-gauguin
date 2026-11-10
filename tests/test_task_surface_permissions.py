#!/usr/bin/env python3
"""Exercise the real core Gpu request writer and the diagnostic's failure paths."""
from pathlib import Path
import hashlib, os, subprocess, tempfile
R = Path(__file__).resolve().parents[1]
C = Path(os.environ['GAUGUIN_TASK_CORE_SOURCE']).resolve()
paths = [Path(__file__), R/'tests/fixtures/task_surface_permissions.cpp',
         R/'userland/metal/task_surface_permissions.cpp', R/'userland/metal/task_surface_permissions.h',
         C/'src/gpu.cpp', *sorted((C/'include/hakios-metal').glob('*.hpp')), C/'include/hakios-metal/hakios_metal.h']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pins = {p: sha(p) for p in paths}
with tempfile.TemporaryDirectory(prefix='task-surface-permissions-') as tmp:
    exe = str(Path(tmp)/'test')
    subprocess.run(['clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I'+str(C/'include'), '-I'+str(R/'userland/metal'), str(C/'src/gpu.cpp'),
                    str(R/'userland/metal/task_surface_permissions.cpp'),
                    str(R/'tests/fixtures/task_surface_permissions.cpp'), '-o', exe], check=True)
    # Two deliberate uncertain-DMA branches retain the command BO until task exit.
    subprocess.run([exe], check=True, env=dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                                              UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
assert all(sha(p) == h for p, h in pins.items()), 'inputs changed'
