#!/usr/bin/env python3
"""Actual b02 consumer with real SHA256 and packer-emitted five-asset ranges."""
from contextlib import ExitStack
from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_payload_nvt_asset as fixtures
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source155-codex')))/'bsd/dev'
S=D/'gauguin_gpu_zap_asset.c'; H=D/'gauguin_gpu_zap_asset.h'; F=R/'tests/fixtures/gpu-zap/asset_host.c'
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),S,H,F]}
source=S.read_text(); match=re.search(r'(static const uint8_t gza_expected\[32\]=\{)(.*?)(\n\};)',source,re.S); assert match
pin=bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]{2})',match[2]))
assert pin.hex()=='61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878'
real=os.environ.get('ZAP_CODE_ASSET_FILE')
data=Path(real).read_bytes() if real else bytes((i*31+5)%251 for i in range(1984)); assert len(data)==1984
if real: assert hashlib.sha256(data).digest()==pin
else:
    replacement=','.join('0x%02x'%x for x in hashlib.sha256(data).digest())
    source=source[:match.start(2)]+replacement+source[match.end(2):]
source=re.sub(r'^#include .*\n','',source,flags=re.M)
fixture=F.read_text(); assert fixture.count('@SOURCE@')==1
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-zap-asset-') as tmp:
    B=Path(tmp); k,a,c=[B/n for n in ('kernel','adt','code')]
    k.write_bytes(fixtures.kernel()); a.write_bytes(fixtures.adt.serialize(fixtures.tree())); c.write_bytes(data)
    old=[('nvt_firmware_path','NVT_FIRMWARE_SHA256',bytes(range(256))*544),
         ('zap_mdt_path','ZAP_MDT_SHA256',bytes(range(256))*26+bytes(range(204))),
         ('gmu_firmware_path','GMU_FIRMWARE_SHA256',bytes((i*19+7)%251 for i in range(32768))),
         ('sqe_firmware_path','SQE_FIRMWARE_SHA256',bytes((i*23+11)%251 for i in range(32304)))]
    with ExitStack() as stack:
        stack.enter_context(patch.object(fixtures.candidate,'ZAP_CODE_SHA256',hashlib.sha256(data).hexdigest()))
        options={}
        for name,key,value in old:
            p=B/name; p.write_bytes(value); options[name]=p
            stack.enter_context(patch.object(fixtures.candidate,key,hashlib.sha256(value).hexdigest()))
        blob,_=fixtures.candidate.build(k,a,'',**options,zap_code_path=c)
    mmap=fixtures.layout(blob)['root'].children[0].children[0]
    descriptor=B/'descriptor'
    descriptor.write_bytes(b''.join(mmap.prop(n) for n in ['A615ZapCode','NovatekFirmware','A615ZapMDT','A619GMUFirmware','A630SQEFirmware']))
    unit=B/'test.c'; binary=B/'test'; unit.write_text(fixture.replace('@SOURCE@',source))
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(unit),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary),str(descriptor),str(c)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
