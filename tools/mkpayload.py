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
# Optional --pas-reservation appends a non-loadable2MiB zero tail WITHIN the
# initrd. Its pending ADT slots are deliberately not kernel pmap/owner names.
# Only the new loader may validate actual ABL handoff and publish a1MiB owned
# subrange. This performs no physical allocation, firmware load or secure call.
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


def encode_cmdline(command):
    """Return a complete UTF-8 command that fits payload and boot_args v1."""
    encoded = command.encode('utf-8')
    if b'\0' in encoded:
        raise ValueError('boot command contains an embedded NUL')
    if len(encoded) >= BOOT_LINE_LENGTH:
        raise ValueError('boot command exceeds 607 UTF-8 bytes')
    return encoded


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


def asset_adt(adt_blob, asset_name='NovatekFirmware'):
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
    if any(name == asset_name for name, _, _ in mmap.props):
        raise ValueError(f'ADT already has {asset_name}')
    return root, mmap


def append_nvt_firmware(pieces, adt_blob, kernel_end, virt_base, phys_base, mem_size, path):
    return append_firmware_asset(pieces, adt_blob, kernel_end, virt_base, phys_base,
                                 mem_size, path, 'NovatekFirmware', NVT_FIRMWARE_SIZE,
                                 NVT_FIRMWARE_SHA256, 'Novatek firmware')


ZAP_MDT_SIZE = 6860
ZAP_MDT_SHA256 = '6f2a0e35325097f98fded6123d755266cdbb44caa932be61251b65b5c516ac7b'
GMU_FIRMWARE_SIZE = 32768
GMU_FIRMWARE_SHA256 = '9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e'
SQE_FIRMWARE_SIZE = 32304
SQE_FIRMWARE_SHA256 = 'a0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b'
ZAP_CODE_SIZE = 1984
ZAP_CODE_SHA256 = '61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878'


def append_firmware_asset(pieces, adt_blob, kernel_end, virt_base, phys_base,
                          mem_size, path, asset_name, expected_size, expected_sha, label,
                          adt_bytes=None):
    # Larger assets (Novatek firmware) describe their full extent; small
    # page-staged assets (A615ZapMDT) describe their reserved descriptor page.
    if adt_bytes is None:
        adt_bytes = expected_size
    elif not (expected_size < adt_bytes <= expected_size + PAGE and
              adt_bytes % PAGE == 0):
        raise ValueError(f'{label} ADT range must be the next page above the pinned asset')
    with open(path, 'rb') as firmware:
        image = firmware.read(expected_size + 1)
    if len(image) != expected_size or hashlib.sha256(image).hexdigest() != expected_sha:
        raise ValueError(f'{label} does not match pinned size/SHA256')
    root, mmap = asset_adt(adt_blob, asset_name)
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
    mmap.props.append((asset_name, 0, struct.pack('<2Q', pa, adt_bytes)))
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
                             sha256=expected_sha, top_of_kernel_data=hex(top))


PAS_TAIL_BYTES = 0x200000
PAS_REGION_BYTES = 0x100000
PAS_ALIGNMENT = 0x100000
PAS_MAX_PAYLOAD = 0x20000000


