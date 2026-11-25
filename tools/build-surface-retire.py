#!/usr/bin/env python3
"""Rebuild the core and prove baseline identity under canonical Apple signing."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import shutil
import subprocess
from surface_signature_compare import compare_signature_reservations

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/surface-retire-334'
OWNER=MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
OLD=OWNER/'research/tmp/metal-ownership-v1/implementation-20261112/native-03'
FQ=MAIN/'research/tmp/gauguin-fault-cache-worktree-20261115/research/tmp/fault-cache-322/native-v2'
SC=MAIN/'research/tmp/gauguin-stage-cache-worktree-20261115/research/tmp/stage-cache-323/native-v1'
TAG='8a71fe61aded108fa9ba5a22'
BASE_SHA='1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
BASE331=MAIN/'research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331/core-native-v1'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);out=ap.parse_args().out.resolve()
    assert out.is_relative_to(STATE) and not out.exists()
    original=json.loads((OLD/'result.json').read_text());prior=json.loads((BASE331/'result.json').read_text());sc=json.loads((SC/'result.json').read_text())
    prepared=STATE/'prepared-v1/result.json';r=json.loads(prepared.read_text())
    spec=importlib.util.spec_from_file_location('builder',OWNER/'tools/build-hakios-metal.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    mb=[Path(p).parent for p in original['input_pins'] if p.endswith('/build.ninja')]
    ms=[Path(p).parents[3] for p in original['input_pins'] if p.endswith('/src/freedreno/ir3/ir3.h')]
    assert len(mb)==len(ms)==1;mb,ms=mb[0],ms[0]
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    pins=dict(prior['input_pins']);pins.update(r['input_pins'])
    for p in [SC/'result.json',BASE331/'result.json',prepared,Path(__file__),WORK/'tools/surface_signature_compare.py',STATE/'storage-resume-admission.json',OLD/'result.json',Path(prior['products']['candidate']['binary'])]:pins[str(p)]=sha(p)
    for v,items in r['source_pins'].items():
        for p,h in items.items():pins[str(Path(r['sources'][v])/p)]=h
    assert all(sha(p)==h for p,h in pins.items())
    assert prior['products']['candidate']['sha256']==BASE_SHA and original['cache_build_tag']==TAG
    common=['xcrun','--sdk','iphoneos','clang++','-target','arm64-apple-ios16.0','-isysroot',str(sdk),
        '-std=c++17','-O2','-Wall','-Wextra','-Werror','-DHAKIOS_METAL_MESA','-DHAKIOS_METAL_TARGET_A619','-DHAKIOS_METAL_CACHE_BUILD="'+TAG+'"']
    out.mkdir(parents=True);result=dict(state='SURF334-native-building',input_pins=pins,steps=[],products={},device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=180)
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        step=dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log))
        result['steps'].append(step);save();assert p.returncode==0,name
    try:
        for v in ('baseline','candidate'):
            source=Path(r['sources'][v]);dest=out/v;dest.mkdir()
            flags=[*common,'-I'+str(source/'include'),*old.mesa_flags(ms,mb),
                '-ffile-prefix-map='+str(source)+'='+original['source'],
                '-ffile-prefix-map='+str(source/'src/compiler.cpp')+'='+sc['source'],
                '-ffile-prefix-map='+str(source/'src/iokit_transport.cpp')+'='+str(FQ/'sources/iokit_transport.cpp')]
            def compile(name):
                argv=[*flags,'-c',str(source/'src'/f'{name}.cpp'),'-o',str(dest/(name+'.o'))]
                p=subprocess.run(argv,capture_output=True,timeout=180)
                log=out/(v+'-compile-'+name+'.log');log.write_bytes(p.stdout+p.stderr)
                return dict(name=v+'-compile-'+name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log))
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:steps=list(pool.map(compile,old.CORE))
            result['steps']+=steps;save();assert all(s['exit']==0 for s in steps),'compile failed'
            for name in old.CORE:old.ios_version(dest/(name+'.o'))
            if v=='baseline':
                matches={name:sha(dest/(name+'.o'))==sha(BASE331/'candidate'/(name+'.o')) for name in old.CORE}
                result['baseline_object_matches']=matches;save();assert all(matches.values()),matches
            library=dest/'libGauguinMetalCore.dylib'
            run([*flags,'-dynamiclib',*[str(dest/(name+'.o')) for name in old.CORE],*[str(mb/name) for name in old.ARCHIVES],
                '-lz','-lm','-framework','IOKit','-framework','IOSurface','-framework','CoreFoundation',
                '-Wl,-install_name,@rpath/libGauguinMetalCore.dylib','-o',str(library)],v+'-link')
            version=old.ios_version(library)
            run(['codesign','--force','--sign','-',str(library)],v+'-sign')
            run(['codesign','--verify','--strict',str(library)],v+'-verify')
            if v == 'baseline':
                installed = Path(prior['products']['candidate']['binary'])
                assert sha(installed) == BASE_SHA
                run(['codesign','--verify','--strict',str(installed)],'installed-verify')
                comparison = compare_signature_reservations(installed.read_bytes(), library.read_bytes())
                comparison['original_sha256'] = BASE_SHA
                comparison['rebuilt_initial_sha256'] = sha(library)
                reference = out/'signature-reference'/library.name
                reference.parent.mkdir()
                shutil.copyfile(installed, reference)
                for name, path in [('reference',reference),('baseline',library)]:
                    run(['codesign','--remove-signature',str(path)],name+'-remove-signature')
                    run(['codesign','--force','--sign','-',str(path)],name+'-canonical-sign')
                    run(['codesign','--verify','--strict',str(path)],name+'-canonical-verify')
                assert reference.read_bytes() == library.read_bytes(), 'canonical signed baseline differs'
                comparison.update(canonical_signed_bytes_identical=True,
                                  canonical_sha256=sha(library), installed_input_unchanged=sha(installed)==BASE_SHA)
                result['baseline_reproduction'] = comparison
                save()
            for args,label in [(['nm','-m','-u'],'imports'),(['nm','-gU'],'exports'),(['otool','-L'],'loads')]:run([*args,str(library)],v+'-'+label)
            result['products'][v]=dict(binary=str(library),bytes=library.stat().st_size,sha256=sha(library),platform_version=version)
            save()
        exports=lambda v:{r.split()[-1] for r in (out/(v+'-exports.log')).read_text().splitlines() if r.strip()}
        result['exports_added']=sorted(exports('candidate')-exports('baseline'))
        result['exports_removed']=sorted(exports('baseline')-exports('candidate'))
        assert not result['exports_removed']
        assert (out/'baseline-imports.log').read_bytes()==(out/'candidate-imports.log').read_bytes()
        assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
        result.update(state='SURF334-native-baseline-canonical-signature-reproduced-candidate-signed',cache_build_tag=TAG,
            all_core_TUs_recompiled=True,imports_unchanged=True,loads_unchanged=True,existing_allocation_bytes=8409088,
            fits_existing_allocation=result['products']['candidate']['bytes']<=8409088,physical_FPS_qualified=False)
    except BaseException as e:result.update(state='SURF334-native-failed',error=repr(e));raise
    finally:
        result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    assert result['inputs_unchanged']
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
