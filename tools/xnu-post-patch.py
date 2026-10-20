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
import shutil
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


def sdk_includes(root):
    """Add the SDK's usr/include to the kernel include path.

    dxb normally patches makedefs/MakeInc.def for this, but our series touches
    that file first (0004-sweet-machine-config), so dxb's patch is skipped and
    the SDK headers that far-from-Apple code needs (<limits.h> from BearSSL,
    <TargetConditionals.h> from the libpthread shims) are not found.
    """
    path = os.path.join(root, 'makedefs/MakeInc.def')
    if not os.path.exists(path):
        return 'MakeInc.def: absent'
    text = open(path).read()
    marker = 'INCFLAGS_SDK\t= -I$(SDKROOT)/usr/local/include/kernel'
    if 'INCFLAGS_SDK' not in text or '$(SDKROOT)/usr/include' in text:
        return 'MakeInc.def: sdk include already set'
    out = []
    for line in text.split('\n'):
        if line.startswith('INCFLAGS_SDK'):
            if 'usr/local/include/kernel' in line and 'usr/include' not in line:
                line = line + ' -I$(SDKROOT)/usr/include'
        out.append(line)
    open(path, 'w').write('\n'.join(out))
    return 'MakeInc.def: -I$(SDKROOT)/usr/include added'


def master_file(root):
    """Give GAUGUIN its own MASTER file.

    doconf looks for MASTER.<cpu>.<soc>[.<platform>] and falls back to
    MASTER.<cpu>.<platform> = MASTER.arm64.MacOSX, which builds Apple's closed
    lib<SOC>.os for the arm64 assembly and pmap. SWEET ships MASTER.arm64.sweet
    with `nos_arm_asm nos_arm_pmap`; GAUGUIN compiles the same open-source
    sources, so it needs the same file under its own name.
    """
    cfg = os.path.join(root, 'config')
    dst = os.path.join(cfg, 'MASTER.arm64.gauguin')
    src = os.path.join(cfg, 'MASTER.arm64.sweet')
    if os.path.exists(dst):
        return 'MASTER.arm64.gauguin: present'
    if not os.path.exists(src):
        return 'MASTER.arm64.gauguin: no sweet master to copy'
    shutil.copy2(src, dst)
    return 'MASTER.arm64.gauguin: copied from the sweet one'


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    if not os.path.exists(os.path.join(root, 'bsd/dev/sweet_sample.c')) and \
       not os.path.exists(os.path.join(root, 'libkern/conf/Makefile.template')):
        sys.exit(f'{root}: not an xnu tree')
    print(guard_sampler(root))
    print('machine-config gates updated:', allow_gauguin(root) or 'none')
    print(sdk_includes(root))
    print(master_file(root))
    return 0


if __name__ == '__main__':
    sys.exit(main())
