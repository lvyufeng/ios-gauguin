#!/usr/bin/env python3
"""Actual low-owner handoff/copy code with real SHA256 and inaccessible bounds."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source167-codex')))/'bsd/dev'
S=D/'gauguin_pas_stage.c';F=R/'tests/fixtures/gpu-zap/owner_host.c'
files=[Path(__file__),S,F,D/'gauguin_pas_stage.h',D/'gauguin_gpu_zap.h',D/'gauguin_gpu_zap_asset.h']
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
real=os.environ.get('ZAP_MDT_ASSET_FILE');mdt=Path(real).read_bytes() if real else bytes(i%251 for i in range(6860));assert len(mdt)==6860
code_path=os.environ.get('ZAP_CODE_ASSET_FILE');code=Path(code_path).read_bytes() if code_path else bytes((i*31+5)%251 for i in range(1984));assert len(code)==1984
if code_path:assert hashlib.sha256(code).hexdigest()=='61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878'
source=S.read_text();pattern=r'(static const uint8_t pst_expected\[SHA256_DIGEST_LENGTH\] = \{)(.*?)(\n\};)';match=re.search(pattern,source,re.S);assert match
pin=bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]{2})',match[2]));assert pin.hex()=='6f2a0e35325097f98fded6123d755266cdbb44caa932be61251b65b5c516ac7b'
if real:assert hashlib.sha256(mdt).digest()==pin
else:source=source[:match.start(2)]+','.join('0x%02x'%x for x in hashlib.sha256(mdt).digest())+source[match.end(2):]
source=re.sub(r'^#include .*\n','',source,flags=re.M);barrier='__asm__ volatile("dsb sy" ::: "memory");';assert source.count(barrier)==2;source=source.replace(barrier,'host_dsb();');assert '__asm__' not in source
fixture=F.read_text();assert fixture.count('@SOURCE@')==1
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-zap-owner-') as tmp:
 B=Path(tmp);u=B/'unit.c';b=B/'test';m=B/'mdt';c=B/'code';m.write_bytes(mdt);c.write_bytes(code);u.write_text(fixture.replace('@SOURCE@',source))
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(u),'-o',str(b)],env=env,check=True)
 subprocess.run([str(b),str(m),str(c)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
