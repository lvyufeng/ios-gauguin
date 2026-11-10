#!/usr/bin/env python3
"""Run the actual gauguin scan sampler with modeled display registers."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve() / "bsd/dev"
    fixture = Path(__file__).resolve().parent / "fixtures/test_scan_timing.c"
    with tempfile.TemporaryDirectory(prefix="gauguin-scan-") as directory:
        work = Path(directory)
        board = work / "pexpert/arm64/board_config.h"
        board.parent.mkdir(parents=True)
        board.write_text("#define GAUGUIN 1\n")
        binary = work / "scan-timing"
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-O1", "-g", "-fsanitize=address,undefined", "-I", str(work),
            "-I", str(source), str(fixture), str(source / "gauguin_scan_timing.c"),
            "-o", str(binary),
        ], check=True, timeout=30)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1:detect_leaks=0",
                   UBSAN_OPTIONS="halt_on_error=1")
        subprocess.run([str(binary)], check=True, timeout=10, env=env)


if __name__ == "__main__":
    main()
