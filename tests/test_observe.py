#!/usr/bin/env python3
"""Guards on the observation scripts themselves.

tools/sweet-observe.sh is how every boot gets measured, so a defect in it is
invisible in exactly the way that matters: it produces numbers that look like
evidence. Two such defects were found on 2026-11-03 - a stale log silently
standing in for a failed pull (round 69), and shim-proven.img carrying a kernel
40 minutes older than the tree (round 68). These checks are cheap source
assertions so neither can come back unnoticed.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OBSERVE = ROOT / "tools" / "sweet-observe.sh"
AUDIT = ROOT / "tools" / "image-audit.py"

checks = []


def check(name, ok, detail=""):
    checks.append((name, ok, detail))


def main():
    text = OBSERVE.read_text()

    # 1. The pull must not be allowed to fail silently over an existing file.
    check("observe removes OUT before pulling",
          "rm -f \"$out\"" in text,
          "a failed pull would otherwise leave the previous log in place")
    check("observe fails when the pull fails",
          re.search(r"if ! sh \"\$here/sweet-log-pull\.sh\" \"\$out\"", text) is not None,
          "the pull used to end in `|| true`")
    check("observe fails on an empty log",
          '[ ! -s "$out" ]' in text)

    # 2. The banner in the log must match the banner inside the image.
    check("observe compares the log banner with the image",
          "banner matches the image" in text and "BANNER MISMATCH" in text,
          "without this a log from another build reads as this run's output")
    check("observe exits non-zero on a banner mismatch",
          re.search(r"BANNER MISMATCH.*?\n(?:.*\n)*?\s*exit 3", text) is not None)
    check("observe still reports progress markers",
          "progress markers" in text)

    # 3. image-audit should keep flagging image/kernel drift.
    audit = AUDIT.read_text()
    check("image-audit reads a kernel banner",
          "Darwin Kernel Version" in audit)

    failed = 0
    for name, ok, detail in checks:
        print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  <- " + detail))
        if not ok:
            failed += 1
    print("\n%d checks, %d failed" % (len(checks), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())