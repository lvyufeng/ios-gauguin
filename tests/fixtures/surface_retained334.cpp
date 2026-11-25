// Exercise real Texture/CommandBuffer retention with an asynchronous fake GPU.
#include "hakios-metal/command.hpp"
#include "hakios-metal/fake_gpu.hpp"
#include "hakios-metal/texture.hpp"
#include <atomic>
#include <cassert>
#include <cerrno>
#include <cstdio>

using namespace hakios::metal;

class CompletionGpu final : public FakeGpu {
public:
    explicit CompletionGpu(bool reject) : FakeGpu(true), reject_(reject) {}
    int call(uint32_t request, void* data, size_t bytes) override {
        if (reject_ && request == kGemSubmit) return EIO;
        return FakeGpu::call(request, data, bytes);
    }
private:
    bool reject_;
};

static void check(bool reject) {
    auto transport = std::make_unique<CompletionGpu>(reject);
    auto* fake = transport.get();
    Gpu gpu(std::move(transport));
    std::string why;
    auto queue = CommandQueue::make(gpu, &why);
    assert(queue);
    fake->addSurface(7, 64, 64, 256, 0x42475241);
    TextureDesc desc;
    desc.format = PixelFormat::kBGRA8Unorm;
    desc.width = desc.height = 64;
    desc.usage = kTextureUsageRenderTarget | kTextureUsageRead;
    auto texture = Texture::wrapSurface(gpu, 7, desc, &why);
    assert(texture);
    std::weak_ptr<const Buffer> lifetime = texture->buffer();
    const auto handle = texture->buffer()->bo().handle();
    const auto address = texture->buffer()->gpuAddress();
    auto cb = queue->commandBuffer();
    RenderPass pass;
    pass.color0 = texture.get();
    pass.load = LoadAction::kClear;
    pass.clearColor[3] = 1.0;
    assert(cb->clear(pass));
    std::atomic<unsigned> callbacks{0};
    cb->addCompletedHandler([&](CommandBuffer& completed) {
        assert(completed.status() == (reject ? CommandBuffer::kError : CommandBuffer::kCompleted));
        auto kept = lifetime.lock();
        assert(kept && kept->bo().handle() == handle);
        auto imported = Texture::wrapSurface(gpu, 7, desc, &why);
        assert(imported && imported->buffer() == kept);
        ++callbacks;
    });
    texture.reset();
    pass.color0 = nullptr;
    assert(!lifetime.expired());  // The recorded command owns the surface now.
    fake->pause();
    cb->commit();
    if (!reject) {
        assert(!lifetime.expired());  // Pending GPU work must retain it too.
        auto imported = Texture::wrapSurface(gpu, 7, desc, &why);
        assert(imported && imported->buffer()->bo().handle() == handle);
        assert(imported->buffer() == lifetime.lock());
    }
    fake->resume();
    cb->waitUntilCompleted();
    assert(callbacks == 1 && lifetime.expired());
    assert(fake->memory(address, 4).empty());
    auto fresh = Texture::wrapSurface(gpu, 7, desc, &why);
    assert(fresh && fresh->buffer()->bo().handle() != handle);
    fresh.reset();
    cb.reset();
    queue.reset();
    assert(fake->liveBuffers() == 0);
    std::printf("PASS surface retention: %s, pending ownership, callback reimport, final release\n",
                reject ? "submission error" : "successful completion");
}

int main() {
    check(false);
    check(true);
}
