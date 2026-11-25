#!/usr/bin/env python3
"""Reproduce Q337 frontend, link 0340 notification frontend to signed core."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/program-io-341'
PRIOR=MAIN/'research/tmp/gauguin-draw-submit-worktree-20261117/research/tmp/draw-submit-340'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--core',type=Path,default=BASE/'native-v1/result.json')
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());native=json.loads(a.core.read_text())
    old=json.loads((PRIOR/'frontend-native-v1/result.json').read_text())
    assert native['state']=='0341-native-core-baseline340-exact-candidate-signed' and native['inputs_unchanged']
    old_source=PRIOR/'prepared-v2/frontend-candidate';old_bundle=Path(old['products']['candidate']['binary']).parent
    compile_step=next(s for s in old['steps'] if s.get('name')=='candidate-compile')
    pins={str(p.resolve()):sha(p) for p in [Path(__file__),a.core,a.prepared,PRIOR/'frontend-native-v1/result.json',
        Path(old['products']['candidate']['binary']),Path(native['products']['candidate']['binary']),
        old_bundle/'Info.plist',old_bundle/'_CodeSignature/CodeResources']}
    for variant in ('frontend-baseline','frontend-candidate'):
        for name,digest in prepared['source_pins'][variant].items():
            p=Path(prepared['sources'][variant])/name;assert sha(p)==digest;pins[str(p)]=digest
    out.mkdir();result=dict(state='0341-frontend-building',steps=[],products={},input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=180)
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)))
        save();assert p.returncode==0,(name,p.stderr[-2200:])
    try:
        for variant in ('baseline','candidate'):
            source=Path(prepared['sources']['frontend-'+variant]);dest=out/variant/'GauguinMetalDesktop.bundle'
            dest.mkdir(parents=True);shutil.copyfile(old_bundle/'Info.plist',dest/'Info.plist')
            binary=dest/'GauguinMetalDesktop';argv=[]
            for arg in compile_step['argv']:
                arg=str(arg).replace(str(old_source),str(source))
                if arg==old['products']['candidate']['binary']:arg=str(binary)
                if variant=='candidate':
                    if arg.startswith('-I') and arg.endswith('/hakios-metal/include'):
                        arg='-I'+str(Path(prepared['sources']['candidate'])/'include')
                    if arg.endswith('/libGauguinMetalCore.dylib'):
                        arg=native['products']['candidate']['binary']
                argv.append(arg)
            run(argv,variant+'-compile')
            run(['codesign','--force','--sign','-',str(dest)],variant+'-sign')
            run(['codesign','--verify','--strict',str(dest)],variant+'-verify')
            for name in ('Info.plist','_CodeSignature/CodeResources'):
                assert sha(dest/name)==sha(old_bundle/name)
            if variant=='baseline':assert binary.read_bytes()==Path(old['products']['candidate']['binary']).read_bytes()
            for args,name in [(['nm','-m','-u'],'imports'),(['nm','-gU'],'exports'),(['otool','-L'],'loads'),(['vtool','-show-build'],'platform')]:
                run([*args,str(binary)],variant+'-'+name)
            result['products'][variant]=dict(binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary))
            save()
        def imports(variant):return {s.strip() for s in (out/(variant+'-imports.log')).read_text().splitlines() if s.strip()}
        added=imports('candidate')-imports('baseline');removed=imports('baseline')-imports('candidate')
        result.update(state='0341-frontend-baseline-reproduced-candidate-signed',baseline_exact_0340_signed_bytes=True,
            resources_unchanged=True,added_imports=sorted(added),removed_imports=sorted(removed),
            existing_core_entrypoints_retained=True,existing_allocation_bytes=430080,
            fits_existing_allocation=result['products']['candidate']['bytes']<=430080,
            asynchronous_notification=True,wire_tags=['C4Q341','Q341','CR341','N341'],physical_FPS_qualified=False)
        assert result['fits_existing_allocation']
        assert not added and not removed
        assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
    except BaseException as error:result.update(state='0341-frontend-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==digest for p,digest in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
