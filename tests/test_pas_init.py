#!/usr/bin/env python3
"""Execute actual PAS INIT helper with explicit SMC/DSB and CPU-platform seams.

No real SMC, MMIO, firmware, device, sleeping, network or assembly execution.
Checks register constraints in the native wrapper before replacing that single
function; all state/flags/bounds/continuation/BUSY logic remains actual C.
Non-returning secure calls and physical watchdog recovery are not simulated proof.
"""
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
COMPONENT = Path(os.environ.get('XNU_SOURCE', str(ROOT / '.deps-cache/p0-20261105/source116-codex'))) / 'bsd/dev'
BASELINE = COMPONENT
FIXTURE = HERE / 'fixtures/gauguin_pas_init_host.c'


def prepare(source_path):
    source = source_path.read_text()
    source = re.sub(r'^#include .*\n', '', source, flags=re.M)
    invoke = re.search(r'static void gpi_invoke\(struct gpi_registers \*r\)\n\{\n.*?\n\}\n', source, re.S)
    if not invoke:
        raise ValueError('actual native SMC wrapper signature changed')
    body = invoke.group()
    for i in range(7):
        assert f'register uint64_t x{i} __asm__("x{i}") = r->x[{i}];' in body
        assert f'"+r"(x{i})' in body and f'r->x[{i}] = x{i};' in body
    for i in range(7, 18):
        assert f'"x{i}"' in body
    assert body.count('"smc #0"') == 1 and '"cc", "memory"' in body
    source = source[:invoke.start()] + (
        'static void gpi_invoke(struct gpi_registers *r)\n{ fake_invoke(r); }\n') + source[invoke.end():]
    barrier = '__asm__ volatile("dsb sy" ::: "memory");'
    assert source.count(barrier) == 1
    source = source.replace(barrier, 'fake_dsb();')
    assert '__asm__' not in source
    assert not re.search(r'\b(?:IOMalloc|IOFree|ml_io_map\w*|ml_vtophys|sweet_pas_stage_once)\s*\(', source)
    assert set(re.findall(r'0x420002[0-9a-fA-F]+', source)) == {'0x42000201'}
    finish = source.split('static enum gpi_rc gpi_finish', 1)[1].split('enum gpi_rc\nsweet_pas_init_image_once', 1)[0]
    assert finish.index('*out = *receipt;') < finish.index('__atomic_store_n(&gpi_lifecycle')
    fixture = FIXTURE.read_text()
    assert fixture.count('\n@SOURCE@\n') == 1
    return fixture.replace('\n@SOURCE@\n', '\n' + source + '\n')


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', type=Path, default=COMPONENT)
    parser.add_argument('--baseline-dev', type=Path, default=BASELINE)
    args = parser.parse_args()
    component, baseline = args.component.resolve(), args.baseline_dev.resolve()
    source = component / 'gauguin_pas_init.c'
    files = [source, component / 'gauguin_pas_init.h', FIXTURE,
             *(baseline / name for name in ('gauguin_pas_stage.h','gauguin_bcm_transport.h','gauguin_bcm_plan.h','gauguin_wdt_lease.h'))]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    build = Path(temporary)
    unit, binary, log_path = build / 'test.c', build / 'test', build / 'run.log'
    report = {'state':'running','inputs':hashes,'scope':'actual PAS INIT C; explicit CPU/SMC/DSB seams; no hardware qualification'}
    env = os.environ.copy()
    env['ASAN_OPTIONS'] = 'halt_on_error=1'
    env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    try:
        unit.write_text(prepare(source))
        commands = [
            ['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g','-pthread',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(component),'-I'+str(baseline),str(unit),'-o',str(binary)],
            [str(binary)],
        ]
        with log_path.open('w') as log:
            for command in commands:
                log.write('$ '+shlex.join(command)+'\n'); log.flush()
                result = subprocess.run(command, env=env, stdout=log, stderr=log)
                log.write(f'exit={result.returncode}\n'); log.flush()
                if result.returncode:
                    raise RuntimeError(f'{command[0]} exited {result.returncode}')
        if {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files} != hashes:
            raise RuntimeError('test inputs changed during execution')
        report['state']='passed'
    except Exception as error:
        report.update(state='failed',error=str(error))
        print(f'FAIL: {error}; {log_path}', file=sys.stderr)
        if log_path.exists():
            print('\n'.join(log_path.read_text().splitlines()[-35:]), file=sys.stderr)
        return 1
    finally:
        (build/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(log_path.read_text().splitlines()[-2])
    print(f'PASS: PAS INIT host fixture; {build / "result.json"}')
    return 0


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix="gauguin-pas-init-") as temporary:
        raise SystemExit(main(temporary))
