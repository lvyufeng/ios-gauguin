#!/usr/bin/env python3
"""Check actual launch jobs and compile the original pilot's mode gate."""
import copy
import hashlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
MAIN=Path('/Users/baai/Project/ios-gauguin')
STATE=WORK/'research/tmp/edr-once-320'
sys.path.insert(0,str(WORK/'tools'))
from sb_cadence_launch import transform_edr_loader,BACKBOARD_JOB,CACHE,EDR_MODE

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    capture=json.loads((STATE/'slot-capture/result.json').read_text())
    originals=[]
    for name,path in [('backboard',BACKBOARD_JOB),('cache',CACHE)]:
        row=capture['files'][path]
        data=(STATE/'slot-capture'/(name+'-old-data.bin')).read_bytes()[:row['logical']]
        assert hashlib.sha256(data).hexdigest()==row['sha256']
        originals.append(plistlib.loads(data))
    backboard,cached=transform_edr_loader(*originals)
    assert len(cached['LaunchDaemons'])==531
    assert {k for k,v in originals[1]['LaunchDaemons'].items() if cached['LaunchDaemons'][k]!=v}=={BACKBOARD_JOB}
    for target in (backboard,cached['LaunchDaemons'][BACKBOARD_JOB]):
        assert target['EnvironmentVariables']['GAUGUIN_EAGL_MODE']==EDR_MODE
        assert not any(k.startswith('DYLD_')for k in target['EnvironmentVariables'])
    for which in range(6):
        changed=copy.deepcopy(originals)
        if which==0:changed[0]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']='/tmp/unexpected'
        if which==1:changed[0]['EnvironmentVariables']['GAUGUIN_EAGL_MODE']='other'
        if which==2:changed[1]['LaunchDaemons'][BACKBOARD_JOB]['EnvironmentVariables']['GAUGUIN_EAGL_MODE']='other'
        if which==3:changed[0]['ProgramArguments']=['/usr/libexec/other']
        if which==4:changed[0]['UserName']='root'
        if which==5:changed[1]['LaunchDaemons'][BACKBOARD_JOB]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']='/tmp/unexpected'
        try:transform_edr_loader(*changed)
        except AssertionError:pass
        else:raise AssertionError('unexpected launch job accepted')
    source=MAIN/'research/tmp/gauguin-ui-worktree-20261109/userland/eagl/pilot.c'
    assert sha(source)=='47745942403d38014191c978327cb72861f446a9e98f13591ae8eae471ebb7e7'
    text=source.read_text();start=text.index('static bool\npilot_enabled(void)')
    body=text[start:text.index('\nstatic bool\nwait_for_gpu',start)]
    out=STATE/'launch-host-v1';out.mkdir(exist_ok=False)
    fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
static const char *mode="edr-default318";
static int calls;
static const char *fake_name(void){return "backboardd";}
static const char *fake_env(const char *key){assert(!strcmp(key,"GAUGUIN_EAGL_MODE"));return mode;}
static unsigned fake_uid(void){return 501;}
static int fake_sysctl(const char *key,void *out,size_t *n,void *unused,size_t zero){
  assert(!strcmp(key,"kern.bootargs") && !unused && zero==0);calls++;
  const char *args="gmt=2 gsp=316 sweeteagl=2";
  assert(*n>strlen(args));strcpy(out,args);*n=strlen(args)+1;return 0;
}
#define getprogname fake_name
#define getenv fake_env
#define getuid fake_uid
#define geteuid fake_uid
#define sysctlbyname fake_sysctl
'''+body+r'''
int main(void){
 assert(!pilot_enabled() && calls==0);
 mode="admission";assert(pilot_enabled() && calls==1);
 mode=NULL;assert(!pilot_enabled() && calls==1);
 mode="edr-default318";assert(!pilot_enabled() && calls==1);
 return 0;
}
'''
    path=out/'actual-pilot-gate.c';path.write_text(fixture)
    argv=['xcrun','clang','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(path),'-o',str(out/'check')]
    subprocess.run(argv,check=True,capture_output=True)
    subprocess.run([str(out/'check')],check=True,capture_output=True)
    pins=[Path(__file__),WORK/'tools/sb_cadence_launch.py',source,STATE/'slot-capture/result.json']
    result=dict(state='passed-actual-launch-transform-and-original-pilot-gate',
        changed_cached_jobs=1,unrelated_cached_jobs=530,negative_launch_cases=6,
        legacy_pilot_disabled_before_sysctl=True,actual_pilot_source_sha256=sha(source),
        input_pins={str(p):sha(p) for p in pins},device_writes=0,device_boots=0,
        iOS_loader_qualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
