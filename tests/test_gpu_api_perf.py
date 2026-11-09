"""Execute actual cached profiling code; verify unchanged hardware bodies."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
S=Path(os.environ.get('XNU_SOURCE',R/'.deps-cache/p0-20261105/source208-codex'))
P=Path(os.environ.get('XNU_REFERENCE',R/'.deps-cache/p0-20261105/source207-codex'))
HOST=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using IOReturn=int;
constexpr IOReturn kIOReturnSuccess=0;
static uint64_t now;
static unsigned clockReads,checks;
static uint64_t mach_absolute_time(){++clockReads;return now;}
static void absolutetime_to_nanoseconds(uint64_t ticks,uint64_t *ns){*ns=ticks;}
static std::vector<std::string> lines;
static void record(const char *line){lines.emplace_back(line);}
#define CHECK(x) do{++checks;assert(x);}while(0)
@HELPER@
static void reset(){
    memset(gapi_samples,0,sizeof(gapi_samples));gapi_pending={};
    gapi_sequence=gapi_pending_queue=gapi_pending_held=now=0;
    gapi_valid=true;gapi_frozen=gapi_dumped=false;clockReads=0;lines.clear();
}
int main(){
    reset();auto token=gapi_begin(0x46,10,30);CHECK(token==1);
    now=130;gapi_end(token,0);CHECK(gapi_samples[6].calls==1&&gapi_samples[6].failures==0);
    CHECK(gapi_samples[6].queue_ticks==20&&gapi_samples[6].held_ticks==100&&gapi_samples[6].max_held_ticks==100);
    token=gapi_begin(0x46,200,250);CHECK(token==2);now=500;gapi_end(token,7);
    CHECK(gapi_samples[6].calls==2&&gapi_samples[6].failures==1);
    CHECK(gapi_samples[6].queue_ticks==70&&gapi_samples[6].held_ticks==350&&gapi_samples[6].max_held_ticks==250);
    token=gapi_begin(0x100,550,600);now=900;gapi_end(token,0);
    CHECK(gapi_samples[13].calls==1&&gapi_samples[13].held_ticks==300);
    CHECK(clockReads==3&&!gapi_pending.token&&gapi_valid);
    struct gapi_sample saved[GAPI_COUNT];memcpy(saved,gapi_samples,sizeof(saved));
    GauguinGPUProfileDump(record);CHECK(lines.empty());
    GauguinGPUProfileFreeze();CHECK(gapi_frozen&&clockReads==3);
    CHECK(!gapi_begin(0x46,1000,1100));gapi_end(100,0);
    CHECK(!memcmp(saved,gapi_samples,sizeof(saved)));
    GauguinGPUProfileDump(nullptr);CHECK(!gapi_dumped);
    GauguinGPUProfileDump(record);CHECK(lines.size()==3);
    CHECK(lines[0].find("valid=1 pending=0 selector=0 queue_ns=0 held_ns=0")!=std::string::npos);
    CHECK(lines[1].find("selector=46 calls=2 failures=1 queue_ns=70 held_ns=350 max_held_ns=250")!=std::string::npos);
    CHECK(lines[2].find("selector=100 calls=1 failures=0 queue_ns=50 held_ns=300 max_held_ns=300")!=std::string::npos);
    GauguinGPUProfileDump(record);CHECK(lines.size()==3&&clockReads==3);

    reset();token=gapi_begin(0x42,10,20);now=120;GauguinGPUProfileFreeze();
    CHECK(gapi_pending_queue==10&&gapi_pending_held==100&&gapi_pending.token==token);
    now=1000;GauguinGPUProfileFreeze();gapi_end(token,1);
    CHECK(gapi_pending_held==100&&!gapi_samples[2].calls&&clockReads==1);
    GauguinGPUProfileDump(record);CHECK(lines.size()==1);
    CHECK(lines[0].find("valid=1 pending=1 selector=42 queue_ns=10 held_ns=100")!=std::string::npos);

    reset();CHECK(!gapi_begin(0x103,0,0));CHECK(!gapi_valid&&!gapi_pending.token);
    reset();CHECK(!gapi_begin(0x46,100,99));CHECK(!gapi_valid&&!gapi_pending.token);
    reset();token=gapi_begin(0x46,10,20);CHECK(!gapi_begin(0x43,20,30));
    CHECK(!gapi_valid&&gapi_pending.token==token);gapi_end(0,0);now=50;gapi_end(token,0);
    CHECK(!gapi_pending.token&&!gapi_samples[6].calls);
    reset();token=gapi_begin(0x46,100,200);now=199;gapi_end(token,0);
    CHECK(!gapi_valid&&!gapi_pending.token&&!gapi_samples[6].calls);
    reset();token=gapi_begin(0x46,10,20);gapi_end(token+1,0);
    CHECK(!gapi_valid&&gapi_pending.token==token);now=40;gapi_end(token,0);CHECK(!gapi_pending.token);
    reset();gapi_sequence=UINT64_MAX;CHECK(!gapi_begin(0x46,0,0)&&!gapi_valid);
    for(unsigned field=0;field<4;field++){
        reset();auto &s=gapi_samples[6];
        if(field==0)s.calls=UINT64_MAX;
        if(field==1)s.failures=UINT64_MAX;
        if(field==2)s.queue_ticks=UINT64_MAX;
        if(field==3)s.held_ticks=UINT64_MAX;
        auto before=s;token=gapi_begin(0x46,0,1);now=2;gapi_end(token,1);
        CHECK(!gapi_valid&&!gapi_pending.token);CHECK(!memcmp(&before,&s,sizeof(s)));
    }
    reset();token=gapi_begin(0x46,0,100);now=99;GauguinGPUProfileFreeze();
    CHECK(gapi_frozen&&!gapi_valid&&gapi_pending.token==token);
    reset();
    for(unsigned i=0;i<GAPI_COUNT;i++){
        token=gapi_begin(gapi_selectors[i],i*20,i*20+5);now=i*20+15;gapi_end(token,0);
        CHECK(gapi_samples[i].calls==1&&!gapi_samples[i].failures);
        CHECK(gapi_samples[i].queue_ticks==5&&gapi_samples[i].held_ticks==10&&gapi_samples[i].max_held_ticks==10);
    }
    GauguinGPUProfileFreeze();GauguinGPUProfileDump(record);
    CHECK(lines.size()==GAPI_COUNT+1&&gapi_valid&&!gapi_pending.token);
    for(auto &line:lines)CHECK(line.size()<256);
    printf("API elapsed profile: %u assertions; actual selector/token/time/freeze/partial/overflow/dump helpers passed; CPU clock only\n",checks);
}
'''
def extract(text,signature):
    start=text.index(signature);return text[start:text.index('\n}\n',start)+3]
def main():
    paths=[Path(__file__),S/'iokit/Kernel/arm/GauguinGPU.cpp',S/'bsd/dev/gauguin_gmu_board.c',S/'bsd/dev/gauguin_gpu_runtime.h',P/'iokit/Kernel/arm/GauguinGPU.cpp',P/'bsd/dev/gauguin_gmu_board.c',P/'bsd/dev/gauguin_gpu_runtime.h']
    pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    cpp=paths[1].read_text();old=paths[4].read_text();board=paths[2].read_text();oldboard=paths[5].read_text()
    for sig in ['static bool gfw_faults(', 'static bool ggrb_live_check(', 'static bool ggrb_micro_settle(bool gpu_probe,uint32_t expected,uint32_t mask,uint32_t current,struct gfw_micro_wait *wait)\n{']:
        assert extract(board,sig)==extract(oldboard,sig)
    for sig in ['IOReturn GauguinGPUUserClient::submit(', 'IOReturn GauguinGPUUserClient::surface(', 'IOReturn GauguinGPUUserClient::add(', 'bool GauguinGPUUserClient::drop(']:
        assert extract(cpp,sig)==extract(old,sig)
    changed=extract(board,'static void ggrb_quarantine(')
    assert changed.index('gmb_fail(')<changed.index('GauguinGPUProfileFreeze(')<changed.index('GauguinGPUProfileDump(')
    changed=changed.replace('    GauguinGPUProfileFreeze();\n','').replace('    GauguinGPUProfileDump(gmb_record);\n','')
    assert changed==extract(oldboard,'static void ggrb_quarantine(')
    for sig in ['extern "C" bool GauguinGPUHeartbeat(', 'IOReturn GauguinGPUUserClient::clientClose(', 'IOReturn GauguinGPUUserClient::clientMemoryForType(', 'IOReturn GauguinGPUUserClient::externalMethod(']:
        body=extract(cpp,sig)
        assert body.index('IOLockLock(gLock)')<body.index('gapi_begin(')<body.index('gapi_end(')<body.index('IOLockUnlock(gLock)')
        body=body.replace('uint64_t queued=mach_absolute_time();IOLockLock(gLock);','IOLockLock(gLock);')
        body=re.sub(r'\s*uint64_t profile=gapi_begin\([^;]+;','',body)
        body=re.sub(r'\s*gapi_end\([^;]+;','',body)
        assert re.sub(r'\s+','',body)==re.sub(r'\s+','',extract(old,sig)),sig
    helper=cpp[cpp.index('/* All mutable samples'):cpp.index('\nstatic bool physicalPage(')]
    with tempfile.TemporaryDirectory(prefix='gpu-api-perf-') as d:
        d=Path(d);unit=d/'profile.cpp';unit.write_text(HOST.replace('@HELPER@',helper))
        env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(unit),'-o',str(d/'profile')],env=env,check=True)
        subprocess.run([str(d/'profile')],env=env,check=True,timeout=30)
    assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    print('Unchanged real submit/add/drop/surface and full live/SMMU predicates; original locked wrapper bodies preserved apart from elapsed samples')
if __name__=='__main__':main()
