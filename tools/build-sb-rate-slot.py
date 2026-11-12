#!/usr/bin/env python3
"""Build and sign the opt-in, read-only SpringBoard rate/timing logger."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import subprocess

DEFAULT_INSTALL_NAME='/usr/local/lib/gauguin/libGauguinSBRateTrace.dylib'
REUSE_SLOT='/usr/local/lib/gauguin/libGauguinEAGL.dylib'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--install-name',choices=(DEFAULT_INSTALL_NAME,REUSE_SLOT),
                    default=DEFAULT_INSTALL_NAME)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    source=repo/'graphics/gauguin-sb-rate-trace/SBRateTrace.m'
    out=args.out.resolve()
    assert out.is_relative_to(repo/'research/tmp') and not out.exists()
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    headers=[sdk/'System/Library/Frameworks/QuartzCore.framework/Headers/CAFrameRateRange.h',
             sdk/'System/Library/Frameworks/QuartzCore.framework/Headers/CAAnimation.h',
             sdk/'System/Library/Frameworks/QuartzCore.framework/Headers/CADisplayLink.h']
    pins={str(p):sha(p) for p in [source,Path(__file__).resolve(),sdk/'SDKSettings.json',*headers]}
    out.mkdir(parents=True)
    binary=out/'libGauguinSBRateTrace.dylib'
    argv=['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0',
          '-isysroot',str(sdk),'-std=gnu11','-O2','-fno-objc-arc','-Wall','-Wextra','-Werror',
          '-dynamiclib','-framework','Foundation','-framework','QuartzCore','-lobjc',
          '-Wl,-install_name,'+args.install_name,
          str(source),'-o',str(binary)]
    def run(command,name):
        with (out/name).open('x') as stream:
            subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True)
    run(argv,'compile-link.log')
    header=struct.unpack_from('<8I',binary.read_bytes())
    assert header[:2]==(0xfeedfacf,0x100000c) and header[3]==6
    spec=importlib.util.spec_from_file_location('core_build',repo/'tools/build-hakios-metal.py')
    core=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    platform=core.ios_version(binary)
    run(['codesign','--force','--sign','-',str(binary)],'sign.log')
    run(['codesign','--verify','--strict',str(binary)],'verify.log')
    run(['otool','-L',str(binary)],'loads.log')
    run(['nm','-m','-u',str(binary)],'imports.log')
    loads=(out/'loads.log').read_text()
    assert '/System/Library/Frameworks/Foundation.framework/Foundation' in loads
    assert '/System/Library/Frameworks/QuartzCore.framework/QuartzCore' in loads
    assert args.install_name in loads
    assert all(sha(Path(p))==value for p,value in pins.items())
    result=dict(state='native-iOS16-readonly-SpringBoard-rate-trace-not-device-qualified',
                binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary),
                platform_version=platform,source=str(source),compiler_argv=argv,
                install_name=args.install_name,
                input_pins=pins,inputs_unchanged=True,installed=False,
                device_writes=0,device_boots=0,remaining=['SpringBoard dyld insertion',
                    '20H392 runtime hook ABI and log output','same-clock 0301 comparison'])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('compiler_argv','input_pins')},indent=2))

if __name__=='__main__':main()
