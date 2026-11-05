#!/usr/bin/env python3
"""Stage the SDK header used by the verified kernel sources.

  xnu-stage-sdk.py XNU_ROOT [--header FILE] [--cache DIRECTORY]

The Apple header stays outside git. An explicit file must match the recorded
digest. Otherwise the immutable SDK mirror is fetched into the ignored cache.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request


REPO = Path(__file__).resolve().parent.parent
HEADER_SHA256 = 'f71d1296dc2c1f2875baa461ef38122d248b23aca5933abefe3791cee8ffb2dd'
HEADER_URL = (
    'https://raw.githubusercontent.com/phracker/MacOSX-SDKs/'
    '041600eda65c6a668f66cb7d56b7d1da3e8bcc93/'
    'MacOSX11.3.sdk/usr/include/TargetConditionals.h'
)
TARGETS = (
    'bsd/pthread/sweet_libpthread/TargetConditionals.h',
    'bsd/sweet_hfs/TargetConditionals.h',
)


def verify_header(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != HEADER_SHA256:
        raise ValueError(f'{path}: SHA256 {digest}, expected {HEADER_SHA256}')


def cached_header(cache):
    path = cache / 'TargetConditionals.h'
    if path.exists():
        verify_header(path)
        return path
    cache.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with urllib.request.urlopen(HEADER_URL, timeout=30) as response:
            data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError('SDK header response exceeds 1 MiB')
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
        verify_header(temporary)
        temporary.replace(path)
        return path
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def stage(root, header=None, cache=REPO / '.deps-cache/sdk-inputs'):
    root = root.resolve()
    if not (root / 'bsd/conf/files').is_file():
        raise ValueError(f'{root}: not an XNU source tree')
    targets = [root / name for name in TARGETS]
    for target in targets:
        if target.is_symlink() or not target.parent.is_dir():
            raise ValueError(f'{target}: stage the dependency mirror first')
    source = header if header is not None else cached_header(cache)
    verify_header(source)
    data = source.read_bytes()
    for target in targets:
        if not target.exists() or target.read_bytes() != data:
            shutil.copyfile(source, target)
    print(f'SDK TargetConditionals.h verified ({HEADER_SHA256})')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--header', type=Path,
                        default=os.environ.get('XNU_TARGET_CONDITIONALS'))
    parser.add_argument('--cache', type=Path, default=REPO / '.deps-cache/sdk-inputs')
    args = parser.parse_args()
    try:
        stage(args.root, args.header, args.cache)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
