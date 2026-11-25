#pragma once
#include "Recording338.hpp"
#include <array>

// Body elapsed includes preemption/nested waits. All accounting is bounded,
// fixed-size and diagnostic only; no allocation, GPU operation or reordering.
#pragma GCC visibility push(hidden)
namespace gauguin339 {
using Values=std::array<uint64_t,8>;
enum Category : unsigned { Control,Bindings,Render,Clear,Compute,Transfer,Commit,Notify,CategoryCount };
enum SubmitStage : unsigned { Entry,PassTail,CommandBo,CommandCopy,QueueLock,FaultQuery,NativeSubmit,Publication,SubmitCount };
inline uint64_t nowNs() noexcept { return gauguin338::nowNs(); }
constexpr uint32_t badCategory=1,badClock=2,badPrefix=4,badCounter=8,badSubmit=16;

inline uint64_t sum(const Values& values) noexcept {
    uint64_t total=0;
    for (auto value:values) total+=value;
    return total;
}

struct WorkMeter {
    uint64_t completed=0,start=0;
    Values completedByClass{};
    unsigned category=Control;
    bool running=false;
    std::atomic<uint64_t> end{0};
    uint64_t partial(uint64_t at) const noexcept {
        const uint64_t ended=end.load(std::memory_order_acquire);
        const uint64_t stop=ended && ended<at ? ended : at;
        return running && stop>=start ? stop-start : 0;
    }
    uint64_t snapshot(uint64_t at) const noexcept { return completed+partial(at); }
    Values snapshotCategories(uint64_t at) const noexcept {
        Values result=completedByClass;
        result[category]+=partial(at);
        return result;
    }
    void begin(uint64_t at,unsigned kind) noexcept {
        category=kind<CategoryCount?kind:Control;
        start=at;end.store(0,std::memory_order_relaxed);running=true;
    }
    void finish(uint64_t at) noexcept { end.store(at,std::memory_order_release); }
    void retire(uint64_t at) noexcept {
        const auto elapsed=at>=start?at-start:0;
        completed+=elapsed;completedByClass[category]+=elapsed;running=false;
    }
};

struct SubmitData {
    Values elapsed{};
    uint64_t beginNs=0,endNs=0;
    unsigned mask=0,calls=0,outcome=4,flags=0;
};
extern thread_local SubmitData* activeSubmit;

struct Trace {
    std::atomic<bool> enabled{false};
    uintptr_t object=0;
    uint64_t madeUs=0,queue=0;
    std::atomic<uint64_t> ticket{0};
    std::atomic<uint32_t> flags{0};
    uint64_t jobs=0,execution=0,queueSum=0,queueMax=0;
    Values counts{},executionByClass{},maxExecution{};
    uint64_t prefixSequence=0;
    Values prefix{};
    unsigned worstCategory=Control;
    uint64_t worstSequence=0,worstEnqueued=0,worstStart=0,worstEnd=0;
    SubmitData submit;
    void identify(uintptr_t obj,uint64_t made,uint64_t q,uint64_t t) noexcept {
        if (!obj || !q || made<220000000 || made>270000000) return;
        if (!enabled.load(std::memory_order_acquire)) {
            object=obj;madeUs=made;queue=q;ticket.store(t,std::memory_order_relaxed);
            enabled.store(true,std::memory_order_release);
        } else if (object==obj && madeUs==made && queue==q && t) ticket.store(t,std::memory_order_release);
    }
    // Caller and worker synchronize through the existing recorder mutex.
    // Store only once, in the CB, rather than growing every queued Job.
    void queued(uint64_t sequence,const Values& values) noexcept {
        if (!enabled.load(std::memory_order_acquire)) return;
        if (prefixSequence) {flags.fetch_or(badPrefix);return;}
        prefixSequence=sequence;prefix=values;
    }
    Values waited(uint64_t sequence,const Values& completed,uint64_t scalar) noexcept {
        Values result{};
        if (!enabled.load(std::memory_order_acquire)) return result;
        if (prefixSequence!=sequence) {flags.fetch_or(badPrefix);return result;}
        for (unsigned i=0;i<CategoryCount;i++) {
            if (completed[i]<prefix[i]) {flags.fetch_or(badPrefix);return Values{};}
            result[i]=completed[i]-prefix[i];
        }
        if (sum(result)!=scalar) flags.fetch_or(badPrefix);
        return result;
    }
};

struct SubmitScope {
    SubmitData* previous;
    explicit SubmitScope(Trace& trace) noexcept : previous(activeSubmit) {
        activeSubmit=trace.enabled.load(std::memory_order_acquire)?&trace.submit:nullptr;
        if (activeSubmit) *activeSubmit=SubmitData{};
    }
    ~SubmitScope() {activeSubmit=previous;}
    SubmitScope(const SubmitScope&)=delete;
    SubmitScope& operator=(const SubmitScope&)=delete;
};

class SubmitProbe {
public:
    using Clock=uint64_t(*)();
    explicit SubmitProbe(Clock clock=nowNs) noexcept : data_(activeSubmit),clock_(clock) {
        if (data_) {
            if (++data_->calls!=1) data_->flags|=badSubmit;
            data_->outcome=5;start_=clock_();data_->beginNs=start_;
            if (!start_) data_->flags|=badClock;
        }
    }
    ~SubmitProbe() { if (data_) close(clock_()); }
    void phase(unsigned next) noexcept {
        if (!data_) return;
        if (next>=SubmitCount || next<=stage_) {data_->flags|=badSubmit;return;}
        const auto at=clock_();close(at);stage_=next;start_=at;
    }
    void outcome(unsigned value) noexcept {if (data_) data_->outcome=value;}
private:
    void close(uint64_t at) noexcept {
        data_->endNs=at;data_->mask|=1u<<stage_;
        if (!start_ || at<start_) {data_->flags|=badClock;return;}
        const uint64_t elapsed=at-start_;
        if (UINT64_MAX-data_->elapsed[stage_]<elapsed) {data_->flags|=badCounter;return;}
        data_->elapsed[stage_]+=elapsed;
    }
    SubmitData* data_;
    Clock clock_;
    unsigned stage_=Entry;
    uint64_t start_=0;
};

inline std::atomic<unsigned> records{0};
constexpr unsigned recordLimit=4096,lineLimit=2048;
inline unsigned long long u(uint64_t n) noexcept {return static_cast<unsigned long long>(n);}
struct Line {
    char bytes[lineLimit]{};
    unsigned size=0;
    bool valid=true;
    template<class... A> void add(const char* format,A... args) noexcept {
        if (!valid) return;
        const int n=std::snprintf(bytes+size,sizeof(bytes)-size,format,args...);
        if (n<=0 || unsigned(n)>=sizeof(bytes)-size) {valid=false;return;}
        size+=unsigned(n);
    }
    void values(const char* name,const Values& v) noexcept {
        add(" %s=%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu",name,
            u(v[0]),u(v[1]),u(v[2]),u(v[3]),u(v[4]),u(v[5]),u(v[6]),u(v[7]));
    }
};

inline void observe(Trace& trace,unsigned kind,unsigned category,uint64_t sequence,uint64_t enqueued,
                    uint64_t began,uint64_t ended,uint64_t busyWait,const Values& waited,
                    unsigned state,bool failed) noexcept {
    if (!trace.enabled.load(std::memory_order_acquire)) return;
    if (category>=CategoryCount) {trace.flags.fetch_or(badCategory);category=Control;}
    if (!enqueued || began<enqueued || ended<began) trace.flags.fetch_or(badClock);
    const uint64_t elapsed=ended>=began?ended-began:0;
    const uint64_t queued=began>=enqueued?began-enqueued:0;
    auto add=[&](uint64_t& target,uint64_t value) noexcept {
        if (UINT64_MAX-target<value) {trace.flags.fetch_or(badCounter);return;}
        target+=value;
    };
    add(trace.jobs,1);add(trace.execution,elapsed);add(trace.queueSum,queued);
    add(trace.counts[category],1);add(trace.executionByClass[category],elapsed);
    if (queued>trace.queueMax) trace.queueMax=queued;
    if (elapsed>trace.maxExecution[category]) trace.maxExecution[category]=elapsed;
    if (!trace.worstSequence || elapsed>trace.worstEnd-trace.worstStart) {
        trace.worstCategory=category;trace.worstSequence=sequence;trace.worstEnqueued=enqueued;
        trace.worstStart=began;trace.worstEnd=ended;
    }
    if (kind!=1) return;
    unsigned n=records.load(std::memory_order_relaxed);
    do {if (n>recordLimit) return;}
    while (!records.compare_exchange_weak(n,n+1,std::memory_order_relaxed));
    if (n==recordLimit) {std::fputs("GAUGUIN CR339: limit=4096 coverage=incomplete\n",stderr);return;}
    Line line;
    line.add("GAUGUIN CR339: object=%p made_us=%llu queue=%llu ticket=%llu job=%llu enq_ns=%llu start_ns=%llu end_ns=%llu busy_wait_ns=%llu jobs=%llu own_exec_ns=%llu sum_queue_ns=%llu max_queue_ns=%llu state=%u failed=%u",
        reinterpret_cast<void*>(trace.object),u(trace.madeUs),u(trace.queue),u(trace.ticket.load(std::memory_order_acquire)),
        u(sequence),u(enqueued),u(began),u(ended),u(busyWait),u(trace.jobs),u(trace.execution),u(trace.queueSum),u(trace.queueMax),state,failed?1u:0u);
    line.values("counts",trace.counts);line.values("exec_ns",trace.executionByClass);
    line.values("wait_ns",waited);line.values("max_exec_ns",trace.maxExecution);
    line.add(" max_class=%u max_job=%llu max_enq_ns=%llu max_start_ns=%llu max_end_ns=%llu submit_mask=%u submit_outcome=%u submit_begin_ns=%llu submit_end_ns=%llu",
        trace.worstCategory,u(trace.worstSequence),u(trace.worstEnqueued),u(trace.worstStart),u(trace.worstEnd),trace.submit.mask,trace.submit.outcome,u(trace.submit.beginNs),u(trace.submit.endNs));
    line.values("submit_ns",trace.submit.elapsed);
    line.add(" flags=%u\n",trace.flags.load(std::memory_order_relaxed)|trace.submit.flags);
    if (!line.valid) {std::fputs("GAUGUIN CR339: formatting=failed coverage=incomplete\n",stderr);return;}
    std::fputs(line.bytes,stderr);
}
} // namespace gauguin339
#pragma GCC visibility pop