def pas_adt(adt_blob):
    """Validate the untrusted byte layout before using the ordinary ADT model."""
    if not adt_blob or len(adt_blob) > 0x100000:
        raise ValueError('PAS ADT extent is not bounded')
    nodes = props = 0
    def walk(offset, depth):
        nonlocal nodes, props
        if depth >= 16 or offset + 8 > len(adt_blob):
            raise ValueError('PAS ADT depth/truncation')
        np, nc = struct.unpack_from('<II', adt_blob, offset)
        nodes += 1; props += np; offset += 8
        if nodes > 4096 or nc > 4096 or props > 16384:
            raise ValueError('PAS ADT work bound')
        names = {}
        for _ in range(np):
            if offset + 36 > len(adt_blob):
                raise ValueError('PAS ADT property header')
            raw = adt_blob[offset:offset + 32]
            if b'\0' not in raw:
                raise ValueError('PAS ADT property name')
            name = raw.split(b'\0', 1)[0]
            raw_length = struct.unpack_from('<I', adt_blob, offset + 32)[0]
            length = raw_length & 0x7fffffff
            value = adt_blob[offset + 36:offset + 36 + length]
            # Existing gauguin ADT has two identical backlight/name entries.
            # Only byte-identical node names may repeat; no ambiguous identity.
            if name in names and not (name == b'name' and names[name] == (raw_length, value)):
                raise ValueError('PAS ADT duplicate property')
            names[name] = (raw_length, value)
            offset += 36 + ((length + 3) & ~3)
            if offset > len(adt_blob):
                raise ValueError('PAS ADT property extent')
        if b'name' not in names:
            raise ValueError('PAS ADT missing node name')
        for _ in range(nc):
            offset = walk(offset, depth + 1)
        return offset
    if walk(0, 0) != len(adt_blob):
        raise ValueError('PAS ADT trailing bytes')
    root, _ = adt.parse(adt_blob)
    if root.name != 'device-tree':
        raise ValueError('PAS ADT root')
    def unique(parent, name):
        found = [n for n in parent.children if n.name == name]
        if len(found) != 1:
            raise ValueError(f'PAS ADT requires exactly one {name}')
        return found[0]
    chosen = unique(root, 'chosen')
    unique(chosen, 'memory-map')
    defaults = [n for n in root.children if n.name == 'defaults']
    if len(defaults) > 1:
        raise ValueError('PAS ADT duplicate defaults')
    if not defaults:
        default = adt.Node(); default.props = [('name', 0, b'defaults\0')]
        root.children.append(default)
    else:
        default = defaults[0]
    for name in ('dram-base', 'dram-size'):
        values = [(flags, value) for key, flags, value in chosen.props if key == name]
        if len(values) != 1 or values[0][0] or len(values[0][1]) != 8:
            raise ValueError('PAS ADT DRAM property')
    if any(key in ('LowPASRequest', 'LowPASReservation') for key, _, _ in chosen.props):
        raise ValueError('PAS ADT already contains ownership metadata')
    if any(key in ('LowPASIOPending', 'pmap-io-ranges') for key, _, _ in default.props):
        raise ValueError('PAS refuses to merge/replace existing pmap-io-ranges')
    return root, chosen, default


def pas_pending_adt(adt_blob, pieces, kernel_end, virt_base, phys_base, mem_size):
    root, chosen, default = pas_adt(adt_blob)
    if not pieces or len(pieces) > ASSET_MAX_SEGMENTS or phys_base % 0x2000000 or mem_size % PAGE or not mem_size:
        raise ValueError('PAS invalid managed range/segment table')
    dram_end = checked_end(phys_base, mem_size, label='PAS managed DRAM')
    previous = virt_base
    for va, vm, data in pieces:
        if not vm or va < previous or (va | vm) & 7 or ((len(data) + 7) & ~7) > vm:
            raise ValueError('PAS invalid ordered copy/zero range')
        previous = checked_end(va, vm, label='PAS segment')
        checked_end(phys_base + va - virt_base, vm, dram_end, 'PAS segment DRAM')
    if kernel_end < previous or kernel_end % PAGE:
        raise ValueError('PAS invalid kernel end')
    chosen.props.append(('LowPASRequest', 0, bytes(128)))
    default.props.append(('LowPASIOPending', 0, bytes(24)))
    size = len(adt.serialize(root))
    if size > 0x100000:
        raise ValueError('PAS enlarged ADT too large')
    end = checked_end(phys_base + kernel_end - virt_base, size, dram_end, 'PAS ADT DRAM')
    top = checked_end((end + PAGE - 1) & ~(PAGE - 1), PAGE, dram_end, 'PAS boot_args DRAM')
    return root, chosen, size, top


def handoff_request_adt(blob, capacity):
    root, chosen, _ = pas_adt(blob)
    if any(name in ('GauguinHandoffPending', 'GauguinHandoffFDT') for name, _, _ in chosen.props):
        raise ValueError('ADT already has handoff FDT metadata')
    request = bytearray(160 + capacity)
    struct.pack_into('<8s4I', request, 0, b'GHFDREQ1', 1, 0, 0, capacity)
    chosen.props.append(('GauguinHandoffPending', 0, bytes(request)))
    result = adt.serialize(root)
    if len(result) > 0x100000:
        raise ValueError('handoff FDT enlarged ADT exceeds one MiB')
    return result


