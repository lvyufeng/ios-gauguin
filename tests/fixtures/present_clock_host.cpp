// Actual software-clock header and driver methods with a virtual absolute clock.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <vector>
#define GAUGUIN 1
#define SWEET_FB_VSYNC_US 16667
#define NSEC_PER_USEC 1000
static unsigned checks,failedLogs,rejectedLogs;
static void check(bool v){++checks;assert(v);}
static uint64_t nowTicks,rate=1;
static int requested=1;
using IOLock=std::mutex;
static void IOLockLock(IOLock *p){p->lock();}
static void IOLockUnlock(IOLock *p){p->unlock();}
static uint64_t mach_absolute_time(){return nowTicks;}
static void clock_interval_to_absolutetime_interval(uint32_t us,uint32_t scale,uint64_t *ticks){check(scale==1000);*ticks=uint64_t(us)*rate;}
static void PE_parse_boot_argn(const char *name,int *out,size_t size){check(!std::strcmp(name,"sweetfb_phase")&&size==sizeof(int));*out=requested;}
static void IOLog(const char *fmt,...){if(std::strstr(fmt,"failed"))failedLogs++;if(std::strstr(fmt,"rejected"))rejectedLogs++;}
using IOReturn=int;
constexpr int kIOReturnSuccess=0;
struct IOTimerEventSource {
    uint64_t deadline=0;
    unsigned absolute=0,relative=0;
    bool fail=false;
    int wakeAtTime(uint64_t at){absolute++;deadline=at;return fail?5:0;}
    int setTimeoutUS(uint32_t us){relative++;deadline=nowTicks+uint64_t(us)*rate;return 0;}
};
@CLOCK_HEADER@
struct AppleCLCD {
    IOLock lock;
    IOLock *fLock=&lock;
    bool fHoldPresent=true,fPhasePresent=false,fDirty=true,fPowerOff=false;
    uint32_t fFlushTicks=2;
    SweetPresentClock fPresentClock={};
    void configurePresentClock();
    bool presentClockTickLocked(uint64_t,uint64_t *,bool *);
    void presentClockCopiedLocked();
    void armVsync(IOTimerEventSource *);
};
@DRIVER_METHODS@
struct LegacyFB { bool fDirty=true;uint32_t fFlushTicks=2; };
static bool legacyFlush(LegacyFB *fb,uint64_t count){ @LEGACY_FLUSH@ return flush; }
static void legacyArm(IOTimerEventSource *sender){ @LEGACY_ARM@ }

