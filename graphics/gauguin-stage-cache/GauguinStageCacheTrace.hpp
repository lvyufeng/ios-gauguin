#pragma once

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mach/mach_time.h>
#include <pthread.h>

// One bounded record per compileStage invocation. No bitcode, constants or paths
// are printed. Timestamps use the same absolute clock as the C4 frontend.
namespace {
struct GauguinStageCacheTrace {
    static constexpr uint64_t limit = 1024;
    inline static std::atomic<uint64_t> count{0};
    uint64_t id = count.fetch_add(1, std::memory_order_relaxed) + 1;
    uint64_t thread = reinterpret_cast<uintptr_t>(pthread_self());
    uint64_t at[10] = {};
    char key[33] = "-";
    unsigned outcome = 0; // 0 failure, 1 fast hit, 2 hit after lock, 3 compiled, 4 no compiler
    unsigned source = 0;  // 0 none, 1 writable cache, 2 seed
    bool known;
    size_t bytes;

    static uint64_t now() {
        static const mach_timebase_info_data_t scale = [] {
            mach_timebase_info_data_t value{};
            if (mach_timebase_info(&value) != 0 || !value.denom) return mach_timebase_info_data_t{};
            return value;
        }();
        if (!scale.denom || !scale.numer) return 0;
        const uint64_t tick = mach_absolute_time();
        const uint64_t whole = tick / scale.denom, part = tick % scale.denom;
        if (whole > UINT64_MAX / scale.numer) return 0;
        const uint64_t base = whole * scale.numer;
        const uint64_t tail = part * uint64_t(scale.numer) / scale.denom;
        if (base > UINT64_MAX - tail) return 0;
        return (base + tail) / 1000;
    }

    GauguinStageCacheTrace(bool k, size_t n) : known(k), bytes(n) {
        if (id <= limit) at[0] = now();
    }
    void mark(unsigned n) { if (id <= limit && n < 10) at[n] = now(); }
    void setKey(const char* value) {
        // stageCacheName is either empty or /<32 hex digits>.stage.
        if (value && std::strlen(value) == 39 && value[0] == '/') {
            std::memcpy(key, value + 1, 32);
            key[32] = 0;
        }
    }
    ~GauguinStageCacheTrace() {
        if (id == limit + 1) {
            std::fprintf(stderr, "GAUGUIN SC323: limit=1 max=1024\n");
        } else if (id <= limit) {
            mark(9);
            std::fprintf(stderr,
                "GAUGUIN SC323: id=%llu thread=%llx key=%s known=%u bytes=%llu outcome=%u source=%u "
                "start=%llu ready=%llu keyed=%llu fast=%llu locking=%llu locked=%llu retry=%llu compiled=%llu saved=%llu end=%llu\n",
                (unsigned long long)id, (unsigned long long)thread, key, unsigned(known),
                (unsigned long long)bytes, outcome, source,
                (unsigned long long)at[0], (unsigned long long)at[1], (unsigned long long)at[2],
                (unsigned long long)at[3], (unsigned long long)at[4], (unsigned long long)at[5],
                (unsigned long long)at[6], (unsigned long long)at[7], (unsigned long long)at[8],
                (unsigned long long)at[9]);
        }
    }
};
} // namespace
