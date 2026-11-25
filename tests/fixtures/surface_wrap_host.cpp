/* Only allocation, VM wiring and publication are mocked. The wrapper and
 * release order below come verbatim from the production kernel source. */
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <algorithm>

using IOReturn = int;
using IOByteCount = uint64_t;
using SInt64 = int64_t;
using task_t = uintptr_t;
constexpr IOReturn kIOReturnSuccess = 0, kIOReturnBadArgument = 1,
    kIOReturnNoMemory = 2, kIOReturnVMError = 3, kIOReturnNoResources = 4;
constexpr unsigned kIODirectionInOut = 3, kIOMemoryThreadSafe = 0x100000,
    kIOMapDefaultCache = 0, kIOMapWriteCombineCache = 2;
constexpr uint32_t SWEET_SURFACE_RESULT_SIZE = 0xa68,
    SWEET_SURFACE_MAX_DIM = 16384, SWEET_SURFACE_MAX_ALLOC = 256u << 20;
constexpr uint64_t SWEET_SURFACE_WIRED_MAX = 1536ull << 20, PAGE_MASK = 16383;
static uint64_t sweet_surface_wired;
static uint32_t sweet_surface_creates_logged;
static uint64_t round_page(uint64_t n) { return (n + PAGE_MASK) & ~PAGE_MASK; }
static SInt64 OSAddAtomic64(SInt64 n, volatile SInt64 *p)
{ return __atomic_fetch_add(p, n, __ATOMIC_SEQ_CST); }
static void proc_selfname(char *p, size_t n) { std::snprintf(p, n, "fixture"); }
static void IOLog(const char *, ...) {}
#define OSSafeReleaseNULL(p) do { if (p) { (p)->release(); (p) = nullptr; } } while (0)

static bool failSurface, failDescriptor, failPrepare, failPublish, failReturn;
static unsigned activeSurfaces, activeDescriptors, activeMaps, allocated,
    prepared, completed, published, returned;
static uintptr_t lastAddress;
static uint64_t lastLength;
static unsigned lastCache, mapCalls;
static bool mapLocked, failMap;
static int *sweet_surface_lock;
static void IOLockLock(int *) { assert(!mapLocked); mapLocked = true; }
static void IOLockUnlock(int *) { assert(mapLocked); mapLocked = false; }
#define OSDynamicCast(type, p) dynamic_cast<type *>(p)

struct OSObject {
    unsigned refs = 1;
    virtual ~OSObject() = default;
    virtual void free() {}
    void retain() { ++refs; }
    void release() { assert(refs); if (!--refs) { free(); delete this; } }
};
struct Mapping;
struct IOMemoryDescriptor : OSObject {
    uint64_t address = 0, length = 0;
    unsigned pins = 0;
    IOMemoryDescriptor() { ++activeDescriptors; }
    ~IOMemoryDescriptor() override { assert(!pins); --activeDescriptors; }
    static IOMemoryDescriptor *withAddressRange(uint64_t a, uint64_t n,
                                               unsigned options, task_t task) {
        ++allocated; lastAddress = a; lastLength = n;
        assert(options == (kIODirectionInOut | kIOMemoryThreadSafe) && task == 42);
        if (failDescriptor) return nullptr;
        auto *m = new IOMemoryDescriptor; m->address = a; m->length = n; return m;
    }
    IOReturn prepare() { ++prepared; if (failPrepare) return kIOReturnVMError; ++pins; return 0; }
    IOReturn complete() { assert(pins && !activeMaps); --pins; ++completed; return 0; }
    Mapping *map(unsigned);
};
struct IOBufferMemoryDescriptor : IOMemoryDescriptor {
    void *getBytesNoCopy() { return reinterpret_cast<void *>(address); }
};
struct Mapping : OSObject {
    Mapping() { ++activeMaps; }
    ~Mapping() override { --activeMaps; }
    uint64_t getVirtualAddress() { return 0x12340000; }
};
Mapping *IOMemoryDescriptor::map(unsigned cache) {
    assert(mapLocked); ++mapCalls; lastCache = cache;
    return failMap ? nullptr : new Mapping;
}
struct SweetSurface : OSObject {
    uint32_t id = 0, width = 0, height = 0, pixelFormat = 0,
        bytesPerRow = 0, allocSize = 0, wiredSize = 0;
    uint16_t bytesPerElement = 0;
    uint8_t elementWidth = 0, elementHeight = 0;
    unsigned mapCache = 0;
    bool memoryPrepared = false;
    IOMemoryDescriptor *memory = nullptr, *state = nullptr;
    Mapping *kernelMap = nullptr;
    SweetSurface() { ++activeSurfaces; }
    ~SweetSurface() override { --activeSurfaces; }
    void free() override;
    uintptr_t kernelAddress();
};
static SweetSurface *table;
static SweetSurface *sweet_surface_alloc() {
    if (failSurface) return nullptr;
    auto *s = new SweetSurface; s->state = new IOMemoryDescriptor; return s;
}
static bool sweet_surface_publish(SweetSurface *s) {
    ++published;
    if (failPublish) return false;
    assert(!table && s->memory && s->memoryPrepared && s->memory->pins == 1);
    s->id = 9; s->retain(); table = s; return true;
}
static void dropTable() { auto *s = table; table = nullptr; if (s) s->release(); }
struct StructureDescriptor {
    const void *bytes;
    IOByteCount length;
    bool shortRead = false;
    IOByteCount getLength() { return length; }
    IOByteCount readBytes(IOByteCount offset, void *out, IOByteCount n) {
        assert(!offset && n <= length);
        n -= shortRead ? 1 : 0; std::memcpy(out, bytes, n); return n;
    }
};
struct IOExternalMethodArguments {
    unsigned scalarInputCount = 0, scalarOutputCount = 0;
    const void *structureInput = nullptr;
    uint32_t structureInputSize = 0, structureOutputSize = SWEET_SURFACE_RESULT_SIZE;
    void *structureOutput = nullptr;
    StructureDescriptor *structureInputDescriptor = nullptr, *structureOutputDescriptor = nullptr;
};
struct IOSurfaceRootUserClient {
    task_t fTask = 42;
    IOReturn wrapImage(IOExternalMethodArguments *);
    IOReturn returnSurface(SweetSurface *s, IOExternalMethodArguments *) {
        ++returned;
        assert(s == table && s->memoryPrepared && s->memory->pins == 1 && s->state);
        if (failReturn) { dropTable(); return kIOReturnVMError; }
        return kIOReturnSuccess;
    }
};