static std::vector<uint64_t> legacyRun(unsigned count,uint64_t cost){
    nowTicks=0;rate=1;LegacyFB fb;IOTimerEventSource timer;legacyArm(&timer);std::vector<uint64_t> copies;
    for(unsigned i=1;i<=count;i++){
        nowTicks=timer.deadline;
        if(legacyFlush(&fb,i)){copies.push_back(nowTicks);nowTicks+=cost;}
        legacyArm(&timer);
    }
    return copies;
}
struct Run { std::vector<uint64_t> copies;uint64_t logical=0,callbacks=0,skipped=0; };
static Run modernRun(unsigned callbacks,const std::vector<uint64_t> &costs,uint64_t jitter=0){
    nowTicks=0;rate=1;requested=1;AppleCLCD fb;IOTimerEventSource timer;fb.configurePresentClock();check(fb.fPhasePresent);
    fb.armVsync(&timer);Run out;
    for(unsigned i=0;i<callbacks;i++){
        check(timer.deadline>nowTicks);nowTicks=timer.deadline+(i%3)*jitter;
        uint64_t elapsed=0;bool copy=false;
        {
            std::lock_guard<IOLock> guard(fb.lock);
            check(fb.presentClockTickLocked(nowTicks,&elapsed,&copy)&&elapsed>0);out.logical+=elapsed;
            if(copy){fb.presentClockCopiedLocked();out.copies.push_back(nowTicks);}
        }
        if(copy)nowTicks+=costs[i%costs.size()];
        fb.armVsync(&timer);check(fb.fPhasePresent&&timer.relative==0);
    }
    out.callbacks=fb.fPresentClock.callbacks;out.skipped=fb.fPresentClock.skippedBeats;
    check(out.callbacks==callbacks&&out.callbacks+out.skipped==out.logical&&fb.fPresentClock.copies==out.copies.size());
    return out;
}
int main(int argc,char **argv){
    check(argc==2);
    if(!std::strcmp(argv[1],"legacy-contract")){
        auto copies=legacyRun(120,12000);check(copies.size()==60);
        check(copies[1]-copies[0]==45334&&copies[1]-copies[0]!=33334);
        std::fputs("FAIL relative rearm adds copy work to the next interval\n",stderr);return 42;
    }
    unsigned cleanLogs=failedLogs+rejectedLogs;
    auto regular=modernRun(120,{12000});check(regular.copies.size()==60&&regular.skipped==0);
    check(regular.copies[0]==33334);
    for(size_t i=1;i<regular.copies.size();i++)check(regular.copies[i]-regular.copies[i-1]==33334);
    auto loaded=modernRun(500,{0,12000,50000,5000,25000},300);
    check(loaded.skipped>0&&loaded.copies.size()<500&&loaded.callbacks==500);
    for(size_t i=1;i<loaded.copies.size();i++)check(loaded.copies[i]>loaded.copies[i-1]);
    check(cleanLogs==failedLogs+rejectedLogs);
    {
        SweetPresentClock c={};SweetPresentTick tick={};uint64_t deadline=0;
        check(!sweet_present_clock_init(&c,0,0,2));check(!sweet_present_clock_init(&c,0,10,0));
        check(!sweet_present_clock_init(&c,0,UINT64_MAX,2));check(!sweet_present_clock_init(&c,UINT64_MAX-19,10,2));
        check(sweet_present_clock_init(&c,100,10,2));check(sweet_present_clock_next(&c,100,&deadline)&&deadline==110);
        check(sweet_present_clock_step(&c,109,true,&tick)&&tick.elapsed==0&&!tick.copyDue&&c.callbacks==0);
        check(!sweet_present_clock_copied(&c));check(sweet_present_clock_step(&c,110,true,&tick)&&tick.elapsed==1&&!tick.copyDue);
        check(sweet_present_clock_step(&c,110,true,&tick)&&tick.elapsed==0);
        check(sweet_present_clock_step(&c,120,true,&tick)&&tick.elapsed==1&&tick.copyDue);
        check(sweet_present_clock_copied(&c)&&c.nextCopy==140&&!sweet_present_clock_copied(&c));
        check(sweet_present_clock_next(&c,125,&deadline)&&deadline==130);
        check(!sweet_present_clock_step(&c,124,true,&tick));
    }
    {
        SweetPresentClock c={};SweetPresentTick tick={};uint64_t deadline=0;
        check(sweet_present_clock_init(&c,0,10,2));check(sweet_present_clock_step(&c,10,false,&tick));
        check(sweet_present_clock_next(&c,45,&deadline)&&deadline==50&&c.nextBeat==20);
        check(sweet_present_clock_step(&c,50,true,&tick)&&tick.elapsed==4&&tick.copyDue&&c.skippedBeats==3);
        check(sweet_present_clock_copied(&c)&&c.nextCopy==70);
        check(sweet_present_clock_step(&c,1010,true,&tick)&&tick.copyDue);check(sweet_present_clock_copied(&c)&&c.nextCopy==1030);
        check(sweet_present_clock_step(&c,1020,true,&tick)&&!tick.copyDue);
        check(sweet_present_clock_step(&c,1030,true,&tick)&&tick.copyDue);check(sweet_present_clock_copied(&c));
    }
    {
        SweetPresentClock c={};SweetPresentTick tick={};
        check(sweet_present_clock_init(&c,0,10,2));check(sweet_present_clock_step(&c,20,true,&tick)&&tick.copyDue);
        // Allocation/handoff did not consume a frame: the offered slot stays due.
        check(c.nextCopy==20&&c.copies==0);
        check(sweet_present_clock_step(&c,30,true,&tick)&&tick.copyDue);check(sweet_present_clock_copied(&c)&&c.nextCopy==50);
        c.callbacks=UINT64_MAX;c.skippedBeats=UINT64_MAX;c.copies=UINT64_MAX;
        check(sweet_present_clock_step(&c,100,true,&tick)&&c.callbacks==UINT64_MAX&&c.skippedBeats==UINT64_MAX);
        check(sweet_present_clock_copied(&c)&&c.copies==UINT64_MAX);
    }
    {
        nowTicks=100;rate=24;requested=1;AppleCLCD fb;fb.configurePresentClock();
        check(fb.fPresentClock.beat==400008&&fb.fPresentClock.copySpan==800016);
        fb.fPowerOff=true;uint64_t elapsed=0;bool copy=false;
        check(fb.presentClockTickLocked(800116,&elapsed,&copy)&&!copy);
        fb.fPowerOff=false;check(fb.presentClockTickLocked(1200124,&elapsed,&copy)&&copy);fb.presentClockCopiedLocked();
        check(fb.fPresentClock.copies==1&&fb.fPresentClock.nextCopy==2000140);rate=1;
    }
    {
        nowTicks=100;requested=1;AppleCLCD fb;fb.configurePresentClock();uint64_t elapsed=0;bool copy=true;
        unsigned failed=failedLogs;check(fb.presentClockTickLocked(99,&elapsed,&copy));check(!fb.fPhasePresent&&elapsed==1&&!copy&&failedLogs==failed+1);
        nowTicks=100;AppleCLCD arm;arm.configurePresentClock();IOTimerEventSource timer;nowTicks=99;arm.armVsync(&timer);
        check(!arm.fPhasePresent&&timer.absolute==0&&timer.relative==1&&failedLogs==failed+2);
        nowTicks=100;AppleCLCD wake;wake.configurePresentClock();IOTimerEventSource failing;failing.fail=true;wake.armVsync(&failing);
        check(!wake.fPhasePresent&&failing.absolute==1&&failing.relative==1&&failedLogs==failed+3);
    }
    {
        nowTicks=0;requested=2;AppleCLCD bad;unsigned rejected=rejectedLogs;bad.configurePresentClock();check(!bad.fPhasePresent&&rejectedLogs==rejected+1);
        requested=1;bad.fHoldPresent=false;bad.configurePresentClock();check(!bad.fPhasePresent&&rejectedLogs==rejected+2);
        requested=0;AppleCLCD legacy;legacy.configurePresentClock();IOTimerEventSource timer;legacy.armVsync(&timer);
        check(!legacy.fPhasePresent&&timer.absolute==0&&timer.relative==1&&timer.deadline==16667);
        nowTicks=UINT64_MAX-1;requested=1;AppleCLCD overflow;overflow.configurePresentClock();check(!overflow.fPhasePresent&&rejectedLogs==rejected+3);
    }
    {
        SweetPresentClock c={};SweetPresentTick tick={};uint64_t deadline=0;
        check(sweet_present_clock_init(&c,UINT64_MAX-20,5,2));
        check(sweet_present_clock_step(&c,UINT64_MAX-10,true,&tick)&&tick.copyDue);check(sweet_present_clock_copied(&c)&&c.nextCopy==UINT64_MAX);
        check(!sweet_present_clock_next(&c,UINT64_MAX,&deadline));check(!sweet_present_clock_step(&c,UINT64_MAX,true,&tick));
    }
    // Independent bounded loop oracle: no modulo/division in expected beat advancement.
    for(uint64_t n=1;n<=1000;n++){
        uint64_t base=(uint64_t(1)<<40)+n*12345,beat=1+n*317;uint32_t divisor=1+n%7;
        SweetPresentClock c={};SweetPresentTick tick={};check(sweet_present_clock_init(&c,base,beat,divisor));
        uint64_t when=base+beat*(1+n%97)+n%beat,expected=base+beat,elapsed=0,last=0;
        while(expected<=when){last=expected;expected+=beat;elapsed++;}
        uint64_t deadline=0;check(sweet_present_clock_next(&c,when,&deadline)&&deadline==expected);
        check(sweet_present_clock_step(&c,when,true,&tick)&&tick.elapsed==elapsed&&c.firedBeat==last&&c.nextBeat==expected);
        check(tick.copyDue==(last>=base+beat*divisor));
        if(tick.copyDue)check(sweet_present_clock_copied(&c)&&c.nextCopy==last+beat*divisor);
    }
    std::printf("PASS software-clock checks=%u; modeled 12ms work: old copy interval45334 -> new33334 ticks; overload/idle/failures/64bit bounds; no physical FPS claim\n",checks);
}
