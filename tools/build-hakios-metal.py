#!/usr/bin/env python3
"""Link the A619 Metal core with matching iOS AIR/NIR/IR3 static archives.

Local artifacts only. No Metal plug-in/CA registration, installation or device
access. Prepared inputs and the Mesa build are verified and left unchanged.
"""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,re,shlex,struct,subprocess

ARCHIVES=['src/compiler/air/libair.a','src/freedreno/ir3/libfreedreno_ir3.a',
 'src/freedreno/isa/libir3encode.a','src/freedreno/isa/libir3decode.a',
 'src/compiler/isaspec/libisaspec.a','src/compiler/nir/libnir.a',
 'src/compiler/libcompiler.a','src/freedreno/fdl/libfreedreno_layout.a',
 'src/freedreno/common/libfreedreno_common.a','src/util/libmesa_util.a',
 'src/util/libmesa_util_sse41.a','src/util/blake3/libblake3.a',
 'src/c11/impl/libmesa_util_c11.a']
CORE=['pm4','gpu','command','compute','texture','render','link','compiler',
      'metallib','c_api','fake_gpu','iokit_transport']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def mesa_flags(source,build):
    ninja=(build/'build.ninja').read_text()
    block=ninja.split('build src/freedreno/ir3/libfreedreno_ir3.a.p/ir3.c.o:',1)[1].split('\n\n',1)[0]
    args=next(l.split('ARGS = ',1)[1] for l in block.splitlines() if l.lstrip().startswith('ARGS = '))
    flags=[v for v in shlex.split(args) if v.startswith('-D')]
    includes=[source/'src',source/'include',source/'src/freedreno',
      source/'src/freedreno/common',source/'src/compiler',source/'src/compiler/nir',
      source/'src/compiler/air',source/'src/gallium/include',build/'src',
      build/'src/compiler',build/'src/compiler/nir',build/'src/freedreno',
      build/'src/freedreno/common',build/'src/freedreno/isa']
    for p in includes:flags+=['-isystem',str(p)]
    return flags

def ios_version(p):
    data=p.read_bytes();h=struct.unpack_from('<8I',data)
    assert h[0]==0xfeedfacf and h[1]==0x100000c
    off=32;rows=[]
    for _ in range(h[4]):
        cmd,size=struct.unpack_from('<II',data,off);assert size>=8 and off+size<=len(data)
        if cmd==0x32:rows.append(struct.unpack_from('<4I',data,off+8))
        off+=size
    assert len(rows)==1 and rows[0][0]==2 and rows[0][1]==0x100000
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for flag in ['prepared','mesa-source','mesa-build','out']:ap.add_argument('--'+flag,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=4)
    a=ap.parse_args();assert 1<=a.jobs<=8
    prep=a.prepared.resolve();receipt=json.loads((prep/'result.json').read_text());source=Path(receipt['source'])
    assert receipt['state']=='prepared-pinned-Metal-core-with-A619-profile'
    ms=a.mesa_source.resolve();mb=a.mesa_build.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    inputs={str(source/p):pin for p,pin in receipt['source_pins'].items()}
    inputs[str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    inputs[str(prep/'result.json')]=sha(prep/'result.json')
    inputs[str(mb/'build.ninja')]=sha(mb/'build.ninja')
    for p in [*(ms/'src').rglob('*.h'),*(mb/'src').rglob('*.h'),*[mb/n for n in ARCHIVES]]:inputs[str(p)]=sha(p)
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    inputs[str(sdk/'SDKSettings.json')]=sha(sdk/'SDKSettings.json')
    assert all(sha(Path(p))==v for p,v in inputs.items())
    tag=hashlib.sha256(('A619\n'+json.dumps(inputs,sort_keys=True)).encode()).hexdigest()[:24]
    common=['xcrun','--sdk','iphoneos','clang++','-target','arm64-apple-ios16.0',
      '-isysroot',str(sdk),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
      '-DHAKIOS_METAL_MESA','-DHAKIOS_METAL_TARGET_A619',
      '-DHAKIOS_METAL_CACHE_BUILD="'+tag+'"','-I'+str(source/'include'),*mesa_flags(ms,mb)]
    def run(argv,name):
        with (out/(name+'.log')).open('x') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True)
    def compile(name):
        obj=out/(name+'.o');run([*common,'-c',str(source/('src/'+name+'.cpp')),'-o',str(obj)],'compile-'+name)
        ios_version(obj);return obj
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:objects=list(pool.map(compile,CORE))
    library=out/'libGauguinMetalCore.dylib'
    run([*common,'-dynamiclib',*[str(p) for p in objects],*[str(mb/p) for p in ARCHIVES],
      '-lz','-lm','-framework','IOKit','-framework','IOSurface','-framework','CoreFoundation',
      '-Wl,-install_name,@rpath/libGauguinMetalCore.dylib','-o',str(library)],'link')
    version=ios_version(library)
    run(['codesign','--force','--sign','-',str(library)],'sign')
    run(['codesign','--verify','--strict',str(library)],'verify-signature')
    run(['nm','-gU',str(library)],'exports');exports=(out/'exports.log').read_text()
    assert all(n in exports for n in ['_hakios_metal_open','_hakios_metal_has_compiler','_hakios_metal_library_open','_hakios_metal_program_new'])
    unchanged=all(sha(Path(p))==v for p,v in inputs.items());assert unchanged
    result=dict(state='linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3',library=str(library),bytes=library.stat().st_size,sha256=sha(library),platform_version=version,source=str(source),source_pins_unchanged=unchanged,cache_build_tag=tag,input_pins=inputs,Metal_device_plugin_linked=False,CoreAnimation_integrated=False,hardware_qualified=False,device_commands=0)
    with (out/'result.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':main()
