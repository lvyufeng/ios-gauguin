#include "Recording341.hpp"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>

namespace gauguin341 {
thread_local SubmitData* activeSubmit=nullptr;
thread_local Workspace* activeWorkspace=nullptr;
thread_local uint64_t activeJobSequence=0;
thread_local DrawData* activeDraw=nullptr;
thread_local FineSubmitData* activeGpu=nullptr;
}
using namespace gauguin341;
#define CHECK(x) do {if (!(x)) {std::fprintf(stderr,"CLOCK341 %d: %s\n",__LINE__,#x);std::abort();}} while(0)
static uint64_t wallValues[4],cpuValues[2];
static unsigned wi=0,ci=0,failAt=99;
uint64_t wallClock() {CHECK(wi<4);return wallValues[wi++];}
bool cpuClock(uint64_t* value) noexcept {CHECK(ci<2);*value=cpuValues[ci];return ci++!=failAt;}

FineSubmitData model(uint64_t delta,unsigned failure=99) {
    wi=ci=0;failAt=failure;
    wallValues[0]=10000000;wallValues[1]=10100000;wallValues[2]=20100000;wallValues[3]=20300000;
    cpuValues[0]=1000000;cpuValues[1]=1000000+delta;
    FineSubmitData data;unsigned calls=0;
    {CpuProbe c(&data,wallClock,cpuClock);{IoProbe io(&data,wallClock);calls++;}}
    CHECK(calls==1 && data.ioCalls==1 && data.ioNs==10000000 && data.cpu.queries==2);
    return data;
}
void bounds() {
    auto x=model(4000000);const auto& c=x.cpu;
    CHECK(c.flags==0 && c.calls==1 && c.ok==1 && c.overhead==300000);
    CHECK(c.lower==3698000 && c.upper==4002000 && c.offLower==5998000 && c.offUpper==6302000);
    auto wait=model(10000);CHECK(wait.cpu.lower==0 && wait.cpu.upper==12000 && wait.cpu.offLower==9988000);
    auto busy=model(10150000);CHECK(busy.cpu.lower==9848000 && busy.cpu.upper==10000000 && busy.cpu.offLower==0);
}
void failures() {
    for (unsigned f:{0u,1u}) {auto d=model(4000000,f);CHECK(d.cpu.ok==0 && d.cpu.flags && d.ioNs==10000000);}
    auto wrong=model(10400000);CHECK(wrong.cpu.flags && wrong.cpu.ok==0);
    FineSubmitData stale;stale.cpu.calls=UINT64_MAX;wi=ci=0;
    {CpuProbe c(&stale,wallClock,cpuClock);}
    CHECK(stale.cpu.flags && stale.cpu.calls==UINT64_MAX && ci==0 && wi==0);
    wi=ci=0;{CpuProbe c(nullptr,wallClock,cpuClock);}CHECK(ci==0 && wi==0);
    ProgramData p;p.counts[0]=UINT64_MAX;programCount(&p,0);CHECK(p.flags && p.counts[0]==UINT64_MAX);
}
void live(bool sleep) {
    FineSubmitData d;errno=E2BIG;
    {CpuProbe c(&d);CHECK(errno==E2BIG);
        {IoProbe io(&d);
            if (sleep) std::this_thread::sleep_for(std::chrono::milliseconds(20));
            else {
                uint64_t began=0,now=0;CHECK(cpuNow(&began));
                do {for (volatile unsigned i=0;i<10000;i++) {}CHECK(cpuNow(&now));} while (now-began<8000000);
            }
            errno=EBUSY;
        }
    }
    CHECK(errno==EBUSY && d.cpu.flags==0 && d.cpu.ok==1 && d.cpu.queries==2);
    CHECK(d.cpu.lower<=d.cpu.upper && d.cpu.upper<=d.ioNs && d.cpu.offLower==d.ioNs-d.cpu.upper);
    if (sleep) CHECK(d.cpu.offLower>5000000);
    else CHECK(d.cpu.after-d.cpu.before>=8000000);
    std::printf("LIVE341 sleep=%u wall=%llu cpu_delta=%llu cpu_low=%llu cpu_high=%llu off_low=%llu off_high=%llu envelope=%llu\n",
        sleep?1u:0u,u(d.ioNs),u(d.cpu.after-d.cpu.before),u(d.cpu.lower),u(d.cpu.upper),u(d.cpu.offLower),u(d.cpu.offUpper),u(d.cpu.overhead));
}
void partitions() {
    ProgramData p;DrawData d;d.program=p;
    {DrawScope draw(&d);CHECK(programData()==&d.program);programCount(programData(),0);draw.complete();}
    CHECK(activeDraw==nullptr && d.program.counts[0]==1);
    std::array<uint64_t,14> max;max.fill(UINT64_MAX);Line line;
    line.values("counter",max);CHECK(line.valid && line.size<lineLimit && lineLimit==8192);
}
int main(int argc,char** argv) {
    CHECK(argc==2);const std::string s=argv[1];
    if(s=="bounds") bounds();
    else if(s=="failures") failures();
    else if(s=="busy") live(false);
    else if(s=="sleep") live(true);
    else if(s=="threads") {std::thread a([]{live(false);}),b([]{live(true);});a.join();b.join();CHECK(activeDraw==nullptr);}
    else if(s=="partitions") partitions();
    else CHECK(false);
    std::printf("PASS341 %s\n",s.c_str());return 0;
}
