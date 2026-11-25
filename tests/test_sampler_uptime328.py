#!/usr/bin/env python3
"""Execute actual sampler body with legacy cases and absolute-uptime deadline seams."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess

W=Path(__file__).resolve().parents[1]
B=W/'research/tmp/gesture-sample-328'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

EXTRA=r'''
static void expected_deadlines(unsigned first_late_ticks) {
 for(unsigned i=0;i<8;i++) {
  char begin[100];uint64_t t=(uint64_t)(220+i*6)*hz+(i==0?first_late_ticks:0);
  snprintf(begin,sizeof(begin),"SMP328 begin cycle=%u tick=%llu\n",i,(unsigned long long)t);
  CHECK(strstr(captured,begin)!=NULL);
 }
}
int main(void) {
 legacy_main();
 const struct option profile[]={{"gsp","328"},{NULL,NULL}};
 unsigned legacy_checks=checks;
 initial_ticks=45*hz;sample_ticks=95;run(profile);
 CHECK(iterations==8&&selected==16&&sb==8&&bb==8&&helpers==0);
 CHECK(sleep_count==8&&delays[0]==175*hz);
 for(unsigned i=1;i<8;i++)CHECK(delays[i]==6*hz-95);
 CHECK(strstr(captured,"SMP armed: SpringBoard,backboardd uptime=220 interval=6 count=8\n")!=NULL);
 CHECK(strstr(captured,"SMP328 armed: targets=SpringBoard,backboardd uptime=220 interval=6 count=8 max_targets=2 max_threads=64 frames=16 coherent_frames=0 lateness_us=1000000\n")!=NULL);
 expected_deadlines(0);
 sample_ticks=1;
 const unsigned starts[]={0,45,219,220};
 for(unsigned j=0;j<4;j++){unsigned start=starts[j];
  initial_ticks=(uint64_t)start*hz;run(profile);CHECK(iterations==8&&selected==16);expected_deadlines(0);
  CHECK(sleep_count==(start==220?7u:8u));
 }
 initial_ticks=220*hz-1;run(profile);CHECK(delays[0]==1);expected_deadlines(0);
 initial_ticks=221*hz;run(profile);CHECK(iterations==8&&sleep_count==7);expected_deadlines(hz);
 const unsigned late_starts[]={221,262,270};
 for(unsigned j=0;j<3;j++){unsigned start=late_starts[j];
  initial_ticks=(uint64_t)start*hz+1;run(profile);
  CHECK(!iterations&&!sleep_count&&strstr(captured,"SMP328 refused: reason=deadline cycle=0\n")!=NULL);
 }
 initial_ticks=45*hz;early_wakes=7;run(profile);
 CHECK(iterations==8&&sleep_count==15&&early_wakes==0);expected_deadlines(0);
 early_wakes=8;run(profile);CHECK(!iterations&&sleep_count==8&&early_wakes==0);
 CHECK(strstr(captured,"reason=deadline cycle=0")!=NULL);
 oversleep_once=hz;run(profile);CHECK(iterations==8);expected_deadlines(hz);
 oversleep_once=hz+1;run(profile);CHECK(!iterations&&sleep_count==1);
 CHECK(strstr(captured,"reason=deadline cycle=0")!=NULL);
 sample_ticks=8*hz;run(profile);CHECK(iterations==1&&sleep_count==1);
 CHECK(strstr(captured,"reason=deadline cycle=1")!=NULL);
 sample_ticks=1;
 const int rates[]={1,100,10000};
 for(unsigned j=0;j<3;j++){int rate=rates[j];
  hz=rate;initial_ticks=45*hz;run(profile);CHECK(iterations==8);expected_deadlines(0);
 }
 const int bad_rates[]={0,-1,10001};
 for(unsigned j=0;j<3;j++){int rate=bad_rates[j];
  hz=rate;initial_ticks=0;run(profile);CHECK(!iterations&&!sleep_count);
 }
 hz=100;initial_ticks=45*hz;
 include_duplicates=true;run(profile);CHECK(iterations==8&&selected==16&&helpers==0);
 CHECK(occurrences("targets=2 duplicates=2")==8);include_duplicates=false;
 const char *legacy[]={"sweetsample","sweetsampledelay","sweetsampleinterval","sweetsamplecount"};
 for(unsigned i=0;i<4;i++){
  const struct option v[]={{"gsp","328"},{legacy[i],i==0?"-":"1"},{NULL,NULL}};
  run(v);CHECK(!iterations&&!sleep_count&&strstr(captured,"SMP328 refused: reason=mixed-options")!=NULL);
 }
 // The retained316 profile still means220 seconds after its thread starts.
 const struct option old[]={{"gsp","316"},{NULL,NULL}};run(old);
 CHECK(iterations==8&&delays[0]==220*hz);
 CHECK(strstr(captured,"SMP316 begin cycle=0 tick=26500\n")!=NULL);
 fprintf(stdout,"{\"state\":\"GESTURE328-actual-uptime-sampler-and-legacy-checks-passed\",\"legacy_checks\":%u,\"new_checks\":%u}\n",legacy_checks,checks-legacy_checks);
 return 0;
}
'''

def main():
    out=B/'sampler-host-v2'
    out.mkdir(exist_ok=False)
    legacy=W/'tests/test_receiver_sample_profile.py'
    spec=importlib.util.spec_from_file_location('legacy_sampler_fixture',legacy)
    fixture=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    source=B/'kernel-source/bsd/dev/sweet_sample.c'
    raw=source.read_text()
    actual='static char sweet_sample_names[128];'+raw.split('static char sweet_sample_names[128];',1)[1].split('\nvoid\nsweet_sample_start(void)',1)[0]
    pre=fixture.PRELUDE
    pre=pre.replace('static uint64_t ticks;','static uint64_t ticks,initial_ticks;\nstatic unsigned sample_ticks=1,early_wakes,oversleep_once;')
    old='delays[sleep_count++]=delay;ticks+=(uint64_t)delay;return 0;'
    new='delays[sleep_count++]=delay;if(early_wakes){--early_wakes;++ticks;return 1;}ticks+=(uint64_t)delay+oversleep_once;oversleep_once=0;return 0;'
    assert pre.count(old)==1
    pre=pre.replace(old,new)
    pre=pre.replace('static uint64_t mach_absolute_time(void){return ticks;}','static uint64_t mach_absolute_time(void){return ticks;}\nstatic void absolutetime_to_nanoseconds(uint64_t t,uint64_t *ns){CHECK(hz>0);*ns=t*1000000000ULL/(unsigned)hz;}')
    pre=pre.replace(' ++ticks;\n}', ' ticks+=sample_ticks;\n}')
    cases=fixture.CASES.replace('int main(void) {','static int legacy_main(void) {').replace('ticks=used=0;', 'ticks=initial_ticks;used=0;')
    unit=out/'sampler.c'
    unit.write_text(pre+actual+cases+EXTRA)
    args=['clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(unit),'-o',str(out/'sampler')]
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    with (out/'compile.log').open('x') as stream:
        result=subprocess.run(args,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    assert result.returncode==0,'compile'
    run=subprocess.run([str(out/'sampler')],env=env,capture_output=True,text=True,timeout=60)
    (out/'run.log').write_text(run.stdout+run.stderr)
    assert run.returncode==0 and not run.stderr,'run'
    result=json.loads(run.stdout.splitlines()[-1])
    result.update(actual_source=str(source),source_sha256=sha(source),legacy_profile316_and_default_unchanged=True,
        absolute_deadlines_checked=[220,226,232,238,244,250,256,262],late_and_early_wake_bounds_checked=True,
        sampling_duration_not_hard_bounded=True,kernel_thread_capture_tested=False,sanitizers='ASan+UBSan',
        input_pins={str(path):sha(path) for path in (Path(__file__),legacy,source)},device_commands=0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':
    main()
