#!/usr/bin/env python3
"""Pack an xnu kernel Mach-O + ADT into the payload the sweet shim boots.

  mkpayload.py KERNEL ADT OUT [--cmdline "..."] [--ramdisk IMAGE] [--nvt-firmware FILE]

The kernel is linked as a PIE with LC_DYLD_CHAINED_FIXUPS. Nobody else
(no kmutil, no iBoot) resolves those for us, and xnu only rebases static
kernelcaches itself, so the chains are walked here and every pointer is
rewritten to its unslid target. The shim then only copies flat segments.

Payload layout (little endian, all offsets from payload start):
  0x000  char  magic[8] = "SWEETXNU"
  0x008  u32   version = 1, nsegs
  0x010  u64   virt_base      kernel VA that maps to phys_base
  0x018  u64   entry_va       LC_UNIXTHREAD pc
  0x020  u64   adt_off, adt_size
  0x030  u64   kernel_end_va  end of the highest segment (page aligned)
  0x038  u64   phys_base      kernel-managed RAM (same values as the ADT's dram-base/size)
  0x040  u64   mem_size
  0x048  char  cmdline[608]
  0x2a8  seg[nsegs] { u64 vmaddr, vmsize, file_off(in payload), file_size }

--ramdisk appends IMAGE as one more segment right after the kernel and moves
kernel_end past it, so the shim needs no changes: the image lands below the
ADT and boot_args, inside topOfKernelData (never handed to the VM), and the
ADT gets /chosen/memory-map "RAMDisk" = <phys, size> for IOFindBSDRoot to
turn into md0 (boot with rd=md0).

--nvt-firmware appends the pinned Novatek image as reserved data after any
ramdisk. NovatekFirmware records its physical address and RAW file size; the
segment and kernel_end reserve zero-padded16K pages. This does not upload or
execute firmware. Payload v1 has no permission bits; a future kernel consumer
must map the asset as data/NX and independently verify the actual touch chip.
"""
import argparse, hashlib, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adt  # noqa: E402

LC_SEGMENT_64, LC_UNIXTHREAD, LC_DYLD_CHAINED_FIXUPS = 0x19, 0x5, 0x80000034
PAGE = 0x4000
BOOT_LINE_LENGTH = 608
CMDLINE = 0x48
SEG_TABLE = CMDLINE + BOOT_LINE_LENGTH	# 0x2a8
NVT_FIRMWARE_SIZE = 139264
NVT_FIRMWARE_SHA256 = '007143e7d0a816e4ef228b5a08bf3132285230a5cd16164e8086696115d60f88'
U64_LIMIT = 1 << 64
# New asset-path policy: keep the complete segment table in the first16K page.
# This is a packer bound, not a hardware capacity advertised by the shim.
ASSET_MAX_SEGMENTS = (PAGE - SEG_TABLE) // 32


def parse_macho(buf):
    magic, cputype, cpusub, ftype, ncmds, sizeofcmds, flags, _ = struct.unpack_from('<8I', buf, 0)
    assert magic == 0xfeedfacf, 'not a 64-bit Mach-O'
    segs, entry, fixups = [], None, None
    off = 32
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<II', buf, off)
        if cmd == LC_SEGMENT_64:
            name = buf[off + 8:off + 24].split(b'\0')[0].decode()
            vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<4Q', buf, off + 24)
            segs.append(dict(name=name, vmaddr=vmaddr, vmsize=vmsize, fileoff=fileoff, filesize=filesize))
        elif cmd == LC_UNIXTHREAD:
            flavor, count = struct.unpack_from('<II', buf, off + 8)
            # arm_thread_state64: x0..x28, fp, lr, sp, pc, cpsr
            entry, = struct.unpack_from('<Q', buf, off + 16 + 32 * 8)
        elif cmd == LC_DYLD_CHAINED_FIXUPS:
            fixups = struct.unpack_from('<II', buf, off + 8)	# dataoff, datasize
        off += size
    return dict(cputype=cputype, cpusub=cpusub & 0xff, segs=segs, entry=entry, fixups=fixups)


