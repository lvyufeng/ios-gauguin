#!/usr/bin/env python3
"""Transform only SpringBoard launch environments for the existing observer slot."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import plistlib

JOB='/System/Library/LaunchDaemons/com.apple.SpringBoard.plist'
CACHE='/System/Library/xpc/launchd.plist'
LIBRARY='/usr/local/lib/gauguin/libGauguinSBRateTrace.dylib'
REUSE_SLOT='/usr/local/lib/gauguin/libGauguinEAGL.dylib'
BACKBOARD_JOB='/System/Library/LaunchDaemons/com.apple.backboardd.plist'
ADMISSION_SLOT='/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib'
EDR_MODE='edr-default318'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def transform(job,cached,library=LIBRARY):
    assert library in (LIBRARY,REUSE_SLOT)
    assert isinstance(job,dict) and isinstance(cached,dict)
    jobs=cached['LaunchDaemons']
    assert len(jobs)==531 and JOB in jobs
    embedded=jobs[JOB]
    expected=dict(Label='com.apple.SpringBoard',
                  ProgramArguments=['/System/Library/CoreServices/SpringBoard.app/SpringBoard'],
                  UserName='mobile',
                  StandardOutPath='/private/var/log/springboard.log',
                  StandardErrorPath='/private/var/log/springboard.log')
    for key,value in expected.items():
        assert job[key]==embedded[key]==value,key
    assert {key:value for key,value in job.items() if key!='EnvironmentVariables'}=={
        key:value for key,value in embedded.items() if key!='EnvironmentVariables'}
    local_env=job['EnvironmentVariables']
    cached_env=embedded['EnvironmentVariables']
    assert local_env=={'CA_ASSERT_MAIN_THREAD_TRANSACTIONS':'1'}
    assert cached_env=={'CA_ASSERT_MAIN_THREAD_TRANSACTIONS':'1',
                        'CFLOG_FORCE_STDERR':'1','OS_ACTIVITY_DT_MODE':'YES'}
    assert 'DYLD_INSERT_LIBRARIES' not in local_env and 'DYLD_INSERT_LIBRARIES' not in cached_env
    new_job,new_cache=copy.deepcopy((job,cached))
    new_job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=library
    new_cache['LaunchDaemons'][JOB]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=library
    assert set(new_cache)==set(cached) and set(new_cache['LaunchDaemons'])==set(jobs)
    for key,value in cached.items():
        if key!='LaunchDaemons':assert new_cache[key]==value
    for name,value in jobs.items():
        if name!=JOB:assert new_cache['LaunchDaemons'][name]==value
    undone_job,undone_cache=copy.deepcopy((new_job,new_cache))
    del undone_job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']
    del undone_cache['LaunchDaemons'][JOB]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']
    assert undone_job==job and undone_cache==cached
    return new_job,new_cache


def transform_edr_loader(backboard,cached):
    """Change only the non-DYLD opt-in mode; C4 performs the explicit load."""
    jobs=cached['LaunchDaemons'];assert len(jobs)==531 and BACKBOARD_JOB in jobs
    embedded=jobs[BACKBOARD_JOB]
    expected=dict(Label='com.apple.backboardd',ProgramArguments=['/usr/libexec/backboardd'],
                  UserName='mobile',StandardOutPath='/private/var/log/backboardd.log',
                  StandardErrorPath='/private/var/log/backboardd.log')
    for key,value in expected.items():assert backboard[key]==embedded[key]==value,key
    assert {k:v for k,v in backboard.items()if k!='EnvironmentVariables'}=={
        k:v for k,v in embedded.items()if k!='EnvironmentVariables'}
    assert backboard['EnvironmentVariables']=={'GAUGUIN_EAGL_MODE':'admission'}
    assert embedded['EnvironmentVariables']=={'CFLOG_FORCE_STDERR':'1',
        'GAUGUIN_EAGL_MODE':'admission','OS_ACTIVITY_DT_MODE':'YES'}
    new_backboard,new_cache=copy.deepcopy((backboard,cached))
    for target in (new_backboard,new_cache['LaunchDaemons'][BACKBOARD_JOB]):
        target['EnvironmentVariables']['GAUGUIN_EAGL_MODE']='edr-default318'
        assert not any(k.startswith('DYLD_') for k in target['EnvironmentVariables'])
    assert {name for name,value in jobs.items() if new_cache['LaunchDaemons'][name]!=value}=={BACKBOARD_JOB}
    undone_backboard,undone_cache=copy.deepcopy((new_backboard,new_cache))
    for target in (undone_backboard,undone_cache['LaunchDaemons'][BACKBOARD_JOB]):
        target['EnvironmentVariables']['GAUGUIN_EAGL_MODE']='admission'
    assert undone_backboard==backboard and undone_cache==cached
    return new_backboard,new_cache
