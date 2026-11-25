#pragma once
#include "Recording338.hpp"
#include "Reuse341.hpp"
#include <array>
#include <cerrno>
#include <time.h>

#pragma GCC visibility push(hidden)
namespace gauguin341 {
constexpr uint32_t finePhase=1,fineClock=2,fineCounter=4,fineIncomplete=8,fineIo=16;
template<size_t N> struct Times {
    std::array<uint64_t,N> ns{},worstPhases{};
    uint64_t calls=0,ok=0,skipped=0,failed=0,worst=0,worstJob=0,worstStart=0,worstEnd=0;
    uint32_t flags=0;
};

template<size_t N> class TimeProbe {
public:
    using Clock=uint64_t(*)();
    explicit TimeProbe(Times<N>* data,Clock clock=gauguin338::nowNs) noexcept : data_(data),clock_(clock) {
        if (data_) {
            add(data_->calls,1);began_=start_=clock_();sequence_=activeJobSequence;
            if (!start_) data_->flags|=fineClock;
        }
    }
    ~TimeProbe() {
        if (!data_) return;
        const auto end=clock_();close(end);
        for (size_t i=0;i<N;i++) add(data_->ns[i],elapsed_[i]);
        if (outcome_==0 && mask_==((1u<<N)-1)) add(data_->ok,1);
        else if (outcome_==1 && (mask_&1)) add(data_->skipped,1);
        else {add(data_->failed,1);data_->flags|=fineIncomplete;}
        const auto length=end>=began_?end-began_:0;
        if (!data_->worstJob || length>data_->worst) {
            data_->worst=length;data_->worstJob=sequence_;data_->worstStart=began_;data_->worstEnd=end;
            data_->worstPhases=elapsed_;
        }
    }
    void phase(unsigned next) noexcept {
        if (!data_) return;
        if (next>=N || next<=stage_) {data_->flags|=finePhase;return;}
        const auto at=clock_();close(at);stage_=next;start_=at;
    }
    void complete() noexcept {outcome_=0;}
    void skip() noexcept {outcome_=1;}
    TimeProbe(const TimeProbe&)=delete;
    TimeProbe& operator=(const TimeProbe&)=delete;
private:
    void add(uint64_t& target,uint64_t value) noexcept {
        if (UINT64_MAX-target<value) {data_->flags|=fineCounter;return;}
        target+=value;
    }
    void close(uint64_t at) noexcept {
        mask_|=1u<<stage_;
        if (!start_ || at<start_) {data_->flags|=fineClock;return;}
        add(elapsed_[stage_],at-start_);
    }
    Times<N>* data_;
    Clock clock_;
    std::array<uint64_t,N> elapsed_{};
    uint64_t began_=0,start_=0,sequence_=0;
    unsigned stage_=0,mask_=0,outcome_=2;
};

struct ProgramData {
    Times<4> address;
    Times<5> resident;
    Times<1> table;
    Times<4> piece;
    Times<6> pool;
    std::array<uint64_t,14> counts{};
    uint32_t flags=0;
};
struct CpuData {
    uint64_t calls=0,ok=0,queries=0,before=0,after=0,outerBegin=0,outerEnd=0;
    uint64_t overhead=0,lower=0,upper=0,offLower=0,offUpper=0;
    uint32_t flags=0;
};
struct DrawData {
    Times<8> common,render;
    ReuseCounts reuse;
    ProgramData program;
};
struct FineSubmitData {
    Times<5> stages;
    ReuseCounts reuse;
    uint64_t ioCalls=0,ioBegin=0,ioEnd=0,ioNs=0;
    uint64_t uses=0,unique=0,comparisons=0,reserveFailures=0;
    unsigned mode=0;
    uint32_t flags=0;
    CpuData cpu;
};
extern thread_local DrawData* activeDraw;
extern thread_local FineSubmitData* activeGpu;

struct DrawScope {
    DrawData* data;
    DrawData* previous;
    TimeProbe<8> probe;
    explicit DrawScope(DrawData* d) noexcept : data(d),previous(activeDraw),probe(d?&d->common:nullptr) {activeDraw=d;}
    ~DrawScope() {activeDraw=previous;}
    ReuseCounts* reuse() noexcept {return data?&data->reuse:nullptr;}
    void phase(unsigned stage) noexcept {probe.phase(stage);}
    void complete() noexcept {probe.complete();}
};

inline ProgramData* programData() noexcept {return activeDraw?&activeDraw->program:nullptr;}
inline void programCount(ProgramData* d,unsigned index,uint64_t n=1) noexcept {
    if (!d) return;
    if (index>=d->counts.size() || UINT64_MAX-d->counts[index]<n) {d->flags|=fineCounter;return;}
    d->counts[index]+=n;
}
constexpr uint64_t cpuClockSlopNs=2000;
inline bool cpuNow(uint64_t* value) noexcept {
    const int saved=errno;timespec sample{};
    const int answer=clock_gettime(CLOCK_THREAD_CPUTIME_ID,&sample);
    errno=saved;
    if (answer!=0 || sample.tv_sec<0 || sample.tv_nsec<0 || sample.tv_nsec>=1000000000) return false;
    const uint64_t seconds=uint64_t(sample.tv_sec),nanos=uint64_t(sample.tv_nsec);
    if (seconds>(UINT64_MAX-nanos)/1000000000) return false;
    *value=seconds*1000000000+nanos;return true;
}
class CpuProbe {
public:
    using Clock=uint64_t(*)();
    using CpuClock=bool(*)(uint64_t*) noexcept;
    explicit CpuProbe(FineSubmitData* data,Clock clock=gauguin338::nowNs,CpuClock cpu=cpuNow) noexcept : data_(data),clock_(clock),cpu_(cpu) {
        if (!data_) return;
        auto& c=data_->cpu;
        if (c.calls || c.ok || c.queries) {c.flags|=fineIo;return;}
        active_=true;c.calls=1;
        c.outerBegin=clock_();c.queries=1;
        first_=cpu_(&c.before);
    }
    ~CpuProbe() {
        if (!data_ || !active_) return;
        auto& c=data_->cpu;
        c.queries=2;
        const bool second=cpu_(&c.after);c.outerEnd=clock_();
        if (!first_ || !second || c.after<c.before || !c.outerBegin || c.outerEnd<c.outerBegin ||
            data_->ioCalls!=1 || data_->ioBegin<c.outerBegin || data_->ioEnd>c.outerEnd ||
            data_->ioEnd<data_->ioBegin || data_->ioNs!=data_->ioEnd-data_->ioBegin) {c.flags|=fineIo;return;}
        const uint64_t wall=c.outerEnd-c.outerBegin,delta=c.after-c.before;
        if (UINT64_MAX-wall<cpuClockSlopNs || UINT64_MAX-delta<cpuClockSlopNs || delta>wall+cpuClockSlopNs) {c.flags|=fineClock;return;}
        c.overhead=wall-data_->ioNs;
        const uint64_t cost=c.overhead+cpuClockSlopNs;
        c.lower=delta>cost?delta-cost:0;
        c.upper=std::min(data_->ioNs,delta+cpuClockSlopNs);
        if (c.lower>c.upper) {c.flags|=fineClock;return;}
        c.offLower=data_->ioNs-c.upper;c.offUpper=data_->ioNs-c.lower;
        c.ok++;
    }
    CpuProbe(const CpuProbe&)=delete;
    CpuProbe& operator=(const CpuProbe&)=delete;
private:
    FineSubmitData* data_;
    Clock clock_;
    CpuClock cpu_;
    bool first_=false,active_=false;
};

class IoProbe {
public:
    using Clock=uint64_t(*)();
    explicit IoProbe(FineSubmitData* data,Clock clock=gauguin338::nowNs) noexcept : data_(data),clock_(clock) {
        if (!data_) return;
        if (data_->ioCalls==UINT64_MAX) data_->flags|=fineCounter;
        else if (++data_->ioCalls!=1) data_->flags|=fineIo;
        start_=clock_();data_->ioBegin=start_;
        if (!start_) data_->flags|=fineClock;
    }
    ~IoProbe() {
        if (!data_) return;
        const auto end=clock_();data_->ioEnd=end;
        if (!start_ || end<start_) {data_->flags|=fineClock;return;}
        if (UINT64_MAX-data_->ioNs<end-start_) {data_->flags|=fineCounter;return;}
        data_->ioNs+=end-start_;
    }
private:
    FineSubmitData* data_;
    Clock clock_;
    uint64_t start_=0;
};
} // namespace gauguin341
#pragma GCC visibility pop
