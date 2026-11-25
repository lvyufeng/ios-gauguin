#!/usr/bin/env python3
"""Apply the scanout trace and incrementally relink the pinned 0343 kernel."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

from kernel_banner import one_banner


WORK = Path(__file__).resolve().parents[1]
MAIN = Path(subprocess.check_output(
    ['git', '-C', str(WORK), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
    text=True,
).strip()).parent
PRIOR = MAIN / 'research/tmp'
BASE = WORK / 'research/tmp/frame-344'
P343 = PRIOR / 'gauguin-runtime-issue-worktree-20261119/research/tmp/runtime-issue-343'
PATCH = WORK / 'xnu/patches/0253-gauguin-scanout-frame-trace.patch'
UNITS = (
    ('bsd/dev/gauguin_ui_trace.c', '0-gauguin_ui_trace.o'),
    ('bsd/dev/gauguin_ui_trace_board.c', '1-gauguin_ui_trace_board.o'),
    ('bsd/dev/sweet_touch.c', '0-sweet_touch.o'),
    ('iokit/Kernel/arm/GauguinGPU.cpp', 'corrected-GauguinGPU.o'),
    ('iokit/Kernel/arm/SweetFramebuffer.cpp', '0-SweetFramebuffer.o'),
)


def load(path):
    return json.loads(path.read_bytes())


def link_util():
    spec = importlib.util.spec_from_file_location('relink342', WORK / 'tools/relink-io342.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compile_templates(paths):
    records = {}
    for path in paths:
        data = load(path)
        if 'results' in data:
            for record in data['results']:
                records.setdefault(record['file'], record)
        else:
            record = next(s for s in data['steps'] if s['label'] == 'candidate-compile')
            records['iokit/Kernel/arm/GauguinGPU.cpp'] = record
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(BASE) or out.exists():
        raise SystemExit('provide a fresh output directory inside frame-344')
    util = link_util()
    sha = util.sha
    manifest = P343 / 'kernel-native/build-manifest.json'
    parent = load(manifest)
    original = parent['products']['candidate']
    steps = {s['label']: s for s in parent['steps'] if s['exit'] == 0}
    link = steps['candidate-link']
    version = steps['candidate-version']
    original_list = Path(link['arguments'][link['arguments'].index('-filelist') + 1])
    objects = original_list.read_text().splitlines()
    receipts = (
        PRIOR / 'gauguin-present-retry-worktree-20261116/research/tmp/present-retry-332/kernel-native-v2/result.json',
        PRIOR / 'gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/kernel-native-v2/result.json',
        PRIOR / 'gauguin-issued-fence-worktree-20261112/research/tmp/wake-310/native-final/result.json',
        PRIOR / 'gauguin-io-path-worktree-20261117/research/tmp/io-path-342/kernel-native-v4/result.json',
    )
    templates = compile_templates(receipts)
    pins = dict(parent['input_pins'])
    for path in (manifest, PATCH, Path(__file__), *receipts, original_list, *map(Path, objects)):
        pins.setdefault(str(path), sha(path))
    if not all(sha(path) == digest for path, digest in pins.items()):
        raise ValueError('a pinned 0343 kernel input differs')
    if sha(original['kernel']) != original['kernel_sha256'] or sha(original['unstripped']) != original['unstripped_sha256']:
        raise ValueError('0343 linked binaries differ')
    source_hashes = {name: digest for name, _kind, digest in parent['source_union']['entries']}
    old_source = Path(parent['source_union']['overlay'])
    common_source = Path(parent['source_union']['base'])
    source = out / 'source'
    out.mkdir(parents=True)
    for old in old_source.rglob('*'):
        if old.is_file():
            name = old.relative_to(old_source)
            if sha(old) != source_hashes[str(name)]:
                raise ValueError(f'0343 source differs: {name}')
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(old, target)
    touch = 'bsd/dev/sweet_touch.c'
    if not (source / touch).exists():
        path = common_source / touch
        if sha(path) != source_hashes[touch]:
            raise ValueError('0343 swipe source differs')
        shutil.copyfile(path, source / touch)
    identity = 'xnu-local344-' + hashlib.sha256(
        (original['kernel_sha256'] + sha(PATCH)).encode()).hexdigest()[:32]
    result = {'state': '0344-kernel-build-running', 'steps': [], 'input_pins': pins,
              'parent_manifest': str(manifest), 'identity': identity, 'device_commands': 0}

    def save():
        (out / 'build-manifest.json').write_text(json.dumps(result, indent=2) + '\n')

    def run(label, argv, cwd=out):
        process = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=180)
        log = out / (label + '.log')
        log.write_bytes(process.stdout + process.stderr)
        result['steps'].append({'label': label, 'arguments': argv, 'cwd': str(cwd),
                                'exit': process.returncode, 'log_sha256': sha(log)})
        save()
        if process.returncode:
            raise RuntimeError(f'{label} failed, see {log}')
        return process.stdout

    def relink(label, argv):
        raw = out / (label + '.unstripped')
        kernel = out / (label + '.kernel')
        argv[argv.index('-o') + 1] = str(raw)
        run(label + '-link', argv, link['cwd'])
        run(label + '-strip', ['xcrun', 'strip', '-S', str(raw), '-o', str(kernel)])
        return raw, kernel

    try:
        run('apply', ['patch', '-p1', '-F', '0', '-i', str(PATCH)], source)
        replacements = {}
        for name, object_name in UNITS:
            record = templates[name]
            argv = list(record['arguments'])
            src_arg, = (i for i, arg in enumerate(argv) if arg.endswith('/' + name))
            obj = out / object_name
            argv[src_arg] = str(source / name)
            argv[argv.index('-MF') + 1] = str(obj.with_suffix('.d'))
            argv[argv.index('-o') + 1] = str(obj)
            run('compile-' + obj.stem, argv, record['cwd'])
            old, = (arg for arg in objects if Path(arg).name == object_name)
            replacements[old] = str(obj)
        (out / 'candidate.filelist').write_text(''.join(replacements.get(obj, obj) + '\n' for obj in objects))

        prior_version = P343 / 'kernel-native/version.c'
        version_source = prior_version.read_text()
        if version_source.count(parent['identity']) != 2:
            raise ValueError('0343 version substitution is ambiguous')
        (out / 'version.c').write_text(version_source.replace(parent['identity'], identity))
        run('version', [arg.replace(str(prior_version.with_suffix('')), str(out / 'version'))
                        for arg in version['arguments']], version['cwd'])

        raw, kernel = relink('baseline', list(link['arguments']))
        if (util.normalized(raw.read_bytes()) != util.normalized(Path(original['unstripped']).read_bytes()) or
                util.normalized(kernel.read_bytes()) != util.normalized(Path(original['kernel']).read_bytes())):
            raise ValueError('0343 link reproduction differs beyond the UUID')
        argv = list(link['arguments'])
        argv[argv.index('-filelist') + 1] = str(out / 'candidate.filelist')
        argv[argv.index(str(prior_version.with_suffix('.o')))] = str(out / 'version.o')
        raw, kernel = relink('candidate', argv)
        if run('undefined', ['xcrun', 'nm', '-ju', str(kernel)]).strip():
            raise ValueError('0344 link has undefined symbols')
        banner = one_banner(kernel.read_bytes()).decode()
        if identity not in banner or parent['identity'] in banner:
            raise ValueError('0344 version identity check failed')
        result.update(state='0344-native-ARM64-linked', kernel=str(kernel), kernel_sha256=sha(kernel),
                      kernel_bytes=kernel.stat().st_size, kernel_banner=banner,
                      source=str(source), object_replacements=replacements,
                      baseline_reproduced_except_uuid=True, physical_FPS_qualified=False)
    except BaseException as error:
        result.update(state='0344-kernel-build-failed', error=str(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(path) == digest for path, digest in pins.items())
        save()
    if not result['inputs_unchanged']:
        raise SystemExit('0343 kernel inputs changed')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
