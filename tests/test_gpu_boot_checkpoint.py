#!/usr/bin/env python3
"""Exercise the production pre-ZAP checkpoint and preserve its guard ordering."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile

R = Path(__file__).resolve().parent.parent
D = Path(os.environ.get('XNU_SOURCE', str(R / '.deps-cache/p0-20261105/source194-codex'))) / 'bsd/dev'
source_path = Path(os.environ.get('GPU_CHECKPOINT_BOARD_SOURCE', str(D / 'gauguin_gmu_board.c')))
fixture = R / 'tests/fixtures/gpu-zap/checkpoint_host.c'


def function(text, name):
    start = text.index('static bool ' + name + '(')
    opening = text.index('{', start)
    depth = 0
    for position in range(opening, len(text)):
        if text[position] == '{':
            depth += 1
        elif text[position] == '}':
            depth -= 1
            if depth == 0:
                return text[start:position + 1]
    raise AssertionError(name)


source = source_path.read_text()
body = function(source, 'gpzb_checkpoint')
guard = function(source, 'gpzb_guard')
call = '    if(!gpzb_checkpoint(phase))return false;\n'
assert guard.count(call) == 1
assert guard.index('gpzb_diagnostic.shadow!=15') < guard.index(call)
assert guard.index('gauguin_wdt_lease_check_budget(GMB_MIN)') < guard.index(call)
assert guard.index(call) < guard.rindex('return gpzb_time(phase,scope);')
assert guard.index('if(scope!=GPZ_LIVE)return true;') < guard.index(call)
base = os.environ.get('GPU_CHECKPOINT_BASELINE')
if base:
    restored = guard.replace(call, '')
    entry_start = restored.index('    bool checkpoint = phase == GPZ_SEAL')
    entry_end = restored.index('    if(!gpzb_time(phase,scope))return false;', entry_start)
    restored = restored[:entry_start] + (
        '    if(!gauguin_wdt_lease_check_budget(minimum*GAUGUIN_WDT_CLOCK_HZ))'
        'return gpzb_reject(phase,scope,PZB_WDT);\n') + restored[entry_end:]
    after = ('    if(checkpoint&&!gauguin_wdt_lease_check_budget(minimum*GAUGUIN_WDT_CLOCK_HZ))'
             'return gpzb_reject(phase,scope,PZB_WDT);\n')
    assert restored.count(after) == 1
    assert guard.index(after) > guard.index(call)
    restored = restored.replace(after, '')
    assert restored == function(Path(base).read_text(), 'gpzb_guard')
unit = fixture.read_text()
assert unit.count('@CHECKPOINT@') == 1
unit = unit.replace('@CHECKPOINT@', body)
paths = [Path(__file__), source_path, fixture, D / 'gauguin_gpu_zap.h', D / 'gauguin_wdt_lease.h']
pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-boot-checkpoint-') as temporary:
    root = Path(temporary)
    test_source, executable = root / 'checkpoint.c', root / 'checkpoint'
    test_source.write_text(unit)
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                    '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I' + str(D), str(test_source), '-o', str(executable)], check=True, env=env)
    subprocess.run([str(executable)], check=True, env=env)
assert pins == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
