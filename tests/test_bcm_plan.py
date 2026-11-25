#!/usr/bin/env python3
"""Execute the pure CMD DB parser and PLAN ONLY BCM encoder with sanitizers."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', str(ROOT / '.deps-cache/p0-20261105/source113-codex')))
DEV = SOURCE / 'bsd/dev'
CFLAGS = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
          '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g']

with tempfile.TemporaryDirectory(prefix='gauguin-bcm-plan-') as directory:
    for name, sources in (
        ('cmd_db_snapshot', ['cmd_db_snapshot.c']),
        ('gauguin_bcm_plan', ['cmd_db_snapshot.c', 'gauguin_bcm_plan.c']),
    ):
        output = Path(directory) / name
        # The existing planner fixture expands large assertion macro strings.
        flags = ['-Wno-overlength-strings'] if name == 'gauguin_bcm_plan' else []
        subprocess.run(['clang', *CFLAGS, *flags, '-I', str(DEV),
                        str(HERE / 'fixtures' / (name + '_host.c')),
                        *(str(DEV / source) for source in sources), '-o', str(output)], check=True)
        subprocess.run([str(output)], check=True)
print('PASS: pure CMD DB parser and BCM plan; no hardware or submission')
