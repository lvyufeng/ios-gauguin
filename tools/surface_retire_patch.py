"""Proposed source-only repair of the reproduced expired-weak surface race."""
HEADER='include/hakios-metal/command.hpp'
SOURCE='src/command.cpp'
def transform(name,raw):
    original=raw;changes=[]
    def replace(a,b):
        nonlocal raw
        assert raw.count(a)==1,(name,a);raw=raw.replace(a,b);changes.append((a,b))
    if name==HEADER:
        replace('private:\n    std::unique_ptr<Bo> bo_;',
                'private:\n    friend std::shared_ptr<Buffer> surfaceBuffer(Gpu&, uint32_t, SurfaceInfo*, std::string*);\n    std::unique_ptr<Bo> bo_;')
    else:
        assert name==SOURCE
        replace('#include <cstring>\n','#include <cstring>\n#include <cstdio>\n')
        a=raw.index('namespace {\n// the live surface buffers');z=raw.index('// --- CommandBuffer',a)
        old=raw[a:z]
        new='''namespace {
// A dying Buffer still owns its kernel handle after its weak_ptr expires.
// Imports wait for that deleter to close it before asking the kernel again.
std::mutex gSurfaceLock;
std::condition_variable gSurfaceChanged;
std::map<std::pair<const Gpu*, uint32_t>, std::weak_ptr<Buffer>> gSurfaceBuffers;
uint32_t gSurfaceRetireWaits = 0;
bool gSurfaceRetireActive = false;
}  // namespace

std::shared_ptr<Buffer> surfaceBuffer(Gpu& gpu, uint32_t surfaceId, SurfaceInfo* info, std::string* why) {
    std::unique_lock<std::mutex> g(gSurfaceLock);
    if (!gSurfaceRetireActive) {
        gSurfaceRetireActive = true;
        std::fprintf(stderr, "GAUGUIN SURF334: enabled close-before-reimport=1\\n");
    }
    for (;;) {
        int error = 0;
        std::unique_ptr<Bo> bo = gpu.surfaceBo(surfaceId, info, &error);
        if (bo == nullptr) {
            *why = "IOSurface " + std::to_string(surfaceId) + ": the driver gave no buffer for it: " +
                   (error == ENOENT ? std::string("no such surface") : error == ENOTSUP ? std::string("a surface around a program's own memory is not one the GPU takes") : strerror(error));
            return nullptr;
        }
        const auto key = std::make_pair(static_cast<const Gpu*>(&gpu), bo->handle());
        auto live = gSurfaceBuffers.find(key);
        if (live != gSurfaceBuffers.end()) {
            if (std::shared_ptr<Buffer> b = live->second.lock()) {
                gpu.disown(std::move(bo));
                return b;
            }
            // Dropping this duplicate must not close the dying owner's handle.
            // The saved weak owner also distinguishes a later handle generation.
            const std::weak_ptr<Buffer> dying = live->second;
            gpu.disown(std::move(bo));
            uint32_t diagnostic = 0;
            if (gSurfaceRetireWaits < 64) {
                diagnostic = ++gSurfaceRetireWaits;
                std::fprintf(stderr, "GAUGUIN SURF334: wait seq=%u handle=%u surface=%u\\n", diagnostic, key.second, surfaceId);
            } else if (gSurfaceRetireWaits == 64) {
                ++gSurfaceRetireWaits;
                std::fprintf(stderr, "GAUGUIN SURF334: limit=64 coverage=incomplete\\n");
            }
            gSurfaceChanged.wait(g, [&] {
                auto current = gSurfaceBuffers.find(key);
                return current == gSurfaceBuffers.end() ||
                       dying.owner_before(current->second) || current->second.owner_before(dying);
            });
            if (diagnostic != 0)
                std::fprintf(stderr, "GAUGUIN SURF334: retired seq=%u handle=%u surface=%u\\n", diagnostic, key.second, surfaceId);
            continue;
        }
        const uint64_t length = bo->size();
        // Allocate both control block and map node before publishing ownership.
        // A construction failure deletes an empty Buffer without re-locking this
        // mutex; the local unique_ptr then closes the sole unpublished Bo.
        std::shared_ptr<Buffer> b(new Buffer(nullptr, length), [key](Buffer* x) {
            if (x->bo_ == nullptr) { delete x; return; }
            std::lock_guard<std::mutex> g(gSurfaceLock);
            auto it = gSurfaceBuffers.find(key);
            if (it != gSurfaceBuffers.end() && it->second.expired()) gSurfaceBuffers.erase(it);
            delete x;  // close before another importer can acquire the lock
            gSurfaceChanged.notify_all();
        });
        gSurfaceBuffers.emplace(key, b);
        b->bo_ = std::move(bo);  // noexcept, after all fallible publication steps
        return b;
    }
}

'''
        replace(old,new)
    undone=raw
    for a,b in reversed(changes):
        assert undone.count(b)==1;undone=undone.replace(b,a)
    assert undone==original
    return raw
