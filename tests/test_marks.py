#!/usr/bin/env python3
"""Tests for tools/sweet-marks.py.

  python3 tests/test_marks.py

Also cross-checks the block geometry against the driver source, so a change to
SWEET_LOG_SIZE or SWEET_MARK_BLOCKS cannot silently move the offset that
sweet-mark-pull.sh uses.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

import importlib
sm = importlib.import_module("sweet-marks")

XNU_SOURCE = os.environ.get("XNU_SOURCE", os.path.join(REPO, ".deps-cache", "xnu-patched-0082-2"))
UFS_C = os.path.join(XNU_SOURCE, "bsd", "dev", "sweet_ufs.c")
PULL = os.path.join(REPO, "tools", "sweet-mark-pull.sh")


def blk(text):
    b = bytearray(sm.BLOCK)
    enc = text.encode() if isinstance(text, str) else text
    b[:len(enc)] = enc
    return bytes(b)


def main():
    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        if cond:
            print(f"  ok   {name}")
        else:
            failures += 1
            print(f"  FAIL {name} {detail}")

    # --- parsing ----------------------------------------------------------
    data = (blk("MARK 00001 KEYS: mmio mapped\n") +
            blk("MARK 00002 KEYS: core read ok\n") +
            blk(""))                                     # empty slot
    marks = sm.parse_marks(data)
    check("reads two marks", [s for s, _ in marks] == [1, 2], marks)
    check("keeps the whole line", marks[0][1] == "MARK 00001 KEYS: mmio mapped",
          marks[0][1])

    # out-of-order slots are sorted by sequence number
    data = blk("MARK 00007 later\n") + blk("MARK 00003 earlier\n")
    check("sorts by sequence", [s for s, _ in sm.parse_marks(data)] == [3, 7])

    # a slot with no sequence number must be skipped, not raise
    data = blk("MARK\n") + blk("MARK notanumber text\n") + blk("MARK 00004 ok\n")
    marks = sm.parse_marks(data)
    check("malformed blocks are skipped", [s for s, _ in marks] == [4], marks)

    # a block that merely starts with MARK but has garbage bytes must not crash
    data = b"MARK " + b"\xff\xfe\x00 garbage\n" + bytes(sm.BLOCK - 20)
    try:
        sm.parse_marks(data)
        ok = True
    except Exception as e:                              # noqa: BLE001
        ok = False
        detail = repr(e)
    check("garbage after MARK does not crash", ok, detail if not ok else "")

    # duplicate sequence (torn write) keeps one entry
    data = blk("MARK 00005 a\n") + blk("MARK 00005 b\n")
    marks = sm.parse_marks(data)
    check("duplicate sequence is deduplicated", len(marks) == 1, marks)

    # a dump that is not a multiple of the block size is truncated, not fatal
    data = blk("MARK 00009 x\n") + b"\x00" * 100
    check("partial trailing block is ignored",
          [s for s, _ in sm.parse_marks(data)] == [9])

    # --- geometry against the driver --------------------------------------
    if os.path.exists(UFS_C):
        log_blocks, mark_blocks = sm.ring_blocks_from_source(UFS_C)
        check("SWEET_LOG_SIZE is 4 MiB -> 1025 blocks incl. header",
              log_blocks == 1025, log_blocks)
        check("SWEET_MARK_BLOCKS is 64", mark_blocks == 64, mark_blocks)
        # the puller's skip must use these numbers, not literals
        with open(PULL, errors="replace") as f:
            pull = f.read()
        # The puller must ASK for the sizes rather than repeat them as
        # literals - a literal here would silently move the offset if the
        # driver's constants changed (NOTES 2026-11-03 (23)).
        check("puller asks the parser for the block sizes",
              "sweet-marks.py" in pull and "--sizes" in pull,
              pull[pull.find("sizes="):pull.find("sizes=") + 80])
        check("puller does not hard-code the mark offset",
              not re.search(r"skip=\\$\{\{?\s*\w+\s*/\s*4096\s*-\s*\d+", pull),
              pull[pull.find("skip="):pull.find("skip=") + 80])
    else:
        print(f"  skip geometry check (driver source not staged: {UFS_C})")

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("all mark checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())