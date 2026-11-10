#!/usr/bin/env python3
"""Prepare local launch plist candidates; never mount, install or access a phone."""
from pathlib import Path
import argparse,copy,hashlib,json,plistlib,stat
ROOT_JOB='/System/Library/LaunchDaemons/org.gauguin.gpu-probe.plist'
BBS_JOB='/System/Library/LaunchDaemons/com.apple.backboardd.plist'
CACHE='/System/Library/xpc/launchd.plist'
LABEL='org.gauguin.gpu-probe'
OLD='/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib'
ROUTER='/usr/libexec/gauguin-gpu-probe-router'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def transform(job,bbs,cache,policies):
    assert isinstance(cache,dict)and len(cache['LaunchDaemons'])==531
    jobs=cache['LaunchDaemons'];assert jobs[ROOT_JOB]==job
    cached_bbs=jobs[BBS_JOB]
    assert {k:v for k,v in cached_bbs.items()if k!='EnvironmentVariables'}=={k:v for k,v in bbs.items()if k!='EnvironmentVariables'}
    # launchd's compiled entry adds its own logging environment. Preserve it.
    for key,value in bbs['EnvironmentVariables'].items():assert cached_bbs['EnvironmentVariables'][key]==value
    assert job['Label']==LABEL and job['ProgramArguments']==['/usr/libexec/gauguin-metal-frontend-probe','--metal230']
    assert job['UserName']=='root'and job['RunAtLoad']is True and job['KeepAlive']is False and job['LaunchOnlyOnce']is True
    assert job['JetsamProperties']=={'ActiveHardMemoryLimit':128,'InactiveHardMemoryLimit':128}
    assert bbs['UserName']=='mobile'and bbs['ProgramArguments']==['/usr/libexec/backboardd']
    assert bbs['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']==OLD
    assert bbs['EnvironmentVariables']['GAUGUIN_EAGL_MODE']=='admission'
    for policy in policies:
        assert policy['Version4']['Daemon']['Override'][LABEL]=={
            'ActiveSoftMemoryLimit':-1,'ActiveHardMemoryLimit':128,'InactiveHardMemoryLimit':128}
    newjob,newbbs,newcache=copy.deepcopy((job,bbs,cache))
    newjob['ProgramArguments']=[ROUTER,'--route247']
    del newbbs['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']
    newcache['LaunchDaemons'][ROOT_JOB]['ProgramArguments']=copy.deepcopy(newjob['ProgramArguments'])
    del newcache['LaunchDaemons'][BBS_JOB]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']
    assert set(newcache['LaunchDaemons'])==set(jobs)
    for path,entry in jobs.items():
        if path not in [ROOT_JOB,BBS_JOB]:assert entry==newcache['LaunchDaemons'][path]
    for key,value in cache.items():
        if key!='LaunchDaemons':assert value==newcache[key]
    checkjob=copy.deepcopy(newjob);checkjob['ProgramArguments']=job['ProgramArguments'];assert checkjob==job
    checkbbs=copy.deepcopy(newbbs);checkbbs['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=OLD;assert checkbbs==bbs
    restored=copy.deepcopy(newcache)
    restored['LaunchDaemons'][ROOT_JOB]['ProgramArguments']=jobs[ROOT_JOB]['ProgramArguments']
    restored['LaunchDaemons'][BBS_JOB]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=OLD
    assert restored==cache
    return newjob,newbbs,newcache

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['capture','router-receipt','out']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();capture=a.capture.resolve();receipt=a.router_receipt.resolve();out=a.out.resolve()
    manifest=capture/'result.json';info=json.loads(manifest.read_text());router=json.loads(receipt.read_text())
    assert router['state']=='native-iOS16-root-probe-router-not-device-qualified'and router['inputs_unchanged']
    assert router['requires_0240_installed']and not router['installed']
    binary=Path(router['binary']);assert sha(binary)==router['sha256']
    for n,h in router['input_pins'].items():assert sha(Path(n))==h,n
    # DevicePolicy files use the actual captured namespace, discovered from the manifest.
    policy_paths=[n for n,row in info['files'].items()if row.get('output')in ['policy-D221.plist','policy-D22.plist']]
    assert len(policy_paths)==2
    wanted=[ROOT_JOB,BBS_JOB,CACHE,*sorted(policy_paths)];paths=[];values=[]
    for name in wanted:
        row=info['files'][name];p=capture/row['output']
        assert Path(row['output']).name==row['output']and row['present']
        assert stat.S_ISREG(row['mode'])and row['uid']==row['gid']==0 and(row['mode']&0o7777)==0o644
        assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],name
        paths.append(p);values.append(plistlib.loads(p.read_bytes()))
    job,bbs,cache=transform(values[0],values[1],values[2],values[3:])
    out.mkdir(parents=True,exist_ok=False);products={}
    for name,filename,value in [(ROOT_JOB,'root-job.plist',job),(BBS_JOB,'backboardd-job.plist',bbs),(CACHE,'launchd.plist',cache)]:
        p=out/filename;p.write_bytes(plistlib.dumps(value,fmt=plistlib.FMT_BINARY,sort_keys=False))
        products[name]=dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),target_uid=0,target_gid=0,target_mode=0o100644)
    pins={str(p):sha(p)for p in [Path(__file__).resolve(),manifest,receipt,binary,*paths]}
    result=dict(state='local-desktop-launch-plists-not-volume-or-installation',files=products,
                source_capture=info['source'],root_header_sha256=info['root_header_sha256'],
                total_jobs=531,changed_jobs=[ROOT_JOB,BBS_JOB],unchanged_jobs=529,all_labels_preserved=True,
                preserved_policy_files={name:info['files'][name]['sha256']for name in policy_paths},
                retained_admission_marker=True,root_memory_policy_label=LABEL,
                router_sha256=router['sha256'],requires_0240_installed=True,
                input_pins=pins,inputs_unchanged=True,device_commands=0,volume_staged=False,installed=False,hardware_qualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['input_pins','files']},indent=2))
if __name__=='__main__':main()
