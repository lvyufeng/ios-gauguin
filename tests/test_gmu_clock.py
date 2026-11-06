#!/usr/bin/env python3
"""Actual private GMU clock body, typed prerequisite seams and sanitizer checks."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source122-codex')))/'bsd/dev'
source=D/'gauguin_cx_power.c';fixture=R/'tests/fixtures/gmu-clock/clock_host.c'
inputs=[source,fixture,D/'gauguin_gmu_clock.h',D/'gauguin_cx_power.h',D/'gauguin_gcc_votes.h',D/'gauguin_cx_rail.h',D/'gauguin_bcm_transport.h',D/'gauguin_bcm_plan.h']
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
text=source.read_text();marker='/* Same translation unit as CX:'
assert text.count(marker)==1;text=marker+text.split(marker,1)[1]
assert text.endswith('#endif /* GAUGUIN */\n');text=text.removesuffix('#endif /* GAUGUIN */\n')
seams={'uint32_t value=*(volatile uint32_t *)(map+off);':'uint32_t value=fake_read(map,off);',
       '*(volatile uint32_t *)(map+off)=value;':'fake_write(map,off,value);',
       '__asm__ volatile("dmb oshld" ::: "memory");':'/* host read barrier seam */',
       '__asm__ volatile("dmb oshst" ::: "memory");':'/* host store barrier seam */',
       '__asm__ volatile("dsb sy" ::: "memory");':'/* host full barrier seam */'}
for old,new in seams.items():assert text.count(old)==1;text=text.replace(old,new)
assert '__asm__' not in text and '*(volatile' not in text
template=fixture.read_text();assert template.count('\n@SOURCE@\n')==1
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-clock-') as temporary:
    B=Path(temporary);unit=B/'test.c';binary=B/'test';unit.write_text(template.replace('\n@SOURCE@\n','\n'+text+'\n'))
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(unit),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
