#!/usr/bin/env python3
"""Synthetic legacy GMU packaging; no CLI bypass of the real production pin."""
import hashlib
from pathlib import Path
import struct,subprocess,sys,tempfile,unittest,warnings
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_payload_nvt_asset as fixtures
pack=fixtures.candidate;adt=fixtures.adt
class PayloadTests(unittest.TestCase):
    def test_production_pin(self):
        self.assertEqual(pack.GMU_FIRMWARE_SIZE,32768)
        self.assertEqual(pack.GMU_FIRMWARE_SHA256,'9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e')
    def test_layout_bounds_and_invalid_assets(self):
        warnings.simplefilter('ignore',ResourceWarning)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);k,a,g,z,n,rd=[root/s for s in ('kernel','adt','gmu','mdt','nvt','rd')]
            k.write_bytes(fixtures.kernel());a.write_bytes(adt.serialize(fixtures.tree()))
            gmu=bytes((i*17+3)%251 for i in range(32768));g.write_bytes(gmu)
            mdt=bytes(range(256))*26+bytes(range(204));self.assertEqual(len(mdt),6860);z.write_bytes(mdt)
            nvt=bytes(range(256))*544;n.write_bytes(nvt);rd.write_bytes(b'R'*17001)
            with patch.object(pack,'GMU_FIRMWARE_SHA256',hashlib.sha256(gmu).hexdigest()), \
                 patch.object(pack,'ZAP_MDT_SHA256',hashlib.sha256(mdt).hexdigest()), \
                 patch.object(pack,'NVT_FIRMWARE_SHA256',hashlib.sha256(nvt).hexdigest()):
                for ramdisk in (None,rd):
                    for touch in (None,n):
                        for metadata in (None,z):
                            before,_=pack.build(k,a,'',ramdisk,touch,False,metadata)
                            base=fixtures.layout(before)
                            for pas in (False,True):
                                blob,info=pack.build(k,a,'',ramdisk,touch,pas,metadata,g)
                                layout=fixtures.layout(blob);self.assertEqual(len(layout['segs']),len(base['segs'])+1)
                                for old,new in zip(base['segs'],layout['segs']):
                                    self.assertEqual(old[:2],new[:2]);self.assertEqual(before[old[2]:old[2]+old[3]],blob[new[2]:new[2]+new[3]])
                                va,size,off,stored=layout['segs'][-1]
                                self.assertEqual((va,size,stored),(base['end'],32768,32768));self.assertEqual(blob[off:off+stored],gmu)
                                mmap=layout['root'].children[0].children[0]
                                pa,raw=struct.unpack('<QQ',mmap.prop('A619GMUFirmware'))
                                self.assertEqual((pa,raw),(fixtures.PA+va-layout['virt'],32768))
                                self.assertEqual(layout['entry'],base['entry'])
                                top=(pa+32768+layout['adt_size']+16383)//16384*16384+16384
                                for key in ('gmu_firmware','nvt_firmware','zap_metadata'):
                                    if key in info:self.assertEqual(int(info[key]['top_of_kernel_data'],16),top)
                                if pas:
                                    self.assertEqual(len(blob),info['low_pas_request']['tail_offset']+0x200000)
                                    self.assertEqual(blob[-0x200000:],bytes(0x200000))
                for value in (gmu[:-1],gmu+b'X',b'X'+gmu[1:]):
                    g.write_bytes(value)
                    with self.assertRaisesRegex(ValueError,'size/SHA256'):pack.build(k,a,'',gmu_firmware_path=g)
                g.write_bytes(gmu)
                _,info=pack.build(k,a,'',gmu_firmware_path=g)
                exact=int(info['gmu_firmware']['top_of_kernel_data'],16)-fixtures.PA
                a.write_bytes(adt.serialize(fixtures.tree(size=exact)));pack.build(k,a,'',gmu_firmware_path=g)
                a.write_bytes(adt.serialize(fixtures.tree(size=exact-1)))
                with self.assertRaises(ValueError):pack.build(k,a,'',gmu_firmware_path=g)
                for props in ([('A619GMUFirmware',0,b'old')],[('other',0,struct.pack('<QQ',int(info['gmu_firmware']['phys'],16),1))]):
                    a.write_bytes(adt.serialize(fixtures.tree(mmap_props=props)))
                    with self.assertRaises(ValueError):pack.build(k,a,'',gmu_firmware_path=g)
            a.write_bytes(adt.serialize(fixtures.tree()));out=root/'out';out.write_bytes(b'preserved')
            result=subprocess.run([sys.executable,str(fixtures.TOOLS/'mkpayload.py'),str(k),str(a),str(out),'--gmu-firmware',str(g)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(out.read_bytes(),b'preserved')
if __name__=='__main__':unittest.main()
