#include "../../graphics/gauguin-display/DirectScanoutFlip.h"

#include <algorithm>
#include <cassert>
#include <vector>

using namespace gauguin::scanout;

constexpr uint32_t crop = (18u << 16) | 22u;
constexpr Layout layout{kRenderWidth,kRenderHeight,kRenderPitch,kBGRA,0,22,18,true};
constexpr BufferProof first{0xb0000000,0x50000000,kSlotBytes,true,true,true};
constexpr BufferProof second{0xb1000000,0x51000000,kSlotBytes,true,true,true};

static void layoutAndMapping()
{
    static_assert(kSlotBytes == 11239424 && kOriginalPitch == 4320);
    static_assert(validLayout(layout) && validBuffer(first) && validBuffer(second));

    auto badLayout = layout;
    badLayout.pitch = kOriginalPitch;
    assert(!validLayout(badLayout));
    badLayout = layout;
    badLayout.height = kPanelHeight;
    assert(!validLayout(badLayout));
    badLayout = layout;
    badLayout.linear = false;
    assert(!validLayout(badLayout));
    badLayout = layout;
    badLayout.planes = 2;
    assert(!validLayout(badLayout));
    badLayout = layout;
    badLayout.pixelFormat = 0x52474241;
    assert(!validLayout(badLayout));
    badLayout = layout;
    badLayout.sourceX = 0;
    assert(!validLayout(badLayout));

    auto shortSlot = first;
    shortSlot.contiguousBytes = 0x9e4000;
    assert(!validBuffer(shortSlot));
    shortSlot.contiguousBytes = uint64_t(kRenderPitch)*kPanelHeight;
    assert(!validBuffer(shortSlot));
    auto uncertainDMA = first;
    uncertainDMA.dpuReadVerified = false;
    assert(!validBuffer(uncertainDMA));
    uncertainDMA = first;
    uncertainDMA.gpuMappingMatches = false;
    assert(!validBuffer(uncertainDMA));
    uncertainDMA = first;
    uncertainDMA.managedPages = false;
    assert(!validBuffer(uncertainDMA));
    auto address = first;
    address.physical = kOriginalBase;
    assert(!validBuffer(address));
    address.physical = kDPUAddressEnd - kPageBytes;
    assert(!validBuffer(address));
    address = first;
    address.gpuAddress = kGPUAddressEnd - kPageBytes;
    assert(!validBuffer(address));
    address = first;
    address.physical += 1;
    assert(!validBuffer(address));

    DirectScanout scanout;
    assert(!scanout.enable(layout,first,first));
    address = second;
    address.gpuAddress = first.gpuAddress+kPageBytes;
    assert(!scanout.enable(layout,first,address));
    address = second;
    address.physical = first.physical+kPageBytes;
    assert(!scanout.enable(layout,first,address));
    assert(scanout.phase() == Phase::Disabled);
    assert(scanout.enable(layout,first,second));
    assert(!scanout.enable(layout,first,second));
}

static Lease readyFrame(DirectScanout &scanout, uint64_t generation, uint32_t fence)
{
    Lease lease;
    assert(scanout.acquire(generation,lease));
    assert(scanout.recordIssue(lease,fence));
    assert(!scanout.canFlip(lease));
    assert(scanout.recordEOP(lease,fence));
    assert(!scanout.canFlip(lease));
    assert(scanout.recordVisibility(lease,fence));
    assert(scanout.canFlip(lease));
    return lease;
}

