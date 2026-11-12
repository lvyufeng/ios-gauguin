"""Strict current-trial ownership-probe readback and handoff log checks."""
import re
def require(ok,message):
    if not ok:raise ValueError(message)
def fnv(data):
    h=14695981039346656037
    for byte in data:h=((h^byte)*1099511628211)&0xffffffffffffffff
    return f'{h:016x}'
def validate(stdout,stderr,kernel,build,core,router):
    require('GAUGUIN OWNED HOST' not in stdout,'host adapter is not hardware evidence')
    require('GAUGUIN OWNED FAIL' not in stdout+stderr,'owned probe failed')
    begin=re.findall(r'^GAUGUIN OWNED begin build=(\w+) core=(\w+) startup_seconds=180 work_seconds=30$',stdout,re.M)
    require(begin==[(build,core)],'one exact native build required')
    identities=re.findall(r'^GAUGUIN OWNED identity gpu=619 chip=06010900 seed=(\d+)$',stdout,re.M)
    require(len(identities)==1 and 0<=int(identities[0])<=0xffffffff,'one bounded seed required');seed=int(identities[0])
    jobs=re.findall(r'^GAUGUIN OWNED job phase=([a-zA-Z-]+) index=(\d+) status=completed(?: gpu_ns=\d+| callback_owner_released=1)$',stdout,re.M)
    phases=['synchronous-fill-copy','deferred-fill-copy','callback-fifo-barrier','clear-A','clear-B','append','error-callback-fifo-barrier','queue-wrapper-released']
    require(jobs==[(p,str(i+1)) for i,p in enumerate(phases)],'job order/count differs')
    expected={}
    for name,value in [('synchronous-fill-copy',seed&255),('deferred-fill-copy',(seed^255)&255),('append',(seed^0x5a)&255)]:
        expected[name]=('4096',str(value),fnv(bytes([value])*4096))
    for i in range(2):
        value=0xff000000
        for k in range(3):
            if (seed^i)&(1<<k):value|=255<<(8*k)
        expected['clear-'+chr(65+i)]=('4096',str(value),fnv(value.to_bytes(4,'little')*4096))
    pixels=re.findall(r'^GAUGUIN OWNED pixels phase=([a-zA-Z-]+) count=(\d+) value=(\d+) hash=([0-9a-f]{16}) PASS$',stdout,re.M)
    require(len(pixels)==5 and len({p[0] for p in pixels})==5 and {p[0]:p[1:] for p in pixels}==expected,'exact readback hashes differ')
    clean=re.findall(r'^GAUGUIN OWNED cleanup phase=([a-z-]+) allocated=0$',stdout,re.M)
    require(clean==['fill-copy','fill-copy','clear','append','refusal','early-queue-release','final'],'cleanup phases differ')
    require(stdout.count('GAUGUIN OWNED refusal callback=1 own_wait=returned owner_released=1 PASS')==1,'error callback missing/duplicate')
    require(stdout.count('GAUGUIN OWNED RESULT PASS jobs=8 callbacks=2 pixel_checks=20480 allocated=0 teardown_requested=1')==1,'terminal result missing/duplicate')
    require(re.findall(r'^GAUGUIN OWNED handoff router=(\w+) hard_mb=128$',stdout,re.M)==[router],'old-router handoff binding differs')
    closes=[tuple(map(int,x)) for x in re.findall(r'SWEET METAL245: root close ready=(\d+) jobs=(\d+) fence=(\d+) epoch=(\d+) clean=(\d+)',kernel)]
    require(len(closes)>=2,'both root owners need kernel close evidence')
    first,second=closes[:2]
    require(first[0]==0 and first[1]==8 and first[2]>0 and first[4]==1,'new-core owner did not close cleanly after eight jobs')
    require(second[0]==1 and second[1]==8 and second[2]>0 and second[3]==first[3]+1 and second[4]==1,'old bootstrap did not complete clean armed handoff')
    return dict(state='owned-core-readback-callback-cleanup-and-handoff-passed',seed=seed,successful_jobs=8,callbacks=2,
                readback_comparisons=20480,root_closes=[first,second],desktop_GPU_composition_qualified=False,physical_FPS_qualified=False)