@METHODS@

struct Wire {
    uint64_t address;
    uint32_t width, height, format, bpe, row, size;
};
static_assert(sizeof(Wire) == 32);
static unsigned assertions;
static void check(bool good) { ++assertions; assert(good); }

int main() {
    IOSurfaceRootUserClient client;
    alignas(16384) uint8_t pixels[32768];
    for (size_t i = 0; i < sizeof(pixels); ++i) pixels[i] = static_cast<uint8_t>(i * 17 + 3);
    uint8_t original[sizeof(pixels)]; std::memcpy(original, pixels, sizeof(pixels));
    uint8_t output[SWEET_SURFACE_RESULT_SIZE];
    const Wire good = {reinterpret_cast<uintptr_t>(pixels), 32, 32, 0x42475241, 4, 128, 4096};
    auto args = [&](const Wire *wire) {
        IOExternalMethodArguments a; a.structureInput = wire;
        a.structureInputSize = sizeof(Wire); a.structureOutput = output; return a;
    };
    auto clear = [&]() {
        dropTable(); check(!activeSurfaces && !activeDescriptors && !activeMaps);
        check(!sweet_surface_wired); failSurface = failDescriptor = failPrepare = failPublish = failReturn = false;
        allocated = prepared = completed = published = returned = mapCalls = 0;
        failMap = false; check(!mapLocked);
    };
    auto run = [&](Wire wire, bool descriptor = false) {
        auto a = args(&wire); StructureDescriptor in{&wire, sizeof(wire), false};
        if (descriptor) { a.structureInput = nullptr; a.structureInputSize = 0; a.structureInputDescriptor = &in; }
        return client.wrapImage(&a);
    };
    check(run(good) == 0); check(table && table->id && table->state);
    check(lastAddress == good.address && lastLength == good.size);
    check(table->width == good.width && table->height == good.height && table->pixelFormat == good.format);
    check(table->bytesPerElement == 4 && table->bytesPerRow == 128 && table->allocSize == 4096);
    check(table->elementWidth == 1 && table->elementHeight == 1);
    check(sweet_surface_wired == 16384 && prepared == 1 && completed == 0);
    check(!std::memcmp(original, pixels, sizeof(pixels)));
    check(table->kernelAddress() == 0x12340000 && lastCache == kIOMapDefaultCache && mapCalls == 1);
    check(table->kernelAddress() == 0x12340000 && mapCalls == 1);
    dropTable(); check(completed == 1); clear();

    check(run(good, true) == 0); clear();
    Wire edge = good; edge.address += 16380; edge.size = 4096;
    check(run(edge) == 0); check(sweet_surface_wired == 32768); clear();
    edge = good; edge.width = edge.height = 16384; edge.bpe = 1;
    edge.row = 16384; edge.size = 256u << 20;
    check(run(edge) == 0); check(table->allocSize == SWEET_SURFACE_MAX_ALLOC); clear();

    for (unsigned field = 0; field < 15; ++field) {
        Wire bad = good;
        switch (field) {
            case 0: bad.address = 0; break;
            case 1: bad.width = 0; break;
            case 2: bad.height = 0; break;
            case 3: bad.width = 16385; break;
            case 4: bad.height = 16385; break;
            case 5: bad.bpe = 0; break;
            case 6: bad.bpe = 65; break;
            case 7: bad.row = 127; break;
            case 8: bad.size = 0; break;
            case 9: bad.size = (256u << 20) + 1; break;
            case 10: bad.size = 4095; break;
            case 11: bad.address = UINT64_MAX - 1; break;
            case 12: bad.row = UINT32_MAX; bad.height = 16384; break;
            case 13: bad.width = UINT32_MAX; bad.bpe = UINT32_MAX; break;
            case 14: bad.height = UINT32_MAX; break;
        }
        check(run(bad) == kIOReturnBadArgument); check(!allocated && !published && !returned); clear();
    }
    for (unsigned field = 0; field < 9; ++field) {
        auto a = args(&good); StructureDescriptor in{&good, sizeof(good), false};
        switch (field) {
            case 0: a.scalarInputCount = 1; break;
            case 1: a.scalarOutputCount = 1; break;
            case 2: a.structureOutputSize = SWEET_SURFACE_RESULT_SIZE - 1; break;
            case 3: a.structureOutput = nullptr; break;
            case 4: a.structureInput = nullptr; break;
            case 5: a.structureInputSize = sizeof(good) - 1; break;
            case 6: a.structureInputSize = sizeof(good) + 1; break;
            case 7: in.length--; a.structureInputDescriptor = &in; break;
            case 8: in.shortRead = true; a.structureInputDescriptor = &in; break;
        }
        check(client.wrapImage(&a) == kIOReturnBadArgument); check(!allocated && !published && !returned); clear();
    }
    failSurface = true; check(run(good) == kIOReturnNoMemory); check(!allocated); clear();
    failDescriptor = true; check(run(good) == kIOReturnNoMemory); check(!prepared && !published); clear();
    failPrepare = true; check(run(good) == kIOReturnVMError); check(prepared == 1 && !completed && !published); clear();
    failPublish = true; check(run(good) == kIOReturnNoResources); check(prepared == 1 && completed == 1 && !returned); clear();
    failReturn = true; check(run(good) == kIOReturnVMError); check(prepared == 1 && completed == 1 && returned == 1); clear();

    sweet_surface_wired = SWEET_SURFACE_WIRED_MAX;
    check(run(good) == kIOReturnNoMemory); check(sweet_surface_wired == SWEET_SURFACE_WIRED_MAX && !allocated);
    sweet_surface_wired = 0; clear();
    sweet_surface_wired = SWEET_SURFACE_WIRED_MAX - 16384;
    check(run(good) == 0); check(sweet_surface_wired == SWEET_SURFACE_WIRED_MAX);
    dropTable(); check(sweet_surface_wired == SWEET_SURFACE_WIRED_MAX - 16384);
    sweet_surface_wired = 0; clear();
    auto a = args(&good); StructureDescriptor out{output, sizeof(output), false};
    a.structureOutput = nullptr; a.structureOutputSize = 0; a.structureOutputDescriptor = &out;
    check(client.wrapImage(&a) == 0); clear();
    out.length--; check(client.wrapImage(&a) == kIOReturnBadArgument); clear();
    check(run(good) == 0); failMap = true;
    check(table->kernelAddress() == 0 && !table->kernelMap); failMap = false;
    check(table->kernelAddress() == 0x12340000 && mapCalls == 2); clear();

    // Buffer allocation and physical surfaces also use the new common free().
    auto *buffer = sweet_surface_alloc(); auto *memory = new IOBufferMemoryDescriptor;
    memory->address = 0x12345000; buffer->memory = memory;
    buffer->wiredSize = 32768; sweet_surface_wired = 32768;
    check(buffer->kernelAddress() == 0x12345000 && !mapCalls); buffer->release(); clear();
    auto *physical = sweet_surface_alloc(); physical->memory = new IOMemoryDescriptor;
    physical->mapCache = kIOMapWriteCombineCache;
    check(physical->kernelAddress() == 0x12340000 && lastCache == kIOMapWriteCombineCache);
    physical->release(); clear();
    check(!std::memcmp(original, pixels, sizeof(pixels)));
    std::printf("surface wrap: %u assertions; geometry, alias, quota and failure unwind passed\n", assertions);
}
