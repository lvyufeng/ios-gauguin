#!/usr/bin/env python3
"""Compile complete candidate probe and unchanged MAC dispatcher under OS seams.
No phone, filesystem policy activation, module loading or kernel installation.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,tempfile

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--mac-base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    repo=Path(__file__).resolve().parent.parent;fixture=repo/'tests/fixtures/sb_dyld_probe_host.c';out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pins={str(p.resolve()):sha(p) for p in [Path(__file__),fixture,a.candidate,a.mac_base]}
    s=a.candidate.read_text();begin=s.index('/* SWEET_DYLD_PROBE_BEGIN:');begin=s.index('\n',begin)+1;end=s.index('/* SWEET_DYLD_PROBE_END */',begin)
    (out/'production-probe.h').write_text(s[begin:end]);mac=a.mac_base.read_text();begin=mac.index('int\n__mac_syscall(');end=mac.index('\nint\nmac_mount_label_get(',begin);(out/'production-dispatch.h').write_text(mac[begin:end])
    assert 'static TUNABLE(uint32_t, sweet_dyld_probe, "sweet_dyld_probe", 0);' in s
    assert 'static TUNABLE(uint32_t, sweet_sb_rate_probe, "sbp", 0);' in s
    compiler=subprocess.check_output(['xcrun','--sdk','macosx','--find','clang'],text=True).strip();sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    binary=out/'dyld-policy-model';argv=[compiler,'-isysroot',sdk,'-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(out),str(fixture),'-o',str(binary)]
    cases=['old-policy-missing','probe-disabled','trusted','root-compositor','input-restricted','input-encrypted','input-both','wrong-policy','wrong-call','null-process','not-current-process','wrong-name','missing-credential','wrong-uid','credential-mismatch','missing-executable','lookup-failure','wrong-executable','wrong-vnode-type','missing-mount','nonroot-mount','getattr-failure','missing-owner-attribute','missing-mode-attribute','nonroot-file-owner','group-writable','world-writable','ACL-writable','ACL-query-failure','ACL-denied-EPERM','unknown-input-bit0','unknown-input-bit3','null-output','unaligned-output','copyin-failure','copyout-failure','policy-copyinstr-failure','MAC-dispatch-denial',
           'sb-trusted','sb-disabled','sb-wrong-uid','sb-lookup-failure','sb-wrong-vnode-type','sb-nonroot-mount','sb-world-writable','sb-ACL-writable','sb-backboard-disabled']
    results=[];report={'state':'running-actual-dyld-probe-boundary-model','input_pins':pins,'results':results,'device_commands':0,'physical_qualified':False}
    def save():report['inputs_unchanged']=all(sha(Path(p))==h for p,h in pins.items());(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command,name):
        p=subprocess.run(command,capture_output=True);(out/(name+'.stdout')).write_bytes(p.stdout);(out/(name+'.stderr')).write_bytes(p.stderr);results.append({'name':name,'exit':p.returncode});save();assert p.returncode==0,(name,p.returncode)
        assert b'AddressSanitizer' not in p.stderr and b'runtime error:' not in p.stderr
        return p.stdout.decode()
    try:
        run(argv,'compile-actual-probe-and-kernel-dispatch')
        for case in cases:assert run([str(binary),case],case).startswith('MODEL PASS case='+case+' ')
        report.update(state='passed-backboardd-and-SpringBoard-AMFI90-boundary-model',cases=len(cases),old_AMFI_missing_returns_ENOPOLICY=True,default_disabled_returns_ENOPOLICY=True,only_PATH_mask2_granted=True,references_balanced=True,sanitizers='ASAN+UBSAN',scope='Actual candidate C policy and unchanged kernel MAC dispatcher under typed OS seams. Exact protected executable and mobile UID for SpringBoard, original backboardd behavior preserved. No launchd-job attestation, runtime dyld/AMFI load, GPU access or physical cadence qualification.')
        save();assert report['inputs_unchanged'];print(json.dumps({k:v for k,v in report.items() if k not in ['input_pins','results']},indent=2))
    except Exception as error:report.update(state='failed-AMFI90-probe-model',error=repr(error));save();raise
if __name__=='__main__':
    if len(sys.argv)>1:
        main()
    else:
        source=os.environ.get('XNU_SOURCE')
        if not source:
            print('SKIP dyld probe model: set XNU_SOURCE to a prepared kernel tree, or pass explicit inputs')
        else:
            with tempfile.TemporaryDirectory(prefix='dyld-probe-host-') as td:
                out=Path(os.environ.get('DYLD_PROBE_TEST_OUT',str(Path(td)/'result')))
                raise SystemExit(subprocess.run([sys.executable,str(Path(__file__).resolve()),'--candidate',str(Path(source)/'bsd/kern/sweet_amfi.c'),'--mac-base',str(Path(source)/'security/mac_base.c'),'--out',str(out)]).returncode)
