#!/usr/bin/env python3
"""Check surface retention through real completion callbacks using qualified core objects."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

WORK = Path(__file__).resolve().parents[1]
STATE = WORK / 'research/tmp/surface-retire-334'
UNITS = ['pm4', 'gpu', 'command', 'compute', 'texture', 'render', 'link',
         'compiler', 'metallib', 'fake_gpu', 'iokit_transport']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(STATE) and not out.exists()
    receipt = STATE / 'core-host-v1/result.json'
    core = json.loads(receipt.read_text())
    assert core['state'] == 'SURF334-full-core-host-equivalence-and-ownership-passed'
    prepared = json.loads((STATE / 'prepared-v1/result.json').read_text())
    fixture = WORK / 'tests/fixtures/surface_retained334.cpp'
    pins = dict(core['input_pins'])
    for path in [receipt, fixture, Path(__file__)]:
        pins[str(path)] = sha(path)
    for variant in ('baseline', 'candidate'):
        for unit in UNITS:
            path = receipt.parent / variant / (unit + '.o')
            pins[str(path)] = sha(path)
    assert all(sha(path) == digest for path, digest in pins.items())
    out.mkdir()
    result = dict(state='SURF334-retention-running', input_pins=pins, steps=[], device_commands=0)
    try:
        for variant in ('baseline', 'candidate'):
            source = Path(prepared['sources'][variant])
            binary = out / variant
            command = ['clang++', '-std=c++17', '-O2', '-gline-tables-only', '-pthread',
                       '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                       '-fno-sanitize-recover=all', '-DHAKIOS_METAL_TARGET_A619',
                       '-I' + str(source / 'include'), str(fixture),
                       *[str(receipt.parent / variant / (u + '.o')) for u in UNITS],
                       '-framework', 'IOKit', '-framework', 'CoreFoundation', '-o', str(binary)]
            for label, argv in [('compile', command), ('run', [str(binary)])]:
                proc = subprocess.run(argv, capture_output=True, timeout=30,
                                      env={**os.environ, 'ASAN_OPTIONS': 'halt_on_error=1:detect_leaks=0',
                                           'UBSAN_OPTIONS': 'halt_on_error=1'})
                log = out / (variant + '-' + label + '.log')
                log.write_bytes(proc.stdout + proc.stderr)
                result['steps'].append(dict(variant=variant, label=label, argv=argv,
                                            exit=proc.returncode, log=str(log), sha256=sha(log)))
                assert proc.returncode == 0, log
                if label == 'run':
                    assert proc.stdout.count(b'PASS surface retention:') == 2
        result.update(state='SURF334-surface-retained-through-completion-passed',
                      cases_per_variant=2, callback_reimport_same_owner=True,
                      released_after_success_and_submission_error=True,
                      sanitizers=['address', 'undefined'])
    except BaseException as error:
        result.update(state='SURF334-retention-failed', error=repr(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(path) == digest for path, digest in pins.items())
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['inputs_unchanged']
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
