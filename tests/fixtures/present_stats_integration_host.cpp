// Host integration harness for the actual SweetFramebuffer present/vsync paths.
// The Python driver injects the candidate stats header and extracted methods.
#include <array>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>
#include <set>
#include <string>
#include <vector>

#define GAUGUIN 1
#define SWEET 1
#define SWEET_FB_SWAP_REC_SIZE 0x46c
#define SWEET_FB_LAYERS 4
#define SWEET_FB_NOTIFY_TYPES 8
#define SWEET_FB_NOTIFY_VSYNC 5

@STATS_HEADER@

static unsigned checks;
static void check(bool ok, const char *what, int line)
{
    ++checks;
    if (!ok) {
        std::fprintf(stderr, "FAIL line %d: %s\n", line, what);
        std::abort();
    }
}
#define CHECK(expr) check((expr), #expr, __LINE__)

static std::vector<std::string> events;
static uint64_t clockCalls;
static std::deque<uint64_t> clockPlan;
static uint64_t nextTick = 1000;
static uint64_t tickStep = 1;

static void event(const std::string &kind, const std::string &detail)
{
    events.push_back(kind + " " + detail);
}

static uint64_t mach_absolute_time(void)
{
    ++clockCalls;
    if (!clockPlan.empty()) {
        uint64_t value = clockPlan.front();
        clockPlan.pop_front();
        return value;
    }
    uint64_t value = nextTick;
    nextTick += tickStep;
    return value;
}

static void absolutetime_to_nanoseconds(uint64_t ticks, uint64_t *ns)
{
    *ns = ticks * UINT64_C(1000000);
}

struct IOLock {
    std::mutex mutex;
};
static void IOLockLock(IOLock *lock) { lock->mutex.lock(); }
static void IOLockUnlock(IOLock *lock) { lock->mutex.unlock(); }

static void IOLog(const char *format, ...)
{
    char text[1024];
    va_list args;
    va_start(args, format);
    int n = std::vsnprintf(text, sizeof(text), format, args);
    va_end(args);
    CHECK(n >= 0 && static_cast<size_t>(n) < sizeof(text));
    if (std::strncmp(text, "SWEET FB STATS:", 15) == 0)
        event("STATS", text);
}

struct PEClockFrequencyInfo {
    uint64_t timebase_frequency_hz;
};
static PEClockFrequencyInfo gPEClockFrequencyInfo = {24000000};

struct Memory {
    size_t length;
    size_t getLength() const { return length; }
};

struct SweetSurface {
    uint32_t id = 0;
    uint32_t width = 0, height = 0, bytesPerRow = 0, offset = 0;
    uint32_t pixelFormat = 0;
    uint16_t bytesPerElement = 4;
    uint8_t elementWidth = 1, elementHeight = 1;
    Memory *memory = nullptr;
    uintptr_t base = 0;
    unsigned refs = 1;

    uintptr_t kernelAddress() { return base; }
    void retain()
    {
        CHECK(refs > 0);
        ++refs;
        event("SURF+", std::to_string(id) + " refs=" + std::to_string(refs));
    }
    void release()
    {
        CHECK(refs > 0);
        --refs;
        event("SURF-", std::to_string(id) + " refs=" + std::to_string(refs));
    }
};

struct IOMobileFramebufferUserClient {
    unsigned name = 0;
    void notify(uint32_t type, const uint64_t *, unsigned)
    {
        event("NOTIFY", std::to_string(name) + " type=" + std::to_string(type));
    }
    bool hasNotification(uint32_t) const { return false; }
};

struct OSObject {};

struct OSArray {
    std::vector<IOMobileFramebufferUserClient *> items;
    unsigned getCount() const { return static_cast<unsigned>(items.size()); }
    IOMobileFramebufferUserClient *getObject(unsigned index) const
    {
        CHECK(index < items.size());
        return items[index];
    }
};

struct IOTimerEventSource {};

struct SweetPresentClock {
    uint64_t callbacks = 0, skippedBeats = 0, copies = 0, nextBeat = 0, nextCopy = 0;
};