def apply_chained_fixups(buf, m):
    """Rewrite every chained rebase in buf (the whole file) to its plain target VA."""
    if not m['fixups']:
        return 0
    data_off, _ = m['fixups']
    _, starts_off, _, _, imports_count, _, _ = struct.unpack_from('<7I', buf, data_off)
    assert imports_count == 0, 'kernel has binds; only rebases are supported'
    image_base = m['segs'][0]['vmaddr']		# __TEXT, holds the mach header
    seg_count, = struct.unpack_from('<I', buf, data_off + starts_off)
    nfix = 0
    for i in range(seg_count):
        seg_info, = struct.unpack_from('<I', buf, data_off + starts_off + 4 + 4 * i)
        if not seg_info:
            continue
        base = data_off + starts_off + seg_info
        size, page_size, fmt, seg_offset, max_valid, page_count = struct.unpack_from('<IHHQIH', buf, base)
        starts = struct.unpack_from('<%dH' % page_count, buf, base + 22)
        seg = m['segs'][i]
        for p, start in enumerate(starts):
            if start == 0xffff:
                continue
            assert not start & 0x8000, 'DYLD_CHAINED_PTR_START_MULTI not supported'
            loc = seg['fileoff'] + p * page_size + start
            while True:
                raw, = struct.unpack_from('<Q', buf, loc)
                target, nxt, stride = decode(raw, fmt, image_base)
                struct.pack_into('<Q', buf, loc, target)
                nfix += 1
                if not nxt:
                    break
                loc += nxt * stride
    return nfix


def decode(raw, fmt, image_base):
    """Return (unslid target VA, next, stride) for one chained pointer."""
    if fmt in (2, 6):		# DYLD_CHAINED_PTR_64 / _64_OFFSET
        assert not raw >> 63, 'bind in kernel'
        target = raw & ((1 << 36) - 1)
        high8 = (raw >> 36) & 0xff
        nxt = (raw >> 51) & 0xfff
        if fmt == 6:
            target += image_base
        return target | (high8 << 56), nxt, 4
    if fmt == 8:		# DYLD_CHAINED_PTR_64_KERNEL_CACHE
        target = raw & ((1 << 30) - 1)
        nxt = (raw >> 51) & 0xfff
        return image_base + target, nxt, 4
    if fmt in (1, 7, 9, 12):	# arm64e variants (stock VMAPPLE kernel only; PAC is not re-signed)
        auth = raw >> 63
        nxt = (raw >> 51) & 0x7ff
        stride = 4 if fmt in (7, 12) else 8
        if auth:
            target = raw & 0xffffffff
        else:
            target = raw & ((1 << 43) - 1)
            target |= ((raw >> 43) & 0xff) << 56
        if fmt in (7, 9, 12) or auth:
            target += image_base
        return target, nxt, stride
    raise ValueError(f'unsupported chained pointer format {fmt}')


def add_ramdisk_to_adt(adt_blob, phys, size):
    """Return the ADT with /chosen/memory-map RAMDisk = <phys, size> (two uintptr_t)."""
    root, _ = adt.parse(adt_blob)
    chosen = next(c for c in root.children if c.name == 'chosen')
    mmap = next(c for c in chosen.children if c.name == 'memory-map')
    assert mmap.prop('RAMDisk') is None, 'ADT already has a RAMDisk'
    mmap.props.append(('RAMDisk', 0, struct.pack('<2Q', phys, size)))
    return adt.serialize(root)


def adt_dram(adt_blob):
    """Kernel-managed RAM <base, size> from the ADT's /chosen dram-base/dram-size."""
    root, _ = adt.parse(adt_blob)
    chosen = next(c for c in root.children if c.name == 'chosen')
    return (struct.unpack('<Q', chosen.prop('dram-base'))[0],
            struct.unpack('<Q', chosen.prop('dram-size'))[0])


def checked_end(start, size, limit=U64_LIMIT, label='range'):
    if start < 0 or size < 0 or start >= limit or size > limit - start:
        raise ValueError(f'{label} exceeds address range')
    if start + size >= U64_LIMIT:
        raise ValueError(f'{label} overflows uint64 address')
    return start + size


def validate_asset_macho(buf):
    """Bound the original load commands before parsing an asset-bearing image."""
    if len(buf) < 32:
        raise ValueError('truncated Mach-O header')
    magic, cpu, _, _, count, length, _, _ = struct.unpack_from('<8I', buf)
    if magic != 0xfeedfacf or cpu != 0x100000c or not count or count > length // 8:
        raise ValueError('asset requires bounded ARM64 Mach-O commands')
    end = checked_end(32, length, len(buf) + 1, 'load commands')
    if end > len(buf):
        raise ValueError('truncated load commands')
    off, threads, executable = 32, 0, []
    for _ in range(count):
        if off > end - 8:
            raise ValueError('truncated load command')
        cmd, size = struct.unpack_from('<II', buf, off)
        if size < 8 or size % 8 or size > end - off:
            raise ValueError('invalid load command size')
        if cmd == LC_SEGMENT_64:
            if size < 72:
                raise ValueError('truncated segment command')
            va, vm, fileoff, filesz = struct.unpack_from('<4Q', buf, off + 24)
            _, prot, sections, _ = struct.unpack_from('<4I', buf, off + 56)
            if sections > (size - 72) // 80 or size != 72 + sections * 80:
                raise ValueError('invalid segment section table')
            if (vm and filesz > vm) or fileoff > len(buf) or filesz > len(buf) - fileoff:
                raise ValueError('segment file bytes exceed range')
            if vm and (va % 8 or vm % 8 or ((filesz + 7) & ~7) > vm):
                raise ValueError('segment copy/zero range is not word aligned')
            checked_end(va, vm, label='segment VA')
            if vm and prot & 4 and filesz:
                executable.append((va, va + filesz))
        elif cmd == LC_UNIXTHREAD:
            if size != 16 + 68 * 4 or struct.unpack_from('<2I', buf, off + 8) != (6, 68):
                raise ValueError('unsupported ARM64 entry state')
            threads += 1
        elif cmd == LC_DYLD_CHAINED_FIXUPS:
            if size != 16:
                raise ValueError('invalid fixup load command')
            position, amount = struct.unpack_from('<2I', buf, off + 8)
            if position > len(buf) or amount > len(buf) - position:
                raise ValueError('fixup bytes exceed file')
        off += size
    if off != end or threads != 1:
        raise ValueError('load command count/entry mismatch')
    return executable


