#!/usr/bin/env python3
"""Build a finite iOS16 MTL-object diagnostic; never install or access a device."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frontend-receipt',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();repo=Path(__file__).resolve().parents[1]
    receipt=a.frontend_receipt.resolve();frontend=json.loads(receipt.read_text())
    assert frontend['state']=='native-iOS16-gauguin-offscreen-frontend-not-runtime-qualified'
    assert frontend['diagnostic_root_only'] and frontend['inputs_unchanged']
    for name,pin in frontend['input_pins'].items():assert sha(Path(name))==pin,name
    binary=Path(frontend['binary']);assert sha(binary)==frontend['sha256']
    source=repo/'userland/metal/frontend_probe.m';header=Path(frontend['source']).parent/'GauguinMetalProfile.h'
    helper=repo/'tools/build-hakios-metal.py'
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    pins={str(p):sha(p) for p in [Path(__file__).resolve(),source,source.parent/'probe_boot.h',header,helper,receipt,binary,sdk/'SDKSettings.json']}
    tag=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:24]
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);probe=out/'gauguin-metal-frontend-probe'
    def run(argv,name):
        with (out/name).open('x') as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
    argv=['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0','-isysroot',str(sdk),
          '-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fblocks','-fno-objc-arc',
          '-DGAUGUIN_METAL_FRONTEND_BUILD="'+tag+'"','-I'+str(header.parent),str(source),
          '-framework','Foundation','-framework','Metal','-framework','IOKit','-framework','IOSurface',
          '-lobjc','-o',str(probe)]
    run(argv,'compile-link.log')
    spec=importlib.util.spec_from_file_location('core_build',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    version=m.ios_version(probe)
    run(['codesign','--force','--sign','-',str(probe)],'sign.log')
    run(['codesign','--verify','--strict',str(probe)],'verify.log')
    run(['otool','-L',str(probe)],'loads.log');run(['nm','-m','-u',str(probe)],'imports.log')
    assert all(sha(Path(name))==pin for name,pin in pins.items())
    result=dict(state='native-iOS16-MTL-object-probe-not-device-qualified',probe=str(probe),
                bytes=probe.stat().st_size,sha256=sha(probe),build=tag,platform_version=version,
                frontend_sha256=frontend['sha256'],core_sha256=frontend['core_sha256'],
                expected_jobs=83,expected_words=339968,abandoned_command_buffers=80,
                shader_pipeline_qualification=False,device_discovery=False,UI_qualification=False,
                input_pins=pins,inputs_unchanged=True,compiler_argv=argv,device_commands=0,installed=False)
    with (out/'result.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','compiler_argv')},indent=2))

if __name__=='__main__':main()
