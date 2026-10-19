#!/usr/bin/env python3
"""Pack an Android boot image header v2 (the geometry shim/build.sh uses).

  mkbootimg2.py OUT --kernel Image --ramdisk rd [--dtb dtb] [--cmdline S]
               [--page-size 4096] [--kernel-offset 0x8000] ...

A self-contained stand-in for AOSP's mkbootimg, so a fresh machine only needs
a host C compiler, mkbootimg-free. Header layout: bootimg.h (v2).
"""
import argparse, struct


def pad(data, ps):
    return data + b'\0' * (-len(data) % ps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--kernel', required=True)
    ap.add_argument('--ramdisk', required=True)
    ap.add_argument('--dtb')
    ap.add_argument('--cmdline', default='')
    ap.add_argument('--name', default='')
    ap.add_argument('--base', type=lambda s: int(s, 0), default=0)
    ap.add_argument('--kernel-offset', type=lambda s: int(s, 0), default=0x8000)
    ap.add_argument('--ramdisk-offset', type=lambda s: int(s, 0), default=0x1000000)
    ap.add_argument('--second-offset', type=lambda s: int(s, 0), default=0xf00000)
    ap.add_argument('--tags-offset', type=lambda s: int(s, 0), default=0x100)
    ap.add_argument('--dtb-offset', type=lambda s: int(s, 0), default=0x1f00000)
    ap.add_argument('--recovery-dtbo-offset', type=lambda s: int(s, 0), default=0)
    ap.add_argument('--page-size', type=int, default=4096)
    ap.add_argument('--os-version', default=None, help='A.B.C')
    ap.add_argument('--os-patch-level', default=None, help='YYYY-MM')
    a = ap.parse_args()

    ps = a.page_size
    kernel = open(a.kernel, 'rb').read()
    ramdisk = open(a.ramdisk, 'rb').read()
    dtb = open(a.dtb, 'rb').read() if a.dtb else b''

    os_version = 0
    if a.os_version:
        major, minor, patch = (int(x) for x in a.os_version.split('.'))
        os_version = (major << 25) | (minor << 18) | (patch << 11)
    if a.os_patch_level:
        y, m = (int(x) for x in a.os_patch_level.split('-'))
        os_version |= ((y - 2000) << 4) | m

    hdr = bytearray(ps)
    struct.pack_into('<8s', hdr, 0, b'ANDROID!')
    struct.pack_into('<10I', hdr, 8,
                     len(kernel), a.base + a.kernel_offset,
                     len(ramdisk), a.base + a.ramdisk_offset,
                     0, a.base + a.second_offset,
                     a.base + a.tags_offset, ps, 2, os_version)
    struct.pack_into('<16s', hdr, 48, a.name.encode()[:16])
    struct.pack_into('<512s', hdr, 64, a.cmdline.encode())
    struct.pack_into('<I', hdr, 576, 1660)            # header_size (v2)
    struct.pack_into('<Q', hdr, 1632, 0)              # recovery_dtbo_size
    struct.pack_into('<I', hdr, 1640, 0)              # recovery_dtbo_offset
    struct.pack_into('<I', hdr, 1644, 1660)           # header_size again
    struct.pack_into('<Q', hdr, 1648, len(dtb))
    struct.pack_into('<Q', hdr, 1656, a.base + a.dtb_offset)

    out = bytes(hdr) + pad(kernel, ps) + pad(ramdisk, ps) + pad(dtb, ps)
    open(a.out, 'wb').write(out)
    print(f'{a.out}: {len(out)} bytes (kernel {len(kernel)}, ramdisk {len(ramdisk)}, dtb {len(dtb)})')


if __name__ == '__main__':
    main()