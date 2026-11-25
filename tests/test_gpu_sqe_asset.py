#!/usr/bin/env python3
"""Exact SQE view with real SHA256, packer descriptors and reserved padding."""
from pathlib import Path
import hashlib,os,re,subprocess,sys,tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_payload_nvt_asset as fixtures
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source149-codex')))/'bsd/dev'
S=D/'gauguin_gpu_sqe_asset.c';H=D/'gauguin_gpu_sqe_asset.h';F=R/'tests/fixtures/gpu-sqe/asset_host.c'
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),S,H,F]}
source=S.read_text();match=re.search(r'(static const uint8_t gsa_expected\[32\]=\{)(.*?)(\n\};)',source,re.S);assert match
pin=bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]{2})',match[2]));assert pin.hex()=='a0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b'
real=os.environ.get('SQE_ASSET_FILE');data=Path(real).read_bytes() if real else bytes((i*23+11)%251 for i in range(32304));assert len(data)==32304
if real:assert hashlib.sha256(data).digest()==pin
else:
 replacement=','.join('0x%02x'%x for x in hashlib.sha256(data).digest())
 source=source[:match.start(2)]+replacement+source[match.end(2):]
source=re.sub(r'^#include .*\n','',source,flags=re.M);fixture=F.read_text();assert fixture.count('@SOURCE@')==1
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-sqe-asset-') as tmp:
 B=Path(tmp);k,a,q,n,z,g=[B/x for x in ['kernel','adt','sqe','nvt','mdt','gmu']]
 k.write_bytes(fixtures.kernel());a.write_bytes(fixtures.adt.serialize(fixtures.tree()));q.write_bytes(data)
 nvt=bytes(range(256))*544;mdt=bytes(range(256))*26+bytes(range(204));gmu=bytes((i*19+7)%251 for i in range(32768))
 n.write_bytes(nvt);z.write_bytes(mdt);g.write_bytes(gmu)
 with patch.object(fixtures.candidate,'SQE_FIRMWARE_SHA256',hashlib.sha256(data).hexdigest()),patch.object(fixtures.candidate,'NVT_FIRMWARE_SHA256',hashlib.sha256(nvt).hexdigest()),patch.object(fixtures.candidate,'ZAP_MDT_SHA256',hashlib.sha256(mdt).hexdigest()),patch.object(fixtures.candidate,'GMU_FIRMWARE_SHA256',hashlib.sha256(gmu).hexdigest()):
  blob,info=fixtures.candidate.build(k,a,'',nvt_firmware_path=n,zap_mdt_path=z,gmu_firmware_path=g,sqe_firmware_path=q)
 mmap=fixtures.layout(blob)['root'].children[0].children[0]
 descriptor=B/'descriptor';descriptor.write_bytes(b''.join(mmap.prop(x) for x in ['A630SQEFirmware','NovatekFirmware','A615ZapMDT','A619GMUFirmware']))
 unit=B/'test.c';binary=B/'test';unit.write_text(fixture.replace('@SOURCE@',source))
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(unit),'-o',str(binary)],env=env,check=True)
 subprocess.run([str(binary),str(descriptor),str(q)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
