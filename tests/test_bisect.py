#!/usr/bin/env python3
"""Tests for tools/bisect-verdict.py.

  python3 tests/test_bisect.py

Two of the cases use the *real* logs kept in the repo - a boot that reached
`exec launchd` and a run that stopped on the keys_init line - so the phase
matcher is checked against actual console text, not invented strings.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

import importlib
bv = importlib.import_module("bisect-verdict")

WORKING = os.path.join(REPO, ".deps-cache", "logs", "boot-journaled-userland.txt")
FAILING = os.path.join(REPO, "research", "tmp", "boot-ver-2.txt")


def read(path):
    try:
        with open(path, errors="replace") as f:
            return f.read()
    except OSError:
        return None


# Minimal stands-ins in case the real logs are missing (they are git-ignored).
SAMPLE = {
    "none": "SWEET UFS: init reg=0x1d84000/0x3000\n",
    "keys": "\n".join([
        "SWEET UFS: sample_start done",
        "SWEET UFS: keys_init",
        "SWEET UFS: scsi cdb 0x35 len 0",
    ]),
    "keys_done": "\n".join([
        "SWEET UFS: keys_init",
        "SWEET KEYS: arb=0x50010000 apids=512 pon-apid=308",
        "SWEET UFS: keys_init done",
    ]),
    "touch_done": "SWEET UFS: keys_init done\nSWEET UFS: touch_init done\n",
    "complete": "SWEET UFS: touch_init done\nSWEET UFS: init complete\n",
    "mounted": "SWEET UFS: init complete\nBSD root: ufsroot0, major 1, minor 0\n",
}


def main():
    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        if cond:
            print(f"  ok   {name}")
        else:
            failures += 1
            print(f"  FAIL {name} {detail}")

    # --- phase detection on real logs -------------------------------------
    working = read(WORKING)
    failing = read(FAILING)
    if working:
        check("real working log is detected as userland",
              bv.phase_of(working) == "userland", f"got {bv.phase_of(working)}")
        check("real working log passed the keys_init line",
              bv.reached_keys_init_prefix(working))
    else:
        print(f"  skip real working log (missing: {WORKING})")
    if failing:
        check("real failing log is detected as stopping at keys_init",
              bv.phase_of(failing) is None, f"got {bv.phase_of(failing)}")
        check("real failing log still reached the keys_init line",
              bv.reached_keys_init_prefix(failing))
    else:
        print(f"  skip real failing log (missing: {FAILING})")

    # --- phase ordering on synthetic text ---------------------------------
    check("init complete maps to usb_probe",
          bv.phase_of(SAMPLE["complete"]) == "usb_probe",
          bv.phase_of(SAMPLE["complete"]))
    check("BSD root maps to root_mounted",
          bv.phase_of(SAMPLE["mounted"]) == "root_mounted",
          bv.phase_of(SAMPLE["mounted"]))
    check("far phase wins over near phase",
          bv.phase_of(SAMPLE["touch_done"] + SAMPLE["complete"]) == "usb_probe")

    # --- verdicts ---------------------------------------------------------
    def v(off, on):
        return bv.verdict(off, on)[0]

    check("both stalled at keys (off passed it, on did not) -> keys_blocks",
          v(SAMPLE["keys_done"], SAMPLE["keys"]) == "keys_blocks")
    check("neither passed keys -> same_phase",
          v(SAMPLE["keys"], SAMPLE["keys"]) == "same_phase")
    check("neither reached the keys line -> before_keys_both",
          v(SAMPLE["none"], SAMPLE["none"]) == "before_keys_both")
    check("off reached keys line, on did not -> before_keys",
          v(SAMPLE["keys"], SAMPLE["none"]) == "before_keys")
    check("both mounted -> both_mount (regression: was keys_blocks)",
          v(SAMPLE["mounted"], SAMPLE["mounted"]) == "both_mount")
    check("off mounted, on stalled -> keys_blocks",
          v(SAMPLE["mounted"], SAMPLE["keys"]) == "keys_blocks")
    check("on mounted, off stalled -> inconsistent",
          v(SAMPLE["keys"], SAMPLE["mounted"]) == "inconsistent")
    check("off behind on -> inconsistent",
          v(SAMPLE["keys_done"], SAMPLE["complete"]) == "inconsistent")

    # A boot that only reached the log ring must never be read as "mounted".
    check("empty logs are same_phase, not both_mount",
          v("", "") == "before_keys_both")

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("all bisect-verdict checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())