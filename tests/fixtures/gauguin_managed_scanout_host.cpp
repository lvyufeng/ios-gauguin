#include "LinearScanout411.h"

#include <cassert>
#include <cstddef>
#include <cstring>
#include <initializer_list>

using boolean_t = bool;
using ppnum_t = uint32_t;
using IOByteCount = size_t;
constexpr unsigned PAGE_SHIFT = 14;
constexpr auto kernel_task = 1;
constexpr unsigned kIODirectionInOut = 3;
constexpr unsigned kIOMemoryPhysicallyContiguous = 0x10;
constexpr unsigned kIOMapWriteCombineCache = 0x80;
constexpr unsigned kIOMemoryMapperNone = 0;
constexpr unsigned allocationOptions =
    kIODirectionInOut | kIOMemoryPhysicallyContiguous | kIOMapWriteCombineCache;

enum Fault { None, FirstAllocation, SecondAllocation, ShortLength, Fragmented, OutOfRange,
             MisalignedVA, BadManagedPage, BadCPUTranslation, Alias };
static Fault fault;
static unsigned allocated, released;
static bool profileMatches;

static bool PE_parse_boot_argn(const char *key, void *value, size_t bytes)
{
    assert(bytes == sizeof(uint32_t));
    uint32_t setting;
    if (!strcmp(key,"swp")) setting = profileMatches ? 4 : 3;
    else if (!strcmp(key,"sweetfb_stats")) setting = 9;
    else if (!strcmp(key,"sweetfb_hz")) setting = 60;
    else if (!strcmp(key,"sweetnvt")) setting = 0;
    else if (!strcmp(key,"gpf")) setting = 5;
    else return false;
    *static_cast<uint32_t *>(value) = setting;
    return true;
}

struct IOBufferMemoryDescriptor {
    unsigned index;

    static IOBufferMemoryDescriptor *inTaskWithPhysicalMask(int task, unsigned options,
        uint64_t bytes, uint64_t mask)
    {
        assert(task == kernel_task && options == allocationOptions);
        assert(bytes == F411_SLOT_BYTES && mask == 0xffffffff);
        const unsigned index = ++allocated;
        if ((fault == FirstAllocation && index == 1) || (fault == SecondAllocation && index == 2))
            return nullptr;
        return new IOBufferMemoryDescriptor{index};
    }

    uint64_t getLength() const { return fault == ShortLength && index == 2 ? F411_SLOT_BYTES-1 : F411_SLOT_BYTES; }

    uint64_t getPhysicalSegment(unsigned offset, IOByteCount *contiguous, unsigned mapper) const
    {
        assert(offset == 0 && mapper == kIOMemoryMapperNone);
        *contiguous = fault == Fragmented && index == 2 ? F411_PAGE_BYTES : F411_SLOT_BYTES;
        if (fault == OutOfRange && index == 2)
            return UINT64_C(0x100000000);
        return base(index);
    }

    static uint64_t base(unsigned index)
    {
        return index == 1 || fault == Alias ? 0xb0000000 : 0xb1000000;
    }

    void *getBytesNoCopy() const
    {
        return reinterpret_cast<void *>(UINT64_C(0x200000000) + base(index) +
            (fault == MisalignedVA && index == 2 ? 1 : 0));
    }

    void release() { ++released; delete this; }
};

extern "C" boolean_t pmap_valid_page(ppnum_t page)
{
    return fault != BadManagedPage || page != ((UINT64_C(0xb1000000) + F411_PAGE_BYTES) >> PAGE_SHIFT);
}

static uint64_t ml_vtophys(uintptr_t va)
{
    const uint64_t pa = va-UINT64_C(0x200000000);
    return fault == BadCPUTranslation && pa == 0xb1004000 ? pa+F411_PAGE_BYTES : pa;
}

#define OSSafeReleaseNULL(p) do { if (p) { (p)->release(); (p) = nullptr; } } while (false)
#define IOLog(...) do {} while (false)

#include "managed_impl.inc"

int main()
{
    uint32_t pa[2] = {11,12};
    uintptr_t va[2] = {13,14};
    prepare411Buffers();
    assert(!sweet_fb411_buffers(pa,va) && allocated == 0 && !f411Attempted);

    profileMatches = true;
    for (Fault boundary : {FirstAllocation,SecondAllocation,ShortLength,Fragmented,OutOfRange,
                           MisalignedVA,BadManagedPage,BadCPUTranslation,Alias}) {
        fault = boundary;
        allocated = released = 0;
        f411Attempted = false;
        prepare411Buffers();
        assert(!sweet_fb411_buffers(pa,va));
        assert(pa[0] == 11 && pa[1] == 12 && va[0] == 13 && va[1] == 14);
        assert(!f411Owner[0] && !f411Owner[1]);
        const unsigned expectedRelease = boundary == FirstAllocation ? 0 : boundary == SecondAllocation ? 1 : 2;
        assert(released == expectedRelease);
        assert(f411Attempted);
    }

    fault = None;
    f411Attempted = false;
    allocated = released = 0;
    prepare411Buffers();
    assert(sweet_fb411_buffers(pa,va) && allocated == 2 && released == 0);
    assert(pa[0] == 0xb0000000 && pa[1] == 0xb1000000 && va[0] == 0x2b0000000 && va[1] == 0x2b1000000);
    prepare411Buffers();
    assert(allocated == 2 && released == 0);
    for (auto &owner : f411Owner)
        OSSafeReleaseNULL(owner);
    assert(released == 2);
}
