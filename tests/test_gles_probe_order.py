#!/usr/bin/env python3
"""Extract the exact probe child/90s ordering function and run typed POSIX seams."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
source=R/'tools/gauguin-gles-probe.c';fixture=R/'tests/fixtures/gles_probe_order.c'
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source,fixture]}
s=source.read_text();start=s.index('static int api_then_late_workload(void)\n');opening=s.index('{',start);depth=0
for end in range(opening,len(s)):
    depth+=(s[end]=='{')-(s[end]=='}')
    if depth==0:break
assert end>opening;unit=fixture.read_text();assert unit.count('@FUNCTION@')==1
unit=unit.replace('@FUNCTION@',s[start:end+1])
with tempfile.TemporaryDirectory(prefix='gles-probe-order-') as td:
    td=Path(td);(td/'unit.c').write_text(unit)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(td/'unit.c'),'-o',str(td/'test')],env=env,check=True)
    subprocess.run([str(td/'test')],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},'inputs changed'
