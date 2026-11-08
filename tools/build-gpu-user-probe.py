#!/usr/bin/env python3
"""Build/sign the iOS GPU user probe with the installed iPhoneOS SDK only."""
from pathlib import Path
import argparse,hashlib,json,os,struct,subprocess
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dev',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();r=Path(__file__).resolve().parent.parent;out=a.out.resolve();dev=a.dev.resolve()
    assert out.is_relative_to(r/'research/tmp');out.mkdir(parents=True,exist_ok=False)
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    source=r/'tools/gauguin-gpu-probe.c';header=dev/'gauguin_gpu_runtime.h'
    inputs=[Path(__file__).resolve(),source,header,sdk/'SDKSettings.json']
    pins={str(p):sha(p) for p in inputs};binary=out/'gauguin-gpu-probe'
    commands=[['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-I'+str(dev),str(source),'-framework','IOKit','-framework','IOSurface','-framework','CoreFoundation','-o',str(binary)],
        ['/usr/bin/codesign','--force','--sign','-',str(binary)],['/usr/bin/codesign','--verify','--strict',str(binary)]]
    results=[];record={'state':'starting','input_pins':pins,'sdk':str(sdk),'results':results,'hardware_qualified':False}
    def save():record['inputs_unchanged']=all(sha(Path(n))==pin for n,pin in pins.items());(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    try:
        for i,command in enumerate(commands):
            with (out/(str(i)+'.log')).open('x') as f:p=subprocess.run(command,cwd=r,stdout=f,stderr=subprocess.STDOUT)
            results.append({'argv':command,'exit':p.returncode});save();assert p.returncode==0,('command failed',i,p.returncode)
        data=binary.read_bytes();header=struct.unpack_from('<8I',data);assert header[0]==0xfeedfacf and header[1]==0x100000c and header[3]==2
        offset=32;versions=[];loads=[]
        for _ in range(header[4]):
            cmd,size=struct.unpack_from('<II',data,offset)
            if cmd==0x32:versions.append(struct.unpack_from('<4I',data,offset+8))
            if cmd in (0xc,0x80000018,0x8000001f):
                name=struct.unpack_from('<I',data,offset+8)[0];loads.append(data[offset+name:offset+size].split(b'\0')[0].decode())
            offset+=size
        assert len(versions)==1 and versions[0][0]==2 and versions[0][1]==0x100000,'expected iOS16 deployment target'
        record.update(state='passed-iOS-arm64-probe-build-and-adhoc-signature',binary=str(binary),bytes=len(data),sha256=sha(binary),platform_versions=versions,dylibs=loads)
        save();assert record['inputs_unchanged']
    except Exception as e:record.update(state='failed',error=repr(e));save();raise
    print(json.dumps({k:v for k,v in record.items() if k not in ('input_pins','results')},indent=2))
if __name__=='__main__':main()
