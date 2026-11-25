#!/usr/bin/env python3
"""Build the bounded root graphics-image probe. No installation or device IO."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['core-receipt', 'shader-receipt', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    core_path, shader_path = args.core_receipt.resolve(), args.shader_receipt.resolve()
    core, shader = (json.loads(p.read_text()) for p in [core_path, shader_path])
    library, source = Path(core['library']), Path(core['source'])
    assert core['state'] == 'linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3'
    assert core['source_pins_unchanged'] and sha(library) == core['sha256'] == 'af6918b6c2703237bcafb722764f7a9d29c5086ba3ecd4a1be75e1b3a0e21177'
    assert json.loads((source.parent / 'result.json').read_text())['profile'] == 'a619-graphics-images'
    assert shader['state'] == 'generated-own-graphics-image-Metal2.4-library-not-runtime-qualified'
    assert shader['platform'] == 'ios' and shader['inputs_unchanged']
    metallib = Path(shader['library'])
    assert sha(metallib) == shader['library_sha256'] and metallib.stat().st_size == shader['library_bytes']
    for receipt in [core, shader]:
        assert all(sha(p) == pin for p, pin in receipt['input_pins'].items())
    sdk = Path(subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip())
    unit = repo / 'userland/metal/image_probe.cpp'
    profile_header = repo / 'graphics/hakios-metal-ca/overlay/userland/src/GauguinMetalProfile.h'
    pins = {str(p): sha(p) for p in [Path(__file__).resolve(), unit, profile_header, core_path, shader_path,
                                     library, metallib, repo / 'tools/build-hakios-metal.py', sdk / 'SDKSettings.json']}
    pins.update(core['input_pins'])
    pins.update(shader['input_pins'])
    tag = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:24]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    data = metallib.read_bytes()
    header = out / 'graphics_images_bytes.h'
    rows = [','.join('0x%02x' % b for b in data[i:i+24]) for i in range(0, len(data), 24)]
    header.write_text('static const unsigned char kGauguinImageLibrary[] = {\n' + ',\n'.join(rows) + '\n};\n'
                      + 'static const char kGauguinImageLibrarySHA256[] = "' + shader['library_sha256'] + '";\n')
    pins[str(header)] = sha(header)
    binary = out / 'gauguin-image-probe'

    def run(argv, name):
        with (out / name).open('x') as log:
            subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT)

    argv = ['xcrun', '--sdk', 'iphoneos', 'clang++', '-target', 'arm64-apple-ios16.0', '-isysroot', str(sdk),
            '-std=c++17', '-O2', '-fno-fast-math', '-Wall', '-Wextra', '-Werror', '-DHAKIOS_METAL_TARGET_A619',
            '-DGAUGUIN_IMAGE_PROBE_BUILD="' + tag + '"', '-DGAUGUIN_IMAGE_CORE_SHA256="' + core['sha256'] + '"',
            '-I' + str(source / 'include'), '-I' + str(profile_header.parent), '-I' + str(out),
            str(unit), str(library), '-Wl,-rpath,/usr/local/lib/gauguin', '-o', str(binary)]
    run(argv, 'compile-link.log')
    spec = importlib.util.spec_from_file_location('core_build', repo / 'tools/build-hakios-metal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    platform = helper.ios_version(binary)
    run(['codesign', '--force', '--sign', '-', str(binary)], 'sign.log')
    run(['codesign', '--verify', '--strict', str(binary)], 'verify.log')
    run(['otool', '-L', str(binary)], 'loads.log')
    run(['nm', '-m', '-u', str(binary)], 'imports.log')
    assert '@rpath/libGauguinMetalCore.dylib' in (out / 'loads.log').read_text()
    assert all(sha(p) == pin for p, pin in pins.items())
    result = dict(state='native-iOS16-bounded-graphics-image-probe-not-runtime-qualified', probe=str(binary),
                  bytes=binary.stat().st_size, sha256=sha(binary), build=tag, core_sha256=core['sha256'],
                  shader_sha256=shader['library_sha256'], platform_version=platform, expected_jobs=9,
                  expected_draws=27, expected_raw_pixels=73728, expected_pixel_checks=110592,
                  input_pins=pins, inputs_unchanged=True, compiler_argv=argv, device_commands=0,
                  installed=False, runtime_qualified=False, desktop_qualified=False)
    with (out / 'result.json').open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['input_pins', 'compiler_argv']}, indent=2))


if __name__ == '__main__':
    main()
