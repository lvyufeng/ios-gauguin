#!/usr/bin/env python3
"""Build a finite iOS16 MTL-object diagnostic; never install or access a device."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frontend-receipt',type=Path,required=True)
    ap.add_argument('--shader-receipt',type=Path)
    ap.add_argument('--ca-renderer',action='store_true',help='real offscreen CA layer scenes; requires gauguin-ca-exact frontend')
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
    shader=None;shader_args=[];ca_args=[]
    if a.ca_renderer:
        assert frontend.get('profile')=='gauguin-ca-exact', 'CA scenes need exact image-owned shader profile'
        assert not a.shader_receipt, 'CA scenes are a separate real-framework qualification'
        for p in [source.parent/'ca_renderer_tests.h',sdk/'System/Library/Frameworks/QuartzCore.framework/Headers/CARenderer.h']:
            pins[str(p)]=sha(p)
        ca_args=['-DGAUGUIN_CA_RENDERER_PROBE=1','-framework','QuartzCore','-framework','CoreGraphics']
    if a.shader_receipt:
        shader_receipt=a.shader_receipt.resolve();shader=json.loads(shader_receipt.read_text())
        assert shader['state']=='generated-project-Metal2.4-iOS16-library-not-runtime-qualified' and shader['inputs_unchanged']
        for name,pin in shader['input_pins'].items():assert sha(Path(name))==pin,name
        library=Path(shader['library']);assert sha(library)==shader['library_sha256'] and library.stat().st_size==shader['library_bytes']
        for p in [shader_receipt,library,source.parent/'pipeline_tests.h']:pins[str(p)]=sha(p)
        shader_args=['-DGAUGUIN_METAL_SHADER_BYTES='+str(shader['library_bytes']),
                     '-DGAUGUIN_METAL_SHADER_SHA256="'+shader['library_sha256']+'"']
    tag=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:24]
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);probe=out/'gauguin-metal-frontend-probe'
    def run(argv,name):
        with (out/name).open('x') as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
    argv=['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0','-isysroot',str(sdk),
          '-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fblocks','-fno-objc-arc',
          '-DGAUGUIN_METAL_FRONTEND_BUILD="'+tag+'"',*shader_args,*ca_args,'-I'+str(header.parent),str(source),
          '-framework','Foundation','-framework','Metal','-framework','IOKit','-framework','IOSurface',
          '-lobjc','-o',str(probe)]
    run(argv,'compile-link.log')
    spec=importlib.util.spec_from_file_location('core_build',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    version=m.ios_version(probe)
    run(['codesign','--force','--sign','-',str(probe)],'sign.log')
    run(['codesign','--verify','--strict',str(probe)],'verify.log')
    run(['otool','-L',str(probe)],'loads.log');run(['nm','-m','-u',str(probe)],'imports.log')
    assert all(sha(Path(name))==pin for name,pin in pins.items())
    result=dict(state='native-iOS16-CARenderer-layer-probe-not-device-qualified' if a.ca_renderer else ('native-iOS16-MTL-shader-probe-not-device-qualified' if shader else 'native-iOS16-MTL-object-probe-not-device-qualified'),probe=str(probe),
                bytes=probe.stat().st_size,sha256=sha(probe),build=tag,platform_version=version,
                frontend_sha256=frontend['sha256'],core_sha256=frontend['core_sha256'],
                expected_jobs=10 if a.ca_renderer else (93 if shader else 83),expected_jobs_scope='explicit poison/readback jobs; framework jobs counted separately' if a.ca_renderer else 'all probe jobs',expected_base_pixel_checks=0 if a.ca_renderer else 339968,
                expected_shader_pixel_checks=32768 if shader else 0,expected_compute_words=512 if shader else 0,
                expected_half_pixels=4096 if shader else 0,abandoned_command_buffers=0 if a.ca_renderer else 80,
                shader_library=shader,shader_pipeline_probe_enabled=bool(shader),
                ca_renderer_probe_enabled=a.ca_renderer,expected_ca_scenes=5 if a.ca_renderer else 0,
                expected_ca_pixel_checks=20480 if a.ca_renderer else 0,
                shader_pipeline_qualification=False,device_discovery=False,UI_qualification=False,
                input_pins=pins,inputs_unchanged=True,compiler_argv=argv,device_commands=0,installed=False)
    with (out/'result.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','compiler_argv')},indent=2))

if __name__=='__main__':main()
