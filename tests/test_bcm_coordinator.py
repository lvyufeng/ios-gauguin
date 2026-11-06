#!/usr/bin/env python3
"""Actual coordinator C with typed dependency/platform seams; no real waits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT = Path(os.environ.get('XNU_SOURCE', str(ROOT / '.deps-cache/p0-20261105/source115-codex'))) / 'bsd/dev'
FIXTURE = HERE / 'fixtures/gauguin_bcm_coordinator_host.c'


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', type=Path, default=DEFAULT)
    args = parser.parse_args()
    dev = baseline = args.dev.resolve()
    source = dev / 'gauguin_bcm_coordinator.c'
    staged = dev.parents[1]
    entries = (staged / 'bsd/conf/files').read_text()
    for name in ('gauguin_bcm_transport.c', 'gauguin_bcm_coordinator.c'):
        assert entries.count('bsd/dev/' + name + '\t\tstandard') == 1
    init = (staged / 'bsd/kern/bsd_init.c').read_text()
    blocks = re.findall(r'#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
    assert init.count('sweet_bcm_vote_init();') == 1
    assert any('\tsweet_bcm_vote_init();\n' in block for block in blocks)
    assert any('extern void sweet_bcm_vote_init(void);\n' in block for block in blocks)
    files = [source, FIXTURE, *(dev / name for name in (
        'gauguin_pas_stage.h', 'gauguin_bus_probe.h', 'gauguin_bcm_transport.h', 'gauguin_wdt_lease.h')),
        baseline / 'gauguin_bcm_plan.h']
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    build = Path(temporary)
    report = {'state': 'running', 'inputs': hashes, 'scope': 'actual coordinator; CPU API seams; no hardware'}
    log_path = build / 'run.log'
    try:
        code = re.sub(r'^#include .*\n', '', source.read_text(), flags=re.M)
        assert not re.search(r'__asm__|\*\(volatile|\bsmc\s*#', code)
        fixture = FIXTURE.read_text()
        assert fixture.count('\n@SOURCE@\n') == 1
        unit, binary = build / 'coordinator.c', build / 'coordinator'
        unit.write_text(fixture.replace('\n@SOURCE@\n', '\n' + code + '\n'))
        env = os.environ.copy()
        env['ASAN_OPTIONS'] = 'halt_on_error=1'
        env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
        commands = [['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
                     '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I' + str(dev),
                     '-I' + str(baseline), str(unit), '-o', str(binary)], [str(binary)]]
        with log_path.open('w') as log:
            for command in commands:
                log.write('$ ' + shlex.join(command) + '\n'); log.flush()
                result = subprocess.run(command, stdout=log, stderr=log, env=env)
                log.write(f'exit={result.returncode}\n'); log.flush()
                if result.returncode:
                    raise RuntimeError(f'{command[0]} exited {result.returncode}')
        if {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files} != hashes:
            raise RuntimeError('inputs changed during run')
        report['state'] = 'passed'
    except Exception as error:
        report.update(state='failed', error=str(error))
        print(f'FAIL: {error}; {log_path}', file=sys.stderr)
        if log_path.exists():
            print('\n'.join(log_path.read_text().splitlines()[-35:]), file=sys.stderr)
        return 1
    finally:
        (build / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(log_path.read_text().splitlines()[-2])
    print(f'PASS: coordinator fixture; {build / "result.json"}')
    return 0


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix="gauguin-bcm-coordinator-") as temporary:
        raise SystemExit(main(temporary))
