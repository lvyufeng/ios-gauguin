#ifndef GAUGUIN_DIRECT_SCANOUT_H
#define GAUGUIN_DIRECT_SCANOUT_H

#include <stdint.h>

namespace gauguin::scanout {

constexpr uint32_t kPanelWidth = 1080;
constexpr uint32_t kPanelHeight = 2400;
constexpr uint32_t kRenderWidth = 1125;
constexpr uint32_t kRenderHeight = 2436;
constexpr uint32_t kCropX = 22;
constexpr uint32_t kCropY = 18;
constexpr uint32_t kPixelBytes = 4;
constexpr uint32_t kBGRA = 0x42475241; // IOSurface 'BGRA'
constexpr uint32_t kOriginalPitch = kPanelWidth * kPixelBytes;
constexpr uint32_t kRenderPitch = 4608;
constexpr uint64_t kPageBytes = 0x4000;
constexpr uint64_t kRenderBytes = uint64_t(kRenderPitch) * kRenderHeight;
constexpr uint64_t kSlotBytes = (kRenderBytes + kPageBytes-1) & ~(kPageBytes-1);
constexpr uint64_t kDPUAddressEnd = UINT64_C(0x100000000);
constexpr uint64_t kGPUAddressStart = 0x40000000;
constexpr uint64_t kGPUAddressEnd = 0x80000000;
constexpr uint64_t kOriginalBase = 0xa0000000;
constexpr uint64_t kOriginalAllocationEnd = 0xa2400000;

static_assert(kRenderPitch % 64 == 0 && kRenderPitch >= kRenderWidth*kPixelBytes);
static_assert(kCropX+kPanelWidth <= kRenderWidth && kCropY+kPanelHeight <= kRenderHeight);

struct Layout {
    uint32_t width, height, pitch, pixelFormat, planes, sourceX, sourceY;
    bool linear;
};

struct BufferProof {
    uint64_t physical, gpuAddress, contiguousBytes;
    bool managedPages, gpuMappingMatches, dpuReadVerified;
};

constexpr bool validLayout(const Layout &layout)
{
    // Preserve the existing A619 render-target pitch and configure a matching
    // VIG source pitch when entering direct scanout. Keep the full render
    // allocation while VIG fetches the same centered rectangle as the copy.
    return layout.width == kRenderWidth && layout.height == kRenderHeight &&
        layout.pitch == kRenderPitch && layout.pixelFormat == kBGRA &&
        layout.planes == 0 && layout.sourceX == kCropX && layout.sourceY == kCropY && layout.linear;
}

constexpr bool overlap(uint64_t a, uint64_t b)
{
    return a < b ? b - a < kSlotBytes : a - b < kSlotBytes;
}

constexpr bool validBuffer(const BufferProof &buffer)
{
    return buffer.physical && buffer.physical % kPageBytes == 0 &&
        buffer.physical <= kDPUAddressEnd - kSlotBytes &&
        (buffer.physical >= kOriginalAllocationEnd || buffer.physical <= kOriginalBase - kSlotBytes) &&
        buffer.gpuAddress >= kGPUAddressStart && buffer.gpuAddress % kPageBytes == 0 &&
        buffer.gpuAddress <= kGPUAddressEnd - kSlotBytes && buffer.contiguousBytes >= kSlotBytes &&
        buffer.managedPages && buffer.gpuMappingMatches && buffer.dpuReadVerified;
}

enum class Slot : uint8_t { Original, First, Second };
enum class Phase : uint8_t {
    Disabled, Idle, Reserved, InFlight, CachePending, Ready, FlipPending, Quarantined
};

struct Lease {
    uint64_t generation = 0;
    Slot slot = Slot::Original;
};

struct Latch {
    uint32_t scan;
    uint64_t source;
    uint32_t pitch;
    uint32_t sourceXY;
    bool flushPending;
    bool qualified;
};

// Serialize all methods with the framebuffer owner lock. The GPU owner
// delivers the exact native fence and cache receipt before this object can
// authorize display publication. The caller owns both backing descriptors.
class DirectScanout {
public:
    DirectScanout() = default;
    DirectScanout(const DirectScanout &) = delete;
    DirectScanout &operator=(const DirectScanout &) = delete;

    bool enable(const Layout &layout, const BufferProof &first, const BufferProof &second)
    {
        if (phase_ != Phase::Disabled || !validLayout(layout) || !validBuffer(first) || !validBuffer(second) ||
            overlap(first.physical, second.physical) || overlap(first.gpuAddress, second.gpuAddress))
            return false;
        addresses_[0] = first.physical;
        addresses_[1] = second.physical;
        phase_ = Phase::Idle;
        return true;
    }

