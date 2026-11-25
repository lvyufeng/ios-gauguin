#!/usr/bin/env python3
"""Incrementally build the signed Core and native kernel against the frozen 0344 inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

from core343_scope import MAIN, WORK, load, require, sha
from kernel_banner import one_banner


P344_WORK = MAIN / 'research/tmp/gauguin-frame-344-worktree-20261119'
P344 = P344_WORK / 'research/tmp/frame-344'
BASE = WORK / 'research/tmp/frame-345'
CORE_PATCH = WORK / 'graphics/gauguin-program-io/0345-core-recording.patch'
KERNEL_PATCH = WORK / 'xnu/patches/0254-gauguin-scanout-gates-submit-resolve.patch'


def stage_source(previous, target, names):
    for name in names:
        dst = target / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous / name, dst)


class Build:
    def __init__(self, out, receipt, patch, previous):
        self.out = out
        self.receipt = out / receipt
        self.source = out / 'source'
        self.patch = patch
        self.pins = {str(path): sha(path) for path in (previous, patch, Path(__file__))}
        self.steps = []
        out.mkdir()

    def pin(self, path, expected=None):
        digest = sha(path)
        require(expected is None or digest == expected, '0344 build input changed: ' + str(path))
        self.pins[str(path)] = digest

    def run(self, name, argv, cwd=None):
        cwd = cwd or self.out
        process = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=240)
        log = self.out / (name + '.log')
        log.write_bytes(process.stdout + process.stderr)
        self.steps.append(dict(name=name, argv=argv, cwd=str(cwd), exit=process.returncode,
                               log_sha256=sha(log)))
        require(not process.returncode, f'{name} exited {process.returncode}. See {log}')
        return process.stdout

    def apply(self):
        self.run('apply', ['patch','-p1','-F','0','-i',str(self.patch)], self.source)

    def finish(self, state, **fields):
        require(all(sha(name) == digest for name,digest in self.pins.items()), 'build inputs changed')
        record = dict(state=state, source=str(self.source), steps=self.steps, input_pins=self.pins,
                      inputs_unchanged=True, device_commands=0, **fields)
        self.receipt.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({k:v for k,v in record.items() if k not in ('input_pins','source_pins','steps')}, indent=2))


def core():
    previous = P344 / 'core-native/result.json'
    old = load(previous)
    build = Build(BASE/'core-native', 'result.json', CORE_PATCH, previous)
    original = Path(old['binary'])
    build.pin(original, old['binary_sha256'])
    source = Path(old['source'])
    for name,digest in old['source_pins'].items():
        build.pin(source/name, digest)
    stage_source(source, build.source, old['source_pins'])
    build.apply()
    steps = {step['name']: step['argv'] for step in old['steps'] if step['exit'] == 0}
    old_compile = steps['compile-render']
    old_object = old_compile[old_compile.index('-o')+1]
    obj = build.out/'render.o'
    for arg in steps['link']:
        if arg.endswith(('.o','.a')):
            build.pin(Path(arg), old['input_pins'].get(arg))
    command = [arg.replace(str(source),str(build.source)) for arg in old_compile]
    command[command.index('-o')+1] = str(obj)
    build.run('compile-render', command)
    binary = build.out/original.name
    link = [str(obj) if arg == old_object else arg for arg in steps['link']]
    require(old_object in steps['link'] and str(obj) in link, 'no render object replacement')
    link[link.index('-o')+1] = str(binary)
    build.run('link', link)
    build.run('strip', ['xcrun','strip','-x',str(binary)])
    build.run('sign', ['codesign','--force','--sign','-',str(binary)])
    build.run('verify', ['codesign','--verify','--strict',str(binary)])
    for kind, argv in (('imports',['nm','-m','-u']), ('exports',['nm','-gU']),
                       ('loads',['otool','-L']), ('platform',['vtool','-show-build'])):
        a = build.run('0344-'+kind, [*argv,str(original)]).splitlines()
        b = build.run('0345-'+kind, [*argv,str(binary)]).splitlines()
        if kind == 'exports':
            a,b = [{s.split()[-1] for s in rows if s.strip()} for rows in (a,b)]
        elif kind in ('loads','platform'):
            a,b = a[1:],b[1:]
        require(a == b, 'Core ABI differs: ' + kind)
    require(binary.stat().st_size == original.stat().st_size == 7_975_792, 'Core slot length changed')
    build.finish('0345-native-core-signed', binary=str(binary), bytes=binary.stat().st_size,
                 binary_sha256=sha(binary), source_pins={name:sha(build.source/name) for name in old['source_pins']},
                 matching_imports_exports_loads_and_platform=True)


def normalized_uuid(data):
    """Normalize only LC_UUID in a little-endian Mach-O 64 binary."""
    import struct
    require(data[:4] == bytes.fromhex('cffaedfe'), 'unexpected Mach-O type')
    count, length = struct.unpack_from('<II', data, 16)
    offset = 32
    offsets = []
    for _ in range(count):
        cmd, size = struct.unpack_from('<II', data, offset)
        require(size >= 8 and offset + size <= 32 + length, 'invalid Mach-O command')
        if cmd == 0x1b:
            require(size == 24, 'invalid LC_UUID')
            offsets.append(offset + 8)
        offset += size
    require(len(offsets) == 1 and offset == 32 + length, 'missing or ambiguous LC_UUID')
    uuid, = offsets
    return data[:uuid] + bytes(16) + data[uuid + 16:]


def kernel():
    previous = P344/'native-kernel-v2/build-manifest.json'
    old = load(previous)
    build = Build(BASE/'native-kernel', 'build-manifest.json', KERNEL_PATCH, previous)
    original = Path(old['kernel'])
    build.pin(original, old['kernel_sha256'])
    source = Path(old['source'])
    names = sorted(str(p.relative_to(source)) for p in source.rglob('*') if p.is_file())
    for name in names:
        build.pin(source/name)
    stage_source(source, build.source, names)
    build.apply()
    steps = {step['label']:step for step in old['steps'] if step['exit'] == 0}
    link = steps['candidate-link']
    argv = link['arguments']
    previous_list = Path(argv[argv.index('-filelist')+1])
    build.pin(previous_list)
    for obj in previous_list.read_text().splitlines():
        build.pin(Path(obj), old['input_pins'].get(obj))
    version_path = previous.parent/'version.c'
    build.pin(version_path)
    old_version = version_path.read_text()
    require(old_version.count(old['identity']) == 2, 'ambiguous 0344 kernel identity')
    version = steps['version']
    identity = 'xnu-local345-'+hashlib.sha256((old['kernel_sha256']+sha(KERNEL_PATCH)).encode()).hexdigest()[:32]

    def relink(label, command, target):
        with TemporaryDirectory(prefix=label+'-', dir=build.out) as temp:
            raw = str(Path(temp)/'kernel.unstripped')
            command = list(command)
            command[command.index('-o')+1] = raw
            build.run(label+'-link', command, link['cwd'])
            build.run(label+'-strip', ['xcrun','strip','-S',raw,'-o',str(target)])
            return sha(raw)

    with TemporaryDirectory(prefix='reproduce-', dir=build.out) as temp:
        reproduced = Path(temp)/'0344.kernel'
        relink('0344', argv, reproduced)
        require(normalized_uuid(reproduced.read_bytes()) == normalized_uuid(original.read_bytes()),
                '0344 kernel differs after normalizing LC_UUID')
    replacements = {}
    for unit in ('1-gauguin_ui_trace_board','corrected-GauguinGPU'):
        step = steps['compile-'+unit]
        cmd = [arg.replace(str(source),str(build.source)) for arg in step['arguments']]
        obj = build.out/(unit+'.o')
        replaced = step['arguments'][cmd.index('-o')+1]
        cmd[cmd.index('-MF')+1] = str(obj.with_suffix('.d'))
        cmd[cmd.index('-o')+1] = str(obj)
        if unit == 'corrected-GauguinGPU':
            cmd.extend(['-Wframe-larger-than=4096','-Werror=frame-larger-than'])
        build.run('compile-'+unit, cmd, step['cwd'])
        replacements[replaced] = str(obj)
    filelist = build.out/'candidate.filelist'
    objects = previous_list.read_text().splitlines()
    require(all(objects.count(item)==1 for item in replacements), 'ambiguous native object replacements')
    filelist.write_text(''.join(replacements.get(item,item)+'\n' for item in objects))
    (build.out/'version.c').write_text(old_version.replace(old['identity'],identity))
    build.run('version', [arg.replace(str(version_path.with_suffix('')),str(build.out/'version'))
                          for arg in version['arguments']], version['cwd'])
    candidate = list(argv)
    candidate[candidate.index('-filelist')+1] = str(filelist)
    candidate[candidate.index(str(version_path.with_suffix('.o')))] = str(build.out/'version.o')
    binary = build.out/'candidate.kernel'
    unstripped = relink('0345', candidate, binary)
    require(not build.run('undefined', ['xcrun','nm','-ju',str(binary)]).strip(),
            'undefined native kernel symbols')
    banner = one_banner(binary.read_bytes()).decode()
    require(identity in banner and old['identity'] not in banner, 'native version mismatch')
    build.finish('0345-native-ARM64-linked', kernel=str(binary), kernel_sha256=sha(binary),
                 kernel_bytes=binary.stat().st_size, unstripped_sha256=unstripped,
                 identity=identity, kernel_banner=banner, object_replacements=replacements,
                 baseline_reproduced_except_uuid=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('core','kernel'))
    {'core':core, 'kernel':kernel}[parser.parse_args().component]()
