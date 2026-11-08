#!/usr/bin/env python3
"""Execute an immutable local stage profile once and record actual inner exits.

Jobs explicitly declared independent run concurrently, each without a shell.
An existing claim is observed, never executed again. Intended for the DSH
executor; profile inputs/logs/results stay reviewable after failures.
"""
from pathlib import Path
import concurrent.futures,hashlib,json,os,subprocess,sys,time
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert len(sys.argv)==2
    profile_path=Path(sys.argv[1]).resolve();profile=json.loads(profile_path.read_text())
    cwd=Path(profile['cwd']).resolve();out=Path(profile['out']).resolve()
    assert out.is_relative_to(cwd/'research/tmp')
    out.mkdir(parents=True,exist_ok=True)
    claim=out/'claim.json';result=out/'result.json'
    try:handle=claim.open('x')
    except FileExistsError:
        if result.exists():
            r=json.loads(result.read_text());print(json.dumps({'duplicate_request':True,'executed_again':False,'inner_exits':r['inner_exits'],'exit':r['exit']}));return r['exit']
        print(json.dumps({'duplicate_request':True,'executed_again':False,'state':'claimed-observe-existing-process-only'}));return 75
    record={'state':'claimed','dispatcher_pid':os.getpid(),'profile':str(profile_path),
        'profile_sha256':sha(profile_path),'dispatcher_sha256':sha(Path(__file__)),'started_time':time.time()}
    with handle:handle.write(json.dumps(record,indent=2)+'\n')
    def execute(job):
        log=out/(job['name']+'.log');assert not log.exists()
        with log.open('x') as f:
            p=subprocess.run(job['argv'],cwd=cwd,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',**job.get('env',{})),stdout=f,stderr=subprocess.STDOUT)
        return {'name':job['name'],'inner_exit':p.returncode,'log':str(log),'log_sha256':sha(log)}
    try:
        for name,pin in profile['input_pins'].items():assert sha(cwd/name)==pin,('input mismatch',name)
        jobs=profile['jobs'];assert jobs and len({j['name'] for j in jobs})==len(jobs)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(jobs),profile.get('parallelism',1))) as executor:
            rows=list(executor.map(execute,jobs))
        unchanged=sha(profile_path)==record['profile_sha256'] and sha(Path(__file__))==record['dispatcher_sha256'] and all(sha(cwd/n)==pin for n,pin in profile['input_pins'].items())
        rc=next((r['inner_exit'] for r in rows if r['inner_exit']),0) if unchanged else 111
        record.update(state='finished',inner_exits={r['name']:r['inner_exit'] for r in rows},jobs=rows,inputs_unchanged=unchanged,exit=rc)
    except Exception as e:record.update(state='failed-before-completion',inner_exits={},exit=112,error=repr(e))
    record['finished_time']=time.time()
    with result.open('x') as f:f.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2));return record['exit']
if __name__=='__main__':raise SystemExit(main())
