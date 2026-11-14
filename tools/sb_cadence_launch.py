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

