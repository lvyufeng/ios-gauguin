#!/usr/bin/env python3
"""Exercise actual health-to-watchdog ordering, not a mirrored service model."""
from pathlib import Path
import hashlib
import os
import re
import subprocess
import tempfile

R = Path(__file__).resolve().parent.parent
D = Path(os.environ.get('XNU_SOURCE', str(R / '.deps-cache/p0-20261105/source177-codex'))) / 'bsd/dev'
fixture = R / 'tests/fixtures/gpu-user/service_host.c'
board = Path(os.environ.get('GPU_SERVICE_BOARD_SOURCE', str(D / 'gauguin_gmu_board.c')))
files = [Path(__file__), fixture, board, D / 'gauguin_gpu_runtime.c',
         D / 'gauguin_gpu_runtime.h', D / 'gauguin_wdt_lease.h']
pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

def function(name):
    source = board.read_text()
    start = re.search(r'^bool ' + name + r'\(void\)\n', source, re.M)
    assert start, name
    opening = source.index('{', start.end())
    depth = 0
    for end in range(opening, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if depth == 0:
            return source[start.start():end + 1]
    raise AssertionError('unterminated actual function ' + name)

unit = fixture.read_text()
checkpoint = 'gpzb_boot_refresh.sequence' in board.read_text()
unit = '#define GPU_HAS_BOOT_CHECKPOINT ' + str(int(checkpoint)) + '\n' + unit
for marker, name in [('READY', 'sweet_gpu_runtime_ready'),
                     ('REQUESTED', 'sweet_gpu_service_requested'),
                     ('HEARTBEAT', 'sweet_gpu_runtime_heartbeat')]:
    assert unit.count('@' + marker + '@') == 1
    unit = unit.replace('@' + marker + '@', function(name))
with tempfile.TemporaryDirectory(prefix='gpu-service-') as td:
    td = Path(td)
    source = td / 'test.c'
    source.write_text(unit)
    binary = td / 'test'
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I' + str(D),
                    str(D / 'gauguin_gpu_runtime.c'), str(source), '-o', str(binary)], env=env, check=True)
    subprocess.run([str(binary)], env=env, check=True)
assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, 'inputs changed'
