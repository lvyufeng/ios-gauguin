#!/usr/bin/env python3
"""Build a hash-bound root SETEXEC router; no device access or installation."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,struct,subprocess
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['retained-receipt','bootstrap-receipt','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=Path(__file__).resolve().parents[1];out=a.out.resolve()
    receipts=[a.retained_receipt.resolve(),a.bootstrap_receipt.resolve()];retained,bootstrap=[json.loads(p.read_text())for p in receipts]
    targets=[Path(retained['probe']),Path(bootstrap['binary'])]
    assert retained['sha256']=='26d09095687544b44af83232fd850c8d8c0d2149a7c17b87b7a0500b697bca3b'
    assert bootstrap['sha256']=='2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c'
    assert bootstrap['initial_delay_seconds']==0 and bootstrap['alarm_seconds']==30 and bootstrap['expected_jobs']==8
    for receipt,target in zip([retained,bootstrap],targets):
        assert receipt['inputs_unchanged']and sha(target)==receipt['sha256']and 0<target.stat().st_size<=1048576
        for n,h in receipt['input_pins'].items():assert sha(Path(n))==h,n
        header=struct.unpack('<8I',target.read_bytes()[:32]);assert header[0]==0xfeedfacf and header[1]==0x100000c and header[3]==2
        subprocess.run(['codesign','--verify','--strict',str(target)],check=True)
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    headers=r/'graphics/hakios-metal-ca/overlay/userland/src';desktop=r/'graphics/hakios-metal-ca/desktop-overlay/userland/src'
    inputs=[Path(__file__).resolve(),r/'tools/build-hakios-metal.py',r/'userland/metal/probe_router.c',r/'userland/metal/router_policy.h',r/'userland/metal/probe_boot.h',
            headers/'GauguinMetalProfile.h',desktop/'GauguinMetalDesktopPolicy.h',sdk/'SDKSettings.json',*receipts,*targets]
    pins={str(p):sha(p)for p in inputs};tag=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:24]
    out.mkdir(parents=True,exist_ok=False);header=out/'GauguinProbeRouterTargets.h'
    lines=['/* Generated target identities; future240 installation prerequisite. */',
           'struct gauguin_router_target {const char *path,*argument;uint64_t bytes;unsigned char sha256[32];};']
    specs=[]
    for kind,receipt,target,path,arg in [('retained',retained,targets[0],'/usr/libexec/gauguin-metal-frontend-probe','--metal230'),
                                         ('bootstrap',bootstrap,targets[1],'/usr/libexec/gauguin-metal-bootstrap','--bootstrap245')]:
        values=','.join('0x'+receipt['sha256'][i:i+2]for i in range(0,64,2))
        lines.append('static const struct gauguin_router_target gauguin_router_'+kind+'={'+json.dumps(path)+','+json.dumps(arg)+','+str(target.stat().st_size)+',{'+values+'}};')
        specs.append(dict(kind=kind,path=path,argument=arg,bytes=target.stat().st_size,sha256=receipt['sha256']))
    header.write_text('\n'.join(lines)+'\n');pins[str(header)]=sha(header);binary=out/'gauguin-gpu-probe-router'
    def run(args,name):
        with(out/name).open('x')as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    argv=['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0','-isysroot',str(sdk),'-std=gnu11','-O1','-Wall','-Wextra','-Werror',
          '-DGAUGUIN_ROUTER_BUILD="'+tag+'"','-I'+str(out),'-I'+str(headers),'-I'+str(desktop),str(r/'userland/metal/probe_router.c'),'-o',str(binary)]
    run(argv,'compile-link.log');run(['codesign','--force','--sign','-',str(binary)],'sign.log');run(['codesign','--verify','--strict',str(binary)],'verify.log')
    run(['nm','-m','-u',str(binary)],'imports.log');run(['otool','-L',str(binary)],'loads.log')
    spec=importlib.util.spec_from_file_location('b',r/'tools/build-hakios-metal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    platform=m.ios_version(binary);assert all(sha(Path(n))==h for n,h in pins.items())
    result=dict(state='native-iOS16-root-probe-router-not-device-qualified',binary=str(binary),probe=str(binary),bytes=binary.stat().st_size,sha256=sha(binary),build=tag,
                platform_version=platform,targets=specs,input_pins=pins,inputs_unchanged=True,requires_0240_installed=True,
                kernel_changes=False,installed=False,device_commands=0,hardware_qualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
