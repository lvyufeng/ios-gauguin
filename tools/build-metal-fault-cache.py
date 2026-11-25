#!/usr/bin/env python3
"""Reproduce the installed core, replacing only its IOKit transport object."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
OLD_WORK = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
OLD = OLD_WORK/'research/tmp/metal-ownership-v1/implementation-20261112/native-03'
OLD_SHA = 'c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674'
TAG = '8a71fe61aded108fa9ba5a22'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def instrument(raw):
    original, edits = raw, []

    def edit(before, after):
        nonlocal raw
        assert raw.count(before) == 1, before
        raw = raw.replace(before, after)
        edits.append((before, after))

    anchor = '#include "hakios-metal/gpu.hpp"\n'
    edit(anchor, anchor+'#include "GauguinFaultQueryCache.hpp"\n')
    anchor = '    int call(uint32_t request, void* data, size_t size) override {\n'
    edit(anchor, anchor+
         '        const bool faultsQuery = GauguinFaultQueryCache::matches(request, data, size);\n'
         '        if (faultsQuery && faultsCache_.unsupported()) return ENOSYS;\n')
    anchor = '        kern_return_t r = IOConnectCallStructMethod(c_, request, data, size, data, &returned);\n'
    edit(anchor, anchor+
         '        if (faultsCache_.observe(faultsQuery, r == KERN_SUCCESS && returned == size,\n'
         '                                 r == kIOReturnUnsupported)) {\n'
         '            fprintf(stderr, "GAUGUIN FQ322: unsupported_cached=1 request=64 param=9\\n");\n'
         '        }\n')
    anchor = 'private:\n    io_connect_t c_;'
    edit(anchor, 'private:\n    GauguinFaultQueryCache faultsCache_;\n    io_connect_t c_;')
    undone = raw
    for before, after in reversed(edits):
        assert undone.count(after) == 1
        undone = undone.replace(after, before)
    assert undone == original
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    receipt = json.loads((OLD/'result.json').read_text())
    assert receipt['state'] == 'linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3'
    assert receipt['sha256'] == sha(receipt['library']) == OLD_SHA
    assert receipt['cache_build_tag'] == TAG and receipt['source_pins_unchanged']
    assert hashlib.sha256(('A619\n'+json.dumps(receipt['input_pins'], sort_keys=True)).encode()).hexdigest()[:24] == TAG
    source = Path(receipt['source'])
    builder = OLD_WORK/'tools/build-hakios-metal.py'
    spec = importlib.util.spec_from_file_location('original_builder', builder)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    mesa_builds = [Path(p).parent for p in receipt['input_pins'] if p.endswith('/build.ninja')]
    mesa_sources = [Path(p).parents[3] for p in receipt['input_pins'] if p.endswith('/src/freedreno/ir3/ir3.h')]
    assert len(mesa_builds) == len(mesa_sources) == 1
    mb, ms = mesa_builds[0], mesa_sources[0]
    sdk = Path(subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip())
    policy = WORK/'graphics/gauguin-fault-cache/GauguinFaultQueryCache.hpp'
    pins = dict(receipt['input_pins'])
    for path in [OLD/'result.json', Path(receipt['library']), policy, Path(__file__).resolve(),
                 *[OLD/(name+'.o') for name in old.CORE]]:
        if str(path) in pins:
            assert pins[str(path)] == sha(path)
        pins[str(path)] = sha(path)
    for name, digest in pins.items():
        assert sha(name) == digest, name
    assert str(sdk/'SDKSettings.json') in pins
    common = ['xcrun', '--sdk', 'iphoneos', 'clang++', '-target', 'arm64-apple-ios16.0',
              '-isysroot', str(sdk), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
              '-DHAKIOS_METAL_MESA', '-DHAKIOS_METAL_TARGET_A619',
              '-DHAKIOS_METAL_CACHE_BUILD="'+TAG+'"', '-I'+str(source/'include'),
              *old.mesa_flags(ms, mb)]
    out.mkdir(parents=True)
    sources = out/'sources'
    sources.mkdir()
    original = source/'src/iokit_transport.cpp'
    (sources/original.name).write_text(instrument(original.read_text()))
    shutil.copyfile(policy, sources/policy.name)
    result = dict(state='native-FQ322-build-started', input_pins=pins, products={}, steps=[],
                  source=str(sources/original.name), original_source=str(original),
                  device_commands=0, runtime_qualified=False)

    def run(argv, label):
        with (out/(label+'.log')).open('x') as stream:
            proc = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        result['steps'].append(dict(label=label, argv=argv, exit=proc.returncode))
        assert proc.returncode == 0, label

    try:
        for variant in ('baseline', 'candidate'):
            dest = out/variant
            dest.mkdir()
            obj = dest/'iokit_transport.o'
            src = original if variant == 'baseline' else sources/original.name
            run([*common, '-c', str(src), '-o', str(obj)], variant+'-compile')
            old.ios_version(obj)
            if variant == 'baseline':
                assert sha(obj) == sha(OLD/'iokit_transport.o'), 'original transport object differs'
            objects = [obj if name == 'iokit_transport' else OLD/(name+'.o') for name in old.CORE]
            library = dest/'libGauguinMetalCore.dylib'
            run([*common, '-dynamiclib', *map(str, objects), *[str(mb/name) for name in old.ARCHIVES],
                 '-lz', '-lm', '-framework', 'IOKit', '-framework', 'IOSurface', '-framework', 'CoreFoundation',
                 '-Wl,-install_name,@rpath/libGauguinMetalCore.dylib', '-o', str(library)], variant+'-link')
            platform = old.ios_version(library)
            run(['codesign', '--force', '--sign', '-', str(library)], variant+'-sign')
            run(['codesign', '--verify', '--strict', str(library)], variant+'-verify')
            run(['nm', '-m', '-u', str(library)], variant+'-imports')
            run(['nm', '-gU', str(library)], variant+'-exports')
            run(['otool', '-L', str(library)], variant+'-loads')
            # The original compiler object can constant-fold the cache-key
            # prefix; the original image itself has no literal TAG string.
            # Reusing the exact compiler.o is the authoritative preservation.
            assert library.read_bytes().count(TAG.encode()+b'\0') == Path(receipt['library']).read_bytes().count(TAG.encode()+b'\0')
            result['products'][variant] = dict(binary=str(library), sha256=sha(library), bytes=library.stat().st_size,
                                                object_sha256=sha(obj), platform_version=platform)
            if variant == 'baseline':
                assert sha(library) == OLD_SHA, 'installed core baseline reproduction differs'
        before = (out/'baseline-imports.log').read_text()
        after = (out/'candidate-imports.log').read_text()
        exports = lambda name: {row.split()[-1] for row in (out/(name+'-exports.log')).read_text().splitlines() if row.strip()}
        result['imports_unchanged'] = before == after
        result['exports_unchanged'] = exports('baseline') == exports('candidate')
        result['added_import_lines'] = sorted(set(after.splitlines())-set(before.splitlines()))
        result['removed_import_lines'] = sorted(set(before.splitlines())-set(after.splitlines()))
        result['loads_unchanged'] = (out/'baseline-loads.log').read_text().splitlines()[1:] == (out/'candidate-loads.log').read_text().splitlines()[1:]
        assert result['imports_unchanged'] and result['exports_unchanged'] and result['loads_unchanged']
        assert result['products']['candidate']['bytes'] <= 2053*4096, 'candidate exceeds existing core allocation'
        result.update(state='native-FQ322-installed-baseline-reproduced-candidate-signed',
                      existing_allocation_bytes=2053*4096, cache_build_tag=TAG,
                      compiler_object_sha256=sha(OLD/'compiler.o'), compiler_object_reused=True,
                      unchanged_objects={name: sha(OLD/(name+'.o')) for name in old.CORE if name != 'iokit_transport'},
                      source_change_reversible=True, additional_threads=0, new_GPU_commands=0,
                      code_change='per-connection exact-query negative capability cache; supported answers stay live')
    except Exception as error:
        result.update(state='native-FQ322-build-failed', error=repr(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(name) == digest for name, digest in pins.items())
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
