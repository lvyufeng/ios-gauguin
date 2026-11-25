#!/usr/bin/env python3
"""Run the actual kernel sampler selection/loop body with bounded host fakes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PRELUDE=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define PZERO 0
#define PROC_ALLPROCLIST 1
#define PROC_RETURNED 0
#define TASK_NULL NULL
typedef void *task_t;
typedef int wait_result_t;
struct fake_proc { int pid; const char *name; task_t task; };
typedef struct fake_proc *proc_t;
static struct fake_proc processes[]={
 {26,"SpringBoard",(void *)1},{57,"backboardd",(void *)2},
 {58,"SpringBoardHelper",(void *)3},{59,"backboardd_helper",(void *)4},
 {60,"empty",NULL},{126,"SpringBoard",(void *)5},{157,"backboardd",(void *)6}
};
struct option { const char *key,*value; };
static const struct option *options;
static unsigned checks,iterations,selected,sb,bb,helpers,sleep_count;
static bool include_duplicates;
static int delays[64];
static uint64_t ticks;
static char captured[65536];
static size_t used;
int hz=100;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"check failed line %d: %s\n",__LINE__,#x); abort(); } } while(0)
static int capture_printf(const char *format,...) {
 va_list args;va_start(args,format);
 int n=vsnprintf(captured+used,sizeof(captured)-used,format,args);va_end(args);
 CHECK(n>=0 && (size_t)n<sizeof(captured)-used);used+=(size_t)n;return n;
}
#define printf capture_printf
static bool PE_parse_boot_argn(const char *key,void *out,int size) {
 for (const struct option *p=options;p->key;++p) {
  if (strcmp(key,p->key))continue;
  if(size==(int)sizeof(int))*(int *)out=(int)strtol(p->value,NULL,10);
  else strlcpy(out,p->value,(size_t)size);
  return true;
 }
 return false;
}
static int proc_pid(proc_t p){return p->pid;}
static void proc_name(int pid,char *out,int size) {
 for(unsigned i=0;i<sizeof(processes)/sizeof(processes[0]);++i)
  if(processes[i].pid==pid){strlcpy(out,processes[i].name,(size_t)size);return;}
 abort();
}
static task_t proc_task(proc_t p){return p->task;}
void sweet_sample_task(const char *name,int pid,task_t task) {
 CHECK(task!=NULL);++selected;
 if(pid==26){CHECK(!strcmp(name,"SpringBoard"));++sb;}
 else if(pid==57){CHECK(!strcmp(name,"backboardd"));++bb;}
 else ++helpers;
}
static int tsleep(void *channel,int priority,const char *message,int delay) {
 CHECK(channel!=NULL && priority==PZERO && !strcmp(message,"sweetsmp"));
 CHECK(sleep_count<64 && delay>0);delays[sleep_count++]=delay;ticks+=(uint64_t)delay;return 0;
}
static uint64_t mach_absolute_time(void){return ticks;}
static void proc_iterate(int flags,int(*callback)(proc_t,void *),void *arg,void *filter,void *filterarg) {
 CHECK(flags==PROC_ALLPROCLIST && filter==NULL && filterarg==NULL);++iterations;
 for(unsigned i=0;i<sizeof(processes)/sizeof(processes[0]);++i) {
  if(processes[i].pid>=100&&!include_duplicates)continue;
  CHECK(callback(&processes[i],arg)==PROC_RETURNED);
 }
 ++ticks;
}
'''

CASES=r'''
static unsigned occurrences(const char *needle) {
 unsigned n=0;const char *p=captured;while((p=strstr(p,needle))!=NULL){++n;p+=strlen(needle);}return n;
}
static void run(const struct option *configuration) {
 options=configuration;iterations=selected=sb=bb=helpers=sleep_count=0;
 ticks=used=0;captured[0]=sweet_sample_names[0]=0;
 sweet_sample_thread(NULL,0);
}
int main(void) {
 const struct option profile[]={{"gsp","316"},{NULL,NULL}};
 run(profile);CHECK(iterations==8 && selected==16 && sb==8 && bb==8 && helpers==0);
 CHECK(sleep_count==8 && delays[0]==220*hz);
 for(unsigned i=1;i<sleep_count;++i)CHECK(delays[i]==6*hz);
 CHECK(occurrences("SMP316 begin cycle=")==8 && occurrences("SMP316 end cycle=")==8);
 CHECK(strstr(captured,"targets=SpringBoard,backboardd delay=220 interval=6 count=8 max_targets=2 max_threads=64 frames=16 coherent_frames=0")!=NULL);
 for(unsigned i=0;i<8;++i) {
  char begin[100],end[100];uint64_t t=(uint64_t)(220+i*6)*hz+i;
  snprintf(begin,sizeof(begin),"SMP316 begin cycle=%u tick=%llu\n",i,(unsigned long long)t);
  snprintf(end,sizeof(end),"SMP316 end cycle=%u tick=%llu targets=2 duplicates=0\n",i,(unsigned long long)(t+1));
  const char *a=strstr(captured,begin),*b=strstr(captured,end);CHECK(a!=NULL&&b!=NULL&&a<b);
 }
 include_duplicates=true;run(profile);
 CHECK(iterations==8&&selected==16&&sb==8&&bb==8&&!helpers);
 CHECK(occurrences("targets=2 duplicates=2")==8);
 include_duplicates=false;
 const char *bad[]={"0","315","317","-1"};
 for(unsigned i=0;i<4;++i) {
  const struct option v[]={{"gsp",bad[i]},{NULL,NULL}};run(v);
  CHECK(!iterations&&!sleep_count&&strstr(captured,"reason=profile")!=NULL);
 }
 const char *legacy[]={"sweetsample","sweetsampledelay","sweetsampleinterval","sweetsamplecount"};
 for(unsigned i=0;i<4;++i) {
  const struct option v[]={{"gsp","316"},{legacy[i],i==0?"-":"1"},{NULL,NULL}};run(v);
  CHECK(!iterations&&!sleep_count&&strstr(captured,"reason=mixed-options")!=NULL);
 }
 const struct option off[]={{"sweetsample","-"},{NULL,NULL}};run(off);
 CHECK(!iterations&&!sleep_count&&!used);
 const struct option defaults[]={{NULL,NULL}};run(defaults);
 CHECK(iterations==40&&selected==80&&sb==40&&bb==40&&helpers==0);
 CHECK(sleep_count==40&&delays[0]==90*hz&&occurrences("SMP316")==0);
 for(unsigned i=1;i<sleep_count;++i)CHECK(delays[i]==120*hz);
 include_duplicates=true;run(defaults);
 CHECK(iterations==40&&selected==160&&sb==40&&bb==40&&helpers==80);
 include_duplicates=false;
 const struct option custom[]={{"sweetsample","backboardd"},{"sweetsampledelay","3"},{"sweetsampleinterval","2"},{"sweetsamplecount","2"},{NULL,NULL}};
 run(custom);CHECK(iterations==2&&selected==2&&bb==2&&!sb&&!helpers);
 CHECK(sleep_count==2&&delays[0]==3*hz&&delays[1]==2*hz&&occurrences("SMP316")==0);
 const struct option bounds[]={{"sweetsampledelay","3601"},{"sweetsampleinterval","0"},{"sweetsamplecount","41"},{NULL,NULL}};
 run(bounds);CHECK(iterations==40&&sleep_count==40&&delays[0]==90*hz&&delays[1]==120*hz);
 const struct option null_task[]={{"sweetsample","empty"},{"sweetsamplecount","1"},{NULL,NULL}};
 run(null_task);CHECK(iterations==1&&!selected);
 fprintf(stdout,"{\"state\":\"actual-sampler-body-host-checks-passed\",\"checks\":%u}\n",checks);
 return 0;
}
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out-dir',type=Path,required=True)
    args=ap.parse_args();args.out_dir.mkdir(parents=True,exist_ok=False)
    source=args.source.read_text()
    assert source.count('static char sweet_sample_names[128];')==1
    assert source.count('\nvoid\nsweet_sample_start(void)')==1
    actual=source.split('static char sweet_sample_names[128];',1)[1].split('\nvoid\nsweet_sample_start(void)',1)[0]
    actual='static char sweet_sample_names[128];'+actual
    harness=args.out_dir/'sampler.c';harness.write_text(PRELUDE+actual+CASES)
    binary=args.out_dir/'sampler'
    command=['xcrun','clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(harness),'-o',str(binary)]
    build=subprocess.run(command,capture_output=True,text=True)
    (args.out_dir/'compile.log').write_text(build.stdout+build.stderr)
    build.check_returncode()
    run=subprocess.run([str(binary.resolve())],capture_output=True,text=True)
    (args.out_dir/'run.log').write_text(run.stdout+run.stderr);run.check_returncode()
    result=json.loads(run.stdout)
    result.update(source=str(args.source.resolve()),source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  input_pins={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              str(args.source.resolve()):hashlib.sha256(source.encode()).hexdigest()},
                  compiler_arguments=command,device_commands=0,kernel_thread_capture_tested=False,
                  scope='Actual process-selection and sampler-loop body; host fakes replace kernel process/thread/clock services.')
    with (args.out_dir/'result.json').open('x')as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ('compiler_arguments','input_pins')},indent=2))

if __name__=='__main__':main()