struct sweet_fb_frame {
    uint8_t record[SWEET_FB_SWAP_REC_SIZE];
    SweetSurface *surfaces[SWEET_FB_LAYERS];
    IOMobileFramebufferUserClient *owner;
};

class AppleCLCD {
public:
    IOLock *fLock = nullptr;
    OSArray *fClients = nullptr;
    uint64_t fVsyncCount = 0;
    uint64_t fPhys = 0;
    uint32_t fWidth = 0, fHeight = 0, fRowBytes = 0;
    uint32_t fLogicalW = 0, fLogicalH = 0;
    int32_t fOffX = 0, fOffY = 0;
    uintptr_t fPixels = 0;
    void *fMap = nullptr;
    SweetSurface *fSurface = nullptr;
    uint32_t fSwapID = 0;
    uint64_t fLastSet = 0;
    bool fConsolePaused = false;
    uint8_t fPending[SWEET_FB_SWAP_REC_SIZE] = {};
    bool fDirty = false;
    bool fHoldPresent = false, fHeldActive = false;
    bool fPhasePresent = false;
    sweet_fb_frame fHeldPending = {};
    uint64_t fHeldSubmitted = 0, fHeldReplaced = 0, fHeldConsumed = 0;
    uint64_t fHeldRetired = 0, fHeldCanceled = 0, fHeldRejected = 0;
    uint64_t fHeldRejectReasons[8] = {};
    SweetPresentClock fPresentClock;
    bool fPresentStatsEnabled = false;
    SweetPresentSample *fPresentSample = nullptr;
    SweetPresentStats fPresentStats = {};
    uint32_t fFlushTicks = 1;
    bool fPowerOff = false;
    uint32_t fFadeStep = 0;

    void armVsync(IOTimerEventSource *);
    void present(const uint8_t *rec, SweetSurface *const *held = nullptr);
    void presentClockCopiedLocked(void);
    bool presentClockTickLocked(uint64_t now, uint64_t *elapsed, bool *copy);
    bool takeHeldFrameLocked(sweet_fb_frame *frame);
    void cancelHeldFrameLocked(sweet_fb_frame *frame, IOMobileFramebufferUserClient *owner);
    void finishHeldFrame(sweet_fb_frame *frame);
    static void vsyncFired(OSObject *owner, IOTimerEventSource *sender);
};

static int sweet_console_muted;
static uint32_t sweet_fb_swaps_logged;
static uint32_t sweet_fb_corner_logged;
static uint32_t sweet_fb_clip_logged;
static uint32_t sweet_fb_swap_count;
static std::vector<SweetSurface *> surfaceTable;
static std::set<uint32_t> refusedIds;
static uint32_t nextGpuToken = 1;

static uint32_t get32(const uint8_t *p, uint32_t off);
static SweetSurface *sweet_fb_present_surface(const uint8_t *rec, SweetSurface *const *held, uint32_t layer);

extern "C" uint32_t GauguinGPUSurfaceBegin(SweetSurface *surface)
{
    uint32_t token = refusedIds.count(surface->id) != 0 ? 0 : nextGpuToken++;
    event("GPU+", std::to_string(surface->id) + " token=" + std::to_string(token));
    return token;
}
extern "C" void GauguinGPUSurfaceEnd(uint32_t token)
{
    event("GPU-", std::to_string(token));
}

class SweetSurfaceGPURead {
    uint32_t token;
public:
    explicit SweetSurfaceGPURead(SweetSurface *surface)
        : token(GauguinGPUSurfaceBegin(surface)) {}
    ~SweetSurfaceGPURead() { GauguinGPUSurfaceEnd(token); }
    bool valid() const { return token != 0; }
    SweetSurfaceGPURead(const SweetSurfaceGPURead &) = delete;
    SweetSurfaceGPURead &operator=(const SweetSurfaceGPURead &) = delete;
};

