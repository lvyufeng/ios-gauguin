#!/usr/bin/env python3
"""Exercise the production late installer against the real Objective-C runtime."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile

R = Path(__file__).resolve().parent.parent
bridge = R / 'userland/eagl/bridge.inc'
fixture = R / 'tests/fixtures/eagl_bridge.c'
paths = [Path(__file__), bridge, fixture]
pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
unit = fixture.read_text()
assert unit.count('@BRIDGE@') == 1
unit = unit.replace('@BRIDGE@', bridge.read_text())
env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='eagl-late-installer-') as temporary:
    root = Path(temporary)
    source, executable = root / 'bridge.c', root / 'bridge'
    source.write_text(unit)
    subprocess.run(['clang', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-framework', 'Foundation', '-lobjc', str(source), '-o', str(executable)],
                   check=True, env=env)
    subprocess.run([str(executable), 'direct'], check=True, env=env)
    subprocess.run([str(executable), 'inherited'], check=True, env=env)
assert pins == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