    Phase phase() const { return phase_; }
    Slot front() const { return front_; }

    bool acquire(uint64_t generation, Lease &lease)
    {
        if (phase_ != Phase::Idle || generation <= lastGeneration_)
            return false;
        lastGeneration_ = generation;
        lease_ = {generation, front_ == Slot::First ? Slot::Second : Slot::First};
        lease = lease_;
        phase_ = Phase::Reserved;
        return true;
    }

    bool cancelBeforeIssue(const Lease &lease)
    {
        if (phase_ != Phase::Reserved || !matches(lease))
            return false;
        phase_ = Phase::Idle;
        return true;
    }

    bool recordIssue(const Lease &lease, uint32_t fence)
    {
        if (phase_ != Phase::Reserved || !matches(lease) || fence <= lastFence_)
            return false;
        lastFence_ = fence;
        phase_ = Phase::InFlight;
        return true;
    }

    bool recordEOP(const Lease &lease, uint32_t fence)
    {
        if (phase_ != Phase::InFlight || !matches(lease) || lastFence_ != fence)
            return false;
        phase_ = Phase::CachePending;
        return true;
    }

    bool recordVisibility(const Lease &lease, uint32_t fence)
    {
        if (phase_ != Phase::CachePending || !matches(lease) || lastFence_ != fence)
            return false;
        phase_ = Phase::Ready;
        return true;
    }

    bool canFlip(const Lease &lease) const
    {
        return phase_ == Phase::Ready && matches(lease);
    }

    bool canRestoreOriginal() const
    {
        return phase_ == Phase::Idle && front_ != Slot::Original;
    }

    bool validIssueScan(uint32_t scan) const
    {
        return !hasLatch_ || scan - lastLatchScan_ < UINT32_C(0x80000000);
    }

    uint64_t sourceFor(Slot slot) const
    {
        switch (slot) {
        case Slot::Original: return kOriginalBase;
        case Slot::First: return addresses_[0];
        case Slot::Second: return addresses_[1];
        }
        return 0;
    }

    static uint32_t pitchFor(Slot slot)
    {
        return slot == Slot::Original ? kOriginalPitch : kRenderPitch;
    }

    static uint32_t sourceXYFor(Slot slot)
    {
        return slot == Slot::Original ? 0 : (kCropY << 16) | kCropX;
    }

    // Call only after the guarded blanking transaction was accepted. On a
    // refused no-write attempt keep the Ready state. An uncertain write
    // takes the quarantine path under the same lock.
    bool recordFlip(const Lease &lease, uint32_t scan)
    {
        if (!canFlip(lease) || !validIssueScan(scan))
            return false;
        pending_ = lease.slot;
        issueScan_ = scan;
        phase_ = Phase::FlipPending;
        return true;
    }

    bool recordOriginalRestore(uint32_t scan)
    {
        if (!canRestoreOriginal() || !validIssueScan(scan))
            return false;
        pending_ = Slot::Original;
        issueScan_ = scan;
        phase_ = Phase::FlipPending;
        return true;
    }

    bool confirmLatch(const Latch &latch)
    {
        if (phase_ != Phase::FlipPending)
            return false;
        const uint32_t delta = latch.scan - issueScan_;
        if (!latch.qualified || delta > 1 || latch.source != sourceFor(pending_) ||
            latch.pitch != pitchFor(pending_) || latch.sourceXY != sourceXYFor(pending_)) {
            quarantine();
            return false;
        }
        if (delta != 1 || latch.flushPending)
            return false;
        front_ = pending_;
        lastLatchScan_ = latch.scan;
        hasLatch_ = true;
        phase_ = Phase::Idle;
        return true;
    }

    // Timeouts, uncertain GPU issue and uncertain DPU publication use this
    // path. Neither descriptor can be released until platform reset.
    void quarantine()
    {
        if (phase_ != Phase::Disabled)
            phase_ = Phase::Quarantined;
    }

    bool disable()
    {
        if (phase_ != Phase::Idle || front_ != Slot::Original)
            return false;
        addresses_[0] = addresses_[1] = 0;
        phase_ = Phase::Disabled;
        return true;
    }

private:
    bool matches(const Lease &lease) const
    {
        return lease.generation == lease_.generation && lease.slot == lease_.slot;
    }

    uint64_t addresses_[2] = {};
    uint64_t lastGeneration_ = 0;
    uint32_t lastFence_ = 0;
    uint32_t issueScan_ = 0;
    uint32_t lastLatchScan_ = 0;
    bool hasLatch_ = false;
    Lease lease_;
    Slot front_ = Slot::Original;
    Slot pending_ = Slot::Original;
    Phase phase_ = Phase::Disabled;
};

} // namespace gauguin::scanout

#endif
