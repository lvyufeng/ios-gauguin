#!/usr/bin/env python3
"""Test the exact native transport source against mocked IOKit, with sanitizers."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

WORK = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    native = json.loads(args.native.read_text())
    assert native['state'] == 'native-FQ322-installed-baseline-reproduced-candidate-signed'
    assert native['inputs_unchanged'] and native['imports_unchanged']
    source = Path(native['source'])
    original_include = Path(native['original_source']).parents[1]/'include'
    header = WORK/'graphics/gauguin-fault-cache/GauguinFaultQueryCache.hpp'
    assert sha(header) == sha(source.parent/header.name)
    fixture = WORK/'tests/fixtures/metal_fault_transport_host.cpp'
    paths = [args.native.resolve(), source, header, source.parent/header.name,
             fixture, Path(__file__).resolve()]
    paths += list(original_include.rglob('*.hpp'))
    pins = {str(path): sha(path) for path in paths}
    out = args.out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    out.mkdir(parents=True)
    argv = ['xcrun', '--sdk', 'macosx', 'clang++', '-std=c++17', '-O1', '-g',
            '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
            '-DHAKIOS_METAL_TARGET_A619', '-DFQ_TRANSPORT_SOURCE="'+str(source)+'"',
            '-I'+str(original_include), str(fixture), '-o', str(out/'check')]
    proc = subprocess.run(argv, capture_output=True, text=True)
    (out/'compile.log').write_text(proc.stdout+proc.stderr)
    assert proc.returncode == 0, 'host compile failed'
    proc = subprocess.run([str(out/'check')], capture_output=True, text=True, timeout=45)
    (out/'stdout.log').write_text(proc.stdout)
    (out/'stderr.log').write_text(proc.stderr)
    assert proc.returncode == 0, 'actual transport host test failed'
    result = json.loads(proc.stdout)
    assert result['cases'] == 25 and result['concurrent_cached_calls'] == 8000
    assert result['both_success_race_orders'] and result['supported_counters_stay_live']
    assert result['transient_errors_not_cached'] and result['invalid_shapes_not_cached']
    assert result['connections_independent'] and result['submit_wait_map_errors_preserved']
    assert result['actual_IOKit_calls'] == 0
    lines = proc.stderr.splitlines()
    assert all(line == 'GAUGUIN FQ322: unsupported_cached=1 request=64 param=9' or
               line.startswith("hakios-metal: the driver's request ") for line in lines)
    assert all(sha(name) == digest for name, digest in pins.items())
    result.update(input_pins=pins, compiler_argv=argv, native_source_sha256=sha(source),
                  tested_actual_transport=True, sanitizer_errors=False,
                  unsupported_transition_logs=sum(line.startswith('GAUGUIN FQ322:') for line in lines),
                  native_iOS_runtime_qualified=False, device_commands=0)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('input_pins', 'compiler_argv')}, indent=2))


if __name__ == '__main__':
    main()
