#!/usr/bin/env python3
"""Run production bootstrap callbacks/open prefix with virtual time and ownership."""
from pathlib import Path
import argparse,os,subprocess

HOST=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cerrno>
#include <ctime>
#include <memory>
#include <string>
#include "@HEADER@"
struct Model {uint64_t now=0,ready=60000000000,cost=0;unsigned clocks=0,failClock=0,opens=0,sleeps=0,alive=0,closed=0,alarms=0;bool failSleep=false,freeze=false;};
static Model model;
struct Transport {Transport(){model.alive++;}virtual ~Transport(){model.alive--;model.closed++;}};
static std::unique_ptr<Transport> openKernelGpu(std::string* why){model.opens++;model.now+=model.cost;if(model.now>=model.ready)return std::make_unique<Transport>();*why="service not yet published";return nullptr;}
static int clockModel(clockid_t,timespec* t){if(++model.clocks==model.failClock)return -1;t->tv_sec=time_t(model.now/1000000000);t->tv_nsec=long(model.now%1000000000);return 0;}
static int sleepModel(const timespec* t,timespec*){model.sleeps++;if(model.failSleep){errno=EINVAL;return -1;}if(!model.freeze)model.now+=uint64_t(t->tv_sec)*1000000000+uint64_t(t->tv_nsec);return 0;}
static unsigned alarmModel(unsigned seconds){assert(seconds==30&&model.alive==1&&model.now>=model.ready);model.alarms++;return 0;}
#define clock_gettime clockModel
#define nanosleep sleepModel
#define alarm alarmModel
@HELPER@
static void require(bool ok,const char*,const std::string&){assert(ok);}
static void actualOpenPrefix(){
@PREFIX@
assert(model.alarms==1&&model.alive==1);
}
int main(){
 std::string why;
 model=Model{};auto a=bootstrapOpen(&why);assert(a&&model.now==60000000000&&model.opens==601&&model.alive==1&&!model.alarms);a.reset();assert(!model.alive&&model.closed==1);
 model=Model{};actualOpenPrefix();assert(model.closed==1&&!model.alive&&model.alarms==1);
 model=Model{};model.ready=UINT64_MAX;assert(!bootstrapOpen(&why)&&model.now==180000000000&&model.opens<=1801&&!model.alive&&!model.alarms);
 model=Model{};model.freeze=true;assert(!bootstrapOpen(&why)&&model.opens==1801&&model.sleeps==1800&&!model.alive);
 model=Model{};model.failClock=1;assert(!bootstrapOpen(&why)&&!model.opens);
 model=Model{};model.ready=0;model.failClock=3;assert(!bootstrapOpen(&why)&&model.closed==1&&!model.alive);
 model=Model{};model.ready=0;model.cost=180000000001;assert(!bootstrapOpen(&why)&&model.closed==1&&!model.alive);
 model=Model{};model.failSleep=true;assert(!bootstrapOpen(&why)&&model.opens==1&&!model.alive);
 puts("PASS actual C++ root startup callbacks, sixty-second readiness, alarm ordering and failure cleanup; virtual time only");
}
'''
LATE=r'''
#include "@HEADER@"
#include <stdio.h>
static uint64_t now;
static bool tick(void* p,uint64_t* n){(void)p;*n=now;return true;}
static bool sleep_model(void* p,uint64_t n){(void)p;now+=n;return true;}
static void* open_model(void* p){return now>=60000000000?p:NULL;}
static void close_model(void* p,void* d){(void)p;(void)d;}
int main(void){int token=1;struct gauguin_metal_wait_ops ops={&token,tick,sleep_model,open_model,close_model};struct gauguin_metal_wait_result r;void* d=gauguin_metal_wait_open(&ops,&r);if(!d){puts("OLD bounded wait misses sixty-second publication");return 42;}if(d!=&token||now!=60000000000||r.reason!=GMW_READY)return 1;puts("PASS late publication at sixty seconds");return 0;}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--old-header',type=Path,required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(exist_ok=False)
    header=root/'graphics/hakios-metal-ca/desktop-overlay/userland/src/GauguinMetalBootstrapWait.h'
    source=(root/'userland/metal/device_probe.cpp').read_text()
    helper=source.split('/* GAUGUIN_BOOTSTRAP_WAIT_BEGIN:',1)[1].split('*/',1)[1].split('/* GAUGUIN_BOOTSTRAP_WAIT_END */',1)[0]
    prefix=source.split('static void run(uint32_t seed) {',1)[1].split('auto wrapped=',1)[0]
    main_body=source.split('int main(int argc,char** argv)',1)[1]
    assert 'alarm(30)'not in main_body and prefix.index('bootstrapOpen')<prefix.index('alarm(30)')
    unit=out/'actual-startup.cpp';unit.write_text(HOST.replace('@HEADER@',str(header)).replace('@HELPER@',helper).replace('@PREFIX@',prefix))
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    subprocess.run(['xcrun','clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-DGAUGUIN_METAL_BOOTSTRAP=1','-fsanitize=address,undefined',str(unit),'-o',str(out/'actual-startup')],check=True,env=env)
    subprocess.run([str(out/'actual-startup')],check=True,env=env)
    for name,h,wanted in [('old',a.old_header.resolve(),42),('new',header,0)]:
        p=out/(name+'-late.c');p.write_text(LATE.replace('@HEADER@',str(h)))
        subprocess.run(['xcrun','clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(out/(name+'-late'))],check=True,env=env)
        result=subprocess.run([str(out/(name+'-late'))],env=env)
        assert result.returncode==wanted,(name,result.returncode,wanted)
    print('PASS actual startup bodies and functional OLD42/NEW0 delayed-publication control; no device IO')

if __name__=='__main__':main()
