#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
static uint64_t ticks=4032000000ull,tid=1234,cpuReads;
static uint64_t mach_absolute_time(){return ticks+=10;}
static void absolutetime_to_nanoseconds(uint64_t value,uint64_t* out){*out=value*625/12;}
static uint64_t thread_get_runtime_self(){++cpuReads;return ticks/2;}
static uint64_t current_thread(){return 1;}
static uint64_t thread_tid(uint64_t value){assert(value==1);return tid;}
static int current_proc(){return 57;}
static int proc_pid(int value){return value;}
#include "Kernel342.hpp"
static std::vector<std::string> lines;
static unsigned frames;
static void frame(const char* data,int n){assert(n>1&&n<=2048&&data[0]=='\n'&&data[n-1]=='\n');++frames;lines.emplace_back(data+1,n-2);}
static void record(const char* line){assert(std::strlen(line)<2048);if(std::strstr(line,"SWEET IO342: begin")==line||std::strstr(line,"SWEET IO342: end")==line)assert(std::strlen(line)+1<=256);lines.emplace_back(line);}
static void enter(io342::Scope& scope){ticks+=5000;scope.phase(1);ticks+=5000;scope.phase(2);scope.activate();}
int main(int argc,char** argv){
    assert(argc==2);std::string name=argv[1];
    if(name=="enabled"){
        io342::Scope scope(true,0x46,mach_absolute_time());enter(scope);scope.tag(1,7,17,4096,5,1);
        auto begin=io342::wall();ticks+=5000;io342::current()->waited(begin);
        for(unsigned i=3;i<12;i++){ticks+=5000;io342::phase(0x46,i);}scope.finish(0);
        assert(io342::count==1&&!io342::invalid&&!io342::active);
        const auto& row=io342::rows[0];assert(row.token==1&&row.tid==1234&&row.waits==1&&row.waitNs>0);
        const auto& p=row.phases;assert(!p.flags&&p.mask==4095&&p.queries==13);
        uint64_t sum=p.queryWall;for(unsigned i=0;i<12;i++)sum+=p.end[i]-p.begin[i];assert(sum==p.last-p.first);
        auto b=gauguin342phase::bounds(p.end[0]-p.begin[0],p.cpu[0],p.envelope[0]);assert(b.cpuLower>1000&&b.offLower>1000);
        io342::dump(record,frame);assert(frames==3&&lines.size()==3);
        const bool positional=lines[0].find("version=2")!=std::string::npos;
        assert(lines[1].find(positional ? "SWEET IO342: row 0 1 57 1234" :
            "SWEET IO342: row index=0 token=1 pid=57 tid=1234")==0);
        io342::dump(record);assert(lines.size()==3);
    }else if(name=="disabled"){
        {io342::Scope scope(false,0x46,mach_absolute_time());enter(scope);scope.finish(0);}
        {io342::Scope scope(true,0x40,mach_absolute_time());enter(scope);scope.finish(0);}
        ticks=12;{io342::Scope scope(true,0x46,mach_absolute_time());enter(scope);scope.finish(0);}
        assert(!io342::count&&!cpuReads&&!io342::active);
    }else if(name=="foreign-thread"){
        io342::Scope scope(true,0x43,mach_absolute_time());enter(scope);const auto before=cpuReads;
        tid=99;assert(!io342::current());io342::phase(0x43,5);assert(cpuReads==before);
        tid=1234;io342::phase(0x43,3);scope.phase(11);scope.finish(0);assert(!io342::rows[0].phases.flags);
    }else if(name=="capacity"){
        for(unsigned i=0;i<=io342::capacity;i++){io342::Scope scope(true,0x43,mach_absolute_time());enter(scope);scope.phase(3);scope.phase(11);scope.finish(0);}
        assert(io342::count==4096&&io342::lost==1&&io342::rows[0].token==1&&io342::rows[4095].token==4096);
    }else if(name=="overflow"){
        io342::sequence=UINT64_MAX;io342::Scope scope(true,0x46,mach_absolute_time());enter(scope);scope.finish(1);
        assert(io342::invalid&&io342::rows[0].phases.flags&gauguin342phase::orderError);
    }else if(name=="pending-dump"){
        io342::Scope scope(true,0x46,mach_absolute_time());enter(scope);io342::dump(record);
        assert(lines[0].find("pending=1")!=std::string::npos);scope.finish(0);assert(!io342::active&&io342::lost==1);
    }else if(name=="format"){
        io342::count=1;auto& r=io342::rows[0];r.token=r.tid=r.bytes=r.waitNs=r.waits=UINT64_MAX;
        r.pid=r.selector=r.queue=r.fence=r.handle=r.bos=r.cmds=r.result=UINT32_MAX;
        auto& p=r.phases;p.first=p.last=p.queryWall=p.queries=p.mask=p.flags=UINT64_MAX;
        for(unsigned i=0;i<12;i++)p.begin[i]=p.end[i]=p.cpu[i]=p.envelope[i]=UINT64_MAX;
        io342::dump(record);assert(lines.size()==3&&lines[1].find("SWEET IO342: row")==0);
        const bool positional=lines[0].find("version=2")!=std::string::npos;
        assert(lines[1].find(positional ? " 18446744073709551615,18446744073709551615" :
            "flags=18446744073709551615")!=std::string::npos);
    }else if(name=="dump-byte-limit"){
        io342::count=io342::capacity;
        for(unsigned j=0;j<io342::capacity;j++){
            auto& r=io342::rows[j];r.token=r.tid=r.bytes=r.waitNs=r.waits=UINT64_MAX;
            r.pid=r.selector=r.queue=r.fence=r.handle=r.bos=r.cmds=r.result=UINT32_MAX;
            auto& p=r.phases;p.first=p.last=p.queryWall=p.queries=p.mask=p.flags=UINT64_MAX;
            for(unsigned i=0;i<12;i++)p.begin[i]=p.end[i]=p.cpu[i]=p.envelope[i]=UINT64_MAX;
        }
        io342::dump(record);assert(io342::invalid&&lines.size()==2);
        assert(lines[0].find("byte_limited=1")!=std::string::npos&&lines[1].find("emitted=0")!=std::string::npos);
        size_t bytes=0;for(const auto& line:lines)bytes+=line.size()+1;assert(bytes<io342::dumpByteLimit);
    }else if(name=="clock-scale"){
        uint64_t ns;absolutetime_to_nanoseconds(12,&ns);assert(ns==625);
        const auto raw=thread_get_runtime_self();uint64_t expected;absolutetime_to_nanoseconds(raw,&expected);
        uint64_t actual;assert(io342::cpu(&actual)&&actual==expected&&actual!=raw);
    }else assert(false);
    std::printf("PASS342 kernel-collector %s\n",name.c_str());
}
