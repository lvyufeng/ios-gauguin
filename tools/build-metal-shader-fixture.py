#!/usr/bin/env python3
"""Compile the project's own shaders for iOS16 using the installed Metal toolchain.

No download, device access, installation or Apple shader extraction.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();repo=Path(__file__).resolve().parents[1];source=repo/'userland/metal/pipeline_fixture.metal'
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    pins={str(p):sha(p)for p in [Path(__file__).resolve(),source,sdk/'SDKSettings.json']}
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def run(argv,name):
        with (out/name).open('x') as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
    run(['xcrun','--sdk','iphoneos','metal','--version'],'tool-version.log')
    air=out/'pipeline_fixture.air';library=out/'pipeline_fixture.metallib'
    compile_argv=['xcrun','--sdk','iphoneos','metal','-target','air64-apple-ios16.0','-std=ios-metal2.4',
                  '-O1','-fno-fast-math','-Wall','-Wextra','-Werror','-c',str(source),'-o',str(air)]
    link_argv=['xcrun','--sdk','iphoneos','metallib',str(air),'-o',str(library)]
    run(compile_argv,'compile.log');run(link_argv,'link.log')
    assert air.stat().st_size>0 and library.stat().st_size>88 and all(sha(Path(n))==pin for n,pin in pins.items())
    r=dict(state='generated-project-Metal2.4-iOS16-library-not-runtime-qualified',library=str(library),
           library_bytes=library.stat().st_size,library_sha256=sha(library),air_sha256=sha(air),
           compiler_version=(out/'tool-version.log').read_text(),compile_argv=compile_argv,link_argv=link_argv,
           input_pins=pins,inputs_unchanged=True,device_commands=0,installed=False,runtime_qualified=False)
    with (out/'result.json').open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['input_pins','compile_argv','link_argv']},indent=2))

if __name__=='__main__':main()
