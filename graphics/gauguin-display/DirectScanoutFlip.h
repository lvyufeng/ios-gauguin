#ifndef GAUGUIN_DIRECT_SCANOUT_FLIP_H
#define GAUGUIN_DIRECT_SCANOUT_FLIP_H

#include "DirectScanout.h"

namespace gauguin::scanout {

struct Position {
    uint32_t scan, line, end;
};

struct SourceView {
    uint64_t address;
    uint32_t pitch, sourceXY;
};

enum class FlipResult : uint8_t { Wait, Submitted, Uncertain };

inline bool sameView(const SourceView &a, const SourceView &b)
{
    return a.address == b.address && a.pitch == b.pitch && a.sourceXY == b.sourceXY;
}

inline SourceView view(const DirectScanout &owner, Slot slot)
{
    return {owner.sourceFor(slot), owner.pitchFor(slot), owner.sourceXYFor(slot)};
}

inline bool inBlank(const Position &position, uint32_t open, uint32_t guard)
{
    return position.line >= open && position.end > position.line &&
        position.end - position.line >= guard;
}

// Requires the framebuffer owner lock and the already qualified VIG/CTL
// route. The Hardware adapter covers only these registers. Geometry and
// address are one transaction when entering or restoring the original view.
template <class Hardware>
FlipResult issueBlankingFlip(Hardware &hardware, const DirectScanout &owner, Slot target,
                            uint32_t open, uint32_t guard, uint32_t &scan)
{
    Position before;
    if (!hardware.position(before) || !inBlank(before,open,guard))
        return FlipResult::Wait;
    const SourceView front = view(owner,owner.front());
    const SourceView next = view(owner,target);
    if (!owner.validIssueScan(before.scan) || !hardware.routeQualified() ||
        !sameView(hardware.sourceView(),front) || hardware.flush())
        return FlipResult::Uncertain;

    const bool interrupts = hardware.disableInterrupts();
    const uint32_t checkedScan = hardware.scan();
    const uint32_t checkedLine = hardware.line();
    if (checkedScan != before.scan || checkedLine < before.line ||
        !inBlank({checkedScan,checkedLine,before.end},open,guard)) {
        hardware.restoreInterrupts(interrupts);
        return FlipResult::Wait;
    }

    if (front.pitch != next.pitch)
        hardware.writePitch(next.pitch);
    if (front.sourceXY != next.sourceXY)
        hardware.writeSourceXY(next.sourceXY);
    hardware.writeSource(next.address);
    hardware.publishStores();
    hardware.writeFlush();
    hardware.completeStores();
    const uint32_t flush = hardware.flush();
    const SourceView installed = hardware.sourceView();
    hardware.restoreInterrupts(interrupts);

    Position after;
    if (flush != 1 || !sameView(installed,next) || !hardware.position(after) ||
        after.scan != before.scan || after.line < checkedLine || after.line >= before.end ||
        after.end != before.end)
        return FlipResult::Uncertain;
    scan = before.scan;
    return FlipResult::Submitted;
}

// Before a swap both software ownership and hardware blanking must agree.
// Publishing and recording the result share the framebuffer owner lock.
template <class Hardware>
FlipResult publishFrame(DirectScanout &owner, const Lease &lease, Hardware &hardware,
                        uint32_t open, uint32_t guard)
{
    if (!owner.canFlip(lease))
        return FlipResult::Wait;
    uint32_t scan;
    const FlipResult result = issueBlankingFlip(hardware,owner,lease.slot,open,guard,scan);
    if (result == FlipResult::Uncertain ||
        (result == FlipResult::Submitted && !owner.recordFlip(lease,scan))) {
        owner.quarantine();
        return FlipResult::Uncertain;
    }
    return result;
}

template <class Hardware>
FlipResult restoreOriginal(DirectScanout &owner, Hardware &hardware, uint32_t open, uint32_t guard)
{
    if (!owner.canRestoreOriginal())
        return FlipResult::Wait;
    uint32_t scan;
    const FlipResult result = issueBlankingFlip(hardware,owner,Slot::Original,open,guard,scan);
    if (result == FlipResult::Uncertain ||
        (result == FlipResult::Submitted && !owner.recordOriginalRestore(scan))) {
        owner.quarantine();
        return FlipResult::Uncertain;
    }
    return result;
}

} // namespace gauguin::scanout

#endif