static void *sweet_copy_bytes_line(void *dst, const void *src, size_t size, int line)
{
    event("MEMCPY", std::to_string(size) + " line=" + std::to_string(line));
    return __builtin_memcpy(dst, src, size);
}
static bool PE_parse_boot_argn(const char *, void *, uint32_t) { return false; }
static void proc_selfname(char *buf, int size)
{
    if (size > 0) buf[0] = '\0';
}
static int sweet_surface_sample(uint32_t, uint32_t *, uint32_t *, uint32_t *) { return 0; }
static void *IOMallocData(size_t size) { event("ALLOC", std::to_string(size)); return std::malloc(size); }
static void IOFreeData(void *pointer, size_t size)
{
    event("FREE", std::to_string(size));
    std::free(pointer);
}

static void sweet_fb_frame_release(sweet_fb_frame *frame)
{
    for (uint32_t layer = 0; layer < SWEET_FB_LAYERS; ++layer) {
        if (frame->surfaces[layer] != nullptr) {
            frame->surfaces[layer]->release();
            frame->surfaces[layer] = nullptr;
        }
    }
    frame->owner = nullptr;
}

static SweetSurface *foundSurface(uint32_t id)
{
    for (SweetSurface *surface : surfaceTable)
        if (surface->id == id) return surface;
    return nullptr;
}

static SweetSurface *sweet_surface_copy(uint32_t id)
{
    SweetSurface *surface = foundSurface(id);
    if (surface != nullptr) surface->retain();
    return surface;
}

static SweetSurface *sweet_fb_present_surface(const uint8_t *rec, SweetSurface *const *held, uint32_t layer)
{
    if (layer >= SWEET_FB_LAYERS) return nullptr;
    uint32_t id = get32(rec, 0x54 + 4 * layer);
    if (!(get32(rec, 0x104) & (1u << layer)) || id == 0) return nullptr;
    if (held == nullptr) return sweet_surface_copy(id);
    SweetSurface *surface = held[layer];
    if (surface == nullptr || surface->id != id) return nullptr;
    surface->retain();
    return surface;
}

#define OSSafeReleaseNULL(pointer) do { if ((pointer) != nullptr) { (pointer)->release(); (pointer) = nullptr; } } while (0)

#define memcpy(dst, src, size) sweet_copy_bytes_line((dst), (src), (size), __LINE__)
@GET32@
@PRESENT_METHOD@
@VSYNC_METHOD@
#undef memcpy

void AppleCLCD::armVsync(IOTimerEventSource *) { event("ARM", "vsync"); }
void AppleCLCD::presentClockCopiedLocked(void) { event("CLOCKCOPIED", ""); }
bool AppleCLCD::presentClockTickLocked(uint64_t, uint64_t *elapsed, bool *)
{
    *elapsed = 1;
    return true;
}
bool AppleCLCD::takeHeldFrameLocked(sweet_fb_frame *frame)
{
    if (!fHoldPresent || !fDirty || fHeldPending.owner == nullptr) return false;
    std::memcpy(frame->record, fHeldPending.record, SWEET_FB_SWAP_REC_SIZE);
    for (uint32_t layer = 0; layer < SWEET_FB_LAYERS; ++layer) {
        frame->surfaces[layer] = fHeldPending.surfaces[layer];
        fHeldPending.surfaces[layer] = nullptr;
    }
    frame->owner = fHeldPending.owner;
    fHeldPending.owner = nullptr;
    fDirty = false;
    event("TAKE", "held");
    return true;
}
void AppleCLCD::cancelHeldFrameLocked(sweet_fb_frame *frame, IOMobileFramebufferUserClient *)
{
    std::memset(frame, 0, sizeof(*frame));
}
void AppleCLCD::finishHeldFrame(sweet_fb_frame *frame)
{
    event("FINISH", frame->owner != nullptr ? "owned" : "empty");
    sweet_fb_frame_release(frame);
}

static std::array<uint8_t, SWEET_FB_SWAP_REC_SIZE> makeRecord(uint32_t id0 = 0, uint32_t id1 = 0,
    uint32_t id2 = 0, uint32_t id3 = 0, uint32_t mask = 0)
{
    std::array<uint8_t, SWEET_FB_SWAP_REC_SIZE> record = {};
    record.fill(0);
    uint32_t ids[4] = {id0, id1, id2, id3};
    for (uint32_t layer = 0; layer < 4; ++layer) {
        std::memcpy(record.data() + 0x54 + 4 * layer, &ids[layer], 4);
        int32_t rect[4] = {0, 0, 0, 0};
        std::memcpy(record.data() + 0x64 + 16 * layer, rect, 16);
        std::memcpy(record.data() + 0xc4 + 16 * layer, rect, 16);
    }
    std::memcpy(record.data() + 0x104, &mask, 4);
    return record;
}

