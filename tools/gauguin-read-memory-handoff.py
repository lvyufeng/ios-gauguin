#!/usr/bin/env python3
"""Validate a saved 4 KiB Gauguin ABL handoff report."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

BLOCK = 4096
HEADER = 80
DIGEST = 32
NAMED = 80
OWNER_NAMES = ("original_fdt", "input", "shim", "pas", "framebuffer", "loaded_prefix", "adt", "managed")
STATUSES = (
    "complete", "bad-record", "bad-context", "bad-pas", "bad-fdt",
    "unavailable", "allocation-failed", "receipt-overflow",
)


def read_receipt(block, run_id):
    if len(block) != BLOCK or block[:8] != b"GAUHRAM1":
        raise ValueError("invalid memory handoff block")
    size, run, status, banks, reserved, fixed, pools, windows = struct.unpack_from("<8I", block, 8)
    if not 0 < run_id < 1 << 32 or run != run_id:
        raise ValueError("handoff run ID mismatch")
    if not HEADER + DIGEST <= size <= BLOCK or any(block[size:]) or any(block[72:HEADER]):
        raise ValueError("invalid handoff length or padding")
    body = size - DIGEST
    if hashlib.sha256(block[:body]).digest() != block[body:size]:
        raise ValueError("handoff block digest mismatch")
    if status >= len(STATUSES):
        raise ValueError("unknown handoff status")
    result = {"run_id": run, "status": STATUSES[status]}
    if status:
        if body != HEADER or any(block[20:72]):
            raise ValueError("failed handoff contains an inventory")
        return result

    counts = (banks, reserved, fixed, pools, windows)
    limits = (32, 128, 128, 128, 256)
    if not banks or any(count > limit for count, limit in zip(counts, limits, strict=True)):
        raise ValueError("handoff inventory count outside bounds")
    if body != HEADER + 16 * (len(OWNER_NAMES) + banks + reserved + windows) + NAMED * (fixed + pools):
        raise ValueError("handoff inventory length disagrees with counts")
    if not any(block[40:72]):
        raise ValueError("missing original FDT digest")
    pos = HEADER

    def get_range():
        nonlocal pos
        start, count = struct.unpack_from("<QQ", block, pos)
        pos += 16
        if not count or start + count >= 1 << 64:
            raise ValueError("invalid physical range")
        return {"base": start, "bytes": count}

    def get_name():
        nonlocal pos
        raw, separator, pad = block[pos:pos + 64].partition(b"\0")
        pos += 64
        if not separator or any(pad) or not re.fullmatch(rb"[A-Za-z0-9,._+@-]{1,63}", raw):
            raise ValueError("invalid reservation name")
        return raw.decode("ascii")

    owners = {name: get_range() for name in OWNER_NAMES}
    memory_banks = [get_range() for _ in range(banks)]
    header_reserves = [get_range() for _ in range(reserved)]
    fixed_reserves = [{**get_range(), "name": get_name()} for _ in range(fixed)]
    dynamic = []
    next_window = 0
    for _ in range(pools):
        capacity, first, count = struct.unpack_from("<QII", block, pos)
        pos += 16
        if not capacity or first != next_window or count > windows - first:
            raise ValueError("invalid dynamic pool window indices")
        dynamic.append({"name": get_name(), "requested_bytes": capacity, "window_count": count})
        next_window += count
    if next_window != windows:
        raise ValueError("unreferenced dynamic pool windows")
    for pool in dynamic:
        pool["allocation_windows"] = [get_range() for _ in range(pool.pop("window_count"))]
    if pos != body:
        raise ValueError("unexpected end of handoff inventory")
    return {
        **result,
        "fdt_sha256": block[40:72].hex(),
        "owners": owners,
        "memory_banks": memory_banks,
        "header_reservations": header_reserves,
        "fixed_reservations": fixed_reserves,
        "unresolved_dynamic_pools": dynamic,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("block", type=Path)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()
    try:
        with args.block.open("rb") as stream:
            record = read_receipt(stream.read(BLOCK + 1), args.run_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"gauguin handoff: {error}\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
