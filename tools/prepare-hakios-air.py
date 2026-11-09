#!/usr/bin/env python3
"""Prepare a fresh, pinned Mesa tree with HakiOS's AIR frontend.

Only local source preparation. The existing GLES source/build remains intact.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,tarfile

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['archive','cache','out']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    manifest=root/'graphics/hakios-metal/air-upstream.json'
    m=json.loads(manifest.read_text());cache=a.cache.resolve();out=a.out.resolve()
    archive=a.archive.resolve();assert sha(archive)==m['mesa_archive_sha256']
    pins={str(archive):sha(archive),str(manifest):sha(manifest),str(Path(__file__).resolve()):sha(Path(__file__).resolve())}
    for f in m['files']:
        rel=Path(f['path']);assert not rel.is_absolute() and '..' not in rel.parts
        p=cache/rel;data=p.read_bytes()
        assert len(data)==f['size']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==f['sha']
        pins[str(p)]=sha(p)
    out.mkdir(parents=True,exist_ok=False)
    with tarfile.open(archive) as t:t.extractall(out,filter='data')
    source=out/('mesa-'+m['mesa_version'])
    assert (source/'VERSION').read_text().strip()==m['mesa_version']
    patches=sorted(cache/f['path'] for f in m['files'] if f['path'].endswith('.patch'))
    assert len(patches)==8
    for i,p in enumerate(patches):
        with (out/(f'patch-{i}.log')).open('x') as f:
            subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-d',str(source),'-i',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
    shutil.copytree(cache/'tools/mesa/air',source/'src/compiler/air')
    shutil.copytree(cache/'tools/mesa/hakios-drm',source/'src/hakios-drm')
    source_pins={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    assert all(sha(Path(p))==v for p,v in pins.items())
    result=dict(state='prepared-pinned-Mesa25-HakiOS-AIR-source',source=str(source),upstream_revision=m['revision'],input_pins=pins,source_pins=source_pins,device_commands=0,hardware_qualified=False)
    with (out/'result.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['input_pins','source_pins']},indent=2))

if __name__=='__main__':main()
