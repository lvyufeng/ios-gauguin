#!/usr/bin/env python3
"""Actual live BO allocation/release boundaries, independent of submit/byte caps."""
from pathlib import Path
import hashlib,os,subprocess,sys,tempfile
R=Path(__file__).resolve().parent.parent
control=Path(os.environ.get('GPU_BO_CONTROL_TREE',R/'.deps-cache/p0-20261105/source208-codex'))
candidate=Path(os.environ.get('GPU_USER_TREE',R/'.deps-cache/p0-20261105/source211-codex'))
cpp='iokit/Kernel/arm/GauguinGPU.cpp';header='bsd/dev/gauguin_gpu_runtime.h'
paths=[Path(__file__),R/'tests/test_gpu_iokit.py',R/'tests/fixtures/gpu-user/iokit_host.cpp',*(root/rel for root in (control,candidate) for rel in (cpp,header,'bsd/dev/gauguin_gpu_runtime.c','iokit/Kernel/arm/SweetSurface.h'))]
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
# Reverse only the seven private-table bounds. The submit count remains256;
# every hardware check, mapping, close, fence and DMA retention path is exact.
a=(control/cpp).read_text();b=(candidate/cpp).read_text()
b=b.replace('GGR_MAX_CLIENT_BUFFERS','GGR_MAX_BUFFERS').replace('flag changes or success-path logging. Private live-object capacity\n         * is independent of the unchanged per-submit BO/byte limits.', 'quota/flag changes or success-path logging.')
assert a==b,'unexpected transport changes outside private table capacity'
assert (control/'bsd/dev/gauguin_gpu_runtime.c').read_bytes()==(candidate/'bsd/dev/gauguin_gpu_runtime.c').read_bytes()
text=(candidate/header).read_text();assert '#define GGR_MAX_CLIENT_BUFFERS 1024u' in text
start=text.index('/* A submission may refer to at most256 BOs;');end=text.index('#define GGR_MAX_QUEUES',start)
assert text[:start]+'#define GGR_MAX_BUFFERS 256u\n'+text[end:]==(control/header).read_text()
for kind,tree in [('baseline',control),('candidate',candidate)]:
    p=subprocess.run([sys.executable,str(R/'tests/test_gpu_iokit.py')],env=dict(os.environ,GPU_USER_TREE=str(tree),GPU_USER_REQUIRE_SLOTS='1'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if kind=='baseline':
        assert p.returncode!=0 and b'error:' not in p.stdout and b'BO new failed attempt=257 size=16384 rc=2' in p.stdout,p.stdout[-2000:]
        print('Baseline rejects exactly the257th live BO; actual production transport, not a compile failure')
    else:
        assert p.returncode==0,p.stdout[-4000:]
        print(p.stdout.decode(),end='')
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
print('PASS unchanged submit256/byte256MiB/mapping/fence/failure-retention paths; three1024-slot allocate/recycle cycles')
