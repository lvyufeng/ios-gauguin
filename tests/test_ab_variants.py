#!/usr/bin/env python3
"""Check that the two A/B kernels differ only where they should.

  python3 tests/test_ab_variants.py [DMB_KERNEL DSB_KERNEL]

Built by deps/ab-keys-barrier.sh. The point of an A/B run is that ONE thing
differs; if the two kernels differed elsewhere the comparison would say
nothing. This test names every differing region and asserts that the only
instructional difference is the barrier opcode.

Skipped (exit 0) when the kernels have not been built.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DMB = os.path.join(REPO, "research", "k-ab-dmb")
DSB = os.path.join(REPO, "research", "k-ab-dsb")

# dmb osh  = 0xd50333bf -> little endian bf 33 03 d5
# dsb osh  = 0xd503339f -> little endian 9f 33 03 d5
DMB_OSH = bytes.fromhex("bf3303d5")
DSB_OSH = bytes.fromhex("9f3303d5")


def regions(a, b):
    diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    if not diff:
        return []
    out, start, prev = [], diff[0], diff[0]
    for i in diff[1:]:
        if i - prev > 8:
            out.append((start, prev))
            start = i
        prev = i
    out.append((start, prev))
    return out


def is_timestamp_of_build(a, b, s, e):
    """A two-byte numeric field surrounded by identical build-time text."""
    return (e - s == 1 and a[s:e + 1].isdigit() and b[s:e + 1].isdigit()
            and a[s - 8:s] == b[s - 8:s] and a[e + 1:e + 9] == b[e + 1:e + 9])


def main():
    dmb_path = sys.argv[1] if len(sys.argv) > 1 else DMB
    dsb_path = sys.argv[2] if len(sys.argv) > 2 else DSB
    if not (os.path.exists(dmb_path) and os.path.exists(dsb_path)):
        print("  skip: A/B kernels not built (deps/ab-keys-barrier.sh)")
        return 0

    a = open(dmb_path, "rb").read()
    b = open(dsb_path, "rb").read()
    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        if cond:
            print(f"  ok   {name}")
        else:
            failures += 1
            print(f"  FAIL {name} {detail}")

    check("same length", len(a) == len(b), f"{len(a)} vs {len(b)}")

    found_barrier = False
    unexplained = []
    for s, e in regions(a, b):
        seg_a, seg_b = a[s:e + 1], b[s:e + 1]
        # The two opcodes share three of four bytes, so the differing region
        # is the single byte that encodes the instruction. Look at the whole
        # 4-byte word on each side instead of expecting the region to contain it.
        # The encoding is little-endian (bf 33 03 d5) and `bf` is the first
        # differing byte, so the instruction starts at the region's start.
        word_a, word_b = a[s:s + 4], b[s:s + 4]
        if DMB_OSH in word_a and DSB_OSH in word_b:
            found_barrier = True
            print(f"  ok   barrier differs at {s:#x} (dmb osh -> dsb osh)")
            continue
        if (e - s + 1) == 16:
            # LC_UUID / signature hash: expected to differ per build
            print(f"  note 16-byte build identity at {s:#x} (expected)")
            continue
        if is_timestamp_of_build(a, b, s, e):
            print(f"  note build timestamp at {s:#x} (expected)")
            continue
        unexplained.append((s, e))

    check("the barrier opcode actually differs", found_barrier)
    check("no unexplained differences", not unexplained,
          "; ".join(f"{s:#x}..{e:#x}" for s, e in unexplained))

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("A/B kernels differ only in the barrier")
    return 0


if __name__ == "__main__":
    sys.exit(main())