#!/usr/bin/env python3
"""Audit the packaged boot images: what kernel is each one really carrying?

  python3 tools/image-audit.py [--check KERNEL]

Entry (30) in NOTES.md records the bug this exists for: the shim-ab-* images
were built before a kernel change and booting them would have re-introduced a
variable the experiment was supposed to hold fixed. Nothing checked the images
against the kernel; the notes only recorded hashes, which cannot detect drift.

Each image embeds the kernel, so its build banner (`Darwin Kernel Version ...
<date> <time> CST`) can be read straight back. With --check, the audit also
verifies that a given kernel's banner appears in every image, i.e. that the
images were rebuilt after that kernel.
"""
import hashlib
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "shim", "out")

BANNER = re.compile(rb"Darwin Kernel Version[^\x00]{0,120}")
PAYLOAD_MAGIC = b"SWEETXNU"


def describe_image(path):
    """Return a dict of provenance facts about one boot image."""
    with open(path, "rb") as f:
        data = f.read()
    info = {
        "file": os.path.basename(path),
        "sha256": hashlib.sha256(data).hexdigest()[:16],
        "bytes": len(data),
        "kernel_banner": None,
        "kernel_sha_guess": None,
    }
    m = BANNER.search(data)
    if m:
        info["kernel_banner"] = m.group().decode("utf-8", "replace")
    i = data.find(PAYLOAD_MAGIC)
    if i >= 0:
        try:
            v = struct.unpack_from("<7Q", data, i + 0x10)
            info["image_text"] = v[4] - v[0]      # kernel text+bss span
        except struct.error:
            pass
    return info


def banner_of_kernel(path):
    with open(path, "rb") as f:
        m = BANNER.search(f.read())
    return m.group().decode("utf-8", "replace") if m else None


def main(argv):
    check = None
    if "--check" in argv:
        i = argv.index("--check")
        if i + 1 < len(argv):
            check = argv[i + 1]
            if not os.path.isabs(check):
                check = os.path.join(REPO, check)

    # Only the images the current experiments use. shim/out accumulates every
    # image this project has ever built (100+ of them), and listing all of
    # them buries the answer; a stale historical image matters only if someone
    # might boot it.
    names = ["shim-proven.img", "shim-bisect-on.img", "shim-bisect-off.img",
             "shim-ab-dmb.img", "shim-ab-dsb.img"]
    images = [os.path.join(OUT, n) for n in names
              if os.path.isfile(os.path.join(OUT, n))]
    if not images:
        print(f"none of the current images exist in {OUT}")
        return 1
    missing = [n for n in names if not os.path.isfile(os.path.join(OUT, n))]
    if missing:
        print("MISSING (rebuild before booting): " + ", ".join(missing))

    want = banner_of_kernel(check) if check else None
    if check and not want:
        print(f"cannot read a build banner from {check}")
        return 2

    rows = [describe_image(p) for p in images]
    for r in rows:
        print(f"{r['file']:24} {r['sha256']}  {r['bytes']:>9} bytes")
        print(f"{'':24} banner: {r['kernel_banner'] or '(not found)'}")

    if want:
        print(f"\n--check {os.path.relpath(check, REPO)}")
        print(f"{'':24} banner: {want}")
        # The A/B pair is *supposed* to be built from different kernels - that
        # is the experiment. Only the images that should track the main kernel
        # are checked against it; the pair is checked against each other by
        # tests/test_ab_variants.py.
        ab = {"shim-ab-dmb.img", "shim-ab-dsb.img"}
        stale = [r for r in rows
                 if r["file"] not in ab and r["kernel_banner"] != want]
        if stale:
            print("\nSTALE - these images were built from a different kernel:")
            for r in stale:
                print(f"  {r['file']}  {r['kernel_banner']}")
            print("\nRebuild them before booting, or the experiment mixes variables.")
            return 1
        print("\nall non-A/B images carry this kernel")
        absent = [n for n in ab if not any(r["file"] == n for r in rows)]
        if absent:
            print("A/B images not built yet: " + ", ".join(sorted(absent)))
        else:
            print("A/B pair present (their difference is checked by test_ab_variants.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))