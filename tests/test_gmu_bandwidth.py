#!/usr/bin/env python3
"""Native GPU BW plan/wire bytes and refusals; no controller or firmware IO."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source141-codex')))/'bsd/dev'
names=['gauguin_gmu_firmware','gauguin_gmu_hfi','gauguin_gmu_memory','cmd_db_snapshot','gauguin_bcm_plan']
sources=[D/(n+'.c') for n in names];fixture=R/'tests/fixtures/gmu-firmware/bandwidth_host.c'
inputs=sources+[D/(n+'.h') for n in names]+[fixture];pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-bandwidth-') as tmp:
 binary=Path(tmp)/'test';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),*map(str,sources),str(fixture),'-o',str(binary)],env=env,check=True)
 subprocess.run([str(binary)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
