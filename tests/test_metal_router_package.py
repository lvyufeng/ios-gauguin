#!/usr/bin/env python3
"""Reproduce the real stale bootstrap tuple against production router code."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['old-router-receipt', 'new-router-receipt', 'capture', 'capture-dir', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'tools'))
    from metal_router_targets import load_router_receipt, validate_target_capture, ROUTER
    old = load_router_receipt(args.old_router_receipt)
    new = load_router_receipt(args.new_router_receipt)
    capture = json.loads(args.capture.read_text())
    out = args.out.resolve()
    out.mkdir(exist_ok=False)
    # The actual installed 0282 package must reproduce its known rejection.
    try:
        validate_target_capture(old, capture, args.capture_dir)
    except ValueError as error:
        assert str(error) == 'target binding differs: /usr/libexec/gauguin-metal-bootstrap'
    else:
        raise AssertionError('stale installed binding unexpectedly accepted')
    candidate = copy.deepcopy(capture)
    binary = Path(new['binary']).read_bytes()
    (out / 'candidate-router').write_bytes(binary)
    candidate['files'][ROUTER].update(bytes=len(binary), sha256=new['sha256'], output='candidate-router')
    for spec in new['targets']:
        name = candidate['files'][spec['path']]['output']
        (out / name).write_bytes((args.capture_dir / name).read_bytes())
    validate_target_capture(new, candidate, out)
    for mutation in ['old-bootstrap-tuple', 'wrong-owner', 'wrong-mode', 'corrupt-bytes']:
        bad = copy.deepcopy(candidate)
        path = '/usr/libexec/gauguin-metal-bootstrap'
        if mutation == 'old-bootstrap-tuple':
            target = next(s for s in old['targets'] if s['kind'] == 'bootstrap')
            bad['files'][path].update(bytes=target['bytes'], sha256=target['sha256'])
        elif mutation == 'wrong-owner':
            bad['files'][path]['uid'] = 501
        elif mutation == 'wrong-mode':
            bad['files'][path]['mode'] |= 0o020
        else:
            bad['files'][path]['output'] = 'corrupt-bootstrap'
            data = bytearray((out / candidate['files'][path]['output']).read_bytes())
            data[-1] ^= 1
            (out / 'corrupt-bootstrap').write_bytes(data)
        try:
            validate_target_capture(new, bad, out)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted ' + mutation)
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
    aliases = ['main=gauguin_router_main', 'getuid=router_getuid', 'geteuid=router_geteuid',
               'getprogname=router_getprogname', 'sysctlbyname=router_sysctl', 'fstat=router_fstat',
               'memorystatus_control=router_mem', 'posix_spawn=router_spawn',
               'posix_spawnattr_setjetsam_ext=router_jetsam']
    def run(argv, log):
        with log.open('x') as stream:
            subprocess.run(list(map(str, argv)), env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    results = []
    for label, receipt, scenario in [('old', old, 'desktop-stale-target'), ('new', new, 'desktop')]:
        case = out / label
        case.mkdir()
        lines = ['#include <stdint.h>', 'struct gauguin_router_target {const char *path,*argument;uint64_t bytes;unsigned char sha256[32];};']
        for spec in receipt['targets']:
            row = capture['files'][spec['path']]
            payload = (args.capture_dir / row['output']).read_bytes()
            file = case / spec['kind']
            file.write_bytes(payload)
            file.chmod(0o755)
            values = ','.join(str(n) for n in bytes.fromhex(spec['sha256']))
            lines.append('static const struct gauguin_router_target gauguin_router_' + spec['kind'] + '={' + json.dumps(str(file)) + ',' + json.dumps(spec['argument']) + ',' + str(spec['bytes']) + ',{' + values + '}};')
        (case / 'GauguinProbeRouterTargets.h').write_text('\n'.join(lines) + '\n')
        common = ['xcrun', 'clang', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                  '-I' + str(case), '-I' + str(root / 'graphics/hakios-metal-ca/overlay/userland/src'),
                  '-I' + str(root / 'graphics/hakios-metal-ca/desktop-overlay/userland/src')]
        run(common + ['-D' + a for a in aliases] + ['-DGAUGUIN_ROUTER_BUILD="package-test"', '-c', root / 'userland/metal/probe_router.c', '-o', case / 'router.o'], case / 'compile.log')
        run(common + [case / 'router.o', root / 'tests/fixtures/metal_probe_router_host.c', '-o', case / 'host'], case / 'link.log')
        run([case / 'host', scenario], case / 'run.log')
        output = (case / 'run.log').read_text()
        if label == 'old':
            assert 'FAIL phase=target code=' in output and 'spawn_calls=0' in output
        else:
            assert 'selected=bootstrap' in output and 'replacement=1 spawn_calls=1' in output
        results.append(dict(binding=label, scenario=scenario, log_sha256=hashlib.sha256(output.encode()).hexdigest()))
    result = dict(state='actual0282-target-mismatch-reproduced-and-new-binding-accepted',
                  actual_capture=str(args.capture), production_router_cases=results,
                  capture_negative_controls=4, real_spawns=0, device_operations=0, hardware_qualified=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
