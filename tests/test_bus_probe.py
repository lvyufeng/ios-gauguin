#!/usr/bin/env python3
"""Actual bus worker/prepare C and real parser, BCM planner and CX policy.

Retains all 70 worker and 36 prepare cases. New CX cases use the same production
CMDDB copy path; no RSC access is allowed in either prepare mode. SHA is the
existing exact-byte seam, supplied with Python hashes of two immutable emitted
fixtures. Three actual RAW logs independently round-trip through the extractor.
Only the existing aligned MMIO-read/barrier seam is replaced; no device I/O.
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
BASELINE = Path(os.environ.get('XNU_SOURCE',str(ROOT / '.deps-cache/p0-20261105/source118-codex')))
CFLAGS = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
          '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g', '-O1']


def prepare(source, fixture):
    # Same single seam as the retained public worker runner; self-contained so
    # this runner can itself be installed publicly without importing itself.
    template, code = fixture.read_text(), source.read_text()
    marker = '\n@WORKER@\n'
    assert template.count(marker) == 1
    code = re.sub(r'^#include .*$\n?', '', code, flags=re.M)
    helper = re.search(r'static uint32_t\nbus_mmio_read\(vm_offset_t base, uint32_t offset\)\n'
                       r'\{\n.*?\n\}\n', code, flags=re.S)
    assert helper, 'actual MMIO helper signature'
    assert '*(volatile uint32_t *)(base + offset)' in helper.group()
    assert '__asm__ volatile("dmb oshld" ::: "memory")' in helper.group()
    code = code[:helper.start()] + ('static uint32_t\nbus_mmio_read(vm_offset_t base, uint32_t offset)\n'
                                  '{ return fake_bus_read32(base, offset); }\n') + code[helper.end():]
    assert '__asm__' not in code
    return template.replace(marker, '\n' + code + '\n')


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', type=Path, default=BASELINE / 'bsd/dev')
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--shared', type=Path, default=BASELINE / 'bsd/dev')
    parser.add_argument('--plan-dir', type=Path, default=BASELINE / 'bsd/dev')
    args = parser.parse_args()
    dev, baseline, shared, policy = (p.resolve() for p in (args.dev, args.baseline, args.shared, args.plan_dir))
    # A fully replayed tree may supply all implementation/header files itself.
    header_dev = dev if (dev / 'cmd_db_snapshot.h').is_file() else baseline / 'bsd/dev'
    if (dev / 'gauguin_cx_rail.h').is_file():
        shared = dev
    if (dev / 'gauguin_cx_rail_plan.c').is_file():
        policy = dev
    source, fixture = dev / 'gauguin_bus_probe.c', HERE / 'fixtures/gauguin_bus_probe_host.c'
    extractor = ROOT / 'tools/extract_cmd_db_snapshot.py'
    native = [header_dev / 'cmd_db_snapshot.c', header_dev / 'gauguin_bcm_plan.c', policy / 'gauguin_cx_rail_plan.c']
    files = [Path(__file__).resolve(), fixture, source, extractor,
             ROOT / 'tools/kernel_banner.py', dev / 'gauguin_bus_probe.h', shared / 'gauguin_cx_rail.h',
             *(header_dev / name for name in ('cmd_db_snapshot.h', 'gauguin_bcm_plan.h', 'gauguin_bcm_transport.h')),
             baseline / 'bsd/conf/files', baseline / 'bsd/kern/bsd_init.c', *native]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    build = Path(temporary)
    report = {'state': 'running', 'inputs': hashes,
              'scope': 'actual C; 70 worker + 36 prepare retained, CX same-snapshot CPU plan; no hardware/native crypto'}
    log_path = build / 'run.log'
    try:
        entries = (baseline / 'bsd/conf/files').read_text()
        for name in ('cmd_db_snapshot.c', 'gauguin_bcm_plan.c', 'gauguin_bus_probe.c'):
            assert entries.count('bsd/dev/' + name + '\t\tstandard') == 1
        init = (baseline / 'bsd/kern/bsd_init.c').read_text()
        assert init.count('extern void sweet_bus_probe_init(void);') == 1
        assert init.count('sweet_bus_probe_init();') == 1
        blocks = re.findall(r'#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
        assert any('\tsweet_bus_probe_init();\n' in block for block in blocks)
        assert any('extern void sweet_bus_probe_init(void);\n' in block for block in blocks)
        text = source.read_text()
        body = text.split('static bool\nbus_plan_prepare(', 1)[1].split('\nstatic void\nbus_worker', 1)[0]
        assert not re.search(r'BUS_RSC_|bus_capture_rsc|bus_run\(', body), 'prepare has no RSC path'
        unit, binary = build / 'bus.c', build / 'bus'
        unit.write_text(prepare(source, fixture))
        env = os.environ.copy()
        env['ASAN_OPTIONS'] = 'halt_on_error=1' + (':detect_leaks=1' if sys.platform != 'darwin' else '')
        env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
        env['PYTHONPATH'] = str(ROOT / 'tools')
        def invoke(command, log):
            command = list(map(str, command))
            log.write('$ ' + shlex.join(command) + '\n'); log.flush()
            result = subprocess.run(command, stdout=log, stderr=log, env=env)
            log.write(f'exit={result.returncode}\n'); log.flush()
            if result.returncode:
                raise RuntimeError(f'{command[0]} exited {result.returncode}')
        with log_path.open('w') as log:
            invoke(['clang', *CFLAGS, '-I' + str(dev), '-I' + str(shared),
                    '-I' + str(header_dev), unit, *native, '-o', binary], log)
            db, cx_db, raw_log = build / 'positive_db.bin', build / 'positive_cx_db.bin', build / 'worker_positive.log'
            invoke([binary, '--emit-db', db], log); invoke([binary, '--emit-cx-db', cx_db], log)
            data, cx_data = db.read_bytes(), cx_db.read_bytes()
            assert len(data) == len(cx_data) == 131072
            # Independently check the extended aux layout: same tables, CX32
            # bytes with nine zero slots; other ARC/BCM aux shifted by16 bytes.
            expected = bytearray(data); expected[16:18] = b'\x00\x10'
            expected[384:512] = bytes(128); expected[164:166] = b'\x20\x00'
            expected[384:400] = data[384:400]
            for index in range(1, 4):
                at = 144 + 24 * index + 22
                expected[at:at + 2] = (16 + 16 * index).to_bytes(2, 'little')
                expected[400 + 16 * index:416 + 16 * index] = data[384 + 16 * index:400 + 16 * index]
            expected[28:30] = (320).to_bytes(2, 'little'); expected[464:512] = data[448:496]
            assert bytes(expected) == cx_data
            digest, cx_digest = hashlib.sha256(data).hexdigest(), hashlib.sha256(cx_data).hexdigest()
            invoke([binary, '--digest', digest, '--log', raw_log, '--cx-digest', cx_digest], log)
            for mode, suffix, expected_data, flags in (
                ('worker', '', data, 'sweetbusprobe=1'),
                ('prepare', '.prepare', data, 'sweetbusvote=1'),
                ('cx', '.cx', cx_data, 'sweetbusvote=1 sweetcxpower=1')):
                banner = f'Darwin Kernel Version 22.6.0: SYNTHETIC118 {mode} FIXTURE; xnu-host-cx118-{mode}'.encode()
                trial = f'synthetic-{mode}-host-118'
                image, bound, decoded = (build / f'{mode}.{ext}' for ext in ('image', 'log', 'decoded.bin'))
                image.write_bytes(banner + b'\x00')
                bound.write_bytes(banner + f'\nboot-args={flags} sweettrial={trial}\n'.encode() +
                                  Path(str(raw_log) + suffix).read_bytes())
                invoke([sys.executable, extractor, '--image', image, '--log', bound,
                        '--trial', trial, '--out', decoded], log)
                assert decoded.read_bytes() == expected_data, f'{mode}: exact actual RAW round-trip'
        output = log_path.read_text()
        assert 'PASS: legacy=70 prepare_additions=36;' in output
        counts = re.search(r'PASS: 106 retained \+ (\d+) CX prepare cases \((\d+) total\);', output)
        assert counts and int(counts[2]) == 106 + int(counts[1])
        assert {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files} == hashes
        report.update(state='passed', retained_cases=106, cx_cases=int(counts[1]), total_cases=int(counts[2]),
                      db_sha256=digest, cx_db_sha256=cx_digest, roundtrips='worker / prepare / CX exact131072 bytes')
    except Exception as error:
        report.update(state='failed', error=str(error))
        print(f'FAIL: {error}; {log_path}', file=sys.stderr)
        if log_path.exists(): print('\n'.join(log_path.read_text().splitlines()[-35:]), file=sys.stderr)
        return 1
    finally:
        (build / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: bus retained106 + CX{report["cx_cases"]}; three actual RAW round-trips; {build / "result.json"}')
    return 0


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix="gauguin-bus-cx-") as temporary:
        raise SystemExit(main(temporary))
