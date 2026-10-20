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
    if not os.path.isdir(src):
        return f'{label}: mirror entry missing ({src})'
    if os.path.isdir(dst) and os.listdir(dst):
        return f'{label}: present'
    os.makedirs(dst, exist_ok=True)
    for entry in os.listdir(src):
        s = os.path.join(src, entry)
        d = os.path.join(dst, entry)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    return f'{label}: staged'


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