static void alternatingAndRestoring()
{
    DirectScanout scanout;
    Lease lease;
    assert(!scanout.acquire(1,lease));
    assert(scanout.enable(layout,first,second));
    assert(!scanout.acquire(0,lease));
    assert(scanout.acquire(1,lease));
    assert(lease.slot == Slot::First && scanout.front() == Slot::Original);
    assert(!scanout.acquire(2,lease));
    assert(lease.generation == 1 && lease.slot == Slot::First);
    assert(!scanout.recordIssue({1,Slot::Second},17));
    assert(!scanout.recordIssue(lease,0));
    assert(scanout.recordIssue(lease,17));
    assert(!scanout.cancelBeforeIssue(lease));
    assert(!scanout.recordVisibility(lease,17));
    assert(!scanout.recordEOP(lease,18));
    assert(scanout.recordEOP(lease,17));
    assert(!scanout.recordVisibility({2,Slot::First},17));
    assert(!scanout.recordFlip(lease,UINT32_MAX));
    assert(scanout.recordVisibility(lease,17));
    assert(scanout.recordFlip(lease,UINT32_MAX));

    assert(!scanout.confirmLatch({UINT32_MAX,first.physical,kRenderPitch,crop,false,true}));
    assert(!scanout.confirmLatch({0,first.physical,kRenderPitch,crop,true,true}));
    assert(!scanout.acquire(2,lease));
    assert(!scanout.disable());
    assert(scanout.front() == Slot::Original);
    assert(scanout.confirmLatch({0,first.physical,kRenderPitch,crop,false,true}));
    assert(scanout.front() == Slot::First);
    assert(!scanout.disable());
    assert(!scanout.canFlip(lease));

    assert(scanout.acquire(2,lease) && lease.slot == Slot::Second);
    assert(!scanout.recordIssue(lease,17));
    assert(scanout.cancelBeforeIssue(lease));
    assert(!scanout.acquire(2,lease));
    lease = readyFrame(scanout,3,18);
    assert(lease.slot == Slot::Second);
    assert(scanout.recordFlip(lease,1));
    assert(scanout.front() == Slot::First);
    assert(!scanout.acquire(4,lease));
    assert(!scanout.recordOriginalRestore(2));
    assert(scanout.confirmLatch({2,second.physical,kRenderPitch,crop,false,true}));

    assert(scanout.front() == Slot::Second && scanout.canRestoreOriginal());
    assert(scanout.sourceFor(Slot::Original) == kOriginalBase);
    assert(scanout.pitchFor(Slot::Original) == kOriginalPitch);
    assert(scanout.recordOriginalRestore(4));
    assert(!scanout.disable());
    assert(!scanout.acquire(4,lease));
    assert(scanout.confirmLatch({5,kOriginalBase,kOriginalPitch,0,false,true}));
    assert(scanout.front() == Slot::Original && scanout.disable());
}

static void quarantineAndTimeouts()
{
    auto expectQuarantine = [](Latch latch) {
        DirectScanout scanout;
        assert(scanout.enable(layout,first,second));
        auto lease = readyFrame(scanout,1,1);
        assert(scanout.recordFlip(lease,10));
        assert(!scanout.confirmLatch(latch));
        assert(scanout.phase() == Phase::Quarantined);
        assert(!scanout.confirmLatch({11,first.physical,kRenderPitch,crop,false,true}));
        assert(!scanout.acquire(2,lease));
        assert(!scanout.disable() && !scanout.canRestoreOriginal());
    };
    expectQuarantine({11,second.physical,kRenderPitch,crop,false,true});
    expectQuarantine({11,first.physical,kOriginalPitch,0,false,true});
    expectQuarantine({12,first.physical,kRenderPitch,crop,false,true});
    expectQuarantine({11,first.physical,kRenderPitch,crop,false,false});
    expectQuarantine({11,first.physical,kRenderPitch,0,false,true});

    DirectScanout scanout;
    assert(scanout.enable(layout,first,second));
    Lease lease;
    assert(scanout.acquire(1,lease));
    assert(scanout.recordIssue(lease,1));
    scanout.quarantine();
    assert(!scanout.recordEOP(lease,1) && !scanout.disable());
    assert(!scanout.acquire(2,lease));

    DirectScanout pending;
    assert(pending.enable(layout,first,second));
    lease = readyFrame(pending,1,1);
    assert(pending.recordFlip(lease,100));
    assert(!pending.confirmLatch({101,first.physical,kRenderPitch,crop,true,true}));
    pending.quarantine();
    assert(!pending.confirmLatch({101,first.physical,kRenderPitch,crop,false,true}));
    assert(!pending.disable());
}

struct FakeRegisters {
    static constexpr uint32_t kOpen = 2440;
    static constexpr uint32_t kGuard = 192;
    Position before{100,4000,4878};
    Position after{100,4003,4878};
    SourceView live{kOriginalBase,kOriginalPitch,0};
    uint32_t checkedScan = 100, checkedLine = 4001, flushWord = 0;
    bool route = true, disabled = false, positionReadable = true, wrongSourceWrite = false;
    unsigned reads = 0, writes = 0, pitchWrites = 0, xyWrites = 0, order = 0;

    bool position(Position &result)
    {
        result = reads++ == 0 ? before : after;
        return positionReadable;
    }
    bool routeQualified() const { return route; }
    SourceView sourceView() const { return live; }
    uint32_t flush() const { return flushWord; }
    bool disableInterrupts() { assert(!disabled); disabled = true; return true; }
    void restoreInterrupts(bool beforeDisabled) { assert(disabled && beforeDisabled); disabled = false; }
    uint32_t scan() const { assert(disabled); return checkedScan; }
    uint32_t line() const { assert(disabled); return checkedLine; }
    void writePitch(uint32_t pitch)
    {
        assert(disabled && order == 0);
        live.pitch = pitch;
        ++pitchWrites;
    }
    void writeSourceXY(uint32_t xy)
    {
        assert(disabled && order == 0);
        live.sourceXY = xy;
        ++xyWrites;
    }
    void writeSource(uint64_t source)
    {
        assert(disabled && order++ == 0);
        live.address = wrongSourceWrite ? kOriginalBase : source;
        ++writes;
    }
    void publishStores() { assert(disabled && order++ == 1); }
    void writeFlush() { assert(disabled && order++ == 2); flushWord = 1; }
    void completeStores() { assert(disabled && order++ == 3); }
    void useScan(uint32_t scan) { before.scan = after.scan = checkedScan = scan; }
};

