#pragma once
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <limits>
#if defined(__APPLE__)
#include <mach/mach_time.h>
#else
#include <chrono>
#endif

/* CPU elapsed only. The recorder's existing single worker owns Trace totals.
 * Identity is published before recording, ticket once at frontend admission.
 * WorkMeter snapshots are taken under the recorder's existing mutex; only its
 * current body's end stamp is published atomically before reacquiring it.
 * No per-job output, new thread, GPU packet or GPU timestamp is introduced. */
#pragma GCC visibility push(hidden)
namespace gauguin338 {
inline uint64_t nowNs() noexcept {
#if defined(__APPLE__)
    static const mach_timebase_info_data_t scale=[] {
        mach_timebase_info_data_t value{};
        if (mach_timebase_info(&value)!=0) value={0,0};
        return value;
    }();
    if (!scale.numer || !scale.denom) return 0;
    const uint64_t tick=mach_absolute_time(), quotient=tick/scale.denom;
    if (quotient>std::numeric_limits<uint64_t>::max()/scale.numer) return 0;
    return quotient*scale.numer+(tick%scale.denom)*scale.numer/scale.denom;
#else
    return uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
#endif
}

struct WorkMeter {
    uint64_t completed=0, start=0;
    bool running=false;
    std::atomic<uint64_t> end{0};
    uint64_t snapshot(uint64_t at) const noexcept {
        const uint64_t done=end.load(std::memory_order_acquire);
        const uint64_t stop=done && done<at ? done : at;
        return completed+(running && stop>=start ? stop-start : 0);
    }
    void begin(uint64_t at) noexcept {
        start=at;end.store(0,std::memory_order_relaxed);running=true;
    }
    void finish(uint64_t at) noexcept { end.store(at,std::memory_order_release); }
    void retire(uint64_t at) noexcept {
        completed+=at-start;running=false;
    }
};

struct Trace {
    std::atomic<bool> enabled{false};
    uintptr_t object=0;
    uint64_t madeUs=0, queue=0;
    std::atomic<uint64_t> ticket{0};
    // Worker-only totals. Sum of job queue latencies can overlap, unlike exec.
    uint64_t jobs=0, execution=0, queueSum=0, queueMax=0;
    void identify(uintptr_t obj,uint64_t made,uint64_t q,uint64_t t) noexcept {
        if (!obj || !q || made<220000000 || made>270000000) return;
        if (!enabled.load(std::memory_order_acquire)) {
            object=obj;madeUs=made;queue=q;ticket.store(t,std::memory_order_relaxed);
            enabled.store(true,std::memory_order_release);
        } else if (object==obj && madeUs==made && queue==q && t) {
            ticket.store(t,std::memory_order_release);
        }
    }
};

inline std::atomic<unsigned> records{0};
constexpr unsigned recordLimit=4096, lineLimit=512;
inline void observe(Trace& trace,unsigned kind,uint64_t sequence,uint64_t enqueued,
                    uint64_t began,uint64_t ended,uint64_t busyWait,unsigned state,
                    bool failed) noexcept {
    if (!trace.enabled.load(std::memory_order_acquire)) return;
    trace.jobs++;
    trace.execution+=ended-began;
    trace.queueSum+=began-enqueued;
    if (began-enqueued>trace.queueMax) trace.queueMax=began-enqueued;
    if (kind!=1) return;
    unsigned n=records.load(std::memory_order_relaxed);
    do { if (n>recordLimit) return; }
    while (!records.compare_exchange_weak(n,n+1,std::memory_order_relaxed));
    if (n==recordLimit) {
        std::fputs("GAUGUIN CR338: limit=4096 coverage=incomplete\n",stderr);return;
    }
    char line[lineLimit];
    const int length=std::snprintf(line,sizeof(line),
        "GAUGUIN CR338: object=%p made_us=%llu queue=%llu ticket=%llu job=%llu enq_ns=%llu start_ns=%llu end_ns=%llu busy_wait_ns=%llu jobs=%llu own_exec_ns=%llu sum_queue_ns=%llu max_queue_ns=%llu state=%u failed=%u\n",
        reinterpret_cast<void*>(trace.object),
        static_cast<unsigned long long>(trace.madeUs),static_cast<unsigned long long>(trace.queue),
        static_cast<unsigned long long>(trace.ticket.load(std::memory_order_acquire)),
        static_cast<unsigned long long>(sequence),static_cast<unsigned long long>(enqueued),
        static_cast<unsigned long long>(began),static_cast<unsigned long long>(ended),
        static_cast<unsigned long long>(busyWait),static_cast<unsigned long long>(trace.jobs),
        static_cast<unsigned long long>(trace.execution),static_cast<unsigned long long>(trace.queueSum),
        static_cast<unsigned long long>(trace.queueMax),state,failed?1u:0u);
    if (length<=0 || unsigned(length)>=sizeof(line)) {
        std::fputs("GAUGUIN CR338: formatting=failed coverage=incomplete\n",stderr);return;
    }
    std::fputs(line,stderr);
}
} // namespace gauguin338
#pragma GCC visibility pop
