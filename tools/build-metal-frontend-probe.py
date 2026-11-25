#!/usr/bin/env python3
"""Build a finite iOS16 MTL-object diagnostic; never install or access a device."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frontend-receipt',type=Path,required=True)
    ap.add_argument('--shader-receipt',type=Path)
    ap.add_argument('--fp16-receipt',type=Path,help='embed own native-half prelude before exact CA scenes')
    ap.add_argument('--ca-renderer',action='store_true',help='real offscreen CA scenes; requires an exact shader frontend')
    ap.add_argument('--task-core-receipt',type=Path,help='opt-in immutable task IOSurface suite; exact installed core8a ABI')
    ap.add_argument('--task-shader-receipt',type=Path,help='own sampler library, separate from the full shader suite')
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
    shader=None;shader_args=[];ca_args=[];fp16=None;fp16_args=[];fp16_library=None
    task=None;task_args=[];task_objects=[];task_core=None;task_source=None;task_shader=None
    assert bool(a.task_core_receipt)==bool(a.task_shader_receipt), 'task core and sampler receipts are paired'
    if a.ca_renderer:
        assert frontend.get('profile') in ('gauguin-ca-exact','gauguin-ca-trace','gauguin-ca-identity','gauguin-ca-fp16'), 'CA scenes need exact image-owned shader profile'
        assert (frontend.get('profile')=='gauguin-ca-fp16')==bool(a.fp16_receipt), 'FP16 profile needs its own readback prelude'
        assert not a.shader_receipt, 'CA scenes are a separate real-framework qualification'
        for p in [source.parent/'ca_renderer_tests.h',sdk/'System/Library/Frameworks/QuartzCore.framework/Headers/CARenderer.h']:
            pins[str(p)]=sha(p)
        ca_args=['-DGAUGUIN_CA_RENDERER_PROBE=1','-framework','QuartzCore','-framework','CoreGraphics']
    if a.fp16_receipt:
        assert a.ca_renderer and not a.shader_receipt and frontend.get('profile')=='gauguin-ca-fp16'
        fp16_receipt=a.fp16_receipt.resolve();fp16=json.loads(fp16_receipt.read_text())
        assert fp16['state']=='generated-own-native-FP16-Metal2.4-library-not-runtime-qualified'
        assert fp16['platform']=='ios' and fp16['inputs_unchanged']
        for name,pin in fp16['input_pins'].items():assert sha(Path(name))==pin,name
        fp16_library=Path(fp16['library']);assert sha(fp16_library)==fp16['library_sha256']
        assert fp16_library.stat().st_size==fp16['library_bytes']<1048576
        for p in [fp16_receipt,fp16_library,source.parent/'native_fp16_tests.h',header.parent/'GauguinFP16Proof.h']:
            pins[str(p)]=sha(p)
        fp16_args=['-DGAUGUIN_NATIVE_FP16_PROBE=1','-I'+str(a.out.resolve()),
                   '-DGAUGUIN_NATIVE_FP16_LIBRARY_SHA256="'+fp16['library_sha256']+'"']
    if a.shader_receipt:
        shader_receipt=a.shader_receipt.resolve();shader=json.loads(shader_receipt.read_text())
        assert shader['state']=='generated-project-Metal2.4-iOS16-library-not-runtime-qualified' and shader['inputs_unchanged']
        for name,pin in shader['input_pins'].items():assert sha(Path(name))==pin,name
        library=Path(shader['library']);assert sha(library)==shader['library_sha256'] and library.stat().st_size==shader['library_bytes']
        for p in [shader_receipt,library,source.parent/'pipeline_tests.h']:pins[str(p)]=sha(p)
        shader_args=['-DGAUGUIN_METAL_SHADER_BYTES='+str(shader['library_bytes']),
                     '-DGAUGUIN_METAL_SHADER_SHA256="'+shader['library_sha256']+'"']
    if a.task_core_receipt:
        assert a.ca_renderer and a.fp16_receipt and not a.shader_receipt
        task_receipt=a.task_core_receipt.resolve();task=json.loads(task_receipt.read_text())
        assert task['state']=='linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3' and task['source_pins_unchanged']
        assert task['sha256']==frontend['core_sha256']=='8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1'
        task_core=Path(task['library']);task_source=Path(task['source'])
        assert sha(task_core)==task['sha256']
        for name,pin in task['input_pins'].items():assert sha(Path(name))==pin,name
        task_shader_receipt=a.task_shader_receipt.resolve();task_shader=json.loads(task_shader_receipt.read_text())
        assert task_shader['state']=='generated-project-Metal2.4-iOS16-library-not-runtime-qualified' and task_shader['inputs_unchanged']
        for name,pin in task_shader['input_pins'].items():assert sha(Path(name))==pin,name
        task_library=Path(task_shader['library'])
        assert sha(task_library)==task_shader['library_sha256']=='218e0c97825567d072886441603f7781fdbd800f53882382a4cd5ab8c8228837'
        assert task_library.stat().st_size==task_shader['library_bytes']<1048576
        for p in [task_receipt,task_core,task_shader_receipt,task_library,task_source/'src/c_api.cpp',
                  *sorted((task_source/'include/hakios-metal').glob('*.hpp')),task_source/'include/hakios-metal/hakios_metal.h',
                  source.parent/'task_surface_tests.h',source.parent/'task_surface_permissions.h',
                  source.parent/'task_surface_permissions.cpp',source.parent/'task_surface_core_bridge.cpp']:
            pins[str(p)]=sha(p)
        task_args=['-DGAUGUIN_TASK_SURFACE_PROBE=1','-I'+str(task_source/'include'),
                   '-DGAUGUIN_TASK_SHADER_BYTES='+str(task_shader['library_bytes']),
                   '-DGAUGUIN_TASK_SHADER_SHA256="'+task_shader['library_sha256']+'"']
    tag=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:24]
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);probe=out/'gauguin-metal-frontend-probe'
    if fp16_library:
        payload=fp16_library.read_bytes()
        embedded=out/'gauguin_native_fp16_library.h'
        embedded.write_text('/* Generated from project-owned Metal source. */\nstatic const unsigned char gauguin_native_fp16_library[] = {\n'+
                            '\n'.join(','.join(str(v)for v in payload[i:i+24])+','for i in range(0,len(payload),24))+'\n};\n')
        pins[str(embedded)]=sha(embedded)
    def run(argv,name):
        with (out/name).open('x') as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
    if task:
        capi=(task_source/'src/c_api.cpp').read_text();definitions=[]
        for name,member in [('device','std::unique_ptr<Gpu> gpu;'),('texture','std::shared_ptr<Texture> texture;')]:
            matches=re.findall(r'struct hakios_metal_'+name+r' \{[^{}]*\};',capi)
            assert len(matches)==1
            normalized=re.sub(r'//[^\n]*','',matches[0])
            assert ''.join(normalized.split())==''.join(('struct hakios_metal_'+name+' {'+member+'};').split()), 'core projection changed'
            definitions.append(matches[0])
        projection=out/'GauguinTaskCoreABI.h'
        projection.write_text('/* Generated from the exact pinned core c_api.cpp; diagnostic only. */\n'
                              '#include <hakios-metal/command.hpp>\n#include <hakios-metal/texture.hpp>\n'
                              'using namespace hakios::metal;\n'+'\n'.join(definitions)+'\n'
                              'static_assert(sizeof(hakios_metal_device)==8);\n'
                              'static_assert(sizeof(hakios_metal_texture)==16);\n')
        pins[str(projection)]=sha(projection)
        for stem in ['task_surface_permissions','task_surface_core_bridge']:
            obj=out/(stem+'.o');task_objects.append(str(obj))
            run(['xcrun','--sdk','iphoneos','clang++','-target','arm64-apple-ios16.0','-isysroot',str(sdk),
                 '-std=c++17','-O1','-Wall','-Wextra','-Werror','-I'+str(task_source/'include'),'-I'+str(out),
                 '-c',str(source.parent/(stem+'.cpp')),'-o',str(obj)],stem+'.log')
    argv=['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0','-isysroot',str(sdk),
          '-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fblocks','-fno-objc-arc',
          '-DGAUGUIN_METAL_FRONTEND_BUILD="'+tag+'"',*shader_args,*ca_args,*fp16_args,*task_args,'-I'+str(header.parent),str(source),
          '-framework','Foundation','-framework','Metal','-framework','IOKit','-framework','IOSurface',
          '-lobjc',*task_objects,*([str(task_core),'-lc++','-Wl,-rpath,/usr/local/lib/gauguin'] if task else []),'-o',str(probe)]
    run(argv,'compile-link.log')
    spec=importlib.util.spec_from_file_location('core_build',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    version=m.ios_version(probe)
    run(['codesign','--force','--sign','-',str(probe)],'sign.log')
    run(['codesign','--verify','--strict',str(probe)],'verify.log')
    run(['otool','-L',str(probe)],'loads.log');run(['nm','-m','-u',str(probe)],'imports.log')
    if task:
        run(['otool','-l',str(probe)],'load-commands.log')
        assert '@rpath/libGauguinMetalCore.dylib' in (out/'loads.log').read_text()
        assert re.search(r'cmd LC_RPATH\n\s+cmdsize \d+\n\s+path /usr/local/lib/gauguin \(offset ', (out/'load-commands.log').read_text()), 'core must resolve before main'
    assert all(sha(Path(name))==pin for name,pin in pins.items())
    result=dict(state='native-iOS16-CARenderer-layer-probe-not-device-qualified' if a.ca_renderer else ('native-iOS16-MTL-shader-probe-not-device-qualified' if shader else 'native-iOS16-MTL-object-probe-not-device-qualified'),probe=str(probe),
                bytes=probe.stat().st_size,sha256=sha(probe),build=tag,platform_version=version,
                frontend_sha256=frontend['sha256'],core_sha256=frontend['core_sha256'],
                expected_jobs=(11+(5 if task else 0) if fp16 else 10) if a.ca_renderer else (93 if shader else 83),expected_jobs_scope='explicit FP16/poison/readback/task jobs; framework jobs counted separately' if task else ('explicit FP16/poison/readback jobs; framework jobs counted separately' if fp16 else ('explicit poison/readback jobs; framework jobs counted separately' if a.ca_renderer else 'all probe jobs')),expected_base_pixel_checks=0 if a.ca_renderer else 339968,
                expected_shader_pixel_checks=32768 if shader else 0,expected_compute_words=512 if shader else 0,
                expected_half_pixels=4096 if shader else 0,abandoned_command_buffers=0 if a.ca_renderer else 80,
                shader_library=shader,shader_pipeline_probe_enabled=bool(shader),
                ca_renderer_probe_enabled=a.ca_renderer,expected_ca_scenes=5 if a.ca_renderer else 0,
                native_fp16_probe_enabled=bool(fp16),fp16_library=fp16,expected_native_fp16_pixels=4096 if fp16 else 0,
                task_surface_probe_enabled=bool(task),task_core_receipt=str(a.task_core_receipt.resolve()) if task else None,
                task_sampler_library=task_shader,expected_task_surface_pixels=20480 if task else 0,
                expected_task_surface_jobs=5 if task else 0,task_surface_hardware_qualified=False,
                expected_ca_pixel_checks=20480 if a.ca_renderer else 0,
                shader_pipeline_qualification=False,device_discovery=False,UI_qualification=False,
                input_pins=pins,inputs_unchanged=True,compiler_argv=argv,device_commands=0,installed=False)
    with (out/'result.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','compiler_argv')},indent=2))

if __name__=='__main__':main()
