#!/usr/bin/env python3
"""Use real host-dispatch diagnostic rows and reject missing/inconsistent prefixes."""
from pathlib import Path
import hashlib,importlib.util,json,re
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/submit-reject-327';SRC=W/'tools/analyze-submit-reject-log.py'
s=importlib.util.spec_from_file_location('reject',SRC);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 host=B/'dispatch-host-v2/candidate-run.log';lines=[line[len('FIXTURE '):]for line in host.read_text().splitlines()if line.startswith('FIXTURE ')]
 assert len(lines)==7
 header='SWEET GPU API PERF: valid=1 pending=0 selector=0 queue_ns=0 held_ns=0; completed prefix, elapsed CPU clock only\n'
 api='SWEET GPU API PERF: selector=46 calls=12 failures=7 queue_ns=0 held_ns=0 max_held_ns=0 wait_ns=0; held excludes unlocked wait\n'
 fixture='\n'.join(lines)+'\n'+header+api;good=m.analyze(fixture)
 assert good['diagnostic_coverage_qualified'] and good['records']==7 and good['stage_counts']=={'1':3,'2':1,'3':1,'10':1,'14':1}
 zero=m.analyze(header+api.replace('failures=7','failures=0'));assert zero['diagnostic_coverage_qualified'] and zero['state']=='no-submit-refusals-in-counter-prefix'
 bad=['',fixture.replace(header,''),fixture.replace(api,''),fixture+header,fixture+api,fixture.replace('valid=1','valid=0'),fixture.replace('pending=0 selector','pending=1 selector'),fixture.replace('failures=7','failures=6'),fixture.replace('failures=7','failures=13'),fixture.replace('calls=12','calls=0'),fixture.replace('seq=1 ','seq=2 '),fixture+lines[0]+'\n',fixture.replace(lines[0]+'\n',''),fixture.replace('rc=00000001','rc=00000000'),fixture.replace('stage=10 ','stage=9 '),fixture.replace('stage=10 ','stage=4 '),fixture.replace('index=4294967295','index=4294967296'),fixture.replace('tick=','tick=-'),fixture+ m.LIMIT+'\n',fixture+m.LIMIT+'\n'+m.LIMIT+'\n',fixture.replace('rc=','result='),fixture.replace('seq=1','seq='+('1'*512)),fixture.replace(lines[1],lines[1].replace('tick='+str(good['rows'][1]['tick']),'tick='+str(good['rows'][0]['tick']))),fixture.replace(lines[1],lines[1].replace('token='+str(good['rows'][1]['token']),'token='+str(good['rows'][0]['token'])))]
 for text in bad:assert not m.analyze(text)['diagnostic_coverage_qualified']
 last=good['rows'][-1];late=lines[-1]
 late=re.sub(r'seq=\d+', 'seq=8',late);late=re.sub(r'tick=\d+','tick='+str(last['tick']+1),late);late=re.sub(r'token=\d+','token=0',late)
 late_result=m.analyze(fixture+late+'\n');assert late_result['diagnostic_coverage_qualified']and late_result['post_prefix_records']==1
 cap=[]
 for i in range(1,65):
  row=lines[0];row=re.sub(r'seq=\d+','seq='+str(i),row);row=re.sub(r'tick=\d+','tick='+str(1000+i),row);row=re.sub(r'token=\d+','token='+str(i),row);cap.append(row)
 saturated='\n'.join(cap)+'\n'+m.LIMIT+'\n'+header+api.replace('calls=12 failures=7','calls=80 failures=80')
 x=m.analyze(saturated);assert x['records']==64 and x['limit_markers']==1 and not x['diagnostic_coverage_qualified']
 assert len((json.dumps(x,indent=2)+'\n').encode())<131072
 r=dict(state='SUBMIT327-diagnostic-parser-passed',positive_cases=3,negative_cases=len(bad)+1,real_host_rows=7,full_64_record_bound_checked=True,missing_rows_not_qualified=True,post_prefix_rows_distinguished=True,device_commands=0,input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in(SRC,Path(__file__),host)})
 with (B/'submit-log-test.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in r.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
