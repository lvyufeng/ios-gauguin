#!/usr/bin/env python3
"""Require eight absolute-uptime sample rounds; reject the actual old late schedule."""
from pathlib import Path
import hashlib
import importlib.util
import json

W=Path(__file__).resolve().parents[1]
B=W/'research/tmp/gesture-sample-328'
SRC=W/'tools/analyze-process-samples328.py'
spec=importlib.util.spec_from_file_location('process_log328',SRC)
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

def fixture(numer=1,denom=1,late_ns=0):
    out=[M.LEGACY_CONFIG,M.CONFIG]
    for i in range(8):
        tick=((220+6*i)*1000000000+late_ns)*denom//numer
        out += [f'SMP328 begin cycle={i} tick={tick}',f'SMP --- sample {i}']
        for j,name in enumerate(M.TARGETS):
            out += [f'SMP {name}[{26+j}] slide 0x1000 mh 0x100000',
                    f'SMP {name} t0 tid {100+j} st 3 ev 0x0 wr 0 pc 0x2000 lr 0x3000 sp 0x4000',
                    f'SMP {name} t0 bt 0x2000 0x3000']
        out += [f'SMP328 end cycle={i} tick={tick+1000000*denom//numer} targets=2 duplicates=0']
    return '\n'.join(out)+'\n'

def main():
    for numer,denom,late in ((1,1,0),(625,12,0),(625,12,1000000000)):
        good=M.summarize(M.parse(fixture(numer,denom,late)),numer,denom)
        assert good['complete'] and good['absolute_uptime_qualified'] and not good['deadline_errors']
        assert good['available_register_samples']==16 and good['profile']==328
    base=fixture()
    bad=[(base,None,None),(fixture(late_ns=1000000001),1,1),(fixture(late_ns=-1),1,1),
         (base.replace(M.CONFIG+'\n',''),1,1),(base.replace('targets=2 duplicates=0','targets=2 duplicates=1'),1,1),
         (base.replace('SMP328 begin cycle=1','SMP328 begin cycle=2'),1,1),
         (base.replace('SMP328 end cycle=7','SMP328 end cycle=8'),1,1),
         (base.replace('max_threads=64','max_threads=65'),1,1)]
    for text,numer,denom in bad:
        try:result=M.summarize(M.parse(text),numer,denom)
        except ValueError:continue
        assert not result['complete']
    refused=M.summarize(M.parse(M.LEGACY_CONFIG+'\n'+M.CONFIG+'\nSMP328 refused: reason=deadline cycle=0\n'),1,1)
    assert not refused['complete'] and refused['refused']==['deadline:0']
    old=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-submit-reject-worktree-20261115/research/tmp/submit-reject-327/execution/kernel.log')
    ui=old.parent/'ui-trace.json'
    h=json.loads(ui.read_text())['header']
    # Deliberately relabel an in-memory fixture while retaining actual327 ticks;
    # the new validator must detect that those samples are45 seconds too late.
    legacy_config='SMP316 armed: targets=SpringBoard,backboardd delay=220 interval=6 count=8 max_targets=2 max_threads=64 frames=16 coherent_frames=0'
    text=old.read_text().replace(legacy_config,M.CONFIG).replace('SMP armed: SpringBoard,backboardd delay=220 interval=6 count=8',M.LEGACY_CONFIG).replace('SMP316 ','SMP328 ')
    rejected=M.summarize(M.parse(text),h['numer'],h['denom'])
    assert not rejected['complete'] and len(rejected['deadline_errors'])==8
    result=dict(state='GESTURE328-absolute-sample-window-parser-passed',positive_cases=3,negative_cases=len(bad)+2,
                real327_wrong_origin_rejected=True,real327_deadline_errors=8,device_commands=0,
                original327_log_unchanged=True,input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),SRC,old,ui)})
    (B/'process-log-test.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':
    main()
