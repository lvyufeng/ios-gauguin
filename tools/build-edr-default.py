#!/usr/bin/env python3
"""Reproduce the installed launcher, then add the scoped optional-EDR fallback."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
ORIGINAL = MAIN/'research/tmp/dsh-ui-0195-bridge/bridge-v1/result.json'
ORIGINAL_SHA = 'a1b98155d1e01b17d50a6bd733dbf560ce21a74572758d8ae97c52a4174d3562'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    prior = json.loads(ORIGINAL.read_text())
    argv = next(row['argv'] for row in prior['results'] if row['name'] == 'admission-link')
    old_sources = [Path(s) for s in argv if s.endswith('.c')]
    assert len(old_sources) == 2
    expected = ['aa4e8da8a18e174e698ffe19258381d6ec210b1da6a9a2c23f4b19668814e958',
                '47745942403d38014191c978327cb72861f446a9e98f13591ae8eae471ebb7e7']
    assert [sha(p) for p in old_sources] == expected
    old_binary = Path(argv[argv.index('-o') + 1])
    assert sha(old_binary) == ORIGINAL_SHA
    sources = WORK/'graphics/gauguin-edr-default'
    files = [sources/n for n in ('EDRDefault.c', 'EDRDefaultCore.h', 'EDRDefaultContract.h')]
    pins = {str(p): sha(p) for p in [Path(__file__).resolve(), ORIGINAL, old_binary,
                                    *old_sources, *files, Path(prior['sdk'])/'SDKSettings.json']}
    out.mkdir(parents=True)
    (out/'sources').mkdir()
    for path in files:
        (out/'sources'/path.name).write_bytes(path.read_bytes())
    steps = []
    result = dict(state='native-EDR320-build-started', input_pins=pins, steps=steps,
                  sdk=prior['sdk'], device_commands=0, runtime_qualified=False)

    def run(command, label):
        with (out/(label+'.log')).open('x') as stream:
            proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        steps.append(dict(label=label, argv=command, exit=proc.returncode))
        assert proc.returncode == 0, label

    try:
        products = {}
        for variant in ('baseline', 'candidate'):
            folder = out/variant
            folder.mkdir()
            binary = folder/'libGauguinEAGLAdmission.dylib'
            command = list(argv)
            command[command.index('-o') + 1] = str(binary)
            if variant == 'candidate':
                command[command.index('-o'):command.index('-o')] = [
                    '-fblocks', str(out/'sources/EDRDefault.c')]
            run(command, variant+'-compile')
            run(['/usr/bin/codesign', '--force', '--sign', '-', str(binary)], variant+'-sign')
            run(['/usr/bin/codesign', '--verify', '--strict', str(binary)], variant+'-verify')
            run(['/usr/bin/otool', '-L', str(binary)], variant+'-loads')
            run(['/usr/bin/nm', '-m', '-u', str(binary)], variant+'-imports')
            raw = binary.read_bytes()
            header = struct.unpack_from('<8I', raw)
            assert header[:2] == (0xfeedfacf, 0x100000c) and header[3] == 6
            cursor = 32
            platforms = []
            for _ in range(header[4]):
                kind, size = struct.unpack_from('<II', raw, cursor)
                assert size >= 8 and cursor + size <= 32 + header[5]
                if kind == 0x32:
                    platforms.append(struct.unpack_from('<III', raw, cursor+8))
                cursor += size
            assert cursor == 32 + header[5] and len(platforms) == 1
            assert platforms[0][0] == 2 and platforms[0][1] == 0x100000
            products[variant] = dict(binary=str(binary), bytes=len(raw), sha256=sha(binary),
                                     platform=platforms[0])
            if variant == 'baseline':
                assert products[variant]['sha256'] == ORIGINAL_SHA, 'installed baseline reproduction differs'
            else:
                assert len(raw) <= 18*4096, 'candidate exceeds existing launcher allocation'
        result.update(state='native-EDR320-launcher-baseline-reproduced-candidate-signed',
                      products=products, installed=False, existing_allocation_bytes=18*4096,
                      private_data_pointer_bytes=8, Apple_code_writes=0)
    except Exception as error:
        result.update(state='native-EDR320-build-failed', error=repr(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(p) == digest for p, digest in pins.items())
        with (out/'result.json').open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
