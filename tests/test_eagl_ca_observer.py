#!/usr/bin/env python3
"""Run the production observer with actual Mach VM, COW pages and ObjC companion tests."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile

R = Path(__file__).resolve().parent.parent
paths = [Path(__file__), R / 'tests/fixtures/eagl_ca_observer.c',
         R / 'userland/eagl/ca_effects.h', R / 'userland/eagl/ca_observer.inc']
pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='eagl-ca-observer-') as temporary:
    executable = Path(temporary) / 'observer'
    subprocess.run(['clang', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I' + str(R / 'userland/eagl'), str(paths[1]), '-o', str(executable)],
                   check=True, env=env)
    subprocess.run([str(executable)], check=True, env=env)
assert pins == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
