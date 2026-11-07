#!/usr/bin/env python3
"""Pinned b02 source asset: layout, preserved old segments and strict refusals."""
from contextlib import ExitStack
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
pack, adt = fixtures.candidate, fixtures.adt


class PayloadZapCodeTests(unittest.TestCase):
    def test_production_pin(self):
        self.assertEqual(pack.ZAP_CODE_SIZE, 1984)
        self.assertEqual(pack.ZAP_CODE_SHA256,
                         '61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878')

    def test_layout_and_refusals(self):
        warnings.simplefilter('ignore', ResourceWarning)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            k, a, code, rd = [root/n for n in ('kernel', 'adt', 'code', 'rd')]
            k.write_bytes(fixtures.kernel()); a.write_bytes(adt.serialize(fixtures.tree()))
            rd.write_bytes(b'R'*17001)
            data = bytes((i*31+5)%251 for i in range(1984)); code.write_bytes(data)
            old = [('nvt_firmware_path', 'NVT_FIRMWARE_SHA256', bytes(range(256))*544),
                   ('zap_mdt_path', 'ZAP_MDT_SHA256', bytes(range(256))*26+bytes(range(204))),
                   ('gmu_firmware_path', 'GMU_FIRMWARE_SHA256', bytes((i*19+7)%251 for i in range(32768))),
                   ('sqe_firmware_path', 'SQE_FIRMWARE_SHA256', bytes((i*23+11)%251 for i in range(32304)))]
            with ExitStack() as stack:
                stack.enter_context(patch.object(pack, 'ZAP_CODE_SHA256', hashlib.sha256(data).hexdigest()))
                for argument, pin, value in old:
                    (root/argument).write_bytes(value)
                    stack.enter_context(patch.object(pack, pin, hashlib.sha256(value).hexdigest()))
                for mask in range(64):
                    options = dict(ramdisk_path=rd if mask&1 else None, pas_reservation=bool(mask&32))
                    options.update({name: root/name if mask&(2<<i) else None for i,(name,_,_) in enumerate(old)})
                    before, _ = pack.build(k, a, '', **options)
                    base = fixtures.layout(before)
                    blob, info = pack.build(k, a, '', **options, zap_code_path=code)
                    layout = fixtures.layout(blob)
                    self.assertEqual(len(layout['segs']), len(base['segs'])+1)
                    for previous, new in zip(base['segs'], layout['segs']):
                        self.assertEqual(previous[:2], new[:2])
                        self.assertEqual(before[previous[2]:previous[2]+previous[3]], blob[new[2]:new[2]+new[3]])
                    va, size, off, stored = layout['segs'][-1]
                    self.assertEqual((va, size, stored), (base['end'], 16384, 16384))
                    self.assertEqual(blob[off:off+1984], data)
                    self.assertEqual(blob[off+1984:off+16384], bytes(14400))
                    mmap = layout['root'].children[0].children[0]
                    pa, raw = struct.unpack('<QQ', mmap.prop('A615ZapCode'))
                    self.assertEqual((pa, raw), (fixtures.PA+va-layout['virt'], 1984))
                    self.assertEqual((layout['virt'],layout['entry']), (base['virt'],base['entry']))
                    top = ((pa+16384+layout['adt_size']+16383)//16384+1)*16384
                    for name in ('nvt_firmware','zap_metadata','gmu_firmware','sqe_firmware','zap_code','low_pas_request'):
                        if name in info: self.assertEqual(int(info[name]['top_of_kernel_data'],16), top)
                    if options['pas_reservation']:
                        self.assertEqual(len(blob), info['low_pas_request']['tail_offset']+0x200000)
                        self.assertEqual(blob[-0x200000:], bytes(0x200000))
                for bad in (data[:-1],data+b'X',bytes([data[0]^1])+data[1:],data[:-1]+bytes([data[-1]^1])):
                    code.write_bytes(bad)
                    with self.assertRaisesRegex(ValueError, 'size/SHA256'): pack.build(k,a,'',zap_code_path=code)
                code.write_bytes(data)
                _, info = pack.build(k,a,'',zap_code_path=code)
                exact = int(info['zap_code']['top_of_kernel_data'],16)-fixtures.PA
                a.write_bytes(adt.serialize(fixtures.tree(size=exact))); pack.build(k,a,'',zap_code_path=code)
                a.write_bytes(adt.serialize(fixtures.tree(size=exact-1)))
                with self.assertRaises(ValueError): pack.build(k,a,'',zap_code_path=code)
                pa = int(info['zap_code']['phys'],16)
                for props in ([('A615ZapCode',0,b'old')], [('other',0,struct.pack('<QQ',pa,1))]):
                    a.write_bytes(adt.serialize(fixtures.tree(mmap_props=props)))
                    with self.assertRaises(ValueError): pack.build(k,a,'',zap_code_path=code)
                a.write_bytes(adt.serialize(fixtures.tree()))
                malformed = fixtures.kernel(); struct.pack_into('<I',malformed,36,0); k.write_bytes(malformed)
                with self.assertRaises(ValueError): pack.build(k,a,'',zap_code_path=code)
                k.write_bytes(fixtures.kernel())
            # Synthetic bytes are refused by the real CLI, before replacing output.
            output = root/'out'; output.write_bytes(b'preserved')
            result = subprocess.run([sys.executable,str(fixtures.TOOLS/'mkpayload.py'),str(k),str(a),str(output),'--zap-code',str(code)],capture_output=True)
            self.assertNotEqual(result.returncode,0); self.assertEqual(output.read_bytes(),b'preserved')


if __name__ == '__main__':
    unittest.main()
