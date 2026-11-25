#!/usr/bin/env python3
"""Independent real UFS completion/sync/stage fixture; no device operations."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))


def main():
    source = (SOURCE / 'bsd/dev/sweet_ufs.c').read_text()
    if 'static bool ufs_poisoned;' not in source:
        if 'XNU_SOURCE' in os.environ:
            raise AssertionError('explicit staged source lacks UFS ownership fix')
        print('skip UFS completion test: default cache lacks new patch')
        return
    def extract(signature):
        begin = source.index(signature)
        return source[begin:source.index('\n}\n', begin) + 3]
    definitions = '\n'.join(re.findall(
        r'^#define (?:REG_\w+|HCS_\w+|CAP_\w+|UFS_SLOT_\w+|DMA_\w+|UFS_BLOCK|'
        r'BOUNCE_SIZE|PRDT_CHUNK|PRDT_MAX|CMD_\w+)\s+[^\n]+', source, re.M))
    for name in ('utrd', 'ucd'):
        begin = source.index('struct ' + name + ' {')
        definitions += '\n' + source[begin:source.index('\n};', begin) + 3]
    helper = extract('static bool ufs_poisoned;')
    functions = '\n'.join(extract(signature) for signature in (
        'static int\nufs_scsi_slot(', 'static int\nsweet_log_sync_cache(void)',
        'void\nsweet_stage(', 'void\nsweet_stage_panic('))
    fixture = (HERE / 'fixtures/ufs_completion_host.c').read_text()
    for name, value in (('@DEFINITIONS@', definitions), ('@HELPER@', helper), ('@FUNCTIONS@', functions)):
        assert fixture.count(name) == 1
        fixture = fixture.replace(name, value)
    with tempfile.TemporaryDirectory(prefix='ufs-completion-') as temporary:
        directory = Path(temporary)
        (directory / 'test.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-O1', '-g', str(directory / 'test.c'),
                        '-o', str(directory / 'test')], check=True)
        subprocess.run([str(directory / 'test')], check=True)


if __name__ == '__main__':
    main()