static void setRect(std::array<uint8_t, SWEET_FB_SWAP_REC_SIZE> &record, uint32_t layer,
    int32_t sx, int32_t sy, int32_t dx, int32_t dy, int32_t w, int32_t h)
{
    int32_t source[4] = {sx, sy, w, h};
    int32_t dest[4] = {dx, dy, w, h};
    std::memcpy(record.data() + 0x64 + 16 * layer, source, 16);
    std::memcpy(record.data() + 0xc4 + 16 * layer, dest, 16);
}

struct SurfaceFixture {
    SweetSurface surface;
    Memory memory;
    std::vector<uint32_t> pixels;
};
static void setupSurface(SurfaceFixture &fixture, uint32_t id, uint32_t width, uint32_t height,
    uint32_t stridePixels, uint32_t baseValue)
{
    fixture.pixels.assign(static_cast<size_t>(stridePixels) * height + 8, baseValue);
    fixture.surface = SweetSurface{};
    fixture.surface.id = id;
    fixture.surface.width = width;
    fixture.surface.height = height;
    fixture.surface.bytesPerRow = stridePixels * 4;
    fixture.surface.base = reinterpret_cast<uintptr_t>(fixture.pixels.data());
    fixture.memory.length = fixture.pixels.size() * 4;
    fixture.surface.memory = &fixture.memory;
    fixture.surface.refs = 1;
    surfaceTable.push_back(&fixture.surface);
}

static void resetWorld()
{
    events.clear();
    clockCalls = 0;
    clockPlan.clear();
    nextTick = 1000;
    tickStep = 1;
    refusedIds.clear();
    nextGpuToken = 1;
    sweet_fb_swaps_logged = 0;
    sweet_fb_corner_logged = 0;
    sweet_fb_clip_logged = 0;
    surfaceTable.clear();
}

static void clearSurfaces()
{
    surfaceTable.clear();
}

static bool isTraceEvent(const std::string &text)
{
    return text.rfind("GPU", 0) == 0 || text.rfind("SURF", 0) == 0 ||
        text.rfind("MEMCPY", 0) == 0 || text.rfind("TAKE", 0) == 0 ||
        text.rfind("FINISH", 0) == 0 || text.rfind("FREE", 0) == 0 ||
        text.rfind("ALLOC", 0) == 0;
}
static std::vector<std::string> traceOnly()
{
    std::vector<std::string> result;
    for (const std::string &text : events)
        if (isTraceEvent(text)) result.push_back(text);
    return result;
}
static size_t eventIndex(const std::string &prefix)
{
    for (size_t i = 0; i < events.size(); ++i)
        if (events[i].rfind(prefix, 0) == 0) return i;
    return events.size();
}
static unsigned countPrefix(const std::string &prefix)
{
    unsigned result = 0;
    for (const std::string &text : events)
        if (text.rfind(prefix, 0) == 0) ++result;
    return result;
}

static void recordSample(SweetPresentStats &stats, const SweetPresentSample &sample)
{
    uint64_t waitNs = 0, copyNs = 0;
    if (sample.timingValid) {
        absolutetime_to_nanoseconds(sample.waitTicks, &waitNs);
        absolutetime_to_nanoseconds(sample.copyTicks, &copyNs);
    }
    CHECK(sweet_present_stats_record(&stats, &sample, waitNs, copyNs));
}

static void fillPanel(AppleCLCD &fb, std::vector<uint32_t> &panel, uint32_t width, uint32_t height)
{
    panel.assign(static_cast<size_t>(width) * height, 0xdeadbeefu);
    fb.fWidth = width;
    fb.fHeight = height;
    fb.fRowBytes = width * 4;
    fb.fPixels = reinterpret_cast<uintptr_t>(panel.data());
}

