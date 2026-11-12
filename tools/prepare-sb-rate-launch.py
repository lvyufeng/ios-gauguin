#!/usr/bin/env python3
"""Prepare SpringBoard's two launch plist variants for a read-only dylib."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import plistlib

JOB='/System/Library/LaunchDaemons/com.apple.SpringBoard.plist'
CACHE='/System/Library/xpc/launchd.plist'
LIBRARY='/usr/local/lib/gauguin/libGauguinSBRateTrace.dylib'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def transform(job,cached):
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
    new_job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=LIBRARY
    new_cache['LaunchDaemons'][JOB]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=LIBRARY
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

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('job','cache','capture','cache_capture','binary_receipt','out'):
        ap.add_argument('--'+name.replace('_','-'),dest=name,type=Path,required=True)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    out=args.out.resolve()
    assert out.is_relative_to(repo/'research/tmp') and not out.exists()
    job_path=args.job.resolve();cache_path=args.cache.resolve()
    capture=json.loads(args.capture.read_text())
    cache_capture=json.loads(args.cache_capture.read_text())
    binary_receipt=json.loads(args.binary_receipt.read_text())
    assert capture['state']=='readonly-springboard-job-captured'
    assert capture['root_header_sha256']==cache_capture['root_header_sha256']
    assert capture['job_path']==JOB and capture['job_sha256']==sha(job_path)
    assert capture['job_bytes']==job_path.stat().st_size
    cache_file=cache_capture['files'][CACHE]
    assert cache_file['present'] and cache_file['sha256']==sha(cache_path)
    assert cache_file['bytes']==cache_path.stat().st_size
    assert binary_receipt['state']=='native-iOS16-readonly-SpringBoard-rate-trace-not-device-qualified'
    assert sha(Path(binary_receipt['binary']))==binary_receipt['sha256']
    job=plistlib.loads(job_path.read_bytes())
    cached=plistlib.loads(cache_path.read_bytes())
    new_job,new_cache=transform(job,cached)
    new_job_bytes=plistlib.dumps(new_job,fmt=plistlib.FMT_BINARY,sort_keys=False)
    new_cache_bytes=plistlib.dumps(new_cache,fmt=plistlib.FMT_BINARY,sort_keys=False)
    job_extent_bytes=capture['job_fork']['blocks']*4096
    cache_extent_bytes=cache_file['fork']['blocks']*4096
    assert len(new_job_bytes)<=job_extent_bytes and len(new_cache_bytes)<=cache_extent_bytes
    out.mkdir(parents=True)
    job_out,cache_out=out/'springboard-job.plist',out/'launchd.plist'
    job_out.write_bytes(new_job_bytes)
    cache_out.write_bytes(new_cache_bytes)
    assert plistlib.loads(job_out.read_bytes())==new_job
    assert plistlib.loads(cache_out.read_bytes())==new_cache
    inputs=[Path(__file__).resolve(),job_path,cache_path,args.capture.resolve(),
            args.cache_capture.resolve(),args.binary_receipt.resolve(),Path(binary_receipt['binary'])]
    pins={str(path):sha(path) for path in inputs}
    assert all(sha(Path(name))==digest for name,digest in pins.items())
    result=dict(state='offline-SpringBoard-rate-launch-candidate-not-installed',
        root_header_sha256=capture['root_header_sha256'],
        binary_sha256=binary_receipt['sha256'],library_path=LIBRARY,
        changed_files={JOB:dict(old_bytes=job_path.stat().st_size,new_bytes=len(new_job_bytes),
            extent_bytes=job_extent_bytes,old_sha256=sha(job_path),new_sha256=sha(job_out),
            new_path=str(job_out)),
            CACHE:dict(old_bytes=cache_path.stat().st_size,new_bytes=len(new_cache_bytes),
            extent_bytes=cache_extent_bytes,old_sha256=sha(cache_path),new_sha256=sha(cache_out),
            new_path=str(cache_out))},
        launch_jobs=531,unrelated_jobs_unchanged=530,cache_sections_unchanged=True,
        reverse_transform_exact=True,
        new_dylib_file_allocation_unplanned=True,device_writes=0,device_boots=0,
        input_pins=pins,inputs_unchanged=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':main()
