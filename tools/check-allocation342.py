#!/usr/bin/env python3
"""Exercise actual342 Gpu::newBo success/GemNew/GemInfo/map failure cleanup."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/io-path-342'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=B/'allocation-host-v3');a=ap.parse_args()
    host=json.loads((B/'core-host-v2/result.json').read_text());out=a.out.resolve();assert out.is_relative_to(B) and not out.exists();out.mkdir()
    fixture=W/'tests/fixtures/allocation342.cpp';old_fixture=W/'tests/fixtures/core_program342.cpp'
    compile_args=list(next(r['argv'] for r in host['steps'] if r['name']=='compile-program342'))
    methods=old_fixture.read_text();assert methods.count('int main(int argc,char** argv)')==1
    (out/'program342-methods.inc').write_text(methods.replace('int main(int argc,char** argv)','int inheritedProgram342(int argc,char** argv)'))
    compile_args.insert(1,'-I'+str(out))
    old_object=str(B/'core-host-v2/program342.o');obj=str(out/'allocation.o');binary=str(out/'allocation')
    compile_args=[str(fixture) if v==str(old_fixture) else obj if v==old_object else v for v in compile_args]
    link_args=list(next(r['argv'] for r in host['steps'] if r['name']=='link-program342'))
    link_args=[obj if v==old_object else binary if v==str(B/'core-host-v2/program342') else v for v in link_args]
    paths=[Path(__file__),fixture,old_fixture,B/'core-host-v2/result.json']+[Path(v) for v in link_args if v.endswith('.o') and v!=obj]
    pins={str(p):sha(p) for p in paths};steps=[]
    for label,args in [('compile',compile_args),('link',link_args)]+[(str(n),[binary,str(n)]) for n in range(4)]:
        p=subprocess.run(args,capture_output=True,timeout=90,env=dict(os.environ,ASAN_OPTIONS='abort_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1'))
        (out/(label+'.log')).write_bytes(p.stdout+p.stderr);steps.append(dict(label=label,exit=p.returncode));assert p.returncode==0,(label,p.stderr[-2000:])
    assert all(sha(p)==h for p,h in pins.items())
    v=dict(state='0342-actual-Gpu-newBo-stages-and-failure-lifetimes-passed',scenarios=4,sanitizers='ASan+UBSan',inputs_unchanged=True,input_pins=pins,steps=steps,device_commands=0)
    (out/'result.json').write_text(json.dumps(v,indent=2)+'\n');print(v['state'])
if __name__=='__main__':main()
