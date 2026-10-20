#!/usr/bin/env python3
"""Stage the pinned third-party sources the SWEET patches expect.

dxb's 0019/0020/0026 stage scripts download them (apple-oss-distributions
git, www.bearssl.org); on a slow or filtered network they fail, so the same
pinned files live in deps/mirror. This copies them into the xnu tree and is
idempotent: a destination that already has content is left alone.

  xnu-stage-mirror.py XNU_ROOT DEPS_MIRROR

Layout the patches compile:
  libkern/crypto/sweet_bearssl/{inc,src}   BearSSL core/hash/symcipher
  bsd/pthread/sweet_libpthread/{kern,private,include}
  bsd/sweet_hfs/{core,hfs_encodings}
"""
import os
import shutil
import sys


def stage(src, dst, label):
    """Copy every file that is missing (dxb's stage scripts may have created
    the directory with only part of the tree, so a directory-level check is
    not enough)."""
    if not os.path.isdir(src):
        return f'{label}: mirror entry missing ({src})'
    copied = 0
    for root, _dirs, names in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in names:
            s = os.path.join(root, name)
            d = os.path.join(target_dir, name)
            if os.path.exists(d) and os.path.getsize(d) == os.path.getsize(s):
                continue
            shutil.copy2(s, d)
            copied += 1
    return f'{label}: {copied} file(s) staged'


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, mirror = sys.argv[1], sys.argv[2]
    if not os.path.exists(os.path.join(root, 'bsd/conf/files')):
        sys.exit(f'{root}: not an xnu tree')
    jobs = [
        ('BearSSL', 'libkern/crypto/sweet_bearssl', 'bearssl'),
        ('libpthread', 'bsd/pthread/sweet_libpthread', 'libpthread'),
        ('hfs', 'bsd/sweet_hfs', 'hfs'),
    ]
    for entry, dest, label in jobs:
        print(stage(os.path.join(mirror, entry),
                    os.path.join(root, dest), label))
    return 0


if __name__ == '__main__':
    sys.exit(main())
