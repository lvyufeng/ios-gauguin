#!/usr/bin/env python3
"""Fix-ups applied to the xnu tree after dxb applied every patch.

Run from the xnu source root (dxb/xnu) right before the kernel build:

  * bsd/dev/sweet_sample.c is added as a `standard` file (every machine
    config) but only builds on SWEET, so wrap it in
    #if defined(ARM64_BOARD_CONFIG_SWEET) -- dxb's VMAPPLE bootstrap kernel
    links every standard file and fails otherwise.
  * libkern/conf and bsd/conf gate the BearSSL objects, the HFS provider and
    the libpthread shims on `ifeq ($(CURRENT_MACHINE_CONFIG),SWEET)`; the
    GAUGUIN config compiles the same sources (-DARM64_BOARD_CONFIG_SWEET
    -DGAUGUIN) and needs the same include paths and -include header.

The repo's patch series leaves these to this script on purpose: the patch
context would otherwise rot against dxb's own patches for the same files.
"""
import os
import sys


def guard_sampler(root):
    path = os.path.join(root, 'bsd/dev/sweet_sample.c')
    if not os.path.exists(path):
        return 'sweet_sample.c: absent'
    text = open(path).read()
    if 'ARM64_BOARD_CONFIG_SWEET' in text:
        return 'sweet_sample.c: already guarded'
    lines = text.split('\n')
    i = 0
    while i < len(lines) and (lines[i].startswith('/*') or
                              lines[i].startswith(' *') or lines[i] == ''):
        if lines[i].rstrip().endswith('*/') and i > 0:
            i += 1
            break
        i += 1
    lines.insert(i, '#if defined(ARM64_BOARD_CONFIG_SWEET)')
    out = '\n'.join(lines).rstrip('\n')
    out += '\n#endif /* ARM64_BOARD_CONFIG_SWEET */\n'
    open(path, 'w').write(out)
    return 'sweet_sample.c: guarded'


def allow_gauguin(root):
    old = 'ifeq ($(CURRENT_MACHINE_CONFIG),SWEET)'
    new = 'ifneq (,$(filter SWEET GAUGUIN,$(CURRENT_MACHINE_CONFIG)))'
    done = []
    for rel in ('libkern/conf/Makefile.template', 'bsd/conf/Makefile.template'):
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            continue
        text = open(path).read()
        if old in text:
            open(path, 'w').write(text.replace(old, new))
            done.append(rel)
    return done


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    if not os.path.exists(os.path.join(root, 'bsd/dev/sweet_sample.c')) and \
       not os.path.exists(os.path.join(root, 'libkern/conf/Makefile.template')):
        sys.exit(f'{root}: not an xnu tree')
    print(guard_sampler(root))
    print('machine-config gates updated:', allow_gauguin(root) or 'none')
    return 0


if __name__ == '__main__':
    sys.exit(main())
