#!/usr/bin/env python3
"""Check real bounded collector failure paths and its native Darwin adapters."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    include = ROOT/'graphics/gauguin-sb-rate-trace'
    model = ROOT/'tests/fixtures/sb_stack_sampler_host.c'
    live = ROOT/'tests/fixtures/sb_stack_mach_live.c'
    inputs = [Path(__file__).resolve(), model, live, *sorted(include.glob('SBStack*.h'))]
    pins = {str(p):sha(p) for p in inputs}
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    cases = []
    for name, source, flags in [('model', model, ['-fsanitize=address,undefined']),
                                ('live', live, ['-Wl,-export_dynamic'])]:
        binary = out/name
        command = ['xcrun', 'clang', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-function', '-fno-omit-frame-pointer', '-fno-optimize-sibling-calls',
                   '-I', str(include), *flags, str(source), '-o', str(binary)]
        with (out/(name+'-compile.log')).open('x') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
        (out/(name+'.stdout')).write_text(result.stdout)
        (out/(name+'.stderr')).write_text(result.stderr)
        assert result.returncode == 0 and not result.stderr and result.stdout.startswith('PASS '), (name, result.returncode, result.stdout, result.stderr)
        cases.append(dict(name=name, output=result.stdout.strip(), binary_sha256=sha(binary),
                          sanitizer='ASAN+UBSAN' if name=='model' else 'none: avoid sanitizer runtime while real target is suspended'))
    assert pins == {str(p):sha(p) for p in inputs}
    receipt = dict(state='passed-bounded-collector-and-live-own-process-Mach', input_pins=pins,
                   inputs_unchanged=True, cases=cases, device_commands=0,
                   iOS_runtime_qualified=False, hard_realtime_pause_limit=False)
    (out/'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='input_pins'}, indent=2))


if __name__ == '__main__':
    main()
