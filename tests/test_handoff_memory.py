#!/usr/bin/env python3
"""Exercise the XNU reader on an ADT produced by the actual loader helpers."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import tempfile


def check_receipt(root, record, expected_hash):
    spec = importlib.util.spec_from_file_location("handoff_reader", root / "tools/gauguin-read-memory-handoff.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    receipt = bytearray(record)
    size, = struct.unpack_from("<I", receipt, 8)

    def seal(raw):
        length, = struct.unpack_from("<I", raw, 8)
        raw[length - 32:length] = hashlib.sha256(raw[:length - 32]).digest()
        return bytes(raw)

    accepted = reader.read_receipt(seal(receipt), 266001)
    assert accepted["status"] == "complete" and accepted["fdt_sha256"] == expected_hash
    assert len(accepted["memory_banks"]) == 3 and len(accepted["fixed_reservations"]) == 21
    pools = accepted["unresolved_dynamic_pools"]
    assert len(pools) == 6 and all(pool["allocation_windows"] == [{"base": 0, "bytes": 0xffffffff}]
                                   for pool in pools)
    failure = bytearray(reader.BLOCK)
    failure[:8] = b"GAUHRAM1"
    struct.pack_into("<III", failure, 8, reader.HEADER + reader.DIGEST, 266001, 7)
    assert reader.read_receipt(seal(failure), 266001) == {"run_id": 266001, "status": "receipt-overflow"}

    correct = seal(receipt)
    damaged = bytearray(correct)
    damaged[size - 1] ^= 1
    invalid_pool = bytearray(correct)
    pool_offset = reader.HEADER + 16 * (8 + 3) + reader.NAMED * 21
    struct.pack_into("<I", invalid_pool, pool_offset + 8, 2)
    invalid_name = bytearray(correct)
    invalid_name[reader.HEADER + 16 * (8 + 3 + 1)] = 0x0a
    for raw, run in ((correct, 266002), (correct[:-1], 266001),
                     (correct[:-1] + b"\x01", 266001), (damaged, 266001),
                     (seal(invalid_pool), 266001), (seal(invalid_name), 266001)):
        try:
            reader.read_receipt(raw, run)
        except ValueError:
            continue
        raise AssertionError("invalid handoff receipt accepted")
    print("C encoder round trip and six invalid block variants passed.")


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
        fdt_hash = hashlib.sha256(args.fdt.read_bytes()).hexdigest()
        record = out / "receipt.bin"
        subprocess.run([str(binary), str(args.payload), str(args.fdt), fdt_hash, str(record)], check=True, timeout=15,
                       env=dict(os.environ, ASAN_OPTIONS="halt_on_error=1:detect_leaks=0",
                                UBSAN_OPTIONS="halt_on_error=1"))
        check_receipt(root, record.read_bytes(), fdt_hash)


if __name__ == "__main__":
    main()
