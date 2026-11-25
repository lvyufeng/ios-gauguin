#!/usr/bin/env python3
"""Actual CX power C with strict MMIO/platform seams; no device or real waits."""
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
COMPONENT = Path(os.environ.get('XNU_SOURCE', str(ROOT / '.deps-cache/p0-20261105/source120-codex'))) / 'bsd/dev'
SHARED = BASELINE = COMPONENT
FIXTURE = HERE / 'fixtures/gauguin_cx_power_host.c'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('platform seam changed: ' + old)
    return source.replace(old, new)


def prepare(source_path):
    text = source_path.read_text()
    marker = '/* Same translation unit as CX:'
    assert text.count(marker) == 1
    core, clocks = text.split(marker, 1)
    assert 'sweet_gmu_clock_once' in clocks
    source = re.sub(r'^#include .*\n', '', core + '#endif /* GAUGUIN */\n', flags=re.M)
    source = replace_once(source, 'uint32_t value = *(volatile uint32_t *)(mapping + offset);',
                          'uint32_t value = fake_read(mapping, offset);')
    source = replace_once(source, '*(volatile uint32_t *)(gcx_gpucc + GCX_GDSCR) = value;',
                          'fake_write(value);')
    for assembly, seam in [('dmb oshld','fake_dmb_read'),('dmb oshst','fake_dmb_store'),('dsb sy','fake_dsb')]:
        source = replace_once(source, f'__asm__ volatile("{assembly}" ::: "memory");', seam + '();')
    assert '__asm__' not in source and '*(volatile' not in source
    write = source.split('static void gcx_write', 1)[1].split('static enum gcx_rc gcx_fail', 1)[0]
    assert write.index('++gcx_work.writes;') < write.index('fake_dmb_store();') < write.index('fake_write(value);') < write.index('fake_dsb();')
    assert not re.search(r'\b(?:IOSleep|ml_io_unmap|IOMalloc|IOFree|smc)\s*\(', source)
    entry = source.split('sweet_cx_power_once(struct gcx_receipt *out)', 1)[1]
    assert entry.index('*out = gcx_work;') < entry.index('__atomic_store_n(&gcx_lifecycle, GCX_COMPLETE')
    fixture = FIXTURE.read_text()
    return replace_once(fixture, '\n@SOURCE@\n', '\n' + source + '\n')


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', type=Path, default=COMPONENT)
    parser.add_argument('--shared', type=Path, default=SHARED)
    parser.add_argument('--baseline-dev', type=Path, default=BASELINE)
    args = parser.parse_args()
    component, shared, baseline = args.component.resolve(), args.shared.resolve(), args.baseline_dev.resolve()
    source = component / 'gauguin_cx_power.c'
    inputs = [source, component / 'gauguin_cx_power.h', shared / 'gauguin_cx_rail.h', FIXTURE,
              *(baseline / name for name in ('gauguin_bcm_transport.h','gauguin_bcm_plan.h','gauguin_wdt_lease.h'))]
    hashes = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    build = Path(temporary)
    unit, binary, log_path = build / 'test.c', build / 'test', build / 'run.log'
    report = {'state':'running','inputs':hashes,'scope':'actualCXpower C; CPU/MMIO/barrier seams; no hardware proof'}
    env = os.environ.copy()
    env['ASAN_OPTIONS']='halt_on_error=1'
    env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    try:
        unit.write_text(prepare(source))
        commands=[['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g',
                   '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(component),
                   '-I'+str(shared),'-I'+str(baseline),str(unit),'-o',str(binary)],[str(binary)]]
        with log_path.open('w') as log:
            for command in commands:
                log.write('$ '+shlex.join(command)+'\n');log.flush()
                result=subprocess.run(command,env=env,stdout=log,stderr=log)
                log.write(f'exit={result.returncode}\n');log.flush()
                if result.returncode:
                    raise RuntimeError(f'{command[0]} exited {result.returncode}')
        if {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}!=hashes:
            raise RuntimeError('inputs changed while tests ran')
        report['state']='passed'
    except Exception as error:
        report.update(state='failed',error=str(error))
        print(f'FAIL: {error}; {log_path}',file=sys.stderr)
        if log_path.exists():
            print('\n'.join(log_path.read_text().splitlines()[-35:]),file=sys.stderr)
        return 1
    finally:
        (build/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(log_path.read_text().splitlines()[-2])
    print(f'PASS: CXpower host fixture; {build/"result.json"}')
    return 0


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix="gauguin-cx-power-") as temporary:
        raise SystemExit(main(temporary))
