#!/usr/bin/env python3
"""Unchanged31-file read-only capture with explicit64MiB BB and48MiB SpringBoard limits."""
import argparse
import importlib.util
import json
from pathlib import Path
import types

spec=importlib.util.spec_from_file_location('bounded_root_capture341',Path(__file__).with_name('capture-sb-cadence-root.py'))
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)
BASE.FILE_LIMITS['/private/var/log/backboardd.log']=64*1048576
BASE.FILE_LIMITS['/private/var/log/springboard.log']=48*1048576
RESULT_MAX=1048576


def bounded_json(value,**kwargs):
    text=json.dumps(value,**kwargs)
    if len((text+'\n').encode())>RESULT_MAX:raise ValueError('capture result metadata exceeds1MiB')
    return text


BASE.json=types.SimpleNamespace(dumps=bounded_json)


def capture(profile,make_io=BASE.RecoveryIO):return BASE.capture(profile,make_io)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('profile',type=Path);a=ap.parse_args()
    result=capture(json.loads(a.profile.read_text()))
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
