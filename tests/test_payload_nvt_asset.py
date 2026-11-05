#!/usr/bin/env python3
"""Layout/error tests use synthetic bytes; the production firmware pin stays fixed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))
import adt


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


candidate = module('asset_payload_candidate', TOOLS / 'mkpayload.py')
LEGACY = json.loads((HERE / 'fixtures/mkpayload_legacy.json').read_text())
VA = 0xfffffe0007004000
PA = 0x180000000
RAM = 32 * 1024 * 1024
PIN = '007143e7d0a816e4ef228b5a08bf3132285230a5cd16164e8086696115d60f88'


def node(name, props=(), children=()):
    result = adt.Node()
    result.props = [('name', 0, name.encode() + b'\0')] + list(props)
    result.children = list(children)
    return result


def tree(size=RAM, base=PA, mmap_props=()):
    return node('device-tree', children=[node('chosen', [
        ('dram-base', 0, struct.pack('<Q', base)), ('dram-size', 0, struct.pack('<Q', size)),
    ], [node('memory-map', mmap_props)])])


def kernel():
    def segment(name, va, vm, off, size, prot):
        return struct.pack('<II16s4Q4I', 0x19, 72, name.encode(), va, vm, off, size, 7, prot, 0, 0)
    text = segment('__TEXT', VA, 0x4000, 0, 0x4000, 5)
    data = segment('__DATA', VA + 0x4000, 0x8000, 0x4000, 0x2000, 3)
    registers = bytearray(68 * 4)
    struct.pack_into('<Q', registers, 32 * 8, VA + 0x1000)
    entry = struct.pack('<4I', 5, 288, 6, 68) + registers
    commands = text + data + entry
    result = bytearray(0x6000)
    struct.pack_into('<8I', result, 0, 0xfeedfacf, 0x100000c, 0, 2, 3, len(commands), 0, 0)
    result[32:32 + len(commands)] = commands
    result[0x1000:0x1100] = b'K' * 256
    result[0x4000:] = b'D' * 0x2000
    return result


def layout(blob):
    _, version, count = struct.unpack_from('<8sII', blob)
    base, entry, adt_off, adt_size, end, phys, mem = struct.unpack_from('<7Q', blob, 0x10)
    segs = [struct.unpack_from('<4Q', blob, candidate.SEG_TABLE + i * 32) for i in range(count)]
    root, consumed = adt.parse(blob[adt_off:adt_off + adt_size])
    assert consumed == adt_size and version == 1
    return dict(virt=base, entry=entry, end=end, phys=phys, mem=mem, segs=segs, root=root, adt_size=adt_size)


class PinTests(unittest.TestCase):
    def test_pinned_metadata_and_table_policy(self):
        self.assertEqual(candidate.NVT_FIRMWARE_SHA256, PIN)
        self.assertEqual(candidate.NVT_FIRMWARE_SIZE, 139264)
        self.assertEqual(candidate.ASSET_MAX_SEGMENTS, 490)


class PayloadTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore', ResourceWarning)  # Legacy baseline opens files inline.
        self.tmp = tempfile.TemporaryDirectory(prefix='payload-asset-')
        self.base = Path(self.tmp.name)
        self.k = self.base / 'kernel'; self.a = self.base / 'tree'; self.f = self.base / 'firmware'
        self.k.write_bytes(kernel()); self.a.write_bytes(adt.serialize(tree()))
        self.image = bytes(range(256)) * (candidate.NVT_FIRMWARE_SIZE // 256)
        self.f.write_bytes(self.image)
        # Layout tests use synthetic data without distributing the real firmware.
        # Production has no hash override option; the real pin is checked above.
        self.pin = patch.object(candidate, 'NVT_FIRMWARE_SHA256', hashlib.sha256(self.image).hexdigest())
        self.pin.start()

    def tearDown(self):
        self.pin.stop(); self.tmp.cleanup()

    def pack(self, ramdisk=None):
        return candidate.build(self.k, self.a, 'physical-input-disabled', ramdisk, self.f)

    def test_default_matches_baseline_exactly_with_and_without_ramdisk(self):
        # Golden bytes/info were produced by the pre-asset packer from these
        # synthetic inputs. No firmware or duplicate packer implementation.
        rd = self.base / 'rd'; rd.write_bytes(b'root-image' * 2000)
        results = []
        for ramdisk in (None, rd):
            for command in ('', 'a' * 800):
                results.append(candidate.build(self.k, self.a, command, ramdisk))
        self.a.write_bytes(adt.serialize(tree(mmap_props=[('NovatekFirmware', 0, b'old')])))
        results.append(candidate.build(self.k, self.a, ''))
        for (blob, info), expected in zip(results, LEGACY):
            self.assertEqual(hashlib.sha256(blob).hexdigest(), expected['sha256'])
            self.assertEqual(json.loads(json.dumps(info)), expected['info'])

    def test_asset_raw_property_zero_padding_entry_and_adt_reservation(self):
        original, _ = candidate.build(self.k, self.a, 'physical-input-disabled')
        blob, info = self.pack(); before, after = layout(original), layout(blob)
        self.assertEqual(after['entry'], before['entry'])
        self.assertEqual(len(after['segs']), len(before['segs']) + 1)
        for old, new in zip(before['segs'], after['segs']):
            self.assertEqual(old[:2], new[:2])
            self.assertEqual(original[old[2]:old[2] + old[3]], blob[new[2]:new[2] + new[3]])
        va, size, offset, stored = after['segs'][-1]
        self.assertEqual((va, size, stored), (before['end'], 147456, 147456))
        self.assertEqual(blob[offset:offset + 139264], self.image)
        self.assertEqual(blob[offset + 139264:offset + stored], bytes(8192))
        self.assertEqual(after['end'], va + size)
        mmap = after['root'].children[0].children[0]
        asset = struct.unpack('<2Q', mmap.prop('NovatekFirmware'))
        self.assertEqual(asset, (PA + va - after['virt'], 139264))
        self.assertIsNone(mmap.prop('RAMDisk'))
        end = asset[0] + size + after['adt_size']
        top = ((end + candidate.PAGE - 1) & ~(candidate.PAGE - 1)) + candidate.PAGE
        self.assertEqual(int(info['nvt_firmware']['top_of_kernel_data'], 16), top)
        mmap.props = [prop for prop in mmap.props if prop[0] != 'NovatekFirmware']
        self.assertEqual(adt.serialize(after['root']), self.a.read_bytes())

    def test_ramdisk_and_asset_are_distinct_and_nonoverlapping(self):
        rd = self.base / 'rd'; rd.write_bytes(b'R' * 17001)
        blob, info = self.pack(rd); out = layout(blob); mmap = out['root'].children[0].children[0]
        rpa, rsize = struct.unpack('<2Q', mmap.prop('RAMDisk'))
        fpa, fsize = struct.unpack('<2Q', mmap.prop('NovatekFirmware'))
        self.assertEqual(rsize, 32768); self.assertEqual(fsize, 139264)
        self.assertEqual(fpa, rpa + rsize)
        self.assertEqual(info['ramdisk'], (hex(rpa), hex(rsize)))

    def test_firmware_wrong_size_and_digest_rejected_before_output_write(self):
        for value in (self.image[:-1], self.image + b'X', b'X' + self.image[1:]):
            self.f.write_bytes(value)
            with self.assertRaisesRegex(ValueError, 'size/SHA256'):
                self.pack()
        output = self.base / 'out'; output.write_bytes(b'preserved')
        result = subprocess.run([sys.executable, str(TOOLS / 'mkpayload.py'), str(self.k), str(self.a),
                                 str(output), '--nvt-firmware', str(self.f)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_bytes(), b'preserved')

    def test_ram_end_includes_adt_boot_args_and_exact_boundary(self):
        _, info = self.pack(); exact = int(info['nvt_firmware']['top_of_kernel_data'], 16) - PA
        self.a.write_bytes(adt.serialize(tree(size=exact))); self.pack()
        for size in (exact - 1, exact - candidate.PAGE, 0x4000):
            self.a.write_bytes(adt.serialize(tree(size=size)))
            with self.assertRaises(ValueError): self.pack()
        self.a.write_bytes(adt.serialize(tree(base=(1 << 64) - 0x4000)))
        with self.assertRaises(ValueError): self.pack()

    def test_duplicate_and_overlapping_adt_ranges(self):
        _, info = self.pack(); pa = int(info['nvt_firmware']['phys'], 16)
        for props in ([('NovatekFirmware', 0, b'')],
                      [('NovatekFirmware', 0, b'a'), ('NovatekFirmware', 0, b'b')],
                      [('other', 0, struct.pack('<2Q', pa + 139264, 1))]):
            self.a.write_bytes(adt.serialize(tree(mmap_props=props)))
            with self.assertRaises(ValueError): self.pack()
        for case in range(4):
            root = tree(); chosen = root.children[0]
            if case == 0: root.children.append(chosen)
            if case == 1: chosen.children.append(chosen.children[0])
            if case == 2: chosen.props.append(('dram-size', 0, struct.pack('<Q', RAM)))
            if case == 3: chosen.props[1] = ('dram-base', 0, b'short')
            self.a.write_bytes(adt.serialize(root))
            with self.assertRaises(ValueError): self.pack()
        self.a.write_bytes(adt.serialize(tree())[:-1])
        with self.assertRaises((ValueError, struct.error)): self.pack()

    def test_malformed_segments_load_commands_and_entry(self):
        changes = [(16, '<I', 0), (36, '<I', 0), (32 + 48, '<Q', 0x8000),
                   (32 + 40, '<Q', 0x100000), (32 + 64, '<I', 1),
                   (32 + 72 + 24, '<Q', VA + 8), (32 + 60, '<I', 1),
                   (32 + 24, '<Q', (1 << 64) - 0x2000)]
        for offset, fmt, value in changes:
            blob = kernel(); struct.pack_into(fmt, blob, offset, value); self.k.write_bytes(blob)
            with self.assertRaises(ValueError, msg=(offset, value)): self.pack()
        self.k.write_bytes(kernel()[:60])
        with self.assertRaises((ValueError, struct.error)): self.pack()

    def test_segment_table_capacity_checked_without_giant_payload(self):
        base = VA & ~(0x2000000 - 1)
        def pieces(count): return [(base + i * candidate.PAGE, candidate.PAGE, b'x') for i in range(count)]
        for count in (candidate.ASSET_MAX_SEGMENTS, candidate.ASSET_MAX_SEGMENTS + 1):
            with self.assertRaisesRegex(ValueError, 'segment table'):
                candidate.append_nvt_firmware(pieces(count), self.a.read_bytes(), base + count * candidate.PAGE,
                                              base, PA, RAM, self.f)
        count = candidate.ASSET_MAX_SEGMENTS - 1
        data = pieces(count)
        candidate.append_nvt_firmware(data, self.a.read_bytes(), base + count * candidate.PAGE, base, PA, RAM, self.f)
        self.assertEqual(candidate.SEG_TABLE + len(data) * 32 <= candidate.PAGE, True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