static void atomicViewAndFlip()
{
    constexpr uint32_t open = FakeRegisters::kOpen, guard = FakeRegisters::kGuard;
    DirectScanout owner;
    assert(owner.enable(layout,first,second));
    auto lease = readyFrame(owner,1,101);
    FakeRegisters registers;
    registers.checkedLine = registers.before.end-guard+1;
    assert(publishFrame(owner,lease,registers,open,guard) == FlipResult::Wait);
    assert(owner.canFlip(lease) && registers.writes == 0 && !registers.disabled);

    registers = FakeRegisters{};
    assert(publishFrame(owner,lease,registers,open,guard) == FlipResult::Submitted);
    assert(registers.pitchWrites == 1 && registers.xyWrites == 1 && registers.writes == 1);
    assert(sameView(registers.live,view(owner,Slot::First)));
    assert(owner.phase() == Phase::FlipPending);
    assert(owner.confirmLatch({101,first.physical,kRenderPitch,crop,false,true}));

    lease = readyFrame(owner,2,102);
    registers = FakeRegisters{};
    registers.live = view(owner,Slot::First);
    registers.useScan(101);
    assert(publishFrame(owner,lease,registers,open,guard) == FlipResult::Submitted);
    assert(registers.pitchWrites == 0 && registers.xyWrites == 0 && registers.writes == 1);
    assert(owner.confirmLatch({102,second.physical,kRenderPitch,crop,false,true}));

    registers = FakeRegisters{};
    registers.live = view(owner,Slot::Second);
    registers.useScan(102);
    assert(restoreOriginal(owner,registers,open,guard) == FlipResult::Submitted);
    assert(registers.pitchWrites == 1 && registers.xyWrites == 1 && registers.writes == 1);
    assert(sameView(registers.live,view(owner,Slot::Original)));
    assert(owner.confirmLatch({103,kOriginalBase,kOriginalPitch,0,false,true}));
    assert(owner.disable());

    assert(owner.enable(layout,first,second));
    lease = readyFrame(owner,3,103);
    registers = FakeRegisters{};
    registers.wrongSourceWrite = true;
    registers.useScan(103);
    assert(publishFrame(owner,lease,registers,open,guard) == FlipResult::Uncertain);
    assert(owner.phase() == Phase::Quarantined && registers.writes == 1);
    assert(!owner.disable() && !registers.disabled);
}

static uint32_t pixelAt(uint32_t x, uint32_t y)
{
    return 0xff000000u | ((x & 255) << 16) | ((y & 255) << 8) | ((x ^ y) & 255);
}

static void centeredViewPreservesPanelPixels()
{
    constexpr uint32_t renderRowPixels = kRenderPitch/kPixelBytes;
    std::vector<uint32_t> rendered(kSlotBytes/kPixelBytes,0x5a5aa5a5);
    for (uint32_t y = 0; y < kRenderHeight; ++y) {
        for (uint32_t x = 0; x < kRenderWidth; ++x)
            rendered[y*renderRowPixels+x] = pixelAt(x,y);
    }

    std::vector<uint32_t> tight(kPanelWidth*kPanelHeight);
    for (uint32_t y = 0; y < kPanelHeight; ++y) {
        for (uint32_t x = 0; x < kPanelWidth; ++x)
            tight[y*kPanelWidth+x] = pixelAt(x+kCropX,y+kCropY);
    }

    const auto matches = [&](uint32_t pitch, uint32_t sourceXY) {
        const uint32_t rowPixels = pitch/kPixelBytes;
        const uint32_t sourceX = sourceXY & 0xffff, sourceY = sourceXY >> 16;
        for (uint32_t y = 0; y < kPanelHeight; ++y) {
            auto visible = rendered.begin() + (sourceY+y)*rowPixels + sourceX;
            if (!std::equal(visible,visible+kPanelWidth,tight.begin()+y*kPanelWidth))
                return false;
        }
        return true;
    };
    assert(matches(kRenderPitch,crop));
    assert(!matches(kRenderPitch,0));
    assert(!matches(kOriginalPitch,crop));
    assert(!matches(kRenderPitch,crop+1));
}

int main()
{
    centeredViewPreservesPanelPixels();
    atomicViewAndFlip();
    layoutAndMapping();
    alternatingAndRestoring();
    quarantineAndTimeouts();
}
