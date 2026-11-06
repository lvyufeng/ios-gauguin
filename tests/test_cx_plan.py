#!/usr/bin/env python3
"""Actual fixed CX policy/parser with synthetic binary CMDDB and sanitizers."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
DEV=Path(os.environ.get('XNU_SOURCE',str(HERE.parent/'.deps-cache/p0-20261105/source118-codex')))/'bsd/dev'
flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
with tempfile.TemporaryDirectory(prefix='gauguin-cx-plan-') as temporary:
    binary=Path(temporary)/'test'
    subprocess.run(['clang',*flags,'-I'+str(DEV),str(HERE/'fixtures/gauguin_cx_plan_host.c'),
                    str(DEV/'gauguin_cx_rail_plan.c'),str(DEV/'cmd_db_snapshot.c'),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
