#!/usr/bin/env python3
"""Reproduce actual signed0340 baseline; compile five diagnostic0341 units."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/program-io-341'
PRIOR=MAIN/'research/tmp/gauguin-draw-submit-worktree-20261117/research/tmp/draw-submit-340'
CHANGED=('c_api','command','render','gpu','iokit_transport')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def sections(data):
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


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--prepared',type=Path,default=BASE/'prepared-v2/result.json')
    ap.add_argument('--host',type=Path,default=BASE/'core-host-v3/result.json');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads(a.prepared.read_text());host=json.loads(a.host.read_text())
    assert host['state']=='0341-real-core-ownership-program-slab-diagnostics-passed' and host['inputs_unchanged']
    old=json.loads((PRIOR/'native-v2/result.json').read_text());parent=json.loads((PRIOR/'prepared-v2/result.json').read_text())
    old_source=Path(parent['sources']['candidate']);old_dest=PRIOR/'native-v2/candidate'
    reference=Path(old['products']['candidate']['binary']);assert sha(reference)=='b1653fd74f1e0ad88752ec40924455a7a7eab67286151c9a98fa1ab53547c94d'
    compile_step=next(s for s in old['steps'] if s['name']=='candidate-compile-c_api')
    link_step=next(s for s in old['steps'] if s['name']=='candidate-link')
    objects=sorted({Path(x) for x in link_step['argv'] if x.endswith('.o')});assert len(objects)==12
    pins={str(p.resolve()):sha(p) for p in (Path(__file__),a.prepared,a.host,PRIOR/'native-v2/result.json',reference,*objects)}
    for variant in ('baseline','candidate'):
        for name,digest in prepared['source_pins'][variant].items():
            p=Path(prepared['sources'][variant])/name;assert sha(p)==digest;pins[str(p)]=digest
    for arg in link_step['argv']:
        if arg.endswith('.a'):pins[arg]=sha(arg)
    out.mkdir();result=dict(state='0341-native-core-building',steps=[],products={},input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,name):
        p=subprocess.run(argv,capture_output=True,timeout=240);log=out/(name+'.log');log.write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log)));save()
        assert p.returncode==0,(name,p.stderr[-2400:])
    try:
        for variant in ('baseline','candidate'):
            source=Path(prepared['sources'][variant]);dest=out/variant;dest.mkdir()
            def rewrite(argv):
                values=[str(x).replace(str(old_source),str(source)) for x in argv]
                return [str(dest/Path(x).name) if x.startswith(str(old_dest)+'/') and (x.endswith('.dylib') or Path(x).stem in CHANGED) else x for x in values]
            for unit in CHANGED:
                argv=[x.replace('/src/c_api.cpp','/src/'+unit+'.cpp').replace('/c_api.o','/'+unit+'.o') for x in rewrite(compile_step['argv'])]
                run(argv,variant+'-compile-'+unit)
                if variant=='baseline':assert sha(dest/(unit+'.o'))==sha(old_dest/(unit+'.o')),(unit,'baseline object differs')
            run(rewrite(link_step['argv']),variant+'-link')
            binary=dest/'libGauguinMetalCore.dylib';before=binary.read_bytes();shutil.copyfile(binary,dest/'unstripped.dylib')
            run(['xcrun','strip','-x',str(binary)],variant+'-strip-local')
            assert sections(before)==sections(binary.read_bytes()),'strip changed code/data section layout or bytes'
            run(['codesign','--force','--sign','-',str(binary)],variant+'-sign')
            run(['codesign','--verify','--strict',str(binary)],variant+'-verify')
            if variant=='baseline':assert binary.read_bytes()==reference.read_bytes(),'signed0340 baseline differs'
            for args,label in [(['nm','-m','-u'],'imports'),(['nm','-gU'],'exports'),(['otool','-L'],'loads'),(['vtool','-show-build'],'platform')]:run([*args,str(binary)],variant+'-'+label)
            result['products'][variant]=dict(binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary));save()
        exports=lambda v:{s.split()[-1] for s in (out/(v+'-exports.log')).read_text().splitlines() if s.strip()}
        imports=lambda v:{s.strip().split(' (from ')[0] for s in (out/(v+'-imports.log')).read_text().splitlines() if s.strip()}
        assert exports('baseline')==exports('candidate') and imports('baseline')==imports('candidate')
        assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
        result.update(state='0341-native-core-baseline340-exact-candidate-signed',baseline_signed_bytes_identical=True,
            all_five_baseline_objects_identical=True,recompiled_units=list(CHANGED),seven_other_objects_reused_without_copy=True,
            all_code_data_section_payloads_addresses_offsets_unchanged_by_strip=True,unstripped_sidecars_retained=True,
            exports_added=[],exports_removed=[],imports_added=[],imports_removed=[],load_commands_unchanged=True,
            existing_allocation_bytes=8409088,fits_existing_allocation=result['products']['candidate']['bytes']<=8409088,
            CPU_workspace_and_stable_ordered_index_reuse=True,diagnostic_only=True,
            program_table_slab_and_IO_CPU_bounds=True,existing_clock_gettime_import_reused=True,physical_FPS_qualified=False)
        assert result['fits_existing_allocation']
    except BaseException as error:result.update(state='0341-native-core-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('steps','input_pins')},indent=2))


if __name__=='__main__':main()
