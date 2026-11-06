#!/usr/bin/env python3
"""Actual shared GCC page owner under CPU/MMIO platform seams and sanitizers."""
from pathlib import Path
import os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source119-codex')))/'bsd/dev'
F=R/'tests/fixtures/gcc-votes'
with tempfile.TemporaryDirectory(prefix='gcc-votes-') as temporary:
    binary=Path(temporary)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                    '-I'+str(F),'-I'+str(D),str(F/'gcc_votes_host.c'),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
