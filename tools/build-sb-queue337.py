#!/usr/bin/env python3
"""Reproduce SB315 and sign the queue fix with the existing insertion identity."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from surface_signature_compare import compare_signature_reservations

WORK=Path(__file__).resolve().parents[1]
MAIN=Path('/Users/baai/Project/ios-gauguin')
OLD=MAIN/'research/tmp/gauguin-sb-stack-worktree-20261114/research/tmp/sb-stack-315'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def imports(binary):
    data=Path(binary).read_bytes();_,cpu,_,kind,n,size,_,_=struct.unpack_from('<8I',data)
    assert cpu==0x100000c and kind==6
    libs=[];symtab=None;at=32
    for _ in range(n):
        cmd,length=struct.unpack_from('<II',data,at);assert length>=8 and at+length<=32+size
        if cmd in (0xc,0x80000018,0x8000001f,0x80000023):
            off=struct.unpack_from('<I',data,at+8)[0];libs.append(data[at+off:data.index(b'\0',at+off)].decode())
        if cmd==2:symtab=struct.unpack_from('<4I',data,at+8)
        at+=length
    assert at==32+size and symtab
    so,n,st,sn=symtab;strings=data[st:st+sn];result=[]
    for off,typ,_,desc,_ in struct.iter_unpack('<IBBHQ',data[so:so+n*16]):
        if typ&0x0e==0 and typ&1:
            ordinal=desc>>8;assert 1<=ordinal<=len(libs)
            result.append((strings[off:strings.index(b'\0',off)].decode(),libs[ordinal-1],bool(desc&0x40)))
    return sorted(result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    out=ap.parse_args().out.resolve();assert out.is_relative_to(WORK/'research/tmp');out.mkdir(parents=True,exist_ok=False)
    receipt=OLD/'native-v3/result.json';old=json.loads(receipt.read_text())
    abi_path=OLD/'abi-v3/result.json';abi=json.loads(abi_path.read_text())
    assert old['sha256']=='10683efc71f95f1a79563727cfef10374df8d1ec94f6249a83328b7d6660683b'
    assert sha(old['binary'])==old['sha256'] and abi['binary_sha256']==old['sha256'] and not abi['missing_imports']
    source=WORK/'graphics/gauguin-sb-rate-trace/SBRateTrace.m'
    pins=dict(old['input_pins'])
    for p in [receipt,abi_path,Path(__file__),WORK/'tools/surface_signature_compare.py',source,*source.parent.glob('SB*.h')]:pins[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in pins.items())
    result=dict(state='SB337-native-started',input_pins=pins,steps=[],products={},device_commands=0,runtime_qualified=False)
    def run(argv,label):
        with (out/(label+'.log')).open('x')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
        result['steps'].append(dict(label=label,argv=argv,exit=r.returncode));assert r.returncode==0,label
    try:
        for tag,src in [('baseline',Path(old['source'])),('candidate',source)]:
            folder=out/tag;folder.mkdir();binary=folder/'libGauguinSBRateTrace.dylib'
            argv=list(old['compiler_argv']);argv[argv.index(old['source'])]=str(src);argv[argv.index('-o')+1]=str(binary)
            run(argv,tag+'-compile');run(['codesign','--force','--sign','-',str(binary)],tag+'-sign')
            run(['codesign','--verify','--strict',str(binary)],tag+'-verify')
            run(['nm','-m','-u',str(binary)],tag+'-imports');run(['otool','-L',str(binary)],tag+'-loads')
            result['products'][tag]=dict(binary=str(binary),sha256=sha(binary),bytes=binary.stat().st_size)
            if tag=='baseline':
                if sha(binary)!=old['sha256']:
                    result['baseline_signature_comparison']=compare_signature_reservations(Path(old['binary']).read_bytes(),binary.read_bytes())
                    canonical=[]
                    for name,p in [('old',Path(old['binary'])),('rebuilt',binary)]:
                        copy=out/('canonical-'+name)/binary.name;copy.parent.mkdir();shutil.copyfile(p,copy)
                        run(['codesign','--verify','--strict',str(copy)],name+'-initial-verify')
                        run(['codesign','--remove-signature',str(copy)],name+'-remove-signature')
                        run(['codesign','--force','--sign','-',str(copy)],name+'-canonical-sign')
                        run(['codesign','--verify','--strict',str(copy)],name+'-canonical-verify');canonical.append(sha(copy))
                    assert canonical[0]==canonical[1];result['baseline_canonical_sha256']=canonical[0]
                result['baseline_all_code_data_UUID_symbols_identical']=True
        candidate=Path(result['products']['candidate']['binary'])
        expected={(r['symbol'],r['provider'],r['weak']) for r in abi['imports'] if r['resolved']}
        actual=imports(candidate);assert set(actual)<=expected
        assert candidate.stat().st_size<=94208
        assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
        result.update(state='native-SB337-baseline-qualified-candidate-signed-import-subset',
                      install_name=old['install_name'],existing_allocation_bytes=94208,
                      imports_20H392_qualified=True,checked_imports=len(actual),missing_imports=[],
                      import_proof='Exact (symbol, provider, weak) subset of the resolved SB315 actual20H392 imports',
                      removed_imports=sorted(expected-set(actual)),capacity=1024,extra_threads=0)
    finally:
        result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['inputs_unchanged']
    print(json.dumps({k:v for k,v in result.items()if k not in ('input_pins','steps','baseline_signature_comparison')},indent=2))

if __name__=='__main__':main()
