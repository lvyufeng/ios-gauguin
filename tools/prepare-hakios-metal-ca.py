#!/usr/bin/env python3
"""Copy a Git-blob-verified complete CA frontend into a fresh local tree.

No download, build, installation, device IO or Apple shader extraction.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--profile',choices=['baseline','gauguin-diagnostic'],default='baseline')
    a=ap.parse_args();repo=Path(__file__).resolve().parents[1]
    manifest=repo/'graphics/hakios-metal-ca/upstream.json';spec=json.loads(manifest.read_text())
    assert spec['revision']=='63fc2b4633bac3af8e57dadab9f5a8d4cb940438'
    assert len(spec['files'])==1
    cache=a.cache.resolve();out=a.out.resolve();assert not out.exists(),'fresh output required'
    pins={str(manifest):sha(manifest),str(Path(__file__).resolve()):sha(Path(__file__).resolve())};rows=[]
    for row in spec['files']:
        rel=Path(row['path']);assert not rel.is_absolute()and '..'not in rel.parts
        p=cache/rel;data=p.read_bytes();assert len(data)==row['size']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['sha']
        assert b'SPDX-License-Identifier: MIT'in data and b'@implementation HakiosMetalDevice'in data
        pins[str(p)]=sha(p);rows.append((p,rel))
    profile=repo/'graphics/hakios-metal-ca'
    patches=sorted((profile/'patches').glob('*.patch')) if a.profile=='gauguin-diagnostic' else []
    overlays=sorted(p for p in (profile/'overlay').rglob('*') if p.is_file()) if patches else []
    if a.profile=='gauguin-diagnostic':assert len(patches)==1 and len(overlays)==2
    for p in patches+overlays:pins[str(p)]=sha(p)
    out.mkdir(parents=True,exist_ok=False);source=out/'source';source.mkdir()
    for p,rel in rows:
        target=source/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for i,p in enumerate(patches):
        with (out/f'patch-{i}.log').open('x') as log:
            subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-d',str(source),'-i',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
    for p in overlays:
        target=source/p.relative_to(profile/'overlay');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    outputs={str(p.relative_to(source)):sha(p)for p in source.rglob('*')if p.is_file()}
    assert all(sha(Path(p))==pin for p,pin in pins.items())
    state='prepared-gauguin-offscreen-Metal-frontend' if patches else 'prepared-complete-pinned-HakiOS-CA-frontend-baseline'
    r=dict(state=state,profile=a.profile,source=str(source),upstream_revision=spec['revision'],source_pins=outputs,input_pins=pins,inputs_unchanged=True,device_commands=0,gauguin_adapted=bool(patches),runtime_qualified=False)
    with (out/'result.json').open('x')as f:f.write(json.dumps(r,indent=2)+'\n')
    print(r['state'])

if __name__=='__main__':main()
