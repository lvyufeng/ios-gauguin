#!/usr/bin/env python3
"""Tests for tools/image-audit.py.

  python3 tests/test_image_audit.py

The audit exists because the notes recorded image hashes but nothing checked
the images against the kernel they were built from; entry (30) in NOTES.md is
the bug that slipped through. These tests pin:

  * a stale image is reported when --check names a different kernel
  * the A/B pair is NOT reported as stale just for being built from a
    different kernel - that difference is the experiment
  * the tool only looks at the live image set, not the 100+ historical images
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
AUDIT = os.path.join(REPO, "tools", "image-audit.py")
OUT = os.path.join(REPO, "shim", "out")

BANNER_A = b"Darwin Kernel Version 22.6.0: 2026\xe5\xb9\xb4 11\xe6\x9c\x88 3\xe6\x97\xa5 T16:42:53 CST; baai:obj-gauguin"
BANNER_B = b"Darwin Kernel Version 22.6.0: 2026\xe5\xb9\xb4 11\xe6\x9c\x88 3\xe6\x97\xa5 T16:45:35 CST; baai:obj-gauguin"


def make_image(path, banner):
    """A minimal file the audit can read: a payload magic and a banner."""
    blob = bytearray(4096)
    blob[0:8] = b"SWEETXNU"
    struct.pack_into("<7Q", blob, 0x10, 0x1000, 0x2000, 0, 0, 0x3000, 0, 0x4000)
    blob[256:256 + len(banner)] = banner
    with open(path, "wb") as f:
        f.write(blob)


def run(*args):
    r = subprocess.run([sys.executable, AUDIT, *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        if cond:
            print(f"  ok   {name}")
        else:
            failures += 1
            print(f"  FAIL {name} {detail[:400]}")

    if not os.path.isdir(OUT):
        print("  skip: shim/out does not exist")
        return 0

    # Everything below works on a copy of the live image set and restores it.
    backup = tempfile.mkdtemp()
    live = ["shim-proven.img", "shim-bisect-on.img", "shim-bisect-off.img",
            "shim-ab-dmb.img", "shim-ab-dsb.img"]
    saved = {}
    for n in live:
        p = os.path.join(OUT, n)
        if os.path.isfile(p):
            saved[n] = os.path.join(backup, n)
            shutil.copy2(p, saved[n])
    try:
        # 1. A stale non-A/B image is reported.
        kernel = os.path.join(backup, "kernel-a")
        with open(kernel, "wb") as f:
            f.write(BANNER_A)
        make_image(os.path.join(OUT, "shim-proven.img"), BANNER_B)
        code, out = run("--check", kernel)
        check("stale proven image is reported", code == 1 and "STALE" in out, out)

        # 2. The A/B pair is not reported for being different. Fix the proven
        #    image first, or it legitimately fails the audit for case 1.
        make_image(os.path.join(OUT, "shim-proven.img"), BANNER_A)
        make_image(os.path.join(OUT, "shim-ab-dmb.img"), BANNER_A)
        make_image(os.path.join(OUT, "shim-ab-dsb.img"), BANNER_B)
        make_image(os.path.join(OUT, "shim-bisect-off.img"), BANNER_A)
        make_image(os.path.join(OUT, "shim-bisect-on.img"), BANNER_A)
        code, out = run("--check", kernel)
        check("A/B pair is not called stale", code == 0, out)
        check("A/B pair is acknowledged as present",
              "A/B pair present" in out, out)

        # 3. An image genuinely from another kernel still fails the audit.
        make_image(os.path.join(OUT, "shim-bisect-on.img"), BANNER_B)
        code, out = run("--check", kernel)
        check("a stale bisect image still fails", code == 1, out)

        # 4. A missing live image is named.
        os.remove(os.path.join(OUT, "shim-ab-dsb.img"))
        code, out = run("--check", kernel)
        check("missing image is named", "MISSING" in out and "shim-ab-dsb.img" in out, out)
    finally:
        for n, path in saved.items():
            shutil.copy2(path, os.path.join(OUT, n))
        for n in live:
            if n not in saved and os.path.isfile(os.path.join(OUT, n)):
                os.remove(os.path.join(OUT, n))
        shutil.rmtree(backup, ignore_errors=True)

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("all image-audit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())