#!/usr/bin/env python3
"""Exercise the actual stage0/stage1 candidate, replacing MMIO primitives only."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))


def main():
    path = SOURCE / 'bsd/dev/gauguin_nvt_probe.c'
    if not path.exists():
        if 'XNU_SOURCE' in os.environ:
            raise FileNotFoundError(f'explicit staged source lacks NVT probe: {path}')
        print(f'skip NVT probe test, source not staged at {path}')
        return
    source = path.read_text()
    substitutions = {
        'uint32_t value = *(volatile uint32_t *)(base + offset);':
            'uint32_t value = fake_read(base, offset);',
        '*(volatile uint32_t *)vote = value;': 'fake_write(vote, value);',
        '__asm__ volatile("dmb oshld" ::: "memory");': '',
        '__asm__ volatile("dmb oshst" ::: "memory");': '',
        '__asm__ volatile("dsb osh" ::: "memory");': '',
    }
    for old, new in substitutions.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    source = re.sub(r'^#include .*$\n?', '', source, flags=re.MULTILINE)
    assert 'volatile' not in source and '__asm__' not in source
    assert '%p' not in source and 'sweet_hid_' not in source and 'sweet_rpmh_' not in source
    fixture = (HERE / 'fixtures/gauguin_nvt_probe_host.c').read_text()
    assert fixture.count('@SOURCE@') == 1
    with tempfile.TemporaryDirectory(prefix='gauguin-nvt-stage1-') as temporary:
        directory = Path(temporary)
        (directory / 'test.c').write_text(fixture.replace('@SOURCE@', source))
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', '-pedantic', '-fsanitize=address,undefined',
                        '-g', '-O1', str(directory / 'test.c'), '-o', str(directory / 'test')], check=True)
        subprocess.run([str(directory / 'test')], check=True)


if __name__ == '__main__':
    main()
