#!/usr/bin/env python3
"""Rebuild the 0343 user Core with the 0344 snapshot and encoding changes."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


WORK = Path(__file__).resolve().parents[1]
MAIN = Path(subprocess.check_output(
    ['git', '-C', str(WORK), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
    text=True,
).strip()).parent
PRIOR = MAIN / 'research/tmp/gauguin-io-path-worktree-20261117/research/tmp/io-path-342'
BASE = WORK / 'research/tmp/frame-344'
PATCH = WORK / 'graphics/gauguin-program-io/0344-core-encoding.patch'
REFERENCE_SHA256 = '5b925bd7d2306c44d4df596fefb38d1cd3b28bd8c95ed68eb332d7fa6087e063'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(BASE) or out.exists():
        raise SystemExit('provide a fresh output directory inside frame-344')

    source_receipt = PRIOR / 'prepared-v3/result.json'
    native_receipt = PRIOR / 'native-v2/result.json'
    prepared, native = (json.loads(p.read_bytes()) for p in (source_receipt, native_receipt))
    previous_source = Path(prepared['sources']['candidate'])
    reference = Path(native['products']['candidate']['binary'])
    if sha(reference) != REFERENCE_SHA256:
        raise SystemExit('0343 core binary differs from the recorded input')

    steps = {step['name']: step['argv'] for step in native['steps'] if step['exit'] == 0}
    compile_template = steps['candidate-compile-c_api']
    link = steps['candidate-link']
    old_objects = [Path(arg) for arg in link if arg.endswith('.o')]
    archives = [Path(arg) for arg in link if arg.endswith('.a')]
    pins = {str(p): sha(p) for p in (Path(__file__), PATCH, source_receipt, native_receipt,
                                      reference, *old_objects, *archives)}
    for name, digest in prepared['source_pins']['candidate'].items():
        path = previous_source / name
        if sha(path) != digest:
            raise SystemExit(f'0343 source changed: {name}')
        pins[str(path)] = digest

    out.mkdir(parents=True)
    source = out / 'source'
    product = out / reference.name
    for name in prepared['source_pins']['candidate']:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous_source / name, target)

    result = {'state': '0344-core-build-running', 'steps': [], 'input_pins': pins,
              'device_commands': 0, 'physical_FPS_qualified': False}

    def save():
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    def run(label, argv, cwd=out):
        process = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=240)
        log = out / (label + '.log')
        log.write_bytes(process.stdout + process.stderr)
        result['steps'].append({'name': label, 'argv': argv, 'exit': process.returncode,
                                'log_sha256': sha(log)})
        save()
        process.check_returncode()
        return process.stdout.decode()

    def move_source(arg):
        return arg.replace(str(previous_source), str(source))

    try:
        run('apply', ['patch', '-p1', '-F', '0', '-i', str(PATCH)], source)
        candidate_pins = {name: sha(source / name) for name in prepared['source_pins']['candidate']}
        for obj in old_objects:
            unit = obj.stem
            argv = [move_source(arg) for arg in compile_template]
            argv[argv.index('-c') + 1] = str(source / 'src' / (unit + '.cpp'))
            argv[argv.index('-o') + 1] = str(out / obj.name)
            run('compile-' + unit, argv)
        argv = [str(out / Path(arg).name) if arg.endswith('.o') else move_source(arg) for arg in link]
        argv[argv.index('-o') + 1] = str(product)
        run('link', argv)
        run('strip', ['xcrun', 'strip', '-x', str(product)])
        run('sign', ['codesign', '--force', '--sign', '-', str(product)])
        run('verify', ['codesign', '--verify', '--strict', str(product)])

        for command, label in ((['nm', '-m', '-u'], 'imports'), (['nm', '-gU'], 'exports'),
                               (['otool', '-L'], 'loads'), (['vtool', '-show-build'], 'platform')):
            old = run('reference-' + label, [*command, str(reference)]).splitlines()
            new = run('candidate-' + label, [*command, str(product)]).splitlines()
            if label == 'exports':
                same = {line.split()[-1] for line in old if line.strip()} == {
                    line.split()[-1] for line in new if line.strip()}
            elif label in ('loads', 'platform'):
                same = old[1:] == new[1:]
            else:
                same = set(old) == set(new)
            if not same:
                raise ValueError('Core ABI comparison failed for ' + label)
        if product.stat().st_size > 8_409_088:
            raise ValueError('0344 does not fit the existing Core slot')
        result.update(state='0344-native-core-signed', binary=str(product), bytes=product.stat().st_size,
                      binary_sha256=sha(product), source=str(source), source_pins=candidate_pins,
                      matching_imports_exports_loads_and_platform=True)
    except BaseException as error:
        result.update(state='0344-native-core-failed', error=str(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(path) == digest for path, digest in pins.items())
        save()
    if not result['inputs_unchanged']:
        raise SystemExit('0343 build inputs changed')
    print(json.dumps({k: v for k, v in result.items() if k not in ('steps', 'input_pins', 'source_pins')}, indent=2))


if __name__ == '__main__':
    main()
