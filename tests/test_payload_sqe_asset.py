#!/usr/bin/env python3
"""Synthetic pinned SQE packaging; all old assets, padding and CLI refusals."""
import hashlib
from pathlib import Path
import struct,subprocess,sys,tempfile,unittest,warnings
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_payload_nvt_asset as fixtures
pack=fixtures.candidate;adt=fixtures.adt
class PayloadTests(unittest.TestCase):
 def test_production_pin(self):
  self.assertEqual(pack.SQE_FIRMWARE_SIZE,32304)
  self.assertEqual(pack.SQE_FIRMWARE_SHA256,'a0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b')
 def test_layout_and_refusals(self):
  warnings.simplefilter('ignore',ResourceWarning)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);k,a,q,n,z,g,rd=[root/s for s in ['kernel','adt','sqe','nvt','mdt','gmu','rd']]
   k.write_bytes(fixtures.kernel());a.write_bytes(adt.serialize(fixtures.tree()));rd.write_bytes(b'R'*17001)
   sqe=bytes((i*23+11)%251 for i in range(32304));nvt=bytes(range(256))*544;mdt=bytes(range(256))*26+bytes(range(204));gmu=bytes((i*19+7)%251 for i in range(32768))
   q.write_bytes(sqe);n.write_bytes(nvt);z.write_bytes(mdt);g.write_bytes(gmu)
   with patch.object(pack,'SQE_FIRMWARE_SHA256',hashlib.sha256(sqe).hexdigest()),patch.object(pack,'NVT_FIRMWARE_SHA256',hashlib.sha256(nvt).hexdigest()),patch.object(pack,'ZAP_MDT_SHA256',hashlib.sha256(mdt).hexdigest()),patch.object(pack,'GMU_FIRMWARE_SHA256',hashlib.sha256(gmu).hexdigest()):
    for ramdisk in (None,rd):
     for touch in (None,n):
      for metadata in (None,z):
       for firmware in (None,g):
        before,_=pack.build(k,a,'',ramdisk,touch,False,metadata,firmware);base=fixtures.layout(before)
        for pas in (False,True):
         blob,info=pack.build(k,a,'',ramdisk,touch,pas,metadata,firmware,q);layout=fixtures.layout(blob)
         self.assertEqual(len(layout['segs']),len(base['segs'])+1)
         for old,new in zip(base['segs'],layout['segs']):
          self.assertEqual(old[:2],new[:2]);self.assertEqual(before[old[2]:old[2]+old[3]],blob[new[2]:new[2]+new[3]])
         va,size,off,stored=layout['segs'][-1];self.assertEqual((va,size,stored),(base['end'],32768,32768))
         self.assertEqual(blob[off:off+32304],sqe);self.assertEqual(blob[off+32304:off+32768],bytes(464))
         mmap=layout['root'].children[0].children[0];pa,raw=struct.unpack('<QQ',mmap.prop('A630SQEFirmware'))
         self.assertEqual((pa,raw),(fixtures.PA+va-layout['virt'],32304));self.assertEqual(layout['entry'],base['entry'])
         top=(pa+32768+layout['adt_size']+16383)//16384*16384+16384
         for key in ['sqe_firmware','gmu_firmware','zap_metadata','nvt_firmware']:
          if key in info:self.assertEqual(int(info[key]['top_of_kernel_data'],16),top)
         if pas:self.assertEqual(len(blob),info['low_pas_request']['tail_offset']+0x200000);self.assertEqual(blob[-0x200000:],bytes(0x200000))
    for data in [sqe[:-1],sqe+b'X',bytes([sqe[0]^1])+sqe[1:],sqe[:-1]+bytes([sqe[-1]^1])]:
     q.write_bytes(data)
     with self.assertRaisesRegex(ValueError,'size/SHA256'):pack.build(k,a,'',sqe_firmware_path=q)
    q.write_bytes(sqe);_,info=pack.build(k,a,'',sqe_firmware_path=q);exact=int(info['sqe_firmware']['top_of_kernel_data'],16)-fixtures.PA
    a.write_bytes(adt.serialize(fixtures.tree(size=exact)));pack.build(k,a,'',sqe_firmware_path=q)
    a.write_bytes(adt.serialize(fixtures.tree(size=exact-1)))
    with self.assertRaises(ValueError):pack.build(k,a,'',sqe_firmware_path=q)
    for props in [[('A630SQEFirmware',0,b'old')],[('other',0,struct.pack('<QQ',int(info['sqe_firmware']['phys'],16),1))]]:
     a.write_bytes(adt.serialize(fixtures.tree(mmap_props=props)))
     with self.assertRaises(ValueError):pack.build(k,a,'',sqe_firmware_path=q)
   a.write_bytes(adt.serialize(fixtures.tree()));out=root/'out';out.write_bytes(b'preserved')
   result=subprocess.run([sys.executable,str(fixtures.TOOLS/'mkpayload.py'),str(k),str(a),str(out),'--sqe-firmware',str(q)],capture_output=True)
   self.assertNotEqual(result.returncode,0);self.assertEqual(out.read_bytes(),b'preserved')
if __name__=='__main__':unittest.main()
