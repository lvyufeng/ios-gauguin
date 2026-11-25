#!/usr/bin/env python3
"""Synthetic MDT asset tests; production size/hash pins are never bypassable by CLI."""
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_payload_nvt_asset as fixtures
pack = fixtures.candidate
adt = fixtures.adt


class PayloadTests(unittest.TestCase):
    def test_production_pin(self):
        self.assertEqual(pack.ZAP_MDT_SIZE, 6860)
        self.assertEqual(pack.ZAP_MDT_SHA256, '6f2a0e35325097f98fded6123d755266cdbb44caa932be61251b65b5c516ac7b')

    def test_assets_layout_errors_and_bounds(self):
        warnings.simplefilter('ignore', ResourceWarning)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            k, a, z, n, rd = [root / s for s in ('kernel','adt','mdt','nvt','rd')]
            k.write_bytes(fixtures.kernel()); a.write_bytes(adt.serialize(fixtures.tree()))
            mdt = (bytes(range(256)) * 27)[:6860]; z.write_bytes(mdt)
            nvt = bytes(range(256)) * 544; n.write_bytes(nvt); rd.write_bytes(b'R' * 17001)
            with patch.object(pack, 'ZAP_MDT_SHA256', hashlib.sha256(mdt).hexdigest()), \
                 patch.object(pack, 'NVT_FIRMWARE_SHA256', hashlib.sha256(nvt).hexdigest()):
                for ramdisk in (None, rd):
                    for touch in (None, n):
                        before, _ = pack.build(k, a, '', ramdisk, touch)
                        for pas in (False, True):
                            blob, info = pack.build(k, a, '', ramdisk, touch, pas, z)
                            base, layout = fixtures.layout(before), fixtures.layout(blob)
                            self.assertEqual(len(layout['segs']), len(base['segs']) + 1)
                            for old, new in zip(base['segs'], layout['segs']):
                                self.assertEqual(old[:2], new[:2])
                                self.assertEqual(before[old[2]:old[2]+old[3]], blob[new[2]:new[2]+new[3]])
                            va, size, offset, stored = layout['segs'][-1]
                            self.assertEqual((va, size, stored), (base['end'], 16384, 16384))
                            self.assertEqual(blob[offset:offset+6860], mdt)
                            self.assertEqual(blob[offset+6860:offset+stored], bytes(stored-6860))
                            mmap = layout['root'].children[0].children[0]
                            pa, raw = struct.unpack('<QQ', mmap.prop('A615ZapMDT'))
                            # The kernel stages the whole 16KiB descriptor page; the raw asset stays 6860.
                            self.assertEqual((pa, raw), (fixtures.PA + va - layout['virt'], 16384))
                            self.assertEqual(layout['entry'], base['entry'])
                            top = (pa + 16384 + layout['adt_size'] + 16383) // 16384 * 16384 + 16384
                            self.assertEqual(int(info['zap_metadata']['top_of_kernel_data'],16), top)
                            if touch:
                                self.assertEqual(info['nvt_firmware']['top_of_kernel_data'], info['zap_metadata']['top_of_kernel_data'])
                for value in (mdt[:-1], mdt+b'X', b'X'+mdt[1:]):
                    z.write_bytes(value)
                    with self.assertRaisesRegex(ValueError, 'size/SHA256'):
                        pack.build(k, a, '', zap_mdt_path=z)
                z.write_bytes(mdt)
                _, info = pack.build(k, a, '', zap_mdt_path=z)
                self.assertEqual(info['zap_metadata']['size'], 6860)
                self.assertEqual(info['zap_metadata']['reserved'], 16384)
                exact = int(info['zap_metadata']['top_of_kernel_data'],16)-fixtures.PA
                a.write_bytes(adt.serialize(fixtures.tree(size=exact))); pack.build(k,a,'',zap_mdt_path=z)
                a.write_bytes(adt.serialize(fixtures.tree(size=exact-1)))
                with self.assertRaises(ValueError): pack.build(k,a,'',zap_mdt_path=z)
                with self.assertRaisesRegex(ValueError, 'next page above'):
                    pack.append_firmware_asset([], a.read_bytes(), 0, 0, fixtures.PA, 1 << 20, z,
                                               'A615ZapMDT', 6860, hashlib.sha256(mdt).hexdigest(),
                                               'A615 ZAP metadata', 16385)
                for props in ([('A615ZapMDT',0,b'old')], [('other',0,struct.pack('<QQ',int(info['zap_metadata']['phys'],16),1))]):
                    a.write_bytes(adt.serialize(fixtures.tree(mmap_props=props)))
                    with self.assertRaises(ValueError): pack.build(k,a,'',zap_mdt_path=z)
            a.write_bytes(adt.serialize(fixtures.tree()))
            output = root/'output'; output.write_bytes(b'preserved')
            result = subprocess.run([sys.executable, str(fixtures.TOOLS/'mkpayload.py'), str(k), str(a), str(output), '--zap-mdt', str(z)], capture_output=True)
            self.assertNotEqual(result.returncode,0)  # Synthetic content fails the real fixed pin.
            self.assertEqual(output.read_bytes(),b'preserved')


if __name__ == '__main__':
    unittest.main()
