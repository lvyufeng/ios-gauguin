#!/usr/bin/env python3
"""Compile the actual NVT protocol with malformed-frame/state-preservation tests."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
MODULE = Path(os.environ.get('NVT_MODULE_ROOT', XNU / 'bsd/dev/gauguin_nvt')).resolve()
FIXTURE = ROOT / 'tests/fixtures/gauguin_nvt/test_nvt_protocol.c'


def main():
    source = MODULE / 'nvt_protocol.c'
    missing = [p for p in (source, MODULE / 'nvt_protocol.h') if not p.is_file()]
    if missing:
        if 'XNU_SOURCE' in os.environ or 'NVT_MODULE_ROOT' in os.environ:
            raise SystemExit(f'NVT protocol inputs missing: {missing}')
        print(f'skip NVT protocol: module not staged at {MODULE}')
        return
    with tempfile.TemporaryDirectory(prefix='gauguin-nvt-protocol-') as temporary:
        binary = Path(temporary) / 'test'
        subprocess.run(shlex.split(os.environ.get('CC', 'cc')) + [
            '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I', str(MODULE), str(source), str(FIXTURE), '-o', str(binary)
        ], check=True, cwd=temporary, timeout=60)
        subprocess.run([str(binary)], check=True, cwd=temporary, timeout=30)


if __name__ == '__main__':
    main()
