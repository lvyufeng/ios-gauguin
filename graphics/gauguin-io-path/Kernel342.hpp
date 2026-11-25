#pragma once
#include "Phase342.hpp"

// Included only by GauguinGPU.cpp. Use the
// ORIGINAL gRequests + gLock for publication/append; the shutdown dump
// requires gLock, and refuses an active request. Pre-lock state is stack-only.
namespace io342 {
constexpr uint64_t windowFirst=210000000000ull,windowLast=270000000000ull;
constexpr unsigned capacity=4096;
inline uint64_t wall() noexcept {uint64_t ns;absolutetime_to_nanoseconds(mach_absolute_time(),&ns);return ns;}
inline bool cpu(uint64_t* ns) noexcept {absolutetime_to_nanoseconds(thread_get_runtime_self(),ns);return true;}
struct Row {
    gauguin342phase::Data<12> phases;
    uint64_t token=0,tid=0,bytes=0,waitNs=0,waits=0;
    uint32_t pid=0,selector=0,queue=0,fence=0,handle=0,bos=0,cmds=0,result=~0u;
    bool enabled=false;
};
static Row rows[capacity];static unsigned count;
static uint64_t sequence,lost;static bool dumped,invalid;
class Scope;static Scope* active;
inline Row initial(bool compositor,uint32_t selector,uint64_t queued) noexcept {
    Row value;
    if(!compositor||(selector!=0x42&&selector!=0x43&&selector!=0x46&&selector!=0x100))return value;
    uint64_t ns;absolutetime_to_nanoseconds(queued,&ns);
    value.enabled=ns>=windowFirst&&ns<windowLast;
    if(value.enabled){value.selector=selector;value.pid=(uint32_t)proc_pid(current_proc());value.tid=thread_tid(current_thread());}
    return value;
}
class Scope {
public:
    Scope(bool compositor,uint32_t selector,uint64_t queued) noexcept : row_(initial(compositor,selector,queued)),
        probe_(row_.enabled?&row_.phases:nullptr,wall,cpu) {}
    ~Scope(){if(row_.enabled&&!finished_){row_.phases.flags|=gauguin342phase::orderError;finish(~0u);}}
    void phase(unsigned next) noexcept {
        if(!row_.enabled||finished_)return;
        if(next==index_)return;
        if(next<index_){row_.phases.flags|=gauguin342phase::orderError;return;}
        probe_.phase(next);index_=next;
    }
    void activate() noexcept {
        if(!row_.enabled)return;
        if(active||dumped||sequence==UINT64_MAX){invalid=true;row_.phases.flags|=gauguin342phase::orderError;return;}
        row_.token=++sequence;active=this;
    }
    bool isThread()const noexcept {return row_.enabled&&row_.tid==thread_tid(current_thread());}
    uint32_t selector()const noexcept{return row_.selector;}
    void tag(uint32_t queue,uint32_t fence,uint32_t handle,uint64_t bytes,uint32_t bos=0,uint32_t cmds=0) noexcept {
        row_.queue=queue;row_.fence=fence;row_.handle=handle;row_.bytes=bytes;row_.bos=bos;row_.cmds=cmds;
    }
    void fence(uint32_t queue,uint32_t fence) noexcept {row_.queue=queue;row_.fence=fence;}
    void allocation(uint32_t handle,uint64_t bytes) noexcept {row_.handle=handle;row_.bytes=bytes;}
    void waited(uint64_t begin) noexcept {
        uint64_t end=wall();
        if(end<begin||!gauguin342phase::add(row_.waitNs,end-begin)||!gauguin342phase::add(row_.waits,1))
            row_.phases.flags|=gauguin342phase::overflow;
    }
    void finish(uint32_t result) noexcept {
        if(!row_.enabled||finished_)return;
        probe_.finish();row_.result=result;finished_=true;
        if(active==this)active=nullptr;
        else {invalid=true;row_.phases.flags|=gauguin342phase::orderError;}
        if(dumped||count==capacity){if(lost==UINT64_MAX)invalid=true;else ++lost;return;}
        rows[count++]=row_;
    }
private:
    Row row_;gauguin342phase::Probe<12> probe_;unsigned index_=0;bool finished_=false;
};
inline Scope* current() noexcept {return active&&active->isThread()?active:nullptr;}
inline void phase(uint32_t selector,unsigned next) noexcept {auto* p=current();if(p&&p->selector()==selector)p->phase(next);}

class Line {
public:
    char data[2048]{};unsigned used=0;bool ok=true;
    void word(const char* s) noexcept {while(*s){if(used+1>=sizeof(data)){ok=false;return;}data[used++]=*s++;}data[used]=0;}
    void number(uint64_t n) noexcept {char reverse[20];unsigned at=0;do{reverse[at++]=char('0'+n%10);n/=10;}while(n);
        while(at){char s[2]={reverse[--at],0};word(s);}}
    void field(const char* name,uint64_t n) noexcept {word(name);number(n);}
    template<size_t N> void array(const char* name,const uint64_t(&values)[N]) noexcept {
        word(name);for(unsigned i=0;i<N;i++){if(i)word(",");number(values[i]);}
    }
};
inline void formatRow(Line& line,const Row& r,unsigned i) noexcept {
    const auto& p=r.phases;line.used=0;line.ok=true;line.data[0]=0;line.word("SWEET IO342: row");
    // Version 2 keeps the original field order and widths. The header
    // identifies positional rows so the names can be dropped from each row.
    line.field(" ",i);line.field(" ",r.token);line.field(" ",r.pid);line.field(" ",r.tid);
    line.field(" ",r.selector);line.field(" ",r.queue);line.field(" ",r.fence);
    line.field(" ",r.handle);line.field(" ",r.bytes);line.field(" ",r.bos);line.field(" ",r.cmds);
    line.field(" ",r.result);line.field(" ",p.first);line.field(" ",p.last);
    line.field(" ",p.queryWall);line.field(" ",p.queries);line.field(" ",p.mask);
    line.field(" ",p.flags);line.field(" ",r.waitNs);line.field(" ",r.waits);
    line.array(" ",p.begin);line.array(" ",p.end);line.array(" ",p.cpu);line.array(" ",p.envelope);
}
// One atomic reservation in the EXISTING persistent RAM ring per complete
// line. Bypass console_write's256-byte chunks; the next original BC335
// record performs the existing persistent flush after all our appends finish.
inline bool emit(Line& line,void(*record)(const char*),void(*frame)(const char*,int)) noexcept {
    if(!line.ok)return false;
    if(!frame){record(line.data);return true;}
    if(line.used+2>sizeof(line.data))return false;
    for(unsigned i=line.used;i;i--)line.data[i]=line.data[i-1];
    line.data[0]='\n';line.data[line.used+1]='\n';frame(line.data,(int)line.used+2);return true;
}
constexpr uint64_t dumpByteLimit=2u*1024u*1024u;
inline void dump(void(*record)(const char*),void(*frame)(const char*,int)=nullptr) noexcept {
    if(dumped||!record)return;dumped=true;
    // Bound the entire new stream before printing any row. The unchanged
    // 4MiB persistent log must retain the old trace and boot identity too.
    Line line;uint64_t rowBytes=0;
    for(unsigned i=0;i<count;i++){
        formatRow(line,rows[i],i);
        if(!line.ok||!gauguin342phase::add(rowBytes,line.used+2))invalid=true;
    }
    const bool byteLimited=rowBytes>dumpByteLimit-4096;
    if(byteLimited)invalid=true;
    line.used=0;line.ok=true;line.data[0]=0;
    line.word("SWEET IO342: begin version=2");line.field(" first_ns=",windowFirst);
    line.field(" last_ns=",windowLast);line.field(" count=",count);line.field(" capacity=",capacity);
    line.field(" lost=",lost);line.field(" pending=",active!=nullptr);line.field(" invalid=",invalid);
    line.field(" row_bytes=",rowBytes);line.field(" byte_limit=",dumpByteLimit);
    line.field(" byte_limited=",byteLimited);if(!emit(line,record,frame))invalid=true;
    unsigned emitted=0;
    if(!byteLimited&&!invalid)for(unsigned i=0;i<count;i++){
        formatRow(line,rows[i],i);
        if(emit(line,record,frame))++emitted;
        else invalid=true;
    }
    line.used=0;line.ok=true;line.data[0]=0;line.word("SWEET IO342: end");line.field(" count=",count);line.field(" lost=",lost);
    line.field(" pending=",active!=nullptr);line.field(" invalid=",invalid);
    line.field(" emitted=",emitted);line.field(" byte_limited=",byteLimited);if(!emit(line,record,frame))invalid=true;
}
} // namespace io342
