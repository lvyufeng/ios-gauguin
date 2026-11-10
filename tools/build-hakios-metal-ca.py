#!/usr/bin/env python3
"""Build the complete CA frontend against a qualified A619 native core.

Software baseline only. No kernel publication, installation or device access.
Unchanged upstream warnings are retained; SDK/runtime compatibility is separate.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,plistlib,struct,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

OPTIONAL_M2V={
    '_native_bridge_metal_open','_native_bridge_metal_first_problem',
    '_native_bridge_metal_status','_native_bridge_metal_formats',
    '_native_bridge_metal_variant_hook',
}

def verify_optional_imports(path):
    data=path.read_bytes();header=struct.unpack_from('<8I',data);at=32;symtab=None
    for _ in range(header[4]):
        cmd,n=struct.unpack_from('<II',data,at);assert n>=8 and at+n<=len(data)
        if cmd==2:symtab=struct.unpack_from('<4I',data,at+8)
        at+=n
    assert symtab;off,count,strings,size=symtab;assert off+count*16<=len(data)and strings+size<=len(data)
    dynamic=[]
    for i in range(count):
        st,typ,section,desc,value=struct.unpack_from('<IBBHQ',data,off+16*i)
        if typ&0xe or not typ&1:continue
        assert st<size;end=data.index(b'\0',strings+st,strings+size);name=data[strings+st:end].decode()
        ordinal=desc>>8
        if name in OPTIONAL_M2V:
            assert desc&0x40 and ordinal==0xfe,('optional hook must remain weak/dynamic',name,desc)
            dynamic.append(name)
        else:assert ordinal not in (0xfe,0xff),('unexpected unbound import',name,desc)
    assert set(dynamic)==OPTIONAL_M2V and len(dynamic)==len(OPTIONAL_M2V)
    return sorted(dynamic)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ['prepared','core-receipt','out']:ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();repo=Path(__file__).resolve().parents[1];prep=a.prepared.resolve();out=a.out.resolve()
    receipt=json.loads((prep/'result.json').read_text());assert receipt['state'] in ('prepared-complete-pinned-HakiOS-CA-frontend-baseline','prepared-gauguin-offscreen-Metal-frontend') and receipt['inputs_unchanged']
    diagnostic=receipt['state']=='prepared-gauguin-offscreen-Metal-frontend'
    source=Path(receipt['source']);unit=source/'userland/src/HakiosMetalCA.m'
    for n,pin in receipt['source_pins'].items():assert sha(source/n)==pin,n
    core_receipt=a.core_receipt.resolve();core=json.loads(core_receipt.read_text());lib=Path(core['library']);headers=Path(core['source'])/'include'
    assert core['state']=='linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3'and core['source_pins_unchanged']
    assert sha(lib)==core['sha256']=='8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1'
    for n,pin in core['input_pins'].items():assert sha(Path(n))==pin,n
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    pins={str(p):sha(p)for p in [Path(__file__).resolve(),repo/'tools/build-hakios-metal.py',prep/'result.json',core_receipt,lib,headers/'hakios-metal/hakios_metal.h',sdk/'SDKSettings.json']}
    for n,pin in receipt['source_pins'].items():pins[str(source/n)]=pin
    out.mkdir(parents=True,exist_ok=False);bundle=out/'GauguinMetal.bundle';bundle.mkdir();binary=bundle/'GauguinMetal'
    info=dict(CFBundleExecutable='GauguinMetal',CFBundleIdentifier='org.gauguin.Metal',CFBundleName='GauguinMetal',CFBundlePackageType='BNDL',CFBundleVersion='1',CFBundleShortVersionString='0.1',CFBundleSupportedPlatforms=['iPhoneOS'],MinimumOSVersion='16.0',NSPrincipalClass='HakiosMetalDevice')
    (bundle/'Info.plist').write_bytes(plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False))
    def run(argv,name):
        with (out/name).open('x')as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
    # Only the five explicitly weak optional m2v hooks may remain dynamically
    # looked up. All required framework/core imports must resolve at link time.
    optional=['-Wl,-U,'+name for name in sorted(OPTIONAL_M2V)]
    profile_units=[str(unit.parent/'GauguinMetalProfile.m')] if diagnostic else []
    argv=['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0','-isysroot',str(sdk),'-std=gnu11','-O1','-fblocks','-fno-objc-arc','-Wall','-Wextra','-bundle','-framework','Foundation','-framework','IOKit','-framework','IOSurface','-framework','Metal','-lobjc','-lc++','-I'+str(headers),str(unit),*profile_units,str(lib),'-Wl,-rpath,/usr/local/lib/gauguin',*optional,'-o',str(binary)]
    run(argv,'compile-link.log')
    spec=importlib.util.spec_from_file_location('core_build',repo/'tools/build-hakios-metal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    version=m.ios_version(binary);header=struct.unpack_from('<8I',binary.read_bytes());assert header[3]==8
    optional_imports=verify_optional_imports(binary)
    run(['codesign','--force','--sign','-',str(bundle)],'sign.log');run(['codesign','--verify','--strict',str(bundle)],'verify.log')
    run(['otool','-L',str(binary)],'loads.log');run(['nm','-gU',str(binary)],'exports.log');run(['nm','-m','-u',str(binary)],'imports.log')
    assert '@rpath/libGauguinMetalCore.dylib'in(out/'loads.log').read_text()
    assert '_OBJC_CLASS_$_HakiosMetalDevice'in(out/'exports.log').read_text()
    assert all(sha(Path(n))==pin for n,pin in pins.items())
    state='native-iOS16-gauguin-offscreen-frontend-not-runtime-qualified' if diagnostic else 'native-iOS16-complete-CA-frontend-baseline-not-deployable'
    r=dict(state=state,bundle=str(bundle),binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary),platform_version=version,principal_class=info['NSPrincipalClass'],core_sha256=core['sha256'],source=str(unit),compiler_argv=argv,optional_weak_dynamic_imports=optional_imports,input_pins=pins,inputs_unchanged=True,device_commands=0,installed=False,diagnostic_root_only=diagnostic,device_discovery_qualified=False,runtime_ABI_qualified=False,hardware_qualified=False,remaining=['actual20H392 private ABI runtime checks','single-owner GLES/Metal admission and discovery timing','actual CA shader-library variants and presentation'])
    with (out/'result.json').open('x')as f:f.write(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items()if k not in ['input_pins','compiler_argv']},indent=2))

if __name__=='__main__':main()
