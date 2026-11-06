#!/usr/bin/env python3
"""Execute actual PE GMU/SMMU interrupt guard with typed GIC/translation seams."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
S=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source122-codex')))/'pexpert/arm/pe_fiq.c'
F=R/'tests/fixtures/gmu-board/irq_host.c'
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [S,F]}
text=S.read_text();m=re.search(r'^bool\nsweet_gmu_irq_quiet\([^;]+?\)\n\{',text,re.M);assert m
begin=text.index('{',m.start());depth=0;end=None
for i in range(begin,len(text)):
    if text[i]=='{':depth+=1
    elif text[i]=='}':
        depth-=1
        if not depth:end=i+1;break
assert end;body=text[m.start():end]
barrier='__asm__ volatile("dmb oshld" ::: "memory");';assert body.count(barrier)==1
body=body.replace(barrier,'read_barrier();');assert '__asm__' not in body
fixture=F.read_text();assert fixture.count('@SOURCE@')==1
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-irq-') as tmp:
    unit=Path(tmp)/'test.c';binary=Path(tmp)/'test';unit.write_text(fixture.replace('@SOURCE@',body))
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(unit),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
