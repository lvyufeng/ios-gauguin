#!/usr/bin/env python3
"""Compile the production fallback and exercise its own-process Darwin VM path."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

WORK = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    out.mkdir(parents=True)
    source = WORK/'tests/fixtures/edr_default_host.c'
    files = [source, Path(__file__).resolve(), *sorted((WORK/'graphics/gauguin-edr-default').glob('*'))]
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    pins = {str(p): sha(p) for p in files}
    binary = out/'host-check'
    command = ['xcrun', 'clang', '-std=gnu11', '-O1', '-g', '-fblocks', '-Wall', '-Wextra', '-Werror',
               '-fsanitize=address,undefined', str(source), '-o', str(binary)]
    with (out/'compile.log').open('x') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
    (out/'stdout.log').write_text(run.stdout)
    (out/'stderr.log').write_text(run.stderr)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['checks'] > 2000 and result['device_commands'] == 0
    assert all(sha(Path(p)) == digest for p, digest in pins.items())
    result.update(input_pins=pins, compiler_argv=command, sanitizer_stderr=run.stderr,
                  real_Darwin_self_task_page_test=True, actual_iOS_image_mutated=False)
    with (out/'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins', 'compiler_argv')}, indent=2))


if __name__ == '__main__':
    main()
