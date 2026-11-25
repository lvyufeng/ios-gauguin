#!/usr/bin/env python3
"""Reject malformed phase joins, preserve loss/edge bounds, decode actual prior logs."""
from pathlib import Path
import copy,hashlib,importlib.util,json
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/bo-allocation-333'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ui=module('ui333',W/'tools/ui_trace_log.py');parser=module('allocation333',W/'tools/analyze-bo-allocation-log.py')
    def event(kind,flags,a=0,b=0,c=0,token=7,pid=57):return dict(kind=kind,id=token,pid=pid,flags=flags,a=a,b=b,c=c)
    good=[event(10,0x42,101,102),event(32,1,17,2,1234),event(32,2,16384),event(32,3,1),event(32,4),event(32,5,16384,9,2),event(32,6,0,9,0),event(11,0,180,0x42)]
    def log(rows,lost=0,reason=1):
        lines=[f'SWEET UI254 H: version=1 count={len(rows)} reason={reason} lost={lost} start=100 end=1000 numer=1000 denom=1 which=3 gestures=3']
        for i,row in enumerate(rows,1):
            tick=102+10*i
            row=dict(row)
            if row['kind']==11 and row['a']==180:row['a']=tick-2
            lines.append('SWEET UI254 E: '+f'seq={i} tick={tick} '+' '.join(f'{k}={v}' for k,v in row.items()))
        lines.append(f'SWEET UI254 F: count={len(rows)} lost={lost}; CPU-clock capture only')
        return '\n'.join(lines)
    def analyze(rows,**kwargs):return parser.analyze(log(rows,**kwargs),ui)
    result=analyze(good);assert result['coverage_qualified'] and result['successful_count']==1
    assert result['rows'][0]['durations_us']==dict(request_queue=1,phase_total=50,dispatch_gate=10,backing_allocation=10,zeroing=10,mapping_preparation=10,synchronization_and_return=10)
    assert not analyze(good,lost=1)['coverage_qualified']
    assert not analyze(good,reason=2)['coverage_qualified']
    partial=good[:-1];assert analyze(partial)['partial_count']==1 and not analyze(partial)['coverage_qualified']
    assert analyze(good[1:])['partial_count']==1
    # Two valid failures, gated before allocation and out of backing memory.
    failed=[good[0],good[1],event(32,6,3,0,1),event(11,3,180,0x42)]
    out=analyze(failed);assert out['failed_count']==1 and not out['coverage_qualified']
    failed2=[good[0],good[1],good[2],event(32,3,0),event(32,6,3,0,2),event(11,3,180,0x42)]
    assert analyze(failed2)['failed_count']==1
    invalid=[]
    def mutate(index,key,value):
        rows=copy.deepcopy(good);rows[index][key]=value;invalid.append(rows)
    for args in [(1,'flags',0),(1,'flags',7),(1,'id',0),(1,'pid',0),(3,'pid',58),(2,'flags',1),(5,'flags',4),(6,'a',3),(7,'flags',3),(6,'c',10),(1,'c',0),(2,'a',4096),(3,'a',2),(3,'a',0),(5,'a',32768),(5,'b',0),(5,'c',1),(6,'b',10),(6,'c',9),(2,'b',1),(4,'a',1),(4,'c',1),(0,'a',0),(0,'b',99),(7,'a',160),(1,'a',67108865)]:mutate(*args)
    invalid.extend([good[:3]+good[4:],good[:1]+good[2:],good[:-2]+good[-1:],good[:2]+[copy.deepcopy(good[1])]+good[2:]])
    for index,rows in enumerate(invalid):
        try:analyze(rows)
        except ValueError:pass
        else:raise AssertionError(('accepted malformed phases',index))
    missing=good[:3]+good[4:];assert not analyze(missing,lost=1)['coverage_qualified']
    prior=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-present-retry-worktree-20261116/research/tmp/present-retry-332/execution/kernel.log')
    observed=parser.analyze(prior.read_text(errors='replace'),ui)
    assert not observed['coverage_qualified'] and observed['complete_count']==0 and observed['missing_metadata_tokens']
    inputs=[Path(__file__),W/'tools/ui_trace_log.py',W/'tools/analyze-bo-allocation-log.py',prior]
    record=dict(state='passed-BO333-allocation-parser',positive_cases=3,negative_cases=len(invalid),loss_and_capacity_unqualified=True,edge_partials_preserved=True,actual332_log_rejected=True,physical_FPS_qualified=False,input_pins={str(p):sha(p) for p in inputs},device_commands=0)
    with (B/'allocation-log-test.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in record.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
