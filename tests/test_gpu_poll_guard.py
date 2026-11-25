#!/usr/bin/env python3
"""Execute the patched native runtime model and bound its full guard calls."""
from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
if "GPU_USER_SOURCE" in os.environ:
    source = Path(os.environ["GPU_USER_SOURCE"])
elif "XNU_SOURCE" in os.environ:
    source = Path(os.environ["XNU_SOURCE"]) / "bsd/dev"
else:
    source = ROOT / ".deps-cache/p0-20261105/source298-build/bsd/dev"

result = subprocess.run([sys.executable, str(ROOT / "tests/test_gpu_user.py")],
                        env={**os.environ, "GPU_USER_SOURCE": str(source)},
                        check=True, capture_output=True, text=True)
match = re.search(r"healthy calls for two IBs fallback=(\d+) span=(\d+)", result.stdout)
assert match, result.stdout
fallback, span = map(int, match.groups())
assert fallback <= 91 and span <= 31 and span < fallback, (fallback, span)
print(f"PASS: bounded full hardware guards fallback={fallback} span={span}; production span path exercised")