def asset_adt(adt_blob):
    root, end = adt.parse(adt_blob)
    if end != len(adt_blob):
        raise ValueError('ADT length mismatch')
    def child(parent, name):
        matches = [n for n in parent.children if n.name == name]
        if len(matches) != 1:
            raise ValueError(f'ADT needs exactly one {name} node')
        return matches[0]
    chosen = child(root, 'chosen')
    mmap = child(chosen, 'memory-map')
    for name in ('dram-base', 'dram-size'):
        values = [(flags, value) for n, flags, value in chosen.props if n == name]
        if len(values) != 1 or values[0][0] or len(values[0][1]) != 8:
            raise ValueError(f'invalid or duplicate ADT {name}')
    if any(name == 'NovatekFirmware' for name, _, _ in mmap.props):
        raise ValueError('ADT already has NovatekFirmware')
    return root, mmap


def append_nvt_firmware(pieces, adt_blob, kernel_end, virt_base, phys_base, mem_size, path):
    with open(path, 'rb') as firmware:
        image = firmware.read(NVT_FIRMWARE_SIZE + 1)
    if len(image) != NVT_FIRMWARE_SIZE or hashlib.sha256(image).hexdigest() != NVT_FIRMWARE_SHA256:
        raise ValueError('Novatek firmware does not match pinned size/SHA256')
    root, mmap = asset_adt(adt_blob)
    if not mem_size or phys_base % PAGE:
        raise ValueError('invalid DRAM base/size')
    dram_end = checked_end(phys_base, mem_size, label='DRAM')
    if not pieces or len(pieces) + 1 > ASSET_MAX_SEGMENTS:
        raise ValueError('asset segment table exceeds one16K page')
    previous_end = virt_base
    for va, size, data in sorted(pieces, key=lambda p: p[0]):
        if not size or va < previous_end or va < virt_base or len(data) > size:
            raise ValueError('overlapping/invalid payload segments')
        previous_end = checked_end(va, size, label='payload segment')
        checked_end(phys_base + va - virt_base, size, dram_end, 'segment DRAM')
    if kernel_end % PAGE or kernel_end < previous_end:
        raise ValueError('invalid aligned kernel end')
    reserved = (len(image) + PAGE - 1) & ~(PAGE - 1)
    end = checked_end(kernel_end, reserved, label='firmware VA')
    pa = phys_base + kernel_end - virt_base
    pa_end = checked_end(pa, reserved, dram_end, 'firmware DRAM')
    for name, _, value in mmap.props:
        if name != 'name' and len(value) == 16:
            other, length = struct.unpack('<2Q', value)
            other_end = checked_end(other, length, label='ADT memory-map range')
            if length and pa < other_end and other < pa_end:
                raise ValueError(f'firmware overlaps ADT memory-map property {name}')
    mmap.props.append(('NovatekFirmware', 0, struct.pack('<2Q', pa, len(image))))
    updated = adt.serialize(root)
    if len(updated) > 0xffffffff:
        raise ValueError('ADT does not fit boot_args length')
    # loader.c puts ADT at kernel_end, then one page for boot_args. Include its
    # rounding so an apparently fitting firmware cannot push metadata past RAM.
    adt_end = checked_end(pa_end, len(updated), dram_end, 'ADT DRAM')
    boot_args = (adt_end + PAGE - 1) & ~(PAGE - 1)
    top = checked_end(boot_args, PAGE, dram_end, 'boot_args DRAM')
    pieces.append((kernel_end, reserved, image + b'\0' * (reserved - len(image))))
    return updated, end, dict(phys=hex(pa), size=len(image), reserved=reserved,
                             sha256=NVT_FIRMWARE_SHA256, top_of_kernel_data=hex(top))


