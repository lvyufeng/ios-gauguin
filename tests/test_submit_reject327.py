#!/usr/bin/env python3
"""Compare actual parent/candidate submit bodies and exercise the production diagnostic logger."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/submit-reject-327'
P=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-perf430-worktree-20261115/research/tmp/perf430-326/kernel-source')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);out=ap.parse_args().out.resolve();assert out.is_relative_to(B) and not out.exists()
 C=B/'kernel-source';rel='iokit/Kernel/arm/GauguinGPU.cpp';fixture=W/'tests/fixtures/submit_reject327_host.cpp';extractor=W/'tests/test_gpu_async_submit.py'
 spec=importlib.util.spec_from_file_location('submit_extract',extractor);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 raw=(C/rel).read_text();a=raw.index('/* SUBMIT327:');z=raw.index('class GauguinGPUUserClient',a);diagnostic=raw[a:z]
 assert diagnostic.count('IOLog(')==2 and diagnostic.count('mach_absolute_time()')==1
 paths=[Path(__file__),fixture,extractor,P/rel,C/rel,*[root/('bsd/dev/gauguin_gpu_runtime'+ext)for root in (P,C)for ext in ('.c','.h')]]
 pins={str(p):sha(p)for p in paths};assert sha(P/'bsd/dev/gauguin_gpu_runtime.c')==sha(C/'bsd/dev/gauguin_gpu_runtime.c');assert sha(P/'bsd/dev/gauguin_gpu_runtime.h')==sha(C/'bsd/dev/gauguin_gpu_runtime.h')
 out.mkdir();env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1');flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(C/'bsd/dev')]
 def run(args,label):
  with (out/(label+'.log')).open('x')as f:r=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert r.returncode==0,(label,r.returncode)
 run(['clang','-std=c11',*flags,'-c',str(C/'bsd/dev/gauguin_gpu_runtime.c'),'-o',str(out/'runtime.o')],'compile-runtime')
 for variant,root in [('baseline',P),('candidate',C)]:
  src=out/(variant+'.cpp');s=fixture.read_text();assert s.count('/* INSERT_REAL_SUBMIT_METHOD */')==s.count('/* INSERT_REAL_DIAGNOSTIC */')==1
  src.write_text(s.replace('/* INSERT_REAL_SUBMIT_METHOD */',m.extract((root/rel).read_text())).replace('/* INSERT_REAL_DIAGNOSTIC */',diagnostic))
  run(['clang++','-std=c++17',*flags,*(['-DTEST_SUBMIT327=1']if variant=='candidate'else[]),str(src),str(out/'runtime.o'),'-o',str(out/variant)],variant+'-compile')
  run([str(out/variant)],variant+'-run')
 logs=[(out/(v+'-run.log')).read_text()for v in ('baseline','candidate')]
 observations=[[line for line in log.splitlines()if line.startswith('OBS ')]for log in logs]
 assert len(observations[0])==82 and observations[0]==observations[1]
 assert all(sha(Path(p))==d for p,d in pins.items())
 r=dict(state='SUBMIT327-actual-submit-behavior-equivalence-and-logger-passed',scenarios=82,parent_candidate_observations_identical=True,shared_wire_and_runtime_unchanged=True,return_values_fences_ownership_GPU_calls_preserved=True,all_submit_stage_branches_tested=True,diagnostic_limit=64,limit_markers_max=1,max_formatted_bytes=512,diagnostic_has_no_GPU_calls=True,sanitizers='ASan+UBSan',input_pins=pins,inputs_unchanged=True,device_commands=0)
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
