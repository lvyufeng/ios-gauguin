#!/usr/bin/env python3
"""Check the actual captured task tree, exact change scope and refusal controls."""
from pathlib import Path
import argparse,copy,importlib.util,json,plistlib
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--capture',type=Path,required=True);a=ap.parse_args()
    r=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('launch',r/'tools/prepare-metal-desktop-launch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    paths=['job.plist','backboardd-job.plist','cache.plist','policy-D221.plist','policy-D22.plist']
    original=[plistlib.loads((a.capture/n).read_bytes())for n in paths];before=copy.deepcopy(original)
    job,bbs,cache=m.transform(*original[:3],original[3:]);assert original==before
    assert len(cache['LaunchDaemons'])==531 and set(cache['LaunchDaemons'])==set(original[2]['LaunchDaemons'])
    assert sum(cache['LaunchDaemons'][n]==entry for n,entry in original[2]['LaunchDaemons'].items())==529
    assert bbs['EnvironmentVariables']['GAUGUIN_EAGL_MODE']=='admission'and'DYLD_INSERT_LIBRARIES'not in bbs['EnvironmentVariables']
    assert job['Label']==m.LABEL and job['ProgramArguments']==[m.ROUTER,'--route247']
    cache_env=copy.deepcopy(original[2]['LaunchDaemons'][m.BBS_JOB]['EnvironmentVariables']);del cache_env['DYLD_INSERT_LIBRARIES']
    assert cache['LaunchDaemons'][m.BBS_JOB]['EnvironmentVariables']==cache_env
    for value in [job,bbs,cache]:assert plistlib.loads(plistlib.dumps(value,fmt=plistlib.FMT_BINARY))==value
    augmented=copy.deepcopy(original);augmented[0]['KeepUnrelated']='yes';augmented[2]['LaunchDaemons'][m.ROOT_JOB]=copy.deepcopy(augmented[0])
    augmented[1]['EnvironmentVariables']['UNRELATED_KEEP']='yes';augmented[2]['LaunchDaemons'][m.BBS_JOB]['EnvironmentVariables']['UNRELATED_KEEP']='yes'
    augmented[2]['LaunchDaemons'][m.BBS_JOB]['EnvironmentVariables']['CACHE_ONLY']='keep'
    newjob,newbbs,newcache=m.transform(*augmented[:3],augmented[3:]);assert newjob['KeepUnrelated']=='yes'and newbbs['EnvironmentVariables']['UNRELATED_KEEP']=='yes'
    assert newcache['LaunchDaemons'][m.BBS_JOB]['EnvironmentVariables']['CACHE_ONLY']=='keep'
    for key in original[2]:
        if key!='LaunchDaemons':assert newcache[key]==original[2][key]
    rejected=0
    for case in ['root-argv','root-user','root-run','root-keep','root-once','root-limit','bbs-user','bbs-argv',
                 'bbs-library','bbs-marker','cache-mismatch','cache-count','policy-soft','policy-hard']:
        v=copy.deepcopy(original)
        if case=='root-argv':v[0]['ProgramArguments']=['/tmp/other']
        if case=='root-user':v[0]['UserName']='mobile'
        if case=='root-run':v[0]['RunAtLoad']=False
        if case=='root-keep':v[0]['KeepAlive']=True
        if case=='root-once':v[0]['LaunchOnlyOnce']=False
        if case=='root-limit':v[0]['JetsamProperties']['ActiveHardMemoryLimit']=6
        if case=='bbs-user':v[1]['UserName']='root'
        if case=='bbs-argv':v[1]['ProgramArguments']=['/tmp/other']
        if case=='bbs-library':v[1]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']+=':/tmp/other'
        if case=='bbs-marker':del v[1]['EnvironmentVariables']['GAUGUIN_EAGL_MODE']
        if case=='cache-mismatch':v[2]['LaunchDaemons'][m.ROOT_JOB]['Label']='other'
        if case=='cache-count':v[2]['LaunchDaemons'].pop(next(n for n in v[2]['LaunchDaemons']if n not in [m.ROOT_JOB,m.BBS_JOB]))
        if case=='policy-soft':v[3]['Version4']['Daemon']['Override'][m.LABEL]['ActiveSoftMemoryLimit']=6
        if case=='policy-hard':v[4]['Version4']['Daemon']['Override'][m.LABEL]['InactiveHardMemoryLimit']=-1
        if case.startswith('root-'):v[2]['LaunchDaemons'][m.ROOT_JOB]=copy.deepcopy(v[0])
        if case.startswith('bbs-'):v[2]['LaunchDaemons'][m.BBS_JOB]=copy.deepcopy(v[1])
        try:m.transform(*v[:3],v[3:])
        except(AssertionError,KeyError,TypeError):rejected+=1
        else:raise AssertionError('corrupt launch contract accepted: '+case)
    assert rejected==14
    print('531 labels/529 unrelated jobs retained; 14 corrupt controls refused; binary plist roundtrips pass; local only')
if __name__=='__main__':main()
