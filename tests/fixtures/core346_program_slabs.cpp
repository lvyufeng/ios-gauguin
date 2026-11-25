#include <array>
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <vector>

#include "fixtures/end_only.hpp"
#include "hakios-metal/command.hpp"
#include "hakios-metal/fake_gpu.hpp"

using namespace hakios::metal;

namespace {
constexpr uint64_t slabBytes = 256 * 1024;
constexpr uint64_t half = slabBytes / 2;
const uint32_t groups[3] = {1, 1, 1};

struct Recording {
    std::vector<uint32_t> words;
    Kernel kernel = kernels::end_only;
    explicit Recording(size_t bytes, uint32_t mark) : words(bytes / sizeof(uint32_t)) {
        memcpy(words.data(), kernel.words, sizeof(kernels::end_only_words));
        words.back() = mark;
        kernel.words = words.data();
        kernel.numWords = static_cast<uint32_t>(words.size());
    }
};

std::shared_ptr<CommandBuffer> record(CommandQueue& queue, const Kernel& program) {
    auto cb = queue.commandBuffer();
    assert(cb->dispatch(program, groups, nullptr, std::vector<Binding>{}));
    return cb;
}

void wait(const std::shared_ptr<CommandBuffer>& cb) {
    cb->waitUntilCompleted();
    assert(cb->status() == CommandBuffer::kCompleted);
}

std::shared_ptr<Buffer> readProgram(uint64_t address, uint64_t offset, size_t bytes, uint32_t mark) {
    uint64_t found = UINT64_MAX;
    auto page = bufferAt(address, &found);
    assert(page && found == offset && page->length() >= offset + bytes);
    const auto* words = static_cast<const uint32_t*>(page->contents()) + offset/sizeof(uint32_t);
    assert(words[1] == kernels::end_only_words[1] && words[bytes/sizeof(uint32_t)-1] == mark);
    return page;
}

void reuseAndRollover() {
    auto transport = std::make_unique<FakeGpu>(true, 20000);
    auto* fake = transport.get();
    Gpu gpu(std::move(transport));
    std::string why;
    auto queue = CommandQueue::make(gpu, &why);
    assert(queue);
    Recording first(half, 1), other(half, 3);
    auto a = record(*queue, first.kernel);
    // The pointer is unchanged. The next command buffer must use its new
    // words while the recorded first command buffer owns the previous slice.
    first.words.back() = 2;
    unsigned before = fake->liveBuffers();
    auto b = record(*queue, first.kernel);
    assert(fake->liveBuffers() == before + 1);  // only the draw/dispatch table BO
    before = fake->liveBuffers();
    auto c = record(*queue, other.kernel);
    assert(fake->liveBuffers() == before + 2);  // next program page and table

    a->commit();
    wait(a);
    uint64_t address = fake->stats().lastDispatch.program;
    assert((address & 255u) == 0);
    auto oldPage = readProgram(address, 0, half, 1);
    assert(oldPage->length() == slabBytes);
    assert(readProgram(address+half, half, half, 2) == oldPage);
    oldPage.reset();

    std::vector<unsigned> order;
    b->addCompletedHandler([&](CommandBuffer&) { order.push_back(2); });
    c->addCompletedHandler([&](CommandBuffer&) { order.push_back(3); });
    b->commit();
    c->commit();
    wait(b);
    wait(c);
    assert((order == std::vector<unsigned>{2,3}));
    uint64_t next = fake->stats().lastDispatch.program;
    assert(next != address && next != address+half);
    assert(readProgram(next, 0, half, 3)->length() == slabBytes);
    auto repeated = record(*queue, other.kernel);
    repeated->commit();
    wait(repeated);
    assert(fake->stats().lastDispatch.program == next);

    // External callers keep the original standalone-buffer contract.
    auto standalone = queue->programBuffer(other.kernel, &why);
    assert(standalone && standalone->length() == half && standalone->gpuAddress() != next);
    assert(memcmp(standalone->contents(), other.words.data(), half) == 0);
    Recording large(half + 256, 4);
    auto largeCall = record(*queue, large.kernel);
    largeCall->commit();
    wait(largeCall);
    assert(readProgram(fake->stats().lastDispatch.program, 0, half+256, 4)->length() == half+256);
    assert(fake->stats().faults == 0);
}

class RejectFirstSlab : public FakeGpu {
public:
    bool rejected = false;
    int call(uint32_t request, void* data, size_t length) override {
        if (!rejected && request == kGemNew && length == sizeof(MsmGemNew) &&
            static_cast<MsmGemNew*>(data)->size == slabBytes) {
            rejected = true;
            return ENOMEM;
        }
        return FakeGpu::call(request, data, length);
    }
};

void smallAllocationFallback() {
    auto transport = std::make_unique<RejectFirstSlab>();
    auto* fake = transport.get();
    Gpu gpu(std::move(transport));
    std::string why;
    auto queue = CommandQueue::make(gpu, &why);
    assert(queue);
    Recording program(256, 7);
    auto cb = record(*queue, program.kernel);
    cb->commit();
    wait(cb);
    assert(fake->rejected && !fake->stats().faults);
    assert(readProgram(fake->stats().lastDispatch.program, 0, 256, 7)->length() == 256);
}
}  // namespace

int main() {
    reuseAndRollover();
    smallAllocationFallback();
    std::puts("PASS: immutable program slabs, pointer reuse, rollover, lifetime, FIFO and standalone fallback");
}
