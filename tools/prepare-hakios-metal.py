#!/usr/bin/env python3
"""Prepare the pinned Metal core and gauguin patch in a fresh local directory.

The cache contains public upstream source; this tool does not download,
compile, install, access a device, or modify an existing output tree.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--profile',choices=['a619-baseline','a619-graphics-images'],default='a619-baseline')
    a=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    spec=repo/'graphics/hakios-metal'
    manifest=json.loads((spec/'upstream.json').read_text())
    cache=a.cache.resolve();out=a.out.resolve()
    assert not out.exists(),'fresh output required'
    rows=manifest['files'];assert len(rows)==227
    pins={str(spec/'upstream.json'):sha(spec/'upstream.json'),str(Path(__file__).resolve()):sha(Path(__file__).resolve())}
    sources=[]
    for row in rows:
        rel=Path(row['path'])
        assert rel.parts[0]=='hakios-metal' and not rel.is_absolute() and '..' not in rel.parts
        p=cache/rel;raw=p.read_bytes()
        assert len(raw)==row['size']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['sha'],str(rel)
        pins[str(p)]=sha(p);sources.append((p,Path(*rel.parts[1:])))
    patch_names=['0001-a619-device-profile.patch']
    if a.profile=='a619-graphics-images':patch_names.append('0002-graphics-storage-images.patch')
    patches=[spec/'patches'/name for name in patch_names];assert all(p.is_file()for p in patches)
    overlays=sorted(p for p in (spec/'overlay').rglob('*') if p.is_file())
    for p in patches+overlays:pins[str(p)]=sha(p)
    out.mkdir(parents=True,exist_ok=False)
    source=out/'hakios-metal';source.mkdir()
    for old,rel in sources:
        new=source/rel;new.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old,new)
    for i,p in enumerate(patches):
        with (out/(f'patch-{i}.log')).open('x') as log:
            subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-d',str(source),'-i',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
    for p in overlays:
        q=source/p.relative_to(spec/'overlay');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    outputs={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    assert len(outputs)==228
    unchanged=all(sha(Path(p))==v for p,v in pins.items());assert unchanged
    proof=dict(state='prepared-pinned-Metal-core-with-A619-profile',profile=a.profile,upstream_revision=manifest['revision'],source=str(source),input_pins=pins,source_pins=outputs,input_pins_unchanged=unchanged,device_commands=0,hardware_qualified=False)
    with (out/'result.json').open('x') as f:f.write(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items() if k not in ['input_pins','source_pins']},indent=2))

if __name__=='__main__':main()
