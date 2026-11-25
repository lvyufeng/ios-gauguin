#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstdio>

#include "gauguin_linear_scanout411.h"

using IOByteCount = uint64_t;
constexpr unsigned kIOMemoryMapperNone = 0;
constexpr unsigned kPages = F411_SLOT_BYTES / 4096;
constexpr uint32_t kPhysical[] = {0xa9000000, 0xa9000000 + F411_SLOT_BYTES};
constexpr uint64_t kVirtual[] = {0x40000000, 0x42000000};
static uint64_t leaves[2][kPages];
static volatile uint64_t *gPtes = leaves[0];
static unsigned scenario, reserves, releases, barriers, syncs, stopped;
static bool backingsReady, runtimeReady = true;

class IOMemoryDescriptor {
    unsigned slot_;
public:
    unsigned refs = 1;
    explicit IOMemoryDescriptor(unsigned slot) : slot_(slot) {}
    uint64_t getLength() const { return F411_SLOT_BYTES; }
    uint64_t getPhysicalSegment(uint64_t offset, IOByteCount *size, unsigned mode) const
    {
        assert(!mode && offset % 4096 == 0 && offset < F411_SLOT_BYTES);
        *size = F411_SLOT_BYTES - offset;
        if (scenario == 2 && slot_ == 1 && offset == 4096) return 0;
        return kPhysical[slot_] + offset;
    }
    void retain() { ++refs; }
    void release() { assert(refs > 1); --refs; }
};
static IOMemoryDescriptor descriptors[] = {IOMemoryDescriptor(0), IOMemoryDescriptor(1)};

extern "C" bool sweet_fb414_reserved_descriptors(IOMemoryDescriptor *out[2], uint32_t physical[2])
{
    if (!backingsReady) return false;
    for (unsigned slot = 0; slot < 2; ++slot) {
        out[slot] = &descriptors[slot];
        physical[slot] = kPhysical[slot];
    }
    return true;
}

static bool sweet_gpu_runtime_ready() { return runtimeReady; }
static void sweet_gpu_runtime_stop() { ++stopped; runtimeReady = false; }
static void memoryBarrier() { ++barriers; }
static void IOLog(const char *, ...) {}
static uint64_t reserveAddress(uint64_t size)
{
    assert(size == F411_SLOT_BYTES && reserves < 2);
    const unsigned slot = reserves++;
    if (scenario == 3 && slot == 1) return 0;
    return kVirtual[slot];
}
static void releaseAddress(uint64_t address, uint64_t size)
{
    assert((address == kVirtual[0] || address == kVirtual[1]) && size == F411_SLOT_BYTES);
    ++releases;
}
static volatile uint64_t *leafAt(uint64_t address)
{
    const unsigned slot = address >= kVirtual[1];
    const uint64_t offset = address - kVirtual[slot];
    assert((offset % 4096) == 0 && offset < F411_SLOT_BYTES);
    return &leaves[slot][offset / 4096];
}
static bool sweet_gpu_runtime_sync()
{
    ++syncs;
    assert(syncs <= 2 && syncs == barriers);
    for (unsigned slot = 0; slot < 2; ++slot) {
        assert(descriptors[slot].refs == 2);
        for (unsigned page = 0; page < kPages; ++page) {
            uint64_t expected = syncs == 1 ? (uint64_t(kPhysical[slot]) + page * 4096) | 0xec3 : 0;
            assert(leaves[slot][page] == expected);
        }
    }
    if (scenario == 6 && syncs == 1) leaves[1][1] = 0;
    return !(scenario == 5 && syncs == 1) && !(scenario == 7 && syncs == 2);
}

#include "gauguin_gpu_probe414.inc"

int main(int argc, char **argv)
{
    assert(argc == 2);
    scenario = static_cast<unsigned>(std::strtoul(argv[1], nullptr, 10));
    assert(scenario <= 7);
    assert(probeBootScanout414() && !reserves && !barriers); // Must await both physical latches.
    backingsReady = true;
    if (scenario == 1) {
        runtimeReady = false;
        assert(probeBootScanout414() && !reserves && !barriers);
        runtimeReady = true;
    }
    if (scenario == 4) leaves[1][4] = 0xdead;
    const bool success = probeBootScanout414();
    assert(success == (scenario < 4));

    switch (scenario) {
    case 0:
    case 1:
        assert(reserves == 2 && releases == 2 && syncs == 2 && !stopped);
        break;
    case 2: assert(!reserves && !releases && !syncs && !stopped); break;
    case 3: assert(reserves == 2 && releases == 1 && !syncs && !stopped); break;
    case 4: assert(reserves == 2 && !releases && !syncs && stopped == 1 && leaves[1][4] == 0xdead); break;
    case 5:
    case 6: assert(reserves == 2 && !releases && syncs == 1 && stopped == 1); break;
    case 7: assert(reserves == 2 && !releases && syncs == 2 && stopped == 1); break;
    }
    for (const auto &descriptor : descriptors)
        assert(descriptor.refs == (success ? 1U : 2U));
    const unsigned attempts = reserves;
    assert(probeBootScanout414() && reserves == attempts);
}
