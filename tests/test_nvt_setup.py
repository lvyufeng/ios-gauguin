#!/usr/bin/env python3
"""Actual native SPI setup/restore, lease loss and transport compatibility gates."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
MODULE = Path(os.environ.get('NVT_MODULE_ROOT', XNU / 'bsd/dev/gauguin_nvt')).resolve()
FIXTURE = ROOT / 'tests/fixtures/gauguin_nvt/setup/test_geni_spi_setup.c'


def main():
    required = ['setup/geni_spi_setup.c', 'setup/geni_spi_setup.h',
                'geni_spi_pio.c', 'geni_spi_pio.h']
    missing = [MODULE / name for name in required if not (MODULE / name).is_file()]
    if missing:
        if 'XNU_SOURCE' in os.environ or 'NVT_MODULE_ROOT' in os.environ:
            raise SystemExit(f'NVT setup inputs missing: {missing}')
        print(f'skip NVT setup: module not staged at {MODULE}')
        return
    with tempfile.TemporaryDirectory(prefix='gauguin-nvt-setup-') as temporary:
        output = Path(temporary) / 'test'
        subprocess.run(shlex.split(os.environ.get('CC', 'cc')) + [
            '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I', str(MODULE), '-I', str(MODULE / 'setup'),
            str(MODULE / 'setup/geni_spi_setup.c'), str(FIXTURE), '-o', str(output)
        ], check=True, cwd=temporary, timeout=60)
        subprocess.run([str(output)], check=True, cwd=temporary, timeout=30)


if __name__ == '__main__':
    main()
