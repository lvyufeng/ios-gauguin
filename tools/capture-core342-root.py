#!/usr/bin/env python3
"""Read-only 31-file capture with legacy file caps or a frozen combined log cap."""
import argparse
import importlib.util
import json
from pathlib import Path
import types

spec=importlib.util.spec_from_file_location('bounded_root_capture342',Path(__file__).with_name('capture-sb-cadence-root.py'))
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)
BASE.FILE_LIMITS['/private/var/log/backboardd.log']=64*1048576
BASE.FILE_LIMITS['/private/var/log/springboard.log']=48*1048576
RESULT_MAX=1048576


def bounded_json(value,**kwargs):
    text=json.dumps(value,**kwargs)
    if len((text+'\n').encode())>RESULT_MAX:raise ValueError('capture result metadata exceeds1MiB')
    return text


BASE.json=types.SimpleNamespace(dumps=bounded_json)


def capture(profile,make_io=BASE.RecoveryIO,*,save_files=True,save_paths=None,prefix_files=None):
    return BASE.capture(profile,make_io,save_files=save_files,save_paths=save_paths,prefix_files=prefix_files)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('profile',type=Path);a=ap.parse_args()
    result=capture(json.loads(a.profile.read_text()))
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