def build(kernel_path, adt_path, cmdline, ramdisk_path=None, nvt_firmware_path=None,
          pas_reservation=False, zap_mdt_path=None, gmu_firmware_path=None, sqe_firmware_path=None,
          zap_code_path=None, handoff_fdt_capacity=0):
    cl = encode_cmdline(cmdline)
    if type(handoff_fdt_capacity) is not int or handoff_fdt_capacity < 0:
        raise ValueError('invalid handoff FDT capacity')
    if handoff_fdt_capacity and (not pas_reservation or handoff_fdt_capacity < PAGE or
                                handoff_fdt_capacity > 0xc0000 or handoff_fdt_capacity % PAGE):
        raise ValueError('handoff FDT requires PAS and 16 KiB..768 KiB page-aligned capacity')
    buf = bytearray(open(kernel_path, 'rb').read())
    executable = validate_asset_macho(buf) if nvt_firmware_path is not None or zap_mdt_path is not None or gmu_firmware_path is not None or sqe_firmware_path is not None or zap_code_path is not None or pas_reservation else None
    m = parse_macho(buf)
    asset_count = int(nvt_firmware_path is not None) + int(zap_mdt_path is not None) + int(gmu_firmware_path is not None) + int(sqe_firmware_path is not None) + int(zap_code_path is not None)
    if asset_count and sum(bool(s['vmsize']) for s in m['segs']) + bool(ramdisk_path) + asset_count > ASSET_MAX_SEGMENTS:
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
    if handoff_fdt_capacity:
        adt_blob = handoff_request_adt(adt_blob, handoff_fdt_capacity)
    if nvt_firmware_path is not None:
        asset_adt(adt_blob)
    if zap_mdt_path is not None:
        asset_adt(adt_blob, 'A615ZapMDT')
    if gmu_firmware_path is not None:
        asset_adt(adt_blob, 'A619GMUFirmware')
    if sqe_firmware_path is not None:
        asset_adt(adt_blob, 'A630SQEFirmware')
    if zap_code_path is not None:
        asset_adt(adt_blob, 'A615ZapCode')
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

    zap = None
    if zap_mdt_path is not None:
        # The kernel stages one16KiB page; its single ADT range therefore
        # describes the reserved page, while the pinned raw asset stays6860.
        adt_blob, kernel_end, zap = append_firmware_asset(
            pieces, adt_blob, kernel_end, virt_base, PHYS_BASE, MEM_SIZE,
            zap_mdt_path, 'A615ZapMDT', ZAP_MDT_SIZE, ZAP_MDT_SHA256,
            'A615 ZAP metadata', 16384)
        if nvt is not None:
            nvt['top_of_kernel_data'] = zap['top_of_kernel_data']

    gmu = None
    if gmu_firmware_path is not None:
        adt_blob, kernel_end, gmu = append_firmware_asset(
            pieces, adt_blob, kernel_end, virt_base, PHYS_BASE, MEM_SIZE,
            gmu_firmware_path, 'A619GMUFirmware', GMU_FIRMWARE_SIZE,
            GMU_FIRMWARE_SHA256, 'A619 legacy GMU firmware')
        for earlier in (nvt, zap):
            if earlier is not None:
                earlier['top_of_kernel_data'] = gmu['top_of_kernel_data']

    sqe = None
    if sqe_firmware_path is not None:
        adt_blob, kernel_end, sqe = append_firmware_asset(
            pieces, adt_blob, kernel_end, virt_base, PHYS_BASE, MEM_SIZE,
            sqe_firmware_path, 'A630SQEFirmware', SQE_FIRMWARE_SIZE,
            SQE_FIRMWARE_SHA256, 'A630 SQE firmware')
        for earlier in (nvt, zap, gmu):
            if earlier is not None:
                earlier['top_of_kernel_data'] = sqe['top_of_kernel_data']

    zap_code = None
    if zap_code_path is not None:
        # Preserve every preceding asset VA. This is immutable high-bank data,
        # not a PAS destination or permission to load/authenticate the segment.
        adt_blob, kernel_end, zap_code = append_firmware_asset(
            pieces, adt_blob, kernel_end, virt_base, PHYS_BASE, MEM_SIZE,
            zap_code_path, 'A615ZapCode', ZAP_CODE_SIZE, ZAP_CODE_SHA256,
            'A615 ZAP b02 code')
        for earlier in (nvt, zap, gmu, sqe):
            if earlier is not None:
                earlier['top_of_kernel_data'] = zap_code['top_of_kernel_data']

    pas = None
    if pas_reservation:
        pas_root, pas_chosen, _, pas_top = pas_pending_adt(
            adt_blob, pieces, kernel_end, virt_base, PHYS_BASE, MEM_SIZE)
        adt_blob = adt.serialize(pas_root)

    hdr_size = SEG_TABLE + 32 * len(pieces)
    out = bytearray(hdr_size)
    seg_table = []
    for vmaddr, vmsize, data in pieces:
        off = len(out)
        out += data
        out += b'\0' * (-len(out) & 0xf)
        seg_table.append((vmaddr, vmsize, off, len(data)))
    adt_off = len(out)
    if pas_reservation:
        tail = (adt_off + len(adt_blob) + PAGE - 1) & ~(PAGE - 1)
        total = tail + PAS_TAIL_BYTES
        if total > PAS_MAX_PAYLOAD:
            raise ValueError('PAS total payload exceeds512MiB')
        request = struct.pack('<8sII6Q', b'LPASREQ1', 1, 0, tail,
                              PAS_TAIL_BYTES, PAS_REGION_BYTES, PAS_ALIGNMENT, total, 0) + bytes(64)
        pas_chosen.props[-1] = ('LowPASRequest', 0, request)
        updated = adt.serialize(pas_root)
        if len(updated) != len(adt_blob):
            raise ValueError('PAS fixed request changed ADT size')
        adt_blob = updated
        pas = dict(tail_offset=tail, tail_bytes=PAS_TAIL_BYTES,
                   region_bytes=PAS_REGION_BYTES, alignment=PAS_ALIGNMENT,
                   runtime_pa=None, top_of_kernel_data=hex(pas_top),
                   state='pending-runtime-validation')
    out += adt_blob
    out += b'\0' * (-len(out) & 0xf)
    if pas_reservation:
        out += bytes(total - len(out))

    struct.pack_into('<8sII', out, 0, b'SWEETXNU', 1, len(pieces))
    struct.pack_into('<7Q', out, 0x10, virt_base, m['entry'], adt_off, len(adt_blob), kernel_end,
                     PHYS_BASE, MEM_SIZE)
    out[CMDLINE:CMDLINE + len(cl)] = cl
    for i, t in enumerate(seg_table):
        struct.pack_into('<4Q', out, SEG_TABLE + 32 * i, *t)
    info = dict(cputype=hex(m['cputype']), cpusub=m['cpusub'], fixups=nfix, virt_base=hex(virt_base),
                entry=hex(m['entry']), kernel_end=hex(kernel_end), ramdisk=ramdisk, size=len(out),
                segs=[(s['name'], hex(s['vmaddr']), hex(s['vmsize'])) for s in segs])
    if nvt is not None:
        info['nvt_firmware'] = nvt
    if zap is not None:
        info['zap_metadata'] = zap
    if gmu is not None:
        info['gmu_firmware'] = gmu
    if sqe is not None:
        info['sqe_firmware'] = sqe
    if zap_code is not None:
        info['zap_code'] = zap_code
    if pas is not None:
        info['low_pas_request'] = pas
        if nvt is not None:
            nvt['top_of_kernel_data'] = hex(pas_top)
        if zap is not None:
            zap['top_of_kernel_data'] = hex(pas_top)
        if gmu is not None:
            gmu['top_of_kernel_data'] = hex(pas_top)
        if sqe is not None:
            sqe['top_of_kernel_data'] = hex(pas_top)
        if zap_code is not None:
            zap_code['top_of_kernel_data'] = hex(pas_top)
    if handoff_fdt_capacity:
        info['handoff_fdt_request'] = dict(version=1, header_bytes=160,
            capacity=handoff_fdt_capacity, source='actual ABL FDT at runtime',
            changes_RAM_admission=False)
    return bytes(out), info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kernel'); ap.add_argument('adt'); ap.add_argument('out')
    ap.add_argument('--cmdline', default='debug=0xc serial=3 cpus=1 keepsyms=1')
    ap.add_argument('--ramdisk', help='root image for md0 (boot with rd=md0)')
    ap.add_argument('--nvt-firmware', help='pinned Novatek firmware data asset; does not upload it')
    ap.add_argument('--pas-reservation', action='store_true', help='request runtime-validated unmanaged low-PA ownership; no PAS operation')
    ap.add_argument('--zap-mdt', help='pinned A615 ZAP metadata data asset; does not authenticate or execute it')
    ap.add_argument('--gmu-firmware', help='pinned A619 legacy GMU data asset; does not execute it')
    ap.add_argument('--sqe-firmware', help='pinned A630 SQE data asset; does not execute it')
    ap.add_argument('--zap-code', help='pinned A615 ZAP b02 data asset; does not load or authenticate it')
    ap.add_argument('--handoff-fdt-capacity', type=lambda value: int(value, 0), default=0,
                    help='optional original ABL FDT capture capacity; requires PAS, does not admit RAM')
    a = ap.parse_args()
    blob, info = build(a.kernel, a.adt, a.cmdline, a.ramdisk, a.nvt_firmware,
                       a.pas_reservation, a.zap_mdt, a.gmu_firmware, a.sqe_firmware, a.zap_code,
                       a.handoff_fdt_capacity)
    open(a.out, 'wb').write(blob)
    for k, v in info.items():
        if k != 'segs':
            print(f'{k}: {v}')
    for s in info['segs']:
        print('  ', *s)
