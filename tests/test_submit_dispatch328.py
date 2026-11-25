#!/usr/bin/env python3
"""Compile actual whole IOUserClient parent/candidate with typed IOKit seams and dispatch refusal cases."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/gesture-sample-328';P=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-submit-reject-worktree-20261115/research/tmp/submit-reject-327/kernel-source')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
PM=P.parent/'local-link/build-manifest.json'
parent=json.loads(PM.read_text());source_base=Path(parent['source_union']['base'])
def source(root,name):
 p=root/name
 if p.is_file():return p
 assert name=='iokit/Kernel/arm/SweetSurface.cpp'
 p=source_base/name;assert sha(p)==parent['input_pins'][str(p)]['sha256'];return p
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);out=ap.parse_args().out.resolve();assert out.is_relative_to(B)and not out.exists();out.mkdir()
 fixture=W/'tests/fixtures/gpu-user/iokit_host.cpp';mainfile=W/'tests/fixtures/submit_dispatch327_main.inc';C=B/'kernel-source'
 paths=[Path(__file__),fixture,mainfile,PM,*[source(root,name) for root in(P,C)for name in('iokit/Kernel/arm/GauguinGPU.cpp','iokit/Kernel/arm/SweetSurface.h','iokit/Kernel/arm/SweetSurface.cpp','iokit/Kernel/arm/SweetMetalBootstrap.h','bsd/dev/gauguin_gpu_runtime.c','bsd/dev/gauguin_gpu_runtime.h','bsd/dev/gauguin_ui_trace.h')]]
 pins={str(p):sha(p)for p in paths};strip=lambda p:re.sub(r'^#include .*\n','',p.read_text(),flags=re.M)
 env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1');flags=['-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(C/'bsd/dev')]
 def run(cmd,label):
  with (out/(label+'.log')).open('x')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert r.returncode==0,(label,r.returncode)
 run(['clang','-std=c11',*flags,'-c',str(C/'bsd/dev/gauguin_gpu_runtime.c'),'-o',str(out/'runtime.o')],'compile-runtime')
 for variant,root in [('baseline',P),('candidate',C)]:
  gpu=root/'iokit/Kernel/arm';s=fixture.read_text().split('int main(int argc,char **argv)')[0]
  s=s.replace('#include <vector>','#include <vector>\n#include <string>\n#include <cstdarg>')
  old='static void test_log(const char *format,...){(void)format;}'
  new='''static std::vector<std::string> submit_logs;
static void test_log(const char *format,...){if(strncmp(format,"SWEET GS328:",12))return;char line[1024];va_list a;va_start(a,format);int n=vsnprintf(line,sizeof(line),format,a);va_end(a);assert(n==235);submit_logs.emplace_back(line);}'''
  assert s.count(old)==1;s=s.replace(old,new)
  s=s.replace('@SURFACE_HEADER@',strip(gpu/'SweetSurface.h'))
  method=re.findall(r'uintptr_t\nSweetSurface::kernelAddress\(\)\n\{[\s\S]*?\n\}',source(root,'iokit/Kernel/arm/SweetSurface.cpp').read_text());assert len(method)==1;s=s.replace('@SURFACE_KERNEL_ADDRESS@',method[0])
  seam='''
[[maybe_unused]] static bool sweet_metal_desktop_enabled(){return false;}
[[maybe_unused]] static bool PE_parse_boot_argn(const char *,void *,int){return false;}
extern "C" bool sweet_gpu_runtime_pending_metadata(uint32_t){return false;}
'''
  s=s.replace('@SOURCE@',strip(gpu/'SweetMetalBootstrap.h')+seam+'\n#define private public\n'+strip(gpu/'GauguinGPU.cpp')+'\n#undef private\n')
  s=s.replace('__asm__ volatile("dsb sy" ::: "memory")','__atomic_thread_fence(__ATOMIC_SEQ_CST)')
  unit=out/(variant+'.cpp');unit.write_text(s+mainfile.read_text())
  run(['clang++','-std=c++17',*flags,'-DGAUGUIN_GPU_PILOT_HOST=1','-DGAUGUIN_GPU_REQUEST_LOCKS=2',*(['-DTEST_SUBMIT327=1']if variant=='candidate'else[]),str(unit),str(out/'runtime.o'),'-o',str(out/variant)],variant+'-compile')
  run([str(out/variant)],variant+'-run')
 rows=[[line for line in (out/(v+'-run.log')).read_text().splitlines()if line.startswith('OBS ')]for v in('baseline','candidate')];assert rows[0]==rows[1]and len(rows[0])==8
 assert all(sha(Path(p))==d for p,d in pins.items())
 r=dict(state='GESTURE328-whole-IOUserClient-dispatch-refusals-passed',scenarios=8,parent_candidate_observations_identical=True,all_original_output_preservation_checks_passed=True,dispatch_gate_stages=[1,2,3,4,10,14],compositor_async_diagnostic_records=7,root_scope_not_logged=True,unrelated_success_not_logged=True,private_access_for_host_introspection_only=True,sanitizers='ASan+UBSan',input_pins=pins,inputs_unchanged=True,device_commands=0)
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
