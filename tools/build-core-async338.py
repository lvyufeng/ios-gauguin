#!/usr/bin/env python3
"""Reproduce installed334, relinking only the changed C API for 0338."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
from surface_signature_compare import compare_signature_reservations

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'
OLD=MAIN/'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json')
    ap.add_argument('--host',type=Path,default=BASE/'core-host-v4/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());host=json.loads(a.host.read_text())
    assert host['state']=='0338-core-host-ownership-and-notification-passed' and host['inputs_unchanged']
    old=json.loads((OLD/'native-v2/result.json').read_text())
    oldPrepared=json.loads((OLD/'prepared-v1/result.json').read_text())
    originalSource=Path(oldPrepared['sources']['candidate']);originalDest=OLD/'native-v2/candidate'
    compile_step=next(s for s in old['steps'] if s['name']=='candidate-compile-c_api')
    link_step=next(s for s in old['steps'] if s['name']=='candidate-link')
    objects=sorted(originalDest.glob('*.o'));assert len(objects)>=12
    installed=Path(old['products']['candidate']['binary'])
    assert sha(installed)=='dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
    pins={str(p.resolve()):sha(p) for p in [a.prepared,a.host,Path(__file__),WORK/'tools/surface_signature_compare.py',
                OLD/'native-v2/result.json',OLD/'prepared-v1/result.json',installed,*objects]}
    for variant in ('baseline','candidate'):
        for name,digest in prepared['source_pins'][variant].items():
            p=Path(prepared['sources'][variant])/name;assert sha(p)==digest;pins[str(p)]=digest
    for arg in link_step['argv']:
        if arg.endswith('.a'):pins[arg]=sha(arg)
    out.mkdir();result=dict(state='0338-native-core-building',input_pins=pins,products={},steps=[],device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=180)
        log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)))
        save();assert p.returncode==0,(name,p.stderr[-1200:])
    try:
        for variant in ('baseline','candidate'):
            source=Path(prepared['sources'][variant]);dest=out/variant;dest.mkdir()
            for p in objects:
                if p.name!='c_api.o':shutil.copyfile(p,dest/p.name)
            def rewrite(argv):
                return [str(arg).replace(str(originalSource),str(source)).replace(str(originalDest),str(dest)) for arg in argv]
            run(rewrite(compile_step['argv']),variant+'-compile-c_api')
            if variant=='baseline':
                assert sha(dest/'c_api.o')==sha(originalDest/'c_api.o'),'baseline C API object differs'
            run(rewrite(link_step['argv']),variant+'-link')
            binary=dest/'libGauguinMetalCore.dylib'
            run(['codesign','--force','--sign','-',str(binary)],variant+'-sign')
            run(['codesign','--verify','--strict',str(binary)],variant+'-verify')
            if variant=='baseline':
                comparison=compare_signature_reservations(installed.read_bytes(),binary.read_bytes())
                reference=out/'signature-reference'/binary.name;reference.parent.mkdir();shutil.copyfile(installed,reference)
                for name,path in [('reference',reference),('baseline',binary)]:
                    run(['codesign','--remove-signature',str(path)],name+'-remove-signature')
                    run(['codesign','--force','--sign','-',str(path)],name+'-canonical-sign')
                    run(['codesign','--verify','--strict',str(path)],name+'-canonical-verify')
                assert reference.read_bytes()==binary.read_bytes(),'installed334 canonical baseline differs'
                comparison['canonical_signed_bytes_identical']=True;result['baseline_reproduction']=comparison
            for args,name in [(['nm','-m','-u'],'imports'),(['nm','-gU'],'exports'),(['otool','-L'],'loads'),(['vtool','-show-build'],'platform')]:
                run([*args,str(binary)],variant+'-'+name)
            result['products'][variant]=dict(binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary))
            save()
        exports=lambda v:{s.split()[-1] for s in (out/(v+'-exports.log')).read_text().splitlines() if s.strip()}
        added=exports('candidate')-exports('baseline');removed=exports('baseline')-exports('candidate')
        assert added=={'_hakios_metal_cb_trace338','_hakios_metal_cb_notify_recorded338'} and not removed,(added,removed)
        def imports(v):
            return {s.strip().split(' (from ')[0] for s in (out/(v+'-imports.log')).read_text().splitlines() if s.strip()}
        extra=imports('candidate')-imports('baseline')
        assert all('_mach_timebase_info' in row or '_mach_absolute_time' in row for row in extra),extra
        assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
        result.update(state='0338-native-core-baseline-reproduced-candidate-signed',all_other_core_objects_identical=True,
            recompiled_units=['c_api'],exports_added=sorted(added),exports_removed=[],added_import_rows=sorted(extra),
            old_imports_retained=not(imports('baseline')-imports('candidate')),
            load_commands_unchanged=True,existing_allocation_bytes=8409088,
            fits_existing_allocation=result['products']['candidate']['bytes']<=8409088,physical_FPS_qualified=False)
        assert result['fits_existing_allocation']
    except BaseException as error:result.update(state='0338-native-core-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==d for p,d in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
