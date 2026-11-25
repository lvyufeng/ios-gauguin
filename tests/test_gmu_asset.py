#!/usr/bin/env python3
"""Actual asset consumer, packer-emitted range and platform SHA256 implementation."""
from pathlib import Path
import hashlib,os,re,subprocess,sys,tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_payload_nvt_asset as fixtures
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source123-codex')))/'bsd/dev'
S=D/'gauguin_gmu_asset.c';H=D/'gauguin_gmu_asset.h';F=R/'tests/fixtures/gmu-firmware/asset_host.c'
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [S,H,F]}
source=S.read_text();match=re.search(r'(static const uint8_t gma_expected\[32\]=\{)(.*?)(\n\};)',source,re.S);assert match
pin=bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]{2})',match[2]))
assert pin.hex()=='9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e'
real=os.environ.get('GMU_ASSET_FILE')
data=Path(real).read_bytes() if real else bytes((i*19+7)%251 for i in range(32768))
assert len(data)==32768
if real:assert hashlib.sha256(data).digest()==pin
else:
    # Only the temporary synthetic host TU changes its expected digest. It
    # still executes actual SHA256 via CommonCrypto; native source/pin stay exact.
    replacement=','.join('0x%02x'%x for x in hashlib.sha256(data).digest())
    source=source[:match.start(2)]+replacement+source[match.end(2):]
source=re.sub(r'^#include .*\n','',source,flags=re.M)
fixture=F.read_text();assert fixture.count('@SOURCE@')==1
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-asset-') as tmp:
    B=Path(tmp);k,a,g=[B/n for n in ('kernel','adt','firmware')]
    k.write_bytes(fixtures.kernel());a.write_bytes(fixtures.adt.serialize(fixtures.tree()));g.write_bytes(data)
    with patch.object(fixtures.candidate,'GMU_FIRMWARE_SHA256',hashlib.sha256(data).hexdigest()):
        blob,info=fixtures.candidate.build(k,a,'',gmu_firmware_path=g)
    layout=fixtures.layout(blob);mmap=layout['root'].children[0].children[0]
    descriptor=B/'descriptor';descriptor.write_bytes(mmap.prop('A619GMUFirmware'))
    unit=B/'test.c';binary=B/'test';unit.write_text(fixture.replace('@SOURCE@',source))
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(unit),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary),str(descriptor),str(g)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
