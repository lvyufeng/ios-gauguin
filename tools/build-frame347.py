#!/usr/bin/env python3
"""Build the 0347 Core and scanout probe from the pinned 0346 products."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from core343_scope import MAIN, WORK, load, require, sha
from kernel_banner import one_banner


BASE = WORK / 'research/tmp/frame-347'
P346 = MAIN / 'research/tmp/gauguin-dpu-hwcg-worktree-20261119/research/tmp/frame-346'
helper = import_module('build-frame345')


def core():
    previous = P346/'core-native/result.json'
    old = load(previous)
    build = helper.Build(BASE/'core-native', 'result.json',
                         WORK/'graphics/gauguin-program-io/0347-packet-shadow-ranges.patch', previous)
    build.pin(Path(__file__))
    baseline = Path(old['binary'])
    build.pin(baseline, old['binary_sha256'])
    source = Path(old['source'])
    for name, digest in old['source_pins'].items():
        build.pin(source/name, digest)
    helper.stage_source(source, build.source, old['source_pins'])
    build.apply()
    steps = {step['name']:step['argv'] for step in old['steps'] if step['exit']==0}
    link = steps['link']
    objects = [Path(arg) for arg in link if arg.endswith('.o')]
    require(len(objects)==len({p.stem for p in objects})==12, 'Core TU scope changed')
    for arg in link:
        if arg.endswith('.a'):
            build.pin(Path(arg), old['input_pins'].get(arg))

    def compile_unit(path):
        argv = [arg.replace(str(source), str(build.source)) for arg in steps['compile-'+path.stem]]
        argv[argv.index('-o')+1] = str(build.out/path.name)
        build.run('compile-'+path.stem, argv)

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(compile_unit, objects))

    binary = build.out/baseline.name
    exports = build.out/'previous-exports.txt'
    exports.write_bytes(build.run('baseline-exports-raw', ['nm','-gUj',str(baseline)]))
    export_flag = '-Wl,-exported_symbols_list,'
    require(sum(arg.startswith(export_flag) for arg in link)==1, 'ambiguous Core export list')
    argv = [str(build.out/Path(arg).name) if arg.endswith('.o') else arg for arg in link]
    argv[argv.index('-o')+1] = str(binary)
    argv = [export_flag+str(exports) if arg.startswith(export_flag) else arg for arg in argv]
    build.run('link', argv)
    build.run('strip', ['xcrun','strip','-x',str(binary)])
    build.run('sign', ['codesign','--force','--sign','-',str(binary)])
    build.run('verify', ['codesign','--verify','--strict',str(binary)])
    for name, command in (('imports',['nm','-m','-u']),('exports',['nm','-gUj']),
                          ('loads',['otool','-L']),('platform',['vtool','-show-build'])):
        a = build.run('baseline-'+name, [*command,str(baseline)]).splitlines()
        b = build.run('candidate-'+name, [*command,str(binary)]).splitlines()
        if name == 'exports':
            a,b = set(a),set(b)
        elif name in ('loads','platform'):
            a,b = a[1:],b[1:]
        require(a==b, 'Core ABI differs: '+name)
    slot = P346/'slot-delta/install-plan.json'
    build.pin(slot)
    slot_bytes = load(slot)['rows']['core']['data_blocks']*4096
    require(0 < binary.stat().st_size <= slot_bytes, 'signed Core exceeds installed extent')
    build.finish('0347-native-core-signed', binary=str(binary), bytes=binary.stat().st_size,
                 binary_sha256=sha(binary), compiled_tus=len(objects), slot_bytes=slot_bytes,
                 source_pins={name:sha(build.source/name) for name in old['source_pins']},
                 matching_imports_exports_loads_and_platform=True)


def kernel():
    patches = tuple(WORK/'xnu/patches'/name for name in (
        '0257-gauguin-arm-scanout-counters.patch','0258-gauguin-scanout-counter-stats-mode.patch'))
    link_scanout(P346/'native-kernel/build-manifest.json',BASE/'native-kernel',
                 parent_trial='0346',trial='0347',patches=patches)


def link_scanout(previous, out, *, parent_trial, trial, patches, extra_units=(), compiler_bin=None,
                 recompile_scanout=True, extra_sources=None):
    old = load(previous)
    build = helper.Build(out, 'build-manifest.json', patches[0], previous)
    build.pin(Path(__file__))
    baseline = Path(old['kernel'])
    build.pin(baseline, old['kernel_sha256'])
    source = Path(old['source'])
    names = sorted(str(p.relative_to(source)) for p in source.rglob('*') if p.is_file())
    for name in names:
        build.pin(source/name)
    helper.stage_source(source, build.source, names)
    extra_sources = extra_sources or {}
    for name, original in extra_sources.items():
        require(name not in names, 'duplicate carried kernel source: '+name)
        build.pin(original)
        helper.stage_source(original.parents[len(Path(name).parts)-1], build.source, (name,))
    build.apply()
    for patch in patches[1:]:
        build.pin(patch)
        build.run('apply-'+patch.stem,['patch','-p1','-F','0','-i',str(patch)],build.source)
    steps = {step['name']:step for step in old['steps'] if step['exit']==0}
    link = steps[parent_trial+'-link']
    filelist = Path(link['argv'][link['argv'].index('-filelist')+1])
    build.pin(filelist)
    objects = filelist.read_text().splitlines()
    for path in objects:
        build.pin(Path(path), old['input_pins'].get(path))

    def compiler_argv(argv):
        if compiler_bin is None:
            return list(argv)
        compiler = compiler_bin / Path(argv[0]).name
        build.pin(compiler)
        return [str(compiler), *argv[1:]]

    if compiler_bin is not None:
        for tool in ('ld', 'strip', 'nm'):
            build.pin(compiler_bin/tool)

    def relink(label, argv, target):
        with TemporaryDirectory(prefix=label+'-', dir=build.out) as directory:
            raw = str(Path(directory)/'kernel.unstripped')
            argv = compiler_argv(argv)
            argv[argv.index('-o')+1] = raw
            build.run(label+'-link', argv, link['cwd'])
            build.run(label+'-strip', ['xcrun','strip','-S',raw,'-o',str(target)])
            return sha(raw)

    with TemporaryDirectory(prefix='baseline-', dir=build.out) as directory:
        reproduced = Path(directory)/(parent_trial+'.kernel')
        relink(parent_trial, link['argv'], reproduced)
        require(helper.normalized_uuid(reproduced.read_bytes()) ==
                helper.normalized_uuid(baseline.read_bytes()), 'baseline kernel failed reproduction')

    units = []
    if recompile_scanout:
        framebuffer = steps.get('compile-SweetFramebuffer')
        if framebuffer is None:
            trace_manifest = helper.P344/'native-kernel-v2/build-manifest.json'
            build.pin(trace_manifest)
            framebuffer = next(step for step in load(trace_manifest)['steps'] if step['label']=='compile-0-SweetFramebuffer')
        units.extend([('gauguin_ui_trace_board',steps['compile-gauguin_ui_trace_board']),
                      ('SweetFramebuffer',framebuffer)])
    for name, receipt, label in extra_units:
        build.pin(receipt)
        origin = load(receipt)
        step, = (entry for entry in origin['steps']
                 if entry.get('name', entry.get('label'))==label and entry['exit']==0)
        previous_args = step.get('argv', step.get('arguments'))
        previous_source, = (Path(arg) for arg in previous_args
                            if Path(arg).stem==name and Path(arg).suffix in ('.c','.cpp'))
        carried_source, = (p for p in [*source.rglob(previous_source.name), *extra_sources.values()]
                           if p.name == previous_source.name)
        build.pin(previous_source, sha(carried_source))
        previous_object = previous_args[previous_args.index('-o')+1]
        if receipt == previous:
            require(previous_object in old['object_replacements'].values() and previous_object in objects,
                    'extra TU is absent from the reproduced kernel: '+name)
        else:
            require(old['input_pins'].get(previous_object)==sha(previous_object), 'extra TU object differs: '+name)
        units.append((name,step))
    require(units, 'no kernel object selected for replacement')
    replacements = {}
    for name, unit in units:
        args = list(unit.get('argv',unit.get('arguments')))
        original = [i for i,arg in enumerate(args) if Path(arg).name in (name+'.c',name+'.cpp')]
        require(len(original)==1, 'ambiguous scanout source: '+name)
        unit_source = next(build.source.rglob(Path(args[original[0]]).name))
        args[original[0]] = str(unit_source)
        obj = build.out/(name+'.o')
        replaced = args[args.index('-o')+1]
        require(objects.count(replaced)==1, 'ambiguous scanout object replacement: '+name)
        args[args.index('-o')+1] = str(obj)
        args[args.index('-MF')+1] = str(obj.with_suffix('.d'))
        build.run('compile-'+name,compiler_argv(args),unit['cwd'])
        replacements[replaced] = str(obj)
    next_filelist = build.out/'candidate.filelist'
    next_filelist.write_text(''.join(replacements.get(x,x)+'\n' for x in objects))

    version_path = previous.parent/'version.c'
    build.pin(version_path)
    version = version_path.read_text()
    require(version.count(old['identity'])==2, 'ambiguous baseline kernel version')
    identity_seed = old['kernel_sha256']+''.join(sha(patch) for patch in patches)
    identity = f'xnu-local{int(trial)}-'+hashlib.sha256(identity_seed.encode()).hexdigest()[:32]
    version_root = build.out/'version'
    version_root.with_suffix('.c').write_text(version.replace(old['identity'],identity))
    step = steps['version']
    build.run('version', compiler_argv([arg.replace(str(version_path.with_suffix('')),str(version_root))
                          for arg in step['argv']]), step['cwd'])
    candidate = list(link['argv'])
    candidate[candidate.index('-filelist')+1] = str(next_filelist)
    candidate[candidate.index(str(version_path.with_suffix('.o')))] = str(version_root.with_suffix('.o'))
    binary = build.out/'candidate.kernel'
    raw_sha = relink(trial,candidate,binary)
    require(not build.run('undefined',['xcrun','nm','-ju',str(binary)]).strip(), 'unresolved kernel symbols')
    banner = one_banner(binary.read_bytes()).decode()
    require(identity in banner and old['identity'] not in banner, 'native kernel identity differs')
    build.finish(trial+'-native-ARM64-linked', kernel=str(binary), kernel_sha256=sha(binary),
                 kernel_bytes=binary.stat().st_size, unstripped_sha256=raw_sha, identity=identity,
                 kernel_banner=banner, object_replacements=replacements, baseline_reproduced_except_uuid=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('core','kernel'))
    require(load(BASE/'build-storage-admission.json')['admitted'], 'whole 0347 build not admitted')
    {'core':core,'kernel':kernel}[parser.parse_args().component]()
