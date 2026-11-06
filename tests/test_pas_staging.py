#!/usr/bin/env python3
"""Actual CPU staging logic with platform seams and inaccessible guard pages.

Only the DSB instruction is replaced; DT, ml_io_map_wcomb, ml_vtophys and the
SHA256 calls are seams in tests/fixtures/gauguin_pas_stage_host.c. The crypto
seam accepts only the exact synthetic6860-byte image; the production pin is
left untouched and is independently checked against the real firmware during
image qualification.
"""
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = Path(os.environ.get('PAS_STAGE_SOURCE', XNU / 'bsd/dev/gauguin_pas_stage.c'))


def main():
    if not SOURCE.is_file():
        if 'XNU_SOURCE' in os.environ or 'PAS_STAGE_SOURCE' in os.environ:
            raise SystemExit(f'PAS staging source missing: {SOURCE}')
        print(f'skip PAS staging: not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    assert not re.search(r'smc #|ml_io_unmap|sweet_spmi|rpmh_write|write32|read32', source)
    assert source.count('ml_io_map_wcomb((vm_offset_t)pa') == 1
    assert not re.search(r'pmap_(enter|remove|protect|map)\b', source)
    assert 'i < PST_PAGE; ++i' in source and 'i < PST_BYTES; ++i' in source
    assert source.count('SHA256_Update(&') == 1
    assert 'SHA256_Update(&ctx, bytes, PST_BYTES);' in source
    barrier = '__asm__ volatile("dsb sy" ::: "memory");'
    assert source.count(barrier) == 1
    source = source.replace(barrier, 'fake_dsb();')
    source = re.sub(r'^#include .*\n', '', source, flags=re.M)
    fixture = (ROOT / 'tests/fixtures/gauguin_pas_stage_host.c').read_text()
    assert fixture.count('@SOURCE@') == 1
    with tempfile.TemporaryDirectory(prefix='pas-staging-') as temporary:
        out = Path(temporary)
        (out / 'test.c').write_text(fixture.replace('@SOURCE@', source))
        subprocess.run(shlex.split(os.environ.get('CC', 'cc')) + [
            '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            str(out / 'test.c'), '-o', str(out / 'test')], check=True, timeout=60)
        subprocess.run([str(out / 'test')], check=True, timeout=30)


if __name__ == '__main__':
    main()