#!/usr/bin/env python3
"""Actual board adapter control flow with kernel/MMIO boundary mocks only."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source119-codex'))
MODULE = Path(os.environ.get('NVT_MODULE_ROOT', XNU / 'bsd/dev/gauguin_nvt')).resolve()
FIXTURES = ROOT / 'tests/fixtures/gauguin_nvt/kernel-bus'


def main():
    required = ['kernel-bus/nvt_kernel_bus.c', 'kernel-bus/nvt_kernel_bus.h',
                'setup/geni_spi_setup.c', 'setup/geni_spi_setup.h',
                'geni_spi_pio.c', 'geni_spi_pio.h']
    missing = [MODULE / name for name in required if not (MODULE / name).is_file()]
    if missing:
        if 'XNU_SOURCE' in os.environ or 'NVT_MODULE_ROOT' in os.environ:
            raise SystemExit(f'NVT bus inputs missing: {missing}')
        print(f'skip NVT bus: module not staged at {MODULE}')
        return
    with tempfile.TemporaryDirectory(prefix='gauguin-nvt-bus-') as temporary:
        output = Path(temporary) / 'test'
        subprocess.run(shlex.split(os.environ.get('CC', 'cc')) + [
            '-std=c11', '-Wall', '-Wextra', '-Werror', '-g',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I', str(FIXTURES), '-I', str(MODULE.parent), '-I', str(MODULE), '-I', str(MODULE / 'kernel-bus'),
            # Force the tracked boundary first, even when NVT_MODULE_ROOT
            # points to a research candidate containing its original test shim.
            '-include', str(FIXTURES / 'test_kernel_shim.h'),
            str(FIXTURES / 'test_nvt_kernel_bus.c'),
            str(MODULE / 'setup/geni_spi_setup.c'), str(MODULE / 'geni_spi_pio.c'),
            '-o', str(output)
        ], check=True, cwd=temporary, timeout=60)
        subprocess.run([str(output)], check=True, cwd=temporary, timeout=30)


if __name__ == '__main__':
    main()