def build(kernel_path, adt_path, cmdline, ramdisk_path=None, nvt_firmware_path=None):
    buf = bytearray(open(kernel_path, 'rb').read())
    executable = validate_asset_macho(buf) if nvt_firmware_path is not None else None
    m = parse_macho(buf)
    if nvt_firmware_path is not None and sum(bool(s['vmsize']) for s in m['segs']) + bool(ramdisk_path) + 1 > ASSET_MAX_SEGMENTS:
        raise ValueError('asset segment table exceeds one16K page')
    if executable is not None and not any(start <= m['entry'] < end for start, end in executable):
        raise ValueError('kernel entry is outside original executable file bytes')
    nfix = apply_chained_fixups(buf, m)
    segs = [s for s in m['segs'] if s['vmsize']]
    text = m['segs'][0]
    assert text['name'] == '__TEXT' and text['fileoff'] == 0
    # virt_base: 32MB (16K-granule L2 block) below the mach header, so start.s's
    # block mapping that starts at the header's block begins exactly at phys_base.
    virt_base = text['vmaddr'] & ~(0x2000000 - 1)
    kernel_end = max(s['vmaddr'] + s['vmsize'] for s in segs)
    kernel_end = (kernel_end + PAGE - 1) & ~(PAGE - 1)

    adt_blob = open(adt_path, 'rb').read()
    if nvt_firmware_path is not None:
        asset_adt(adt_blob)
    # The ADT decides where the kernel's RAM is (mkadt.py --highmem).
    PHYS_BASE, MEM_SIZE = adt_dram(adt_blob)
    pieces = [(s['vmaddr'], s['vmsize'], buf[s['fileoff']:s['fileoff'] + s['filesize']]) for s in segs]
    ramdisk = None
    if ramdisk_path:
        image = open(ramdisk_path, 'rb').read()
        rd_size = (len(image) + PAGE - 1) & ~(PAGE - 1)
        rd_va = kernel_end
        kernel_end = rd_va + rd_size
        rd_pa = rd_va - virt_base + PHYS_BASE
        pieces.append((rd_va, rd_size, image))
        adt_blob = add_ramdisk_to_adt(adt_blob, rd_pa, rd_size)
        ramdisk = (hex(rd_pa), hex(rd_size))

    nvt = None
    if nvt_firmware_path is not None:
        adt_blob, kernel_end, nvt = append_nvt_firmware(
            pieces, adt_blob, kernel_end, virt_base, PHYS_BASE, MEM_SIZE, nvt_firmware_path)

    hdr_size = SEG_TABLE + 32 * len(pieces)
    out = bytearray(hdr_size)
    seg_table = []
    for vmaddr, vmsize, data in pieces:
        off = len(out)
        out += data
        out += b'\0' * (-len(out) & 0xf)
        seg_table.append((vmaddr, vmsize, off, len(data)))
    adt_off = len(out)
    out += adt_blob
    out += b'\0' * (-len(out) & 0xf)

    struct.pack_into('<8sII', out, 0, b'SWEETXNU', 1, len(pieces))
    struct.pack_into('<7Q', out, 0x10, virt_base, m['entry'], adt_off, len(adt_blob), kernel_end,
                     PHYS_BASE, MEM_SIZE)
    cl = cmdline.encode()[:BOOT_LINE_LENGTH - 1]
    out[CMDLINE:CMDLINE + len(cl)] = cl
    for i, t in enumerate(seg_table):
        struct.pack_into('<4Q', out, SEG_TABLE + 32 * i, *t)
    info = dict(cputype=hex(m['cputype']), cpusub=m['cpusub'], fixups=nfix, virt_base=hex(virt_base),
                entry=hex(m['entry']), kernel_end=hex(kernel_end), ramdisk=ramdisk, size=len(out),
                segs=[(s['name'], hex(s['vmaddr']), hex(s['vmsize'])) for s in segs])
    if nvt is not None:
        info['nvt_firmware'] = nvt
    return bytes(out), info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kernel'); ap.add_argument('adt'); ap.add_argument('out')
    ap.add_argument('--cmdline', default='debug=0xc serial=3 cpus=1 keepsyms=1')
    ap.add_argument('--ramdisk', help='root image for md0 (boot with rd=md0)')
    ap.add_argument('--nvt-firmware', help='pinned Novatek firmware data asset; does not upload it')
    a = ap.parse_args()
    blob, info = build(a.kernel, a.adt, a.cmdline, a.ramdisk, a.nvt_firmware)
    open(a.out, 'wb').write(blob)
    for k, v in info.items():
        if k != 'segs':
            print(f'{k}: {v}')
    for s in info['segs']:
        print('  ', *s)
