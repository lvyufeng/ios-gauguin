#!/usr/bin/env python3
"""Exercise the XNU reader on an ADT produced by the actual loader helpers."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--fdt", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    dev = args.source.resolve() / "bsd/dev"
    shim = root / "shim"
    with tempfile.TemporaryDirectory(prefix="gauguin-handoff-memory-") as directory:
        out = Path(directory)
        config = out / "pexpert/arm64/board_config.h"
        config.parent.mkdir(parents=True)
        config.write_text("#define GAUGUIN 1\n")
        binary = out / "consumer"
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c11", "-D_DARWIN_C_SOURCE",
            "-Wall", "-Wextra", "-Werror", "-O1", "-g", "-fsanitize=address,undefined",
            "-I", str(out), "-I", str(dev), "-I", str(shim),
            str(root / "tests/fixtures/test_handoff_memory.c"),
            str(dev / "gauguin_handoff_memory.c"), str(shim / "pas_reservation.c"),
            "-o", str(binary),
        ], check=True, timeout=30)
        subprocess.run([str(binary), str(args.payload), str(args.fdt)], check=True, timeout=15,
                       env=dict(os.environ, ASAN_OPTIONS="halt_on_error=1:detect_leaks=0",
                                UBSAN_OPTIONS="halt_on_error=1"))


if __name__ == "__main__":
    main()
