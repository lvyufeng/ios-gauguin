#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include "hakios-metal/gpu.hpp"

namespace hakios::metal {

/* Capability knowledge belongs to one IOKit connection, not a process/global
 * chip ID. Unsupported is not a successful zero fault count: the caller still
 * receives ENOSYS. Submit/wait error handling is unchanged. A positive answer
 * permanently keeps queries live, including if an older unsupported response
 * races it. Transient errors do not establish a negative capability. */
class GauguinFaultQueryCache {
public:
    static bool matches(uint32_t request, const void* data, size_t size) noexcept {
        if (request != kGetParam || !data || size != sizeof(MsmParam)) return false;
        MsmParam param;
        std::memcpy(&param, data, sizeof(param));  // also safe for unaligned input
        return param.pipe == kPipe3D && param.param == kParamFaults &&
               param.value == 0 && param.len == 0 && param.pad == 0;
    }

    bool unsupported() const noexcept {
        return state_.load(std::memory_order_acquire) == kUnsupported;
    }

    /* True only for the first transition to Unsupported, for one bounded log.
     * The caller evaluates success only after validating the returned size. */
    bool observe(bool exactQuery, bool validSuccess, bool unsupportedResult) noexcept {
        if (!exactQuery) return false;
        if (validSuccess) {
            state_.store(kSupported, std::memory_order_release);
            return false;
        }
        if (!unsupportedResult) return false;
        unsigned unknown = kUnknown;
        return state_.compare_exchange_strong(unknown, kUnsupported,
                                              std::memory_order_acq_rel,
                                              std::memory_order_acquire);
    }

private:
    enum : unsigned { kUnknown, kUnsupported, kSupported };
    std::atomic<unsigned> state_{kUnknown};
};

}  // namespace hakios::metal
