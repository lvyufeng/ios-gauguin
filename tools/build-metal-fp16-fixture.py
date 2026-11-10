#!/usr/bin/env python3
"""Compile only the project's own native FP16 shaders; no device access."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--platform', choices=['ios', 'macos'], default='ios')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    source = repo / 'userland/metal/native_fp16.metal'
    sdk_name = 'iphoneos' if args.platform == 'ios' else 'macosx'
    target = 'air64-apple-ios16.0' if args.platform == 'ios' else 'air64-apple-macos13.0'
    standard = 'ios-metal2.4' if args.platform == 'ios' else 'macos-metal2.4'
    sdk = Path(subprocess.check_output(['xcrun', '--sdk', sdk_name, '--show-sdk-path'], text=True).strip())
    pins = {str(p): sha(p) for p in [Path(__file__).resolve(), source, sdk / 'SDKSettings.json']}
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    air, library = out / 'native_fp16.air', out / 'native_fp16.metallib'
    compile_argv = ['xcrun', '--sdk', sdk_name, 'metal', '-target', target, '-std=' + standard,
                    '-O1', '-fno-fast-math', '-Wall', '-Wextra', '-Werror', '-c', str(source), '-o', str(air)]
    link_argv = ['xcrun', '--sdk', sdk_name, 'metallib', str(air), '-o', str(library)]
    for argv, name in [(compile_argv, 'compile.log'), (link_argv, 'link.log')]:
        with (out / name).open('x') as log:
            subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT)
    assert 88 < library.stat().st_size < 1048576
    assert all(sha(Path(p)) == pin for p, pin in pins.items())
    result = dict(state='generated-own-native-FP16-Metal2.4-library-not-runtime-qualified',
                  platform=args.platform, library=str(library), library_bytes=library.stat().st_size,
                  library_sha256=sha(library), air_sha256=sha(air), input_pins=pins, inputs_unchanged=True,
                  compile_argv=compile_argv, link_argv=link_argv, device_commands=0, hardware_qualified=False)
    with (out / 'result.json').open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['input_pins', 'compile_argv', 'link_argv']}, indent=2))


if __name__ == '__main__':
    main()
