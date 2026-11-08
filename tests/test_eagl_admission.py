#!/usr/bin/env python3
"""Execute complete production EAGL admission C under typed OS boundaries.
No phone access. A positive metadata report must still never enable hooks.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    repo=Path(__file__).resolve().parent.parent;source=repo/'userland/eagl/admission.c';fixture=repo/'tests/fixtures/eagl_admission.c'
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={str(p):sha(p) for p in (Path(__file__).resolve(),source,fixture)}
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    compiler=subprocess.check_output(['xcrun','--sdk','macosx','--find','clang'],text=True).strip()
    common=[compiler,'-isysroot',sdk,'-std=gnu11','-g','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer']
    boundary=['getprogname','getuid','geteuid','getenv','getpid','sysctlbyname','task_info','IOServiceMatching','IOServiceGetMatchingService','IOObjectRelease']
    cases=['normal','mode-render','mode-absent','wrong-program','wrong-uid','wrong-euid','class-absent','method-absent','encoding-mismatch','get8-failure','vm-failure','vm-short','service-absent','version-failure']
    steps=[];record={'state':'testing-actual-EAGL-admission-function','input_pins':pins,'steps':steps,'device_commands':0,'UI_qualified':False}
    def save():record['inputs_unchanged']=all(sha(Path(p))==pin for p,pin in pins.items());(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    def run(argv,name):
        q=subprocess.run(argv,capture_output=True);(out/(name+'.stdout')).write_bytes(q.stdout);(out/(name+'.stderr')).write_bytes(q.stderr)
        steps.append({'name':name,'argv':argv,'exit':q.returncode});save();assert q.returncode==0,(name,q.returncode)
        return q.stdout.decode(),q.stderr.decode()
    try:
        obj=out/'admission.o';binary=out/'admission-test'
        run(common+['-D'+n+'=test_'+n for n in boundary]+['-c',str(source),'-o',str(obj)],'compile-production')
        run(common+[str(fixture),str(obj),'-framework','Foundation','-framework','CoreFoundation','-framework','IOKit','-lobjc','-o',str(binary)],'link-typed-boundaries')
        for case in cases:
            stdout,stderr=run([str(binary),case],case)
            assert stdout==f'FIXTURE PASS case={case} all_original_IMPs_unchanged=1 admitted=0\n'
            assert 'AddressSanitizer' not in stderr and 'runtime error:' not in stderr
            if case in ['wrong-program','wrong-uid','wrong-euid']:assert not stderr;continue
            expected=0 if case=='class-absent' else 7 if case in ['method-absent','encoding-mismatch'] else 8
            present=0 if case=='service-absent' else 1
            assert f'finish methods={expected}/8 gpu_service_present={present} hooks=0 gpu_opens=0 rendering=disabled\n' in stderr
            assert stderr.count('GAUGUIN EAGL186 method=')==8
            if case=='get8-failure':assert 'memory get8_rc=-1 errno=1 active_mb=0' in stderr
            if case in ['vm-failure','vm-short']:assert 'vm_valid=0 footprint_bytes=0' in stderr
            if case=='mode-render':assert 'mode=render' in stderr
        record.update(state='passed-actual-admission-14-scenarios',cases=len(cases),all_original_IMPs_unchanged=True,admitted_in_every_case=False,sanitizers='ASAN+UBSAN',scope='Complete production diagnostic C with real host ObjC metadata and typed OS seams; no device dyld insertion, actual backboardd budget, GPU or UI acceptance')
        save();assert record['inputs_unchanged'];print(json.dumps({k:v for k,v in record.items() if k not in ('steps','input_pins')},indent=2))
    except Exception as exc:record.update(state='failed-admission-test',error=repr(exc));save();raise
if __name__=='__main__':main()
