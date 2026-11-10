#!/usr/bin/env python3
"""Execute actual framebuffer setup and desktop predicate, with typed clock/arg seams."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def method(text,signature):
    start=text.index(signature);return text[start:text.index('\n}\n',start)+3]
def unit(tree):
    fb=(tree/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    start=method(fb,'bool\nAppleCLCD::start(')
    at=start.index('    int held =');held=start[at:start.index('    fHeldActive =',at)]
    predicate=method((tree/'bsd/kern/kern_exec.c').read_text(),'bool\nsweet_metal_desktop_enabled(')
    configure=method(fb,'void\nAppleCLCD::configurePresentClock(')
    clock=(tree/'iokit/Kernel/arm/SweetPresentClock.h').read_text()
    return HOST.replace('@PREDICATE@',predicate).replace('@HELD@',held).replace('@CONFIGURE@',configure).replace('@CLOCK@',clock)
HOST=r'''
#include <cassert>
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#define GAUGUIN 1
#define SWEET_FB_VSYNC_US 16667
#define NSEC_PER_USEC 1000
static int sweet_exec_loader_probe,sweet_eagl_inject_requested,sweet_metal_requested;
static unsigned checks;
static void check(bool ok){checks++;assert(ok);}
@PREDICATE@
static std::map<std::string,int> arguments;
static bool PE_parse_boot_argn(const char *key,void *out,size_t size){
    check(size==sizeof(int));auto i=arguments.find(key);if(i==arguments.end())return false;
    std::memcpy(out,&i->second,size);return true;
}
static void IOLog(const char *,...){}
static uint64_t mach_absolute_time(){return 100;}
static void clock_interval_to_absolutetime_interval(uint32_t us,uint32_t scale,uint64_t *ticks){check(scale==1000);*ticks=us;}
@CLOCK@
struct AppleCLCD {
    bool fHoldPresent=false,fPhasePresent=false;
    uint32_t fFlushTicks=1;
    SweetPresentClock fPresentClock={};
    void held(){ @HELD@ }
    void configurePresentClock();
};
@CONFIGURE@
int main(int argc,char **){
    if(argc==2){
        sweet_exec_loader_probe=1;sweet_eagl_inject_requested=2;sweet_metal_requested=2;
        AppleCLCD fb;fb.held();fb.configurePresentClock();
        if(!fb.fHoldPresent||!fb.fPhasePresent){
            std::fputs("FAIL exact desktop without redundant flags misses held/phase policy\n",stderr);return 42;
        }
        return 0;
    }
    constexpr int selectors[]={-1,0,1,2,3,INT_MAX};
    constexpr int flags[]={INT_MIN,0,1,-1,2}; // INT_MIN denotes absent
    unsigned cases=0;
    for(int a:selectors)for(int b:selectors)for(int c:selectors)
    for(int h:flags)for(int p:flags){
        sweet_exec_loader_probe=a;sweet_eagl_inject_requested=b;sweet_metal_requested=c;
        arguments.clear();if(h!=INT_MIN)arguments["sweetfb_hold"]=h;if(p!=INT_MIN)arguments["sweetfb_phase"]=p;
        const bool desktop=a==1&&b==2&&c==2;
        const bool held=h==INT_MIN?desktop:h==1;
        const int phase=p==INT_MIN?int(desktop):p;
        AppleCLCD fb;fb.held();fb.configurePresentClock();
        check(fb.fHoldPresent==held);check(fb.fPhasePresent==(held&&phase==1));
        if(fb.fPhasePresent)check(fb.fPresentClock.beat==16667&&fb.fPresentClock.copySpan==16667);
        cases++;
    }
    std::printf("PASS %u selector/override cases, %u assertions; real setup/predicate, host clock/args only\n",cases,checks);
}
'''
def main():
    tree=Path(os.environ['XNU_SOURCE']);old=Path(os.environ['DESKTOP_POLICY_REFERENCE'])
    paths=[Path(__file__)]+[t/p for t in [tree,old]for p in
        ['iokit/Kernel/arm/SweetFramebuffer.cpp','iokit/Kernel/arm/SweetPresentClock.h','bsd/kern/kern_exec.c']]
    pins={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    with tempfile.TemporaryDirectory(prefix='desktop-present-policy-')as directory:
        for name,source in [('old',old),('candidate',tree)]:
            cpp=Path(directory)/(name+'.cpp');cpp.write_text(unit(source));exe=cpp.with_suffix('')
            subprocess.run(['xcrun','clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror',
                '-pedantic','-fsanitize=address,undefined',str(cpp),'-o',str(exe)],env=env,check=True)
            result=subprocess.run([str(exe),'desktop-contract']if name=='old'else[str(exe)],
                capture_output=True,text=True,env=env,timeout=30)
            if name=='old':
                assert result.returncode==42 and result.stderr=='FAIL exact desktop without redundant flags misses held/phase policy\n',(result.returncode,result.stdout,result.stderr)
                print('Baseline functional RED: actual249 desktop requires redundant boot flags')
            else:
                assert result.returncode==0,(result.returncode,result.stdout,result.stderr);print(result.stdout,end='')
    assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
if __name__=='__main__':main()
