#!/usr/bin/env python3
"""Parse SWEET mark blocks: the 64 x 4 KiB blocks below the log ring.

  python3 tools/sweet-marks.py IMAGE.bin [-v]

`IMAGE.bin` is the raw 64-block dump that tools/sweet-mark-pull.sh takes from
the phone. Split out of the shell script so it can be tested
(tests/test_marks.py) - the shell used to guess at two things it should not
have had to guess at:

  * the number of ring blocks was hard-coded to 1025 (= 4 MiB ring + 1 header
    block). If the kernel changes SWEET_LOG_SIZE the offset moves and the tool
    would silently read the wrong place and report "no marks".
  * a block that starts with "MARK " but is not well formed made
    `line.split(" ")[1]` / `int(seq)` raise, killing the whole run.

The block geometry below is checked against bsd/dev/sweet_ufs.c by
tests/test_marks.py, which reads the constants out of the source.
"""
import re
import sys

BLOCK = 4096
MARK_PREFIX = b"MARK "


def parse_marks(data):
    """Return [(seq, line)] sorted by seq. Malformed blocks are skipped."""
    seen = []
    for n in range(len(data) // BLOCK):
        blk = data[n * BLOCK:(n + 1) * BLOCK]
        if not blk.startswith(MARK_PREFIX):
            continue
        try:
            line = blk.split(b"\n", 1)[0].decode("utf-8", "replace")
        except Exception:
            continue
        parts = line.split(" ", 2)      # "MARK" "NNNNN" "text..."
        if len(parts) < 2:
            continue
        try:
            seq = int(parts[1])
        except ValueError:
            continue                    # damaged slot: not a mark we can order
        seen.append((seq, line))
    # Duplicate sequence numbers can only come from a torn write; keep the
    # first (lowest offset) so the ordering stays stable.
    out, used = [], set()
    for seq, line in sorted(seen):
        if seq in used:
            continue
        used.add(seq)
        out.append((seq, line))
    return out


def ring_blocks_from_source(path):
    """Read SWEET_LOG_SIZE from sweet_ufs.c and return its size in blocks.

    Returns (log_blocks, mark_blocks) where log_blocks counts the header block
    as well, matching SWEET_LOG_BLOCKS in the driver.
    """
    with open(path, errors="replace") as f:
        src = f.read()
    m = re.search(r"#define\s+SWEET_LOG_SIZE\s+\((\d+)\s*u?\s*<<\s*(\d+)\)", src)
    if not m:
        raise ValueError("SWEET_LOG_SIZE not found in %s" % path)
    size = int(m.group(1)) << int(m.group(2))
    mk = re.search(r"#define\s+SWEET_MARK_BLOCKS\s+(\d+)u?", src)
    if not mk:
        raise ValueError("SWEET_MARK_BLOCKS not found in %s" % path)
    return (1 + size // BLOCK, int(mk.group(1)))


def main(argv):
    if len(argv) >= 2 and argv[1] == "--sizes":
        # Used by tools/sweet-mark-pull.sh so the block geometry is read from
        # the driver source instead of being duplicated as literals.
        src = argv[2] if len(argv) > 2 else ""
        try:
            log_blocks, mark_blocks = ring_blocks_from_source(src)
        except (OSError, ValueError):
            log_blocks, mark_blocks = 1025, 64
        print(f"{log_blocks} {mark_blocks}")
        return 0
    if len(argv) < 2:
        sys.stderr.write("usage: sweet-marks.py IMAGE.bin [-v] | --sizes SRC\n")
        return 2
    with open(argv[1], "rb") as f:
        data = f.read()
    marks = parse_marks(data)
    for _seq, line in marks:
        print(line)
    if not marks:
        print("(no MARK blocks: the kernel did not reach sweet_log_mark)")
        return 1
    if "-v" in argv[2:]:
        print(f"({len(marks)} mark(s) in {len(data) // BLOCK} block(s))", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))