#!/usr/bin/env python3
"""Actual coordinator: retained legacy/CX/clock cases and native firmware ordering; typed seams, no hardware."""
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
DEFAULT = Path(os.environ.get('XNU_SOURCE',str(ROOT / '.deps-cache/p0-20261105/source177-codex'))) / 'bsd/dev'
PAS_INIT = BASELINE = DEFAULT
FIXTURE = HERE / 'fixtures/gauguin_bcm_coordinator_host.c'


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', type=Path, default=DEFAULT)
    parser.add_argument('--baseline-dev', type=Path, default=BASELINE)
    parser.add_argument('--pas-init-dir', type=Path, default=PAS_INIT)
    parser.add_argument('--bus-dir', type=Path, default=DEFAULT)
    parser.add_argument('--shared', type=Path, default=DEFAULT)
    parser.add_argument('--cx-power-dir', type=Path, default=DEFAULT)
    args = parser.parse_args()
    dev, baseline = args.dev.resolve(), args.baseline_dev.resolve()
    api = args.pas_init_dir.resolve()
    source = dev / 'gauguin_bcm_coordinator.c'
    # Complete staged trees provide all headers in dev. In candidate mode
    # use the candidate CX/prepare headers and already-integrated117 PAS headers.
    if (dev / 'gauguin_pas_init.h').is_file():
        api = dev
    header_dev = dev if (dev / 'gauguin_pas_stage.h').is_file() else baseline
    bus = dev if (dev / 'gauguin_bus_probe.h').is_file() else args.bus_dir.resolve()
    shared = dev if (dev / 'gauguin_cx_rail.h').is_file() else args.shared.resolve()
    power = dev if (dev / 'gauguin_cx_power.h').is_file() else args.cx_power_dir.resolve()
    files = [Path(__file__).resolve(), source, FIXTURE, api / 'gauguin_pas_init.h',
             bus / 'gauguin_bus_probe.h', shared / 'gauguin_cx_rail.h', power / 'gauguin_cx_power.h', power / 'gauguin_gmu_clock.h',
             *(header_dev / name for name in ('gauguin_pas_stage.h', 'gauguin_bcm_transport.h',
                 'gauguin_wdt_lease.h', 'gauguin_bcm_plan.h'))]
    files += [dev/n for n in ['gauguin_gpu_unsecure.h','gauguin_gpu_data.h','gauguin_gpu_write.h','gauguin_gpu_ib.h','gauguin_gpu_eop.h','gauguin_gpu_compute.h','gauguin_gpu_clear.h','gauguin_gpu_draw.h','gauguin_gpu_sequence.h','gauguin_gpu_varying.h','gauguin_gpu_texture.h','gauguin_gpu_runtime.h']]
    files += [dev/name for name in ('gauguin_gmu_board.h','gauguin_gmu_asset.h',
        'gauguin_gmu_firmware.h','gauguin_gmu_hfi.h','gauguin_gmu_memory.h',
        'gauguin_gmu_smmu.h','gauguin_gpu_smmu.h','gauguin_gpu_memory.h','gauguin_gpu_aperture.h','gauguin_gpu_start.h','gauguin_gpu_core.h','gauguin_gpu_cp.h','gauguin_gpu_zap.h','gauguin_gpu_zap_asset.h','cmd_db_snapshot.h')]
    for path in files:
        if not path.is_file():
            raise SystemExit(f'missing input: {path}')
    # Avoid a local quoted-include shadowing an unrecorded staging header.
    shadow = api / 'gauguin_pas_stage.h'
    if shadow.is_file():
        assert shadow.read_bytes() == (header_dev / 'gauguin_pas_stage.h').read_bytes()
        if shadow not in files:
            files.append(shadow)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    build = Path(temporary)
    report = {'state': 'running', 'inputs': hashes, 'scope': 'actual120 coordinator + actual headers; retained149 + typed ARC/CX dependency/platform seams; no SMC/hardware'}
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
                     '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I' + str(bus),
                     '-I' + str(shared), '-I' + str(power), '-I' + str(api), '-I' + str(header_dev), str(unit), '-o', str(binary)], [str(binary)]]
        with log_path.open('w') as log:
            for command in commands:
                log.write('$ ' + shlex.join(command) + '\n'); log.flush()
                result = subprocess.run(command, stdout=log, stderr=log, env=env)
                log.write(f'exit={result.returncode}\n'); log.flush()
                if result.returncode:
                    raise RuntimeError(f'{command[0]} exited {result.returncode}')
        if {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files} != hashes:
            raise RuntimeError('inputs changed during run')
        output = log_path.read_text()
        assert 'PASS: retained 58 original coordinator cases with INIT disabled' in output
        assert 'PASS: 58 original + 42 INIT coordinator cases (100 total);' in output
        assert 'PASS: 100 retained + 49 MEM coordinator cases (149 total);' in output
        counts = re.search(r'PASS: 149 retained \+ (\d+) CX coordinator cases \((\d+) total\);', output)
        assert counts and int(counts[2]) == 149 + int(counts[1])
        clock = re.search(r'PASS: 241 retained \+ (\d+) GMU clock coordinator cases \((\d+) total\)', output)
        firmware = re.search(r'PASS: (\d+) retained \+ (\d+) GMU firmware coordinator cases \((\d+) total\)', output)
        assert clock and firmware and int(clock[2]) == int(firmware[1])
        assert int(firmware[2]) == 24 and int(firmware[3]) == int(firmware[1]) + 24
        perf = re.search(r'PASS: (\d+) retained \+ (\d+) PERF coordinator cases \((\d+) total\)', output)
        assert perf and int(perf[1]) == int(firmware[3]) and int(perf[2]) == 23 and int(perf[3]) == int(perf[1]) + 23
        triangle=re.search(r'PASS: (\d+) new mode8 coordinator cases \((\d+) total\); old cases retained',output)
        assert triangle and int(triangle[1])==35
        sequence=re.search(r'PASS: (\d+) new mode9 coordinator cases \((\d+) total\); old cases retained',output)
        assert sequence and int(sequence[1])==36 and int(sequence[2])==int(triangle[2])+36
        varying=re.search(r'PASS: (\d+) new mode10 coordinator cases \((\d+) total\); old cases retained',output)
        assert varying and int(varying[1])==37 and int(varying[2])==int(sequence[2])+37
        texture=re.search(r'PASS: (\d+) new mode11 coordinator cases \((\d+) total\); old cases retained',output)
        assert texture and int(texture[1])==38 and int(texture[2])==int(varying[2])+38
        runtime=re.search(r'PASS: (\d+) new mode12 coordinator cases \((\d+) total\); old cases retained',output)
        assert runtime and int(runtime[1])==22 and int(runtime[2])==int(texture[2])+22
        service=re.search(r'PASS: (\d+) new service coordinator cases \((\d+) total\); default798 retained',output)
        assert service and int(service[1])>0 and int(service[2])==int(runtime[2])+int(service[1])
        report.update(state='passed', original_cases=58, init_cases=42, mem_cases=49,
                      cx_cases=int(counts[1]), clock_cases=int(clock[1]),
                      firmware_cases=int(firmware[2]), perf_cases=int(perf[2]), total_cases=int(service[2]), service_cases=int(service[1]), runtime_cases=int(runtime[1]), triangle_cases=int(triangle[1]), sequence_cases=int(sequence[1]), varying_cases=int(varying[1]), texture_cases=int(texture[1]))
    except Exception as error:
        report.update(state='failed', error=str(error))
        print(f'FAIL: {error}; {log_path}', file=sys.stderr)
        if log_path.exists():
            print('\n'.join(log_path.read_text().splitlines()[-35:]), file=sys.stderr)
        return 1
    finally:
        (build / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(log_path.read_text().splitlines()[-2])
    print(f'PASS: retained149 + optional CX coordinator fixture; {build / "result.json"}')
    return 0


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix="gauguin-coordinator-") as temporary:
        raise SystemExit(main(temporary))
