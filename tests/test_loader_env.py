#!/usr/bin/env python3
"""Exercise complete exec and file diagnostics under typed boundaries."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,tempfile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    fixture=Path(__file__).resolve().parent/'fixtures/loader_env_host.c';out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sources=[a.source/'bsd/kern/kern_exec.c',a.source/'bsd/kern/sweet_amfi.c']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pins={str(p.resolve()):sha(p) for p in [Path(__file__),fixture,*sources]}
    for path,label,name in [(sources[0],'EXEC','production-exec.h'),(sources[1],'FILE','production-file.h')]:
        s=path.read_text();first=s.index('/* SWEET_DYLD_'+label+'_PROBE_BEGIN:');first=s.index('\n',first)+1;last=s.index('/* SWEET_DYLD_'+label+'_PROBE_END */',first);(out/name).write_text(s[first:last])
    assert 'static TUNABLE(uint32_t, sweet_exec_loader_probe, "sweet_dyld_probe", 0);' in sources[0].read_text()
    assert '.mpo_vnode_check_open = sweet_dyld_probe_open,' in sources[1].read_text() and '.mpo_file_check_mmap = sweet_dyld_probe_mmap,' in sources[1].read_text()
    cases=['exec-good','exec-no-env','exec-missing-insert','exec-wrong-insert','exec-false-key','exec-duplicate-insert','exec-wrong-mode','exec-empty-env','exec-proxy','exec-proxy-other-job','exec-disabled','exec-otherimage','exec-relativeimage','exec-nullproc','exec-nullbase','exec-reversed','exec-envaftertail','exec-tailpastcap','exec-negative-argc','exec-negative-envc','exec-argv-overcount','exec-env-overcount','exec-path-nonul','exec-argv-nonul','exec-env-nonul','exec-address-overflow','exec-null-image','file-open','file-xpcproxy','file-mmap-read','file-mmap-exec','file-mmap-write','file-mmap-null-maxprot','file-disabled','file-wrongproc','file-nullproc','file-nullvp','file-directory','file-nullleaf','file-wrongleaf','file-pathalias','file-patherror','file-emptylen','file-oversizelen','file-unterminated','file-nullfg','file-nullops','file-pipe','file-null-data']
    compiler=subprocess.check_output(['xcrun','--sdk','macosx','--find','clang'],text=True).strip();sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip();binary=out/'loader-env-model'
    commands=[('compile',[compiler,'-isysroot',sdk,'-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(out),str(fixture),'-o',str(binary)])]+[(name,[str(binary),name]) for name in cases]
    result={'state':'running188-complete-loader-diagnostic-host-model','input_pins':pins,'results':[],'device_commands':0,'hardware_qualified':False}
    def save():result['inputs_unchanged']=all(sha(Path(p))==h for p,h in pins.items());(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        for name,argv in commands:
            p=subprocess.run(argv,capture_output=True);(out/(name+'.stdout')).write_bytes(p.stdout);(out/(name+'.stderr')).write_bytes(p.stderr);result['results'].append({'case':name,'exit':p.returncode});save();assert p.returncode==0,(name,p.returncode,p.stderr.decode(errors='replace')[:1600])
            assert b'AddressSanitizer' not in p.stderr and b'runtime error:' not in p.stderr
            if name!='compile':assert p.stdout.startswith(('MODEL PASS case='+name+' ').encode())
        result.update(state='passed188-complete-readonly-exec-and-file-diagnostic-model',cases=len(cases),sanitizers='ASAN+UBSAN',environment_and_argv_unchanged=True,file_checks_always_allow_without_protection_mutation=True,name_references_balanced=True,scope='Complete actual production helpers and callbacks with typed OS seams; not runtime env/library loading proof or GPU UI qualification.');save();assert result['inputs_unchanged'];print(json.dumps({k:v for k,v in result.items() if k not in ['input_pins','results']},indent=2))
    except Exception as error:result.update(state='failed188-loader-diagnostic-model',error=repr(error));save();raise

if __name__=='__main__':
    if len(sys.argv)>1:main()
    elif not os.environ.get('XNU_SOURCE'):print('SKIP loader env model: set XNU_SOURCE or pass explicit prepared source')
    else:
        with tempfile.TemporaryDirectory(prefix='loader-env-host-') as td:
            out=Path(os.environ.get('LOADER_ENV_TEST_OUT',str(Path(td)/'result')))
            raise SystemExit(subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',os.environ['XNU_SOURCE'],'--out',str(out)]).returncode)
