#!/usr/bin/env python3
"""Build the finite mode2 eight-job bootstrap; no install, boot or device access."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--core-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=Path(__file__).resolve().parents[1];receipt=a.core_receipt.resolve();core=json.loads(receipt.read_text())
    lib=Path(core['library']);source=Path(core['source']);out=a.out.resolve()
    assert core['state']=='linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3' and core['source_pins_unchanged']
    assert sha(lib)==core['sha256']=='8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1'
    assert all(sha(Path(n))==v for n,v in core['input_pins'].items())
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    paths=[Path(__file__).resolve(),r/'tools/build-hakios-metal.py',r/'userland/metal/device_probe.cpp',
           r/'userland/metal/probe_pixels.hpp',r/'graphics/hakios-metal-ca/bootstrap/gauguin_metal_bootstrap.h',
           r/'graphics/hakios-metal-ca/desktop-overlay/userland/src/GauguinMetalDesktopPolicy.h',receipt,lib,sdk/'SDKSettings.json']
    paths += [source/('tests/fixtures/'+name+'_bc.hpp')for name in ['fill_id','tri_attr_vs','tri_color_fs','tri_cflat_fs','tri_tex_fs']]
    pins={str(p):sha(p)for p in paths};tag=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:24]
    out.mkdir(parents=True,exist_ok=False);binary=out/'gauguin-metal-bootstrap'
    argv=['xcrun','--sdk','iphoneos','clang++','-target','arm64-apple-ios16.0','-isysroot',str(sdk),
          '-std=c++17','-O2','-Wall','-Wextra','-Werror','-DHAKIOS_METAL_TARGET_A619','-DGAUGUIN_METAL_BOOTSTRAP=1',
          '-DGAUGUIN_METAL_PROBE_BUILD="'+tag+'"','-DGAUGUIN_METAL_CORE_SHA256="'+sha(lib)+'"',
          '-I'+str(source/'include'),'-I'+str(source/'tests'),
          '-I'+str(r/'graphics/hakios-metal-ca/bootstrap'),
          '-I'+str(r/'graphics/hakios-metal-ca/desktop-overlay/userland/src'),
          str(r/'userland/metal/device_probe.cpp'),str(lib),'-Wl,-rpath,/usr/local/lib/gauguin','-o',str(binary)]
    def run(args,name):
        with(out/name).open('x')as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    run(argv,'compile-link.log');run(['codesign','--force','--sign','-',str(binary)],'sign.log')
    run(['codesign','--verify','--strict',str(binary)],'verify.log');run(['nm','-m','-u',str(binary)],'imports.log')
    run(['otool','-L',str(binary)],'loads.log');assert '@rpath/libGauguinMetalCore.dylib'in(out/'loads.log').read_text()
    spec=importlib.util.spec_from_file_location('b',r/'tools/build-hakios-metal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    version=m.ios_version(binary);assert all(sha(Path(n))==v for n,v in pins.items())
    result=dict(state='native-iOS16-eight-job-bootstrap-not-device-qualified',binary=str(binary),probe=str(binary),
                bytes=binary.stat().st_size,sha256=sha(binary),build=tag,platform_version=version,
                expected_argument='--bootstrap245',initial_delay_seconds=0,alarm_seconds=30,expected_jobs=8,
                core_sha256=sha(lib),input_pins=pins,inputs_unchanged=True,
                required_kernel_selector=0x7c,requires_clean_armed_owner_close=True,
                device_commands=0,installed=False,hardware_qualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
