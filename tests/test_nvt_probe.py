#!/usr/bin/env python3
"""Test the staged GCC/TLMM-only probe through its actual control flow."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
FIXTURE = Path(__file__).resolve().parent / 'fixtures/gauguin_nvt_probe_host.c'


def main():
    path = SOURCE / 'bsd/dev/gauguin_nvt_probe.c'
    if not path.exists():
        if 'XNU_SOURCE' in os.environ:
            raise FileNotFoundError(f'explicit staged source lacks NVT probe: {path}')
        print(f'skip NVT probe test, source not staged at {path}')
        return
    source = path.read_text()
    load = 'uint32_t value = *(volatile uint32_t *)(base + offset);'
    barrier = '__asm__ volatile("dmb oshld" ::: "memory");'
    assert source.count(load) == 1 and source.count(barrier) == 1
    # Mock only the load/barrier and XNU services. The whitelist sees addresses
    # chosen by the actual source's worker, DFS logic and selected-parent path.
    source = source.replace(load, 'uint32_t value = fake_read(base, offset);')
    source = source.replace(barrier, '')
    source = re.sub(r'^#include .*$\n?', '', source, flags=re.MULTILINE)
    assert 'volatile' not in source and '__asm__' not in source
    assert '%p' not in source and 'sweet_hid_' not in source and 'sweet_rpmh_' not in source
    template = FIXTURE.read_text()
    assert template.count('@SOURCE@') == 1
    with tempfile.TemporaryDirectory(prefix='gauguin-nvt-stage0-') as temporary:
        directory = Path(temporary)
        (directory / 'test.c').write_text(template.replace('@SOURCE@', source))
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', '-pedantic', '-fsanitize=address,undefined',
                        '-g', '-O1', str(directory / 'test.c'), '-o', str(directory / 'test')], check=True)
        subprocess.run([str(directory / 'test')], check=True)


if __name__ == '__main__':
    main()
