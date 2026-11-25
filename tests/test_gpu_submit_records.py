#!/usr/bin/env python3
"""Exercise the production submission wrapper across startup, streaming and faults."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile

R = Path(__file__).resolve().parent.parent
D = Path(os.environ.get('XNU_SOURCE', str(R / '.deps-cache/p0-20261105/source195-codex'))) / 'bsd/dev'
board = Path(os.environ.get('GPU_SUBMIT_BOARD_SOURCE', str(D / 'gauguin_gmu_board.c')))
fixture = R / 'tests/fixtures/gpu-user/submit_records_host.c'
text = board.read_text()
start = text.index('bool sweet_gpu_runtime_submit(')
opening = text.index('{', start)
depth = 0
for end in range(opening, len(text)):
    depth += (text[end] == '{') - (text[end] == '}')
    if depth == 0:
        break
body = text[start:end + 1]
assert body.endswith('}')
template = fixture.read_text()
assert template.count('@SUBMIT@') == 1
unit = template.replace('@SUBMIT@', body)
paths = [Path(__file__), board, fixture, D / 'gauguin_gpu_runtime.h']
pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-submit-records-') as temporary:
    root = Path(temporary)
    source, executable = root / 'records.c', root / 'records'
    source.write_text(unit)
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                    '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I' + str(D), str(source), '-o', str(executable)], check=True, env=env)
    subprocess.run([str(executable)], check=True, env=env)
assert pins == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
