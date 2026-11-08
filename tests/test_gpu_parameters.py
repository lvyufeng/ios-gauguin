#!/usr/bin/env python3
"""Real board parameter dispatch and native configured UCHE GMEM aperture."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source179-codex')))/'bsd/dev'
board=D/'gauguin_gmu_board.c';fixture=R/'tests/fixtures/gpu-user/parameters_host.c'
files=[Path(__file__),board,fixture,*[D/(n+s) for n in ['gauguin_gpu_core','gauguin_gpu_memory','gauguin_gmu_memory'] for s in ('.c','.h')],D/'gauguin_gpu_start.h',D/'gauguin_gpu_smmu.h',D/'gauguin_gmu_smmu.h']
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
source=board.read_text();start=re.search(r'^bool sweet_gpu_runtime_parameter\(uint32_t p,uint64_t \*v\)\n',source,re.M);assert start
opening=source.index('{',start.end());depth=0
for end in range(opening,len(source)):
    depth+=(source[end]=='{')-(source[end]=='}')
    if depth==0:break
assert end>opening
unit=fixture.read_text();assert unit.count('@PARAMETER@')==1
unit=unit.replace('@PARAMETER@',source[start.start():end+1])
with tempfile.TemporaryDirectory(prefix='gpu-parameters-') as td:
    td=Path(td);(td/'test.c').write_text(unit)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),
        *[str(D/(n+'.c')) for n in ['gauguin_gpu_core','gauguin_gpu_memory','gauguin_gmu_memory']],
        str(td/'test.c'),'-o',str(td/'test')],env=env,check=True)
    subprocess.run([str(td/'test')],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'inputs changed'
