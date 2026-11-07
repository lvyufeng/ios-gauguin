#!/usr/bin/env python3
"""Actual GPU context transaction, independent walks and callback failures."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent;D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source161-codex')))/'bsd/dev'
F=R/'tests/fixtures/gpu-smmu/smmu_host.c';OLD=R/'tests/fixtures/gmu-smmu/smmu_host.c'
sources=[D/(n+'.c') for n in ['gauguin_gpu_smmu','gauguin_gpu_data','gauguin_gpu_memory','gauguin_gmu_smmu','gauguin_gmu_memory']]
inputs=[F,OLD,*sources,*[p.with_suffix('.h') for p in sources]];pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
old=OLD.read_text();assert old.count('int main(void)')==1;old=old.replace('int main(void)','void gmu_fixture_entry(void)')
code=F.read_text();assert code.count('@GMU_FIXTURE@')==1;code=code.replace('@GMU_FIXTURE@',old)
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gpu-smmu-') as tmp:
 unit=Path(tmp)/'test.c';binary=Path(tmp)/'test';unit.write_text(code)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-I'+str(D),*map(str,sources),str(unit),'-o',str(binary)],env=env,check=True);subprocess.run([str(binary)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
