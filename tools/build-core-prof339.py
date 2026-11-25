#!/usr/bin/env python3
"""Reproduce0338 baseline; replace only C API and command TU for0339."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import struct
from surface_signature_compare import compare_signature_reservations

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-prof-339'
PRIOR=MAIN/'research/tmp/gauguin-core-async-worktree-20261117/research/tmp/core-async-338'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json')
    ap.add_argument('--host',type=Path,default=BASE/'core-host-v3/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());host=json.loads(a.host.read_text())
    assert host['state']=='0339-real-core-ownership-categories-submit-phases-passed' and host['inputs_unchanged']
    old=json.loads((PRIOR/'native-v1/result.json').read_text());old_prepared=json.loads((PRIOR/'prepared-v2/result.json').read_text())
    old_source=Path(old_prepared['sources']['candidate']);old_dest=PRIOR/'native-v1/candidate'
    reference=Path(old['products']['candidate']['binary']);assert sha(reference)=='9eeab2b81413cb2cc34f6a1912854c62259decd360414e32fc51c2cbeef0fea1'
    compile_step=next(s for s in old['steps'] if s['name']=='candidate-compile-c_api')
    link_step=next(s for s in old['steps'] if s['name']=='candidate-link')
    objects=sorted(old_dest.glob('*.o'));assert len(objects)==12
    paths=[Path(__file__),a.prepared,a.host,PRIOR/'native-v1/result.json',reference,*objects]
    pins={str(p.resolve()):sha(p) for p in paths}
    for variant in ('baseline','candidate'):
        for name,h in prepared['source_pins'][variant].items():
            p=Path(prepared['sources'][variant])/name;assert sha(p)==h;pins[str(p)]=h
    for arg in link_step['argv']:
        if arg.endswith('.a'):pins[arg]=sha(arg)
    out.mkdir();result=dict(state='0339-native-core-building',steps=[],products={},input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=180);log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)))
        save();assert p.returncode==0,(name,p.stderr[-2000:])
    try:
        for variant in ('baseline','candidate'):
            source=Path(prepared['sources'][variant]);dest=out/variant;dest.mkdir()
            for p in objects:
                if p.name not in ('c_api.o','command.o'):shutil.copyfile(p,dest/p.name)
            def rewrite(argv):return [str(x).replace(str(old_source),str(source)).replace(str(old_dest),str(dest)) for x in argv]
            for unit in ('c_api','command'):
                argv=rewrite(compile_step['argv'])
                argv=[x.replace('/src/c_api.cpp','/src/'+unit+'.cpp').replace('/c_api.o','/'+unit+'.o') for x in argv]
                run(argv,variant+'-compile-'+unit)
                if variant=='baseline':assert sha(dest/(unit+'.o'))==sha(old_dest/(unit+'.o')),(unit,'baseline object differs')
            run(rewrite(link_step['argv']),variant+'-link')
            binary=dest/'libGauguinMetalCore.dylib'
            if variant=='candidate':
                # Standard Mach-O local-symbol stripping changes LINKEDIT
                # metadata only. Keep the full sidecar for offline PC lookup.
                before=binary.read_bytes();shutil.copyfile(binary,dest/'unstripped.dylib')
                run(['xcrun','strip','-x',str(binary)],'candidate-trim-local-symbols')
                def section_payloads(data):
                    result={};at=32
                    for _ in range(struct.unpack_from('<I',data,16)[0]):
                        cmd,size=struct.unpack_from('<II',data,at)
                        if cmd==0x19:
                            seg=data[at+8:at+24].rstrip(b'\0')
                            for i in range(struct.unpack_from('<I',data,at+64)[0]):
                                q=at+72+i*80;name=data[q:q+16].rstrip(b'\0')
                                addr,length,offset=struct.unpack_from('<QQI',data,q+32)
                                kind=struct.unpack_from('<I',data,q+64)[0]&255
                                payload=b'' if kind in (1,12,18) else data[offset:offset+length]
                                assert kind in (1,12,18) or len(payload)==length
                                result[(seg,name)]=(addr,length,offset,hashlib.sha256(payload).hexdigest())
                        at+=size
                    return result
                assert section_payloads(before)==section_payloads(binary.read_bytes()),'symbol trim changed section data/layout'
                result['local_symbol_trim']=dict(standard_strip_x=True,removed_only_local_symbols=True,
                    unstripped_sidecar=str(dest/'unstripped.dylib'),unstripped_sha256=sha(dest/'unstripped.dylib'),
                    all_section_payloads_addresses_sizes_and_offsets_identical=True,
                    unstripped_bytes=len(before),stripped_bytes=binary.stat().st_size)
            run(['codesign','--force','--sign','-',str(binary)],variant+'-sign')
            run(['codesign','--verify','--strict',str(binary)],variant+'-verify')
            if variant=='baseline':
                comparison=compare_signature_reservations(reference.read_bytes(),binary.read_bytes())
                original=out/'signature-reference'/binary.name;original.parent.mkdir();shutil.copyfile(reference,original)
                for label,path in [('reference',original),('baseline',binary)]:
                    run(['codesign','--remove-signature',str(path)],label+'-remove-signature')
                    run(['codesign','--force','--sign','-',str(path)],label+'-canonical-sign')
                assert original.read_bytes()==binary.read_bytes(),'signed0338 baseline differs'
                result['baseline_reproduction']=dict(comparison,canonical_signed_bytes_identical=True)
            for args,label in [(['nm','-m','-u'],'imports'),(['nm','-gU'],'exports'),(['otool','-L'],'loads'),(['vtool','-show-build'],'platform')]:
                run([*args,str(binary)],variant+'-'+label)
            result['products'][variant]=dict(binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary));save()
        exports=lambda v:{s.split()[-1] for s in (out/(v+'-exports.log')).read_text().splitlines() if s.strip()}
        imports=lambda v:{s.strip().split(' (from ')[0] for s in (out/(v+'-imports.log')).read_text().splitlines() if s.strip()}
        assert exports('baseline')==exports('candidate'),'external exports differ'
        assert imports('baseline')==imports('candidate'),'imports differ'
        assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
        result.update(state='0339-native-core-baseline-reproduced-candidate-signed',recompiled_units=['c_api','command'],
            all_other_core_objects_identical=True,exports_added=[],exports_removed=[],imports_added=[],imports_removed=[],
            load_commands_unchanged=True,existing_allocation_bytes=8409088,
            fits_existing_allocation=result['products']['candidate']['bytes']<=8409088,
            diagnostic_only=True,physical_FPS_qualified=False)
        assert result['fits_existing_allocation'],'candidate exceeds original allocated slot'
    except BaseException as error:result.update(state='0339-native-core-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))


if __name__=='__main__':main()
