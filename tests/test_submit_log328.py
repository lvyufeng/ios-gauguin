#!/usr/bin/env python3
"""Check fixed-width refusal parsing with real whole-client dispatch output."""
from pathlib import Path
import hashlib
import importlib.util
import json

W=Path(__file__).resolve().parents[1]
B=W/'research/tmp/gesture-sample-328'
SRC=W/'tools/analyze-submit-reject-log.py'
spec=importlib.util.spec_from_file_location('submit_log328',SRC)
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

def row(values):
    return M.PREFIX+' '.join(format(values[name],'016x' if name in M.U64 else '08x') for name in M.FIELDS)

def main():
    host=B/'dispatch-host-v1/candidate-run.log'
    lines=[line[8:] for line in host.read_text().splitlines() if line.startswith('FIXTURE ')]
    assert len(lines)==7 and all(len(line.encode())+1==235 for line in lines)
    header='SWEET GPU API PERF: valid=1 pending=0 selector=0 queue_ns=0 held_ns=0; completed prefix, elapsed CPU clock only\n'
    api='SWEET GPU API PERF: selector=46 calls=12 failures=7 queue_ns=0 held_ns=0 max_held_ns=0 wait_ns=0; held excludes unlocked wait\n'
    def text(rows):return '\n'.join(rows)+'\n'+header+api
    fixture=text(lines);good=M.analyze(fixture)
    assert good['diagnostic_coverage_qualified'] and good['records']==7
    assert good['stage_counts']=={'1':3,'2':1,'3':1,'10':1,'14':1}
    assert [row(v) for v in good['rows']]==lines
    zero=M.analyze(header+api.replace('failures=7','failures=0'))
    assert zero['diagnostic_coverage_qualified'] and zero['records']==0
    bad=['',fixture.replace(header,''),fixture.replace(api,''),fixture+header,fixture+api,
         fixture.replace('valid=1','valid=0'),fixture.replace('pending=0 selector','pending=1 selector'),
         fixture.replace('failures=7','failures=6'),fixture.replace('failures=7','failures=13'),
         fixture.replace('calls=12','calls=0'),text(lines[1:]),fixture+lines[0]+'\n',
         fixture+M.LIMIT+'\n',fixture+M.LIMIT+'\n'+M.LIMIT+'\n',
         fixture.replace(lines[0],lines[0][:-1]),fixture.replace(lines[0],lines[0]+'0'),
         fixture.replace(lines[0],lines[0].replace('00000001','g0000001',1))]
    for field,value in [('seq',2),('seq',65),('tick',0),('rc',0),('stage',4),('stage',9),('index',1<<32),('tick',1<<64)]:
        values=good['rows'][0].copy();values[field]=value
        bad.append(text([row(values),*lines[1:]]))
    for field in ('tick','token'):
        values=good['rows'][1].copy();values[field]=good['rows'][0][field]
        bad.append(text([lines[0],row(values),*lines[2:]]))
    values=good['rows'][0].copy();values['token']=0
    bad.append(text([row(values),*lines[1:]]))
    for sample in bad:
        assert not M.analyze(sample)['diagnostic_coverage_qualified']
    late=good['rows'][-1].copy();late.update(seq=8,tick=late['tick']+1,token=0)
    decoded=M.analyze(fixture+row(late)+'\n')
    assert decoded['diagnostic_coverage_qualified'] and decoded['post_prefix_records']==1
    cap=[]
    for i in range(1,65):
        value=good['rows'][0].copy();value.update(seq=i,tick=1000+i,token=i);cap.append(row(value))
    captext='\n'.join(cap)+'\n'+header+api.replace('calls=12 failures=7','calls=64 failures=64')
    assert M.analyze(captext)['diagnostic_coverage_qualified']
    limited=M.analyze(captext+M.LIMIT+'\n')
    assert not limited['diagnostic_coverage_qualified'] and limited['records']==64 and limited['limit_markers']==1
    assert len((json.dumps(limited,indent=2)+'\n').encode())<131072
    result=dict(state='GESTURE328-fixed-width-diagnostic-parser-passed',real_host_rows=7,positive_cases=4,
                negative_cases=len(bad)+1,full_64_record_bound_checked=True,post_prefix_rows_distinguished=True,
                maximum_record_bytes=235,device_commands=0,
                input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SRC,Path(__file__),host)})
    (B/'submit-log-test.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':
    main()
