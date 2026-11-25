#include "Phase342.hpp"
#include <cassert>
#include <cstdio>
using namespace gauguin342phase;
static uint64_t walls[32],cpus[16];static size_t wi,ci;static bool ok=true;
static uint64_t wall() noexcept{return walls[wi++];}
static bool cpu(uint64_t* value) noexcept{*value=cpus[ci++];return ok;}
static void reset(){wi=ci=0;ok=true;for(auto&v:walls)v=0;for(auto&v:cpus)v=0;}
int main(){
    reset();walls[0]=100;walls[1]=110;walls[2]=10110;walls[3]=10130;
    walls[4]=30130;walls[5]=30160;cpus[0]=500;cpus[1]=8500;cpus[2]=18500;
    Data<2> data;{Probe<2> p(&data,wall,cpu);p.phase(1);p.finish();}
    assert(!data.flags&&data.queries==3&&data.mask==3&&data.queryWall==60);
    assert(data.last-data.first==30060&&data.end[0]-data.begin[0]==10000);
    assert(data.cpu[0]==8000&&data.envelope[0]==30);
    auto b=bounds(10000,8000,30);assert(b.cpuLower==5970&&b.cpuUpper==10000&&b.offUpper==4030);
    reset();{Probe<2> p(nullptr,wall,cpu);p.phase(1);}assert(!wi&&!ci);
    reset();walls[0]=100;walls[1]=110;walls[2]=50110;walls[3]=50130;cpus[0]=100;cpus[1]=1100;
    Data<4> skipped;{Probe<4> p(&skipped,wall,cpu);p.finish();}
    assert(!skipped.flags&&skipped.mask==1&&skipped.queries==2&&skipped.end[1]==0);
    b=bounds(50000,1000,30);assert(b.cpuLower==0&&b.cpuUpper==3000&&b.offLower==47000);
    reset();ok=false;Data<1> failed;{Probe<1> p(&failed,wall,cpu);p.finish();}assert(failed.flags&clockError);
    reset();walls[0]=100;walls[1]=110;walls[2]=90;walls[3]=95;Data<1> backwardWall;
    {Probe<1> p(&backwardWall,wall,cpu);}assert(backwardWall.flags&backward);
    reset();cpus[0]=100;cpus[1]=99;Data<1> backwardCPU;
    {Probe<1> p(&backwardCPU,wall,cpu);}assert(backwardCPU.flags&backward);
    reset();cpus[0]=0;cpus[1]=50000;Data<1> impossible;
    {Probe<1> p(&impossible,wall,cpu);}assert(impossible.flags&incoherent);
    reset();Data<2> wrong;{Probe<2> p(&wrong,wall,cpu);p.phase(0);p.phase(3);}assert(wrong.flags&orderError);
    uint64_t total=UINT64_MAX;assert(!add(total,1)&&total==UINT64_MAX);
    puts("0342 shared phase brackets: nonzero bounds, skips, failures, disabled, ordering and overflow passed");
}
