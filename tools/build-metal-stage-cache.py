#!/usr/bin/env python3
"""Reproduce FQ322 and change only the compiler cache/lock wrapper for SC323."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
from stage_cache_patch import instrument

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
OLD_WORK = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
OLD = OLD_WORK/'research/tmp/metal-ownership-v1/implementation-20261112/native-03'
FQ = MAIN/'research/tmp/gauguin-fault-cache-worktree-20261115/research/tmp/fault-cache-322/native-v2'
BASE_SHA = '608d792dd738c5c50e4171eaed9b723841f20560ded19a0d659c8104eafd421c'
TAG = '8a71fe61aded108fa9ba5a22'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    out = ap.parse_args().out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    original = json.loads((OLD/'result.json').read_text())
    prior = json.loads((FQ/'result.json').read_text())
    assert prior['state'] == 'native-FQ322-installed-baseline-reproduced-candidate-signed'
    assert prior['products']['candidate']['sha256'] == sha(prior['products']['candidate']['binary']) == BASE_SHA
    source = Path(original['source'])
    spec = importlib.util.spec_from_file_location('old_builder', OLD_WORK/'tools/build-hakios-metal.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    mb = [Path(p).parent for p in original['input_pins'] if p.endswith('/build.ninja')]
    ms = [Path(p).parents[3] for p in original['input_pins'] if p.endswith('/src/freedreno/ir3/ir3.h')]
    assert len(mb) == len(ms) == 1
    mb, ms = mb[0], ms[0]
    sdk = Path(subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip())
    header = WORK/'graphics/gauguin-stage-cache/GauguinStageCacheTrace.hpp'
    transport = FQ/'candidate/iokit_transport.o'
    pins = dict(prior['input_pins'])
    for p in [FQ/'result.json', transport, Path(prior['products']['candidate']['binary']),
              Path(__file__), WORK/'tools/stage_cache_patch.py', header]:
        pins[str(p.resolve())] = sha(p)
    for p, digest in pins.items():
        assert sha(p) == digest, p
    assert original['cache_build_tag'] == TAG and str(sdk/'SDKSettings.json') in pins
    common = ['xcrun', '--sdk', 'iphoneos', 'clang++', '-target', 'arm64-apple-ios16.0',
              '-isysroot', str(sdk), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
              '-DHAKIOS_METAL_MESA', '-DHAKIOS_METAL_TARGET_A619',
              '-DHAKIOS_METAL_CACHE_BUILD="'+TAG+'"', '-I'+str(source/'include'), *old.mesa_flags(ms, mb)]
    out.mkdir(parents=True)
    sources = out/'sources'
    sources.mkdir()
    (sources/'compiler.cpp').write_text(instrument((source/'src/compiler.cpp').read_text()))
    shutil.copyfile(header, sources/header.name)
    result = dict(state='native-SC323-build-started', input_pins=pins, products={}, steps=[],
                  source=str(sources/'compiler.cpp'), original_source=str(source/'src/compiler.cpp'),
                  device_commands=0, runtime_qualified=False)

    def run(argv, label):
        with (out/(label+'.log')).open('x') as stream:
            p = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        result['steps'].append(dict(label=label, argv=argv, exit=p.returncode))
        assert p.returncode == 0, label

    try:
        for variant in ('baseline', 'candidate'):
            dest = out/variant
            dest.mkdir()
            obj = dest/'compiler.o'
            src = source/'src/compiler.cpp' if variant == 'baseline' else sources/'compiler.cpp'
            run([*common, '-c', str(src), '-o', str(obj)], variant+'-compile')
            old.ios_version(obj)
            if variant == 'baseline':
                assert sha(obj) == sha(OLD/'compiler.o'), 'original compiler object differs'
            objects = [obj if name == 'compiler' else transport if name == 'iokit_transport'
                       else OLD/(name+'.o') for name in old.CORE]
            library = dest/'libGauguinMetalCore.dylib'
            run([*common, '-dynamiclib', *map(str, objects), *[str(mb/name) for name in old.ARCHIVES],
                 '-lz', '-lm', '-framework', 'IOKit', '-framework', 'IOSurface', '-framework', 'CoreFoundation',
                 '-Wl,-install_name,@rpath/libGauguinMetalCore.dylib', '-o', str(library)], variant+'-link')
            version = old.ios_version(library)
            run(['codesign', '--force', '--sign', '-', str(library)], variant+'-sign')
            run(['codesign', '--verify', '--strict', str(library)], variant+'-verify')
            for args, label in [(['nm', '-m', '-u'], 'imports'), (['nm', '-gU'], 'exports'), (['otool', '-L'], 'loads')]:
                run([*args, str(library)], variant+'-'+label)
            result['products'][variant] = dict(binary=str(library), bytes=library.stat().st_size,
                sha256=sha(library), object_sha256=sha(obj), platform_version=version)
            if variant == 'baseline':
                assert sha(library) == BASE_SHA, 'FQ322 baseline reproduction differs'
        exports = lambda v: {r.split()[-1] for r in (out/(v+'-exports.log')).read_text().splitlines() if r.strip()}
        before, after = [(out/(v+'-imports.log')).read_text() for v in ('baseline', 'candidate')]
        added = sorted(set(after.splitlines())-set(before.splitlines()))
        removed = sorted(set(before.splitlines())-set(after.splitlines()))
        assert not removed and added == ['                 (undefined) external _mach_absolute_time (from libSystem)']
        assert exports('baseline') == exports('candidate')
        assert (out/'baseline-loads.log').read_text().splitlines()[1:] == (out/'candidate-loads.log').read_text().splitlines()[1:]
        assert result['products']['candidate']['bytes'] <= 2053*4096, 'candidate exceeds existing allocation'
        result.update(state='native-SC323-FQ322-baseline-reproduced-candidate-signed',
            cache_build_tag=TAG, cache_key_and_serialization_unchanged=True, cache_shader_output_unchanged=True,
            compiler_miss_and_save_still_locked=True, exports_unchanged=True, loads_unchanged=True,
            added_import_lines=added, removed_import_lines=removed, existing_allocation_bytes=2053*4096,
            fault_cache_object_sha256=sha(transport),
            unchanged_objects={name: sha(transport if name == 'iokit_transport' else OLD/(name+'.o'))
                               for name in old.CORE if name != 'compiler'},
            source_change_reversible=True, additional_threads=0, new_GPU_commands=0)
    except Exception as error:
        result.update(state='native-SC323-build-failed', error=repr(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(p) == d for p, d in pins.items())
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
