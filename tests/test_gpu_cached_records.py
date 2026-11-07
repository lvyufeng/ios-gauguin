#!/usr/bin/env python3
"""Actual success-record batching against fixed164 text/persistence behavior."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source165-codex')))/'bsd/dev'
S=Path(os.environ.get('GPU_CACHED_BOARD_SOURCE',str(D/'gauguin_gmu_board.c')))
F=R/'tests/fixtures/gpu-cached-records/records_host.c';B=F.with_name('baseline164.inc')
names=['gmb_record','gmb_record_cached','ggb_records','ggx_records','ggc_records','ggq_records']
def function(text,name):
    a=text.index('static void '+name+'(');b=text.index('{',a);depth=0
    for i in range(b,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':
            depth-=1
            if not depth:return text[a:i+1]
    raise AssertionError(name)
source=S.read_text();bodies='\n\n'.join(function(source,n) for n in names)
assert hashlib.sha256(B.read_bytes()).hexdigest()=='2c7d7fefd069deb3aa34ffdac129c6cc20f69fbd7f0e5fef4ea5f063ce156658'
base=B.read_text();assert 'baseline_gmb_record' in base and 'baseline_ggq_records' in base
fixture=F.read_text();m=re.search(r'static struct driver_state \{(.*?)\n\} state;',fixture,re.S);assert m
# Generate aliases for the actual driver's private global names. This changes
# only storage spelling, not any selected production function body.
fields=re.findall(r'\b((?:ggb|gmb|ggx|ggc|ggq)_[a-z_]+)\s*(?=[;,])',m[1]);assert len(fields)==len(set(fields)) and len(fields)>25
aliases='\n'.join('#define '+n+' state.'+n for n in fields)
for token in ['@ALIASES@','@BASELINE@','@SOURCE@']:assert fixture.count(token)==1
unit=fixture.replace('@ALIASES@',aliases).replace('@BASELINE@',base).replace('@SOURCE@',bodies)
inputs=[Path(__file__),F,B,S,*sorted(D.glob('gauguin_*.h'))]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-cached-records-') as tmp:
    c=Path(tmp)/'test.c';out=Path(tmp)/'test';c.write_text(unit)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-I'+str(D),str(c),'-o',str(out)],env=env,check=True)
    subprocess.run([str(out)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
