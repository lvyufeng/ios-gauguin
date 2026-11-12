#!/usr/bin/env python3
"""Link a prepared ordered desktop frontend to the owned A619 core locally."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def helper(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'core-receipt', 'desktop-receipt', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    prep_path, core_path, old_path = [getattr(args, name).resolve()
                                      for name in ('prepared', 'core_receipt', 'desktop_receipt')]
    prep, core, old = [load(path) for path in (prep_path, core_path, old_path)]
    source, library, old_source = Path(prep['source']), Path(core['library']), Path(old['source'])
    old_root = old_source.parents[2]
    old_bundle = Path(old['bundle'])
    old_info = old_bundle / 'Info.plist'
    assert prep['state'] == 'prepared-owned-C4-desktop-frontend'
    assert prep['profile'] == 'gauguin-ca-owned-c4' and len(prep['source_pins']) == 8
    assert core['state'] == 'linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3'
    assert core['sha256'] == sha(library) == 'c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674'
    assert core['source_pins_unchanged'] and core['hardware_qualified'] is False
    assert old['state'] == 'native-iOS16-gauguin-desktop-frontend-candidate-not-runtime-qualified'
    assert old['core_sha256'] == '8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1'
    assert sha(Path(old['binary'])) == old['sha256']
    assert source != old_root and not args.out.exists()
    for name, digest in prep['source_pins'].items():
        assert sha(source / name) == digest, name
    for name, digest in prep['input_pins'].items():
        assert sha(Path(name)) == digest, name
    header = Path(core['source']) / 'include/hakios-metal/hakios_metal.h'
    assert header.is_file()

    out = args.out.resolve()
    bundle = out / 'GauguinMetalDesktop.bundle'
    binary = bundle / 'GauguinMetalDesktop'
    argv = list(old['compiler_argv'])
    old_library = [arg for arg in argv if arg.endswith('/libGauguinMetalCore.dylib')]
    old_includes = [arg for arg in argv if arg.startswith('-I') and arg[2:].endswith('/include')]
    old_rpath = '-Wl,-rpath,/usr/local/lib/gauguin'
    private_rpath = '-Wl,-rpath,/usr/local/lib/gauguin/owned'
    assert len(old_library) == len(old_includes) == 1
    assert sum(str(old_root) in arg for arg in argv) == 2
    assert argv.count(old_rpath) == 1
    assert argv.count('-o') == 1
    replaced = []
    for arg in argv:
        arg = arg.replace(str(old_root), str(source))
        if arg == old_includes[0]:
            arg = '-I' + str(header.parents[1])
        if arg == old_library[0]:
            arg = str(library)
        if arg == old_rpath:
            arg = private_rpath
        replaced.append(arg)
    replaced[replaced.index('-o') + 1] = str(binary)
    assert sum(str(source) in arg for arg in replaced) == 2
    assert str(library) in replaced and '-I' + str(header.parents[1]) in replaced
    assert replaced.count(private_rpath) == 1 and old_rpath not in replaced

    bundle.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(old_info, bundle / 'Info.plist')
    def run(command: list[str], logfile: str) -> None:
        with (out / logfile).open('x') as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
    run(replaced, 'compile-link.log')
    run(['codesign', '--force', '--sign', '-', str(bundle)], 'sign.log')
    run(['codesign', '--verify', '--strict', str(bundle)], 'verify.log')
    run(['otool', '-L', str(binary)], 'loads.log')
    run(['otool', '-l', str(binary)], 'load-commands.log')
    assert '@rpath/libGauguinMetalCore.dylib' in (out / 'loads.log').read_text()
    assert 'path /usr/local/lib/gauguin/owned ' in (out / 'load-commands.log').read_text()
    ca_helper = helper(repo / 'tools/build-hakios-metal-ca.py', 'ca_build')
    core_helper = helper(repo / 'tools/build-hakios-metal.py', 'core_build')
    optional = ca_helper.verify_optional_imports(binary)
    version = core_helper.ios_version(binary)
    assert all(sha(source / name) == digest for name, digest in prep['source_pins'].items())
    assert sha(library) == core['sha256']
    pins = {str(path): sha(path) for path in [Path(__file__).resolve(), prep_path,
            core_path, old_path, old_info, library, header,
            repo / 'tools/build-hakios-metal-ca.py', repo / 'tools/build-hakios-metal.py']}
    pins.update({str(source / name): digest for name, digest in prep['source_pins'].items()})
    result = dict(state='native-owned-C4-desktop-frontend-candidate', profile=prep['profile'],
                  bundle=str(bundle), binary=str(binary), bytes=binary.stat().st_size,
                  sha256=sha(binary), source=str(source / 'userland/src/HakiosMetalCA.m'),
                  core_sha256=core['sha256'], platform_version=version,
                  core_runtime_path='/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib',
                  optional_weak_dynamic_imports=optional, compiler_argv=replaced,
                  input_pins=pins, inputs_unchanged=True, device_commands=0,
                  installed=False, hardware_qualified=False, high_refresh_qualified=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('input_pins', 'compiler_argv')}, indent=2))


if __name__ == '__main__':
    main()