static void checkNoStats(const SweetPresentStats &stats)
{
    SweetPresentStats empty = {};
    CHECK(std::memcmp(&stats, &empty, sizeof(stats)) == 0);
}

int main()
{
    // Direct actual present(): multi-row copy with two layers, then a clipped
    // layer, a GPU refusal and non-copying layers.
    {
        resetWorld();
        AppleCLCD fb;
        IOLock lock;
        OSArray clients;
        fb.fLock = &lock;
        fb.fClients = &clients;
        std::vector<uint32_t> panel;
        fillPanel(fb, panel, 10, 9);
        SurfaceFixture a, b;
        setupSurface(a, 1, 6, 5, 7, 0x11111111u);
        setupSurface(b, 2, 5, 5, 5, 0x22222222u);
        for (uint32_t y = 0; y < 5; ++y)
            for (uint32_t x = 0; x < 6; ++x)
                a.pixels[y * 7 + x] = 0x1000u + y * 16 + x;
        for (uint32_t y = 0; y < 5; ++y)
            for (uint32_t x = 0; x < 5; ++x)
                b.pixels[y * 5 + x] = 0x2000u + y * 16 + x;
        auto rec = makeRecord(1, 2, 0, 0, 3);
        setRect(rec, 0, 1, 1, 2, 2, 3, 4);
        setRect(rec, 1, 0, 0, 8, 0, 4, 2);  // clipped to panel width 2
        SweetPresentSample sample = {};
        sample.timingValid = true;
        fb.fPresentSample = &sample;
        clockCalls = 0;
        fb.present(rec.data());
        fb.fPresentSample = nullptr;
        CHECK(clockCalls == 8); // two guards + two copies, begin/end each
        CHECK(sample.gpuGuards == 2);
        CHECK(sample.gpuRefusals == 0);
        CHECK(sample.copiedBytes == (3 * 4 + 2 * 2) * 4);
        CHECK(sample.copiedLayers == 2);
        CHECK(sample.timingValid);
        unsigned begin = countPrefix("GPU+"), end = countPrefix("GPU-");
        CHECK(begin == 2 && end == 2);
        CHECK(countPrefix("MEMCPY 12 line") == 4 && countPrefix("MEMCPY 8 line") == 2);
        size_t gpuBegin = eventIndex("GPU+"), gpuEnd = eventIndex("GPU-");
        size_t firstCopy = eventIndex("MEMCPY 12 line");
        size_t surfaceHold = eventIndex("SURF+"), surfaceDrop = eventIndex("SURF-");
        CHECK(surfaceHold < gpuBegin && gpuBegin < firstCopy && firstCopy < gpuEnd);
        CHECK(surfaceDrop < gpuEnd);
        for (uint32_t y = 0; y < 4; ++y)
            for (uint32_t x = 0; x < 3; ++x)
                CHECK(panel[(2 + y) * 10 + (2 + x)] == a.pixels[(1 + y) * 7 + (1 + x)]);
        for (uint32_t y = 0; y < 2; ++y)
            for (uint32_t x = 0; x < 2; ++x)
                CHECK(panel[y * 10 + 8 + x] == b.pixels[y * 5 + x]);
        CHECK(panel[0] == 0xdeadbeefu);
        SweetPresentStats stats = {};
        recordSample(stats, sample);
        CHECK(stats.attempts == 1 && stats.copied == 1 && stats.zeroBytes == 0);
        CHECK(stats.bytes == 64 && stats.layers == 2);
        CHECK(stats.gpuGuards == 2 && stats.gpuRefusals == 0);
        CHECK(stats.waitSamples == 1 && stats.copySamples == 1);
        CHECK(stats.invalidTime == 0);
        CHECK(stats.waitHistogram[3] == 1 && stats.copyHistogram[3] == 1);
        clearSurfaces();
    }
    // Tracing disabled: identical bytes and identical GPU/surface ordering,
    // without reading the clock from the instrumentation.
    {
        resetWorld();
        AppleCLCD fb;
        IOLock lock;
        OSArray clients;
        fb.fLock = &lock;
        fb.fClients = &clients;
        std::vector<uint32_t> panel;
        fillPanel(fb, panel, 8, 6);
        SurfaceFixture a;
        setupSurface(a, 7, 4, 3, 4, 0x77777777u);
        for (uint32_t i = 0; i < 12; ++i) a.pixels[i] = 0x7000u + i;
        auto rec = makeRecord(7, 0, 0, 0, 1);
        setRect(rec, 0, 0, 0, 1, 1, 4, 3);

        clockCalls = 0;
        events.clear();
        fb.present(rec.data());
        auto disabledTrace = traceOnly();
        auto disabledPanel = panel;
        CHECK(clockCalls == 0);
        checkNoStats(fb.fPresentStats);

        SweetPresentSample sample = {};
        sample.timingValid = true;
        fb.fPresentSample = &sample;
        clockCalls = 0;
        events.clear();
        nextGpuToken = 1;
        fb.present(rec.data());
        fb.fPresentSample = nullptr;
        CHECK(clockCalls == 4);
        CHECK(traceOnly() == disabledTrace);
        CHECK(panel == disabledPanel);
        CHECK(sample.copiedBytes == 48 && sample.copiedLayers == 1);
        clearSurfaces();
    }
    // GPU guard refusal and non-copying layers are accounted, not copied.
    {
        resetWorld();
        AppleCLCD fb;
        IOLock lock;
        OSArray clients;
        fb.fLock = &lock;
        fb.fClients = &clients;
        std::vector<uint32_t> panel;
        fillPanel(fb, panel, 8, 6);
        SurfaceFixture a, b, panelSurface;
        setupSurface(a, 10, 4, 4, 4, 0xaaaaaaaa);
        setupSurface(b, 11, 4, 4, 4, 0xbbbbbbbb);
        setupSurface(panelSurface, 12, 4, 4, 4, 0x12121212);
        fb.fSurface = &panelSurface.surface;
        refusedIds.insert(10);
        auto rec = makeRecord(10, 11, 12, 13, 0xf);
        setRect(rec, 0, 0, 0, 0, 0, 4, 4);
        setRect(rec, 1, 0, 0, 2, 2, 2, 2);
        setRect(rec, 2, 0, 0, 0, 3, 4, 3);
        setRect(rec, 3, 0, 0, 0, 0, 4, 4); // missing surface
        SweetPresentSample sample = {};
        sample.timingValid = true;
        fb.fPresentSample = &sample;
        fb.present(rec.data());
        fb.fPresentSample = nullptr;
        CHECK(sample.gpuGuards == 2); // refused layer and valid layer; panel/missing resolve before the guard
        CHECK(sample.gpuRefusals == 1);
        CHECK(sample.copiedLayers == 1);
        CHECK(sample.copiedBytes == 2 * 2 * 4);
        CHECK(panel[2 * 8 + 2] == 0xbbbbbbbbu);
        CHECK(panel[0] == 0xdeadbeefu);
        SweetPresentStats stats = {};
        recordSample(stats, sample);
        CHECK(stats.copied == 1 && stats.zeroBytes == 0);
        CHECK(stats.gpuGuards == 2 && stats.gpuRefusals == 1);
        CHECK(stats.bytes == 16 && stats.layers == 1);
        clearSurfaces();
    }
    // Invalid layers that resolve to a surface still guard it, but a bad
    // element size, memory bound or bpe refuses the copy.
    {
        resetWorld();
        AppleCLCD fb;
        IOLock lock;
        OSArray clients;
        fb.fLock = &lock;
        fb.fClients = &clients;
        std::vector<uint32_t> panel;
        fillPanel(fb, panel, 8, 6);
        SurfaceFixture shortMemory, wideElement, narrowBpe;
        setupSurface(shortMemory, 40, 4, 4, 4, 0x40404040u);
        shortMemory.memory.length = 16;
        setupSurface(wideElement, 41, 4, 4, 4, 0x41414141u);
        wideElement.surface.elementWidth = 2;
        setupSurface(narrowBpe, 42, 4, 4, 4, 0x42424242u);
        narrowBpe.surface.bytesPerElement = 2;
        auto rec = makeRecord(40, 41, 42, 0, 0x7);
        for (uint32_t layer = 0; layer < 3; ++layer)
            setRect(rec, layer, 0, 0, 0, layer, 4, 4);
        SweetPresentSample sample = {};
        sample.timingValid = true;
        fb.fPresentSample = &sample;
        fb.present(rec.data());
        fb.fPresentSample = nullptr;
        CHECK(sample.gpuGuards == 3);
        CHECK(sample.gpuRefusals == 0);
        CHECK(sample.copiedLayers == 0 && sample.copiedBytes == 0);
        for (uint32_t value : panel) CHECK(value == 0xdeadbeefu);
        SweetPresentStats stats = {};
        recordSample(stats, sample);
        CHECK(stats.attempts == 1 && stats.zeroBytes == 1 && stats.copied == 0);
        CHECK(stats.bytes == 0 && stats.layers == 0);
        CHECK(stats.waitSamples == 1 && stats.copySamples == 0);
        clearSurfaces();
    }
    // Zero-work (no enabled layers) and invalid clock are honest: bytes and
    // attempts are counted, but no timing histogram is entered.
    {
        resetWorld();
        AppleCLCD fb;
        IOLock lock;
        OSArray clients;
        fb.fLock = &lock;
        fb.fClients = &clients;
        std::vector<uint32_t> panel;
        fillPanel(fb, panel, 4, 4);
        auto rec = makeRecord(0, 0, 0, 0, 1);
        SweetPresentSample sample = {};
        sample.timingValid = true;
        fb.fPresentSample = &sample;
        clockCalls = 0;
        fb.present(rec.data());
        fb.fPresentSample = nullptr;
        CHECK(clockCalls == 0);
        CHECK(sample.gpuGuards == 0 && sample.copiedBytes == 0 && sample.copiedLayers == 0);
        SweetPresentStats stats = {};
        recordSample(stats, sample);
        CHECK(stats.attempts == 1 && stats.zeroBytes == 1 && stats.copied == 0);
        CHECK(stats.invalidTime == 0 && stats.bytes == 0 && stats.layers == 0);
        CHECK(stats.waitSamples == 0 && stats.copySamples == 0);
        for (unsigned i = 0; i < 8; ++i)
            CHECK(stats.waitHistogram[i] == 0 && stats.copyHistogram[i] == 0);

        SurfaceFixture a;
        setupSurface(a, 20, 4, 4, 4, 0x20202020u);
        auto timed = makeRecord(20, 0, 0, 0, 1);
        setRect(timed, 0, 0, 0, 0, 0, 4, 4);
        SweetPresentSample invalid = {};
        invalid.timingValid = true;
        fb.fPresentSample = &invalid;
        clockPlan = {500, 499}; // guard end precedes begin
        clockCalls = 0;
        fb.present(timed.data());
        fb.fPresentSample = nullptr;
        CHECK(clockCalls == 2); // copy timing is skipped after the guard fails
        CHECK(!invalid.timingValid);
        CHECK(invalid.copiedBytes == 64 && invalid.copiedLayers == 1);
        SweetPresentStats invalidStats = {};
        recordSample(invalidStats, invalid);
        CHECK(invalidStats.attempts == 1 && invalidStats.invalidTime == 1);
        CHECK(invalidStats.copied == 1 && invalidStats.zeroBytes == 0);
        CHECK(invalidStats.bytes == 64 && invalidStats.layers == 1);
        CHECK(invalidStats.waitSamples == 0 && invalidStats.copySamples == 0);
        for (unsigned i = 0; i < 8; ++i)
            CHECK(invalidStats.waitHistogram[i] == 0 && invalidStats.copyHistogram[i] == 0);
        clearSurfaces();
    }
    // Actual vsync tail: stats collection after finishHeldFrame / IOFreeData,
    // and after every surface reference has been dropped.
    for (bool held : {false, true}) {
        std::vector<std::vector<std::string>> traces;
        std::vector<uint32_t> savedPanel;
        for (bool enabled : {false, true}) {
            resetWorld();
            AppleCLCD fb;
            IOLock lock;
            OSArray clients;
            IOMobileFramebufferUserClient client{9};
            clients.items.push_back(&client);
            fb.fLock = &lock;
            fb.fClients = &clients;
            fb.fHoldPresent = held;
            fb.fDirty = true;
            std::vector<uint32_t> panel;
            fillPanel(fb, panel, 9, 5);
            SurfaceFixture a, b;
            setupSurface(a, 30, 4, 3, 4, 0x30303030u);
            setupSurface(b, 31, 3, 2, 3, 0x31313131u);
            for (uint32_t i = 0; i < 12; ++i) a.pixels[i] = 0x3000u + i;
            for (uint32_t i = 0; i < 6; ++i) b.pixels[i] = 0x3100u + i;
            auto rec = makeRecord(30, 31, 0, 0, 3);
            setRect(rec, 0, 1, 1, 0, 0, 2, 2);
            setRect(rec, 1, 0, 0, 6, 3, 3, 2);
            if (held) {
                std::memcpy(fb.fPending, rec.data(), SWEET_FB_SWAP_REC_SIZE);
                std::memcpy(fb.fHeldPending.record, rec.data(), SWEET_FB_SWAP_REC_SIZE);
                fb.fHeldPending.owner = &client;
                fb.fHeldPending.surfaces[0] = &a.surface;
                fb.fHeldPending.surfaces[1] = &b.surface;
                a.surface.refs = 2;
                b.surface.refs = 2;
            } else {
                std::memcpy(fb.fPending, rec.data(), SWEET_FB_SWAP_REC_SIZE);
            }
            fb.fPresentStatsEnabled = enabled;
            IOTimerEventSource timer;
            events.clear();
            AppleCLCD::vsyncFired(reinterpret_cast<OSObject *>(&fb), &timer);
            CHECK(fb.fPresentSample == nullptr);
            CHECK(fb.fPresentStats.attempts == (enabled ? 1u : 0u));
            CHECK(fb.fPresentStats.copied == (enabled ? 1u : 0u));
            CHECK(fb.fPresentStats.bytes == (enabled ? 40u : 0u));
            CHECK(fb.fPresentStats.layers == (enabled ? 2u : 0u));
            CHECK(fb.fPresentStats.gpuGuards == (enabled ? 2u : 0u));
            CHECK(fb.fPresentStats.gpuRefusals == 0);
            CHECK(a.surface.refs == 1 && b.surface.refs == 1);
            auto trace = traceOnly();
            if (enabled) {
                size_t finishOrFree = held ? eventIndex("FINISH") : eventIndex("FREE");
                size_t stats = eventIndex("STATS");
                CHECK(finishOrFree < events.size() && stats < events.size() && finishOrFree < stats);
                for (size_t i = stats + 1; i < events.size(); ++i)
                    CHECK(events[i].rfind("SURF", 0) != 0);
                CHECK(countPrefix("GPU+") == 2 && countPrefix("GPU-") == 2);
                CHECK(countPrefix("MEMCPY 12 line") == 2 && countPrefix("MEMCPY 8 line") == 2);
                bool sawStatsLog = false;
                for (const std::string &line : events) {
                    if (line.rfind("STATS", 0) == 0) {
                        sawStatsLog = true;
                        CHECK(line.find("CPU, not scanout") != std::string::npos);
                    }
                }
                CHECK(sawStatsLog);
            } else {
                CHECK(eventIndex("STATS") == events.size());
                checkNoStats(fb.fPresentStats);
            }
            traces.push_back(trace);
            if (!enabled) savedPanel = panel;
            else CHECK(panel == savedPanel);
            clearSurfaces();
        }
        CHECK(traces.size() == 2 && traces[0] == traces[1]);
    }
    std::printf("PASS present-stats integration checks=%u; actual present/vsync source with host surfaces, "
        "GPU guard, pixels, clock and locks; CPU-side bytes only, not kernel timing, scanout, FPS or panel\n",
        checks);
    return 0;
}
