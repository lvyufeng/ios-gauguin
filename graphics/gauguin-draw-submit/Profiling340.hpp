#pragma once
#include "Recording338.hpp"
#include "Reuse340.hpp"
#include <array>

#pragma GCC visibility push(hidden)
namespace gauguin340 {
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

struct DrawData {
    Times<8> common,render;
    ReuseCounts reuse;
};
struct FineSubmitData {
    Times<5> stages;
    ReuseCounts reuse;
    uint64_t ioCalls=0,ioBegin=0,ioEnd=0,ioNs=0;
    uint64_t uses=0,unique=0,comparisons=0,reserveFailures=0;
    unsigned mode=0;
    uint32_t flags=0;
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
} // namespace gauguin340
#pragma GCC visibility pop
