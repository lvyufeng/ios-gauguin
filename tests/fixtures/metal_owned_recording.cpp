// Positive lifetime/ordering regressions for the a619-ownership profile only.
// Including the real C API lets tests gate its actual recorder, not a model.
// The other eleven complete core translation units are linked by the runner.
#include <chrono>
#include <cstdlib>
#include <new>
#include <stdexcept>
#include "c_api.cpp"

thread_local bool rejectAllocation = false;
void* operator new(std::size_t n) {
    if (rejectAllocation) throw std::bad_alloc();
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete[](void* p) noexcept { ::operator delete(p); }

#define CHECK(condition) do { if (!(condition)) { \
    std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); std::abort(); \
} } while (0)

namespace {
using namespace std::chrono_literals;
struct Signal {
    std::mutex mutex;
    std::condition_variable cv;
    bool value = false;
    void set() { { std::lock_guard<std::mutex> g(mutex); value = true; } cv.notify_all(); }
    bool wait(std::chrono::milliseconds timeout = 5000ms) {
        std::unique_lock<std::mutex> g(mutex);
        return cv.wait_for(g, timeout, [&] { return value; });
    }
};
struct Gate {
    Signal entered, release;
    void block() { entered.set(); CHECK(release.wait()); }
};
struct Events {
    std::atomic<unsigned> buffersMade{0}, buffersClosed{0}, queuesMade{0}, queuesClosed{0};
    std::atomic<int> failure{0};
    Signal destroyed;
};
class CountingFake final : public FakeGpu {
public:
    explicit CountingFake(Events& events) : FakeGpu(true), events_(events) {}
    ~CountingFake() override {
        CHECK(liveBuffers() == 0);
        CHECK(events_.buffersMade == events_.buffersClosed);
        CHECK(events_.queuesMade == events_.queuesClosed);
        events_.destroyed.set();
    }
    int call(uint32_t request, void* data, size_t size) override {
        if (request == kGemNew && events_.failure == 1 &&
            (static_cast<MsmGemNew*>(data)->flags & kBoGpuReadOnly)) {
            events_.failure = 0; return ENOMEM;
        }
        if (request == kGemSubmit && events_.failure == 2) {
            events_.failure = 0; return EIO;
        }
        const int result = FakeGpu::call(request, data, size);
        if (result == 0) {
            if (request == kGemNew) events_.buffersMade++;
            if (request == kGemClose) events_.buffersClosed++;
            if (request == kSubmitQueueNew) events_.queuesMade++;
            if (request == kSubmitQueueClose) events_.queuesClosed++;
        }
        return result;
    }
private:
    Events& events_;
};
hakios_metal_device* device(Events& events) { return deviceOn(std::make_unique<CountingFake>(events)); }
hakios_metal_queue* queue(hakios_metal_device* d, bool deferred = true) {
    auto* q = hakios_metal_queue_new(d); CHECK(q);
    hakios_metal_queue_set_deferred(q, deferred); return q;
}
void close(hakios_metal_queue* q, hakios_metal_device* d, Events& events) {
    hakios_metal_queue_free(q); hakios_metal_close(d);
    CHECK(events.destroyed.wait());
}
struct CallbackRelease {
    hakios_metal_queue* queue;
    hakios_metal_device* device;
    bool error, deferred;
    Signal done;
};
void releaseOwners(hakios_metal_cb* cb, void* opaque) {
    auto& context = *static_cast<CallbackRelease*>(opaque);
    CHECK(cb->cb->isCompleting());
    if (context.deferred) CHECK(!Deferrer::anyWorker());
    CHECK(hakios_metal_cb_status(cb) == (context.error ? HAKIOS_METAL_ERROR : HAKIOS_METAL_COMPLETED));
    hakios_metal_cb_wait(cb); // own callback must return without waiting for itself
    hakios_metal_cb_free(cb);
    hakios_metal_queue_free(context.queue);
    hakios_metal_close(context.device);
    context.done.set();
}
void callbackRelease(bool deferred, int failure) {
    Events events;
    auto* d = device(events); auto* q = queue(d, deferred);
    auto* cb = hakios_metal_cb_new(q); CHECK(cb);
    auto* b = hakios_metal_buffer_new(d, 64); CHECK(b);
    CHECK(hakios_metal_cb_fill(cb, b, 0, 64, 0x3c) == 0);
    hakios_metal_buffer_free(b);
    if (failure == 3) CHECK(hakios_metal_cb_refuse(cb, "recording refused") == -1);
    else events.failure = failure;
    CallbackRelease context{q, d, failure != 0, deferred, {}};
    hakios_metal_cb_commit(cb, releaseOwners, &context);
    CHECK(context.done.wait());
    CHECK(events.destroyed.wait()); // native queue joined, every BO closed
}
void wrappersFirst() {
    Events events;
    auto* d = device(events); auto* q = queue(d);
    auto* cb = hakios_metal_cb_new(q);
    auto* b = hakios_metal_buffer_new(d, 64); CHECK(b);
    CHECK(hakios_metal_cb_fill(cb, b, 0, 64, 0x42) == 0);
    hakios_metal_buffer_free(b);
    hakios_metal_queue_free(q); hakios_metal_close(d);
    CHECK(!events.destroyed.wait(40ms));
    hakios_metal_cb_commit(cb, nullptr, nullptr);
    hakios_metal_cb_free(cb); // drains and waits, despite wrapper release
    CHECK(events.destroyed.wait());
}
void externalFree(bool error) {
    Events events;
    auto* d = device(events); auto* q = queue(d);
    auto* cb = hakios_metal_cb_new(q);
    Gate callback;
    if (error) hakios_metal_cb_refuse(cb, "gated error");
    hakios_metal_cb_commit(cb, [](hakios_metal_cb*, void* opaque) { static_cast<Gate*>(opaque)->block(); }, &callback);
    CHECK(callback.entered.wait()); // native status is already terminal
    Signal freeing, freed;
    std::thread owner([&] { freeing.set(); hakios_metal_cb_free(cb); freed.set(); });
    CHECK(freeing.wait()); CHECK(!freed.wait(40ms));
    callback.release.set(); CHECK(freed.wait()); owner.join();
    close(q, d, events);
}
void differentRecorders() {
    Events events;
    auto* d = device(events); auto* a = queue(d); auto* b = queue(d);
    auto* ca = hakios_metal_cb_new(a); auto* cb = hakios_metal_cb_new(b);
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    Signal started, drained;
    ca->deferrer->post(ca, [&] { started.set(); syncOne(cb); drained.set(); });
    CHECK(started.wait()); CHECK(!drained.wait(40ms));
    blocked.release.set(); CHECK(drained.wait()); syncOne(ca); syncOne(cb);
    hakios_metal_cb_free(ca); hakios_metal_cb_free(cb);
    hakios_metal_queue_free(a); close(b, d, events);
}
void releaseOtherRecorder() {
    Events ea, eb;
    auto* da = device(ea); auto* db = device(eb);
    auto* a = queue(da); auto* b = queue(db);
    auto* ca = hakios_metal_cb_new(a); auto* cb = hakios_metal_cb_new(b);
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    hakios_metal_queue_free(b); hakios_metal_close(db);
    Signal released;
    ca->deferrer->post(ca, [&] { hakios_metal_cb_free(cb); released.set(); });
    CHECK(released.wait()); CHECK(!eb.destroyed.wait(40ms));
    blocked.release.set(); CHECK(eb.destroyed.wait());
    syncOne(ca); hakios_metal_cb_free(ca); close(a, da, ea);
}
void fifoEncoding() {
    Events events;
    auto* d = device(events); auto* q = queue(d);
    auto* cb = hakios_metal_cb_new(q); auto* other = hakios_metal_cb_new(q);
    auto* b = hakios_metal_buffer_new(d, 64); CHECK(b);
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    Signal encoded, checked;
    std::thread caller([&] { CHECK(hakios_metal_cb_fill(cb, b, 0, 64, 0x56) == 0); encoded.set(); });
    const auto deadline = std::chrono::steady_clock::now() + 5s;
    while (cb->pending.load() < 2 && std::chrono::steady_clock::now() < deadline) std::this_thread::yield();
    CHECK(cb->pending.load() == 2); CHECK(!encoded.wait(40ms));
    other->deferrer->post(other, [&] { CHECK(cb->cb->streamWords() > 0); checked.set(); });
    blocked.release.set(); CHECK(encoded.wait()); CHECK(checked.wait()); caller.join();
    hakios_metal_cb_commit(cb, nullptr, nullptr); hakios_metal_cb_wait(cb);
    CHECK(hakios_metal_cb_status(cb) == HAKIOS_METAL_COMPLETED);
    const auto* bytes = static_cast<const unsigned char*>(hakios_metal_buffer_contents(b));
    for (unsigned i = 0; i < 64; ++i) CHECK(bytes[i] == 0x56);
    hakios_metal_cb_free(cb); hakios_metal_cb_free(other); hakios_metal_buffer_free(b); close(q, d, events);
}
void modeFrozen() {
    Events events;
    auto* d = device(events); auto* q = queue(d);
    auto recorder = q->control->deferrer;
    auto* cb = hakios_metal_cb_new(q);
    hakios_metal_queue_set_deferred(q, 1); CHECK(q->control->deferrer == recorder);
    hakios_metal_queue_set_deferred(q, 0); CHECK(q->control->deferrer == recorder);
    CHECK(std::strstr(hakios_metal_error(), "fixed after the first"));
    recorder.reset(); hakios_metal_cb_free(cb); close(q, d, events);
}
void workerException() {
    Events events;
    auto* d = device(events); auto* q = queue(d); auto* cb = hakios_metal_cb_new(q);
    cb->deferrer->post(cb, [] { throw std::runtime_error("encoding failed"); });
    hakios_metal_cb_commit(cb, nullptr, nullptr); hakios_metal_cb_wait(cb);
    CHECK(cb->pending == 0); CHECK(hakios_metal_cb_status(cb) == HAKIOS_METAL_ERROR);
    CHECK(std::strcmp(hakios_metal_cb_error(cb), "deferred command recording failed") == 0);
    hakios_metal_cb_free(cb); close(q, d, events);
}
void synchronousException() {
    Events events;
    auto* d = device(events); auto* q = queue(d); auto* cb = hakios_metal_cb_new(q);
    bool caught = false;
    try { cb->deferrer->invoke(cb, []() -> int { throw std::runtime_error("synchronous encode failed"); }); }
    catch (const std::runtime_error&) { caught = true; }
    CHECK(caught);
    hakios_metal_cb_commit(cb, nullptr, nullptr); hakios_metal_cb_wait(cb);
    CHECK(hakios_metal_cb_status(cb) == HAKIOS_METAL_ERROR);
    hakios_metal_cb_free(cb); close(q, d, events);
}
void nestedCompletion() {
    Events events;
    auto* d = device(events); auto* q = queue(d, false);
    auto* outer = hakios_metal_cb_new(q); auto* inner = hakios_metal_cb_new(q);
    struct Context { hakios_metal_cb* outer; hakios_metal_cb* inner; bool nested = false; } context{outer, inner};
    hakios_metal_cb_refuse(outer, "outer"); hakios_metal_cb_refuse(inner, "inner");
    hakios_metal_cb_commit(outer, [](hakios_metal_cb*, void* opaque) {
        auto* c = static_cast<Context*>(opaque);
        hakios_metal_cb_commit(c->inner, [](hakios_metal_cb* cb, void* opaqueInner) {
            auto* c = static_cast<Context*>(opaqueInner);
            CHECK(c->outer->cb->isCompleting() && cb->cb->isCompleting());
            hakios_metal_cb_wait(c->outer); hakios_metal_cb_wait(cb);
            c->nested = true;
        }, c);
    }, &context);
    CHECK(context.nested);
    hakios_metal_cb_free(outer); hakios_metal_cb_free(inner); close(q, d, events);
}
void orderedIndexedRefusal() {
    Events events;
    auto* d = device(events); auto* q = queue(d); auto* cb = hakios_metal_cb_new(q);
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    CHECK(hakios_metal_cb_draw_indexed(cb, nullptr, nullptr, nullptr, nullptr,
          3, 0, 0, nullptr, 0, 1, 0, 0, nullptr, nullptr, 0,
          nullptr, nullptr, 0, nullptr, 0, nullptr, 0) == -1);
    CHECK(cb->cb->error().empty()); // refusal is queued behind the gate
    blocked.release.set();
    hakios_metal_cb_commit(cb, nullptr, nullptr); hakios_metal_cb_wait(cb);
    CHECK(hakios_metal_cb_status(cb) == HAKIOS_METAL_ERROR);
    CHECK(std::strstr(hakios_metal_cb_error(cb), "no index buffer"));
    hakios_metal_cb_free(cb); close(q, d, events);
}
void enqueueAllocation() {
    Events events;
    auto* d = device(events); auto* q = queue(d); auto* cb = hakios_metal_cb_new(q);
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    unsigned accepted = 0; bool caught = false;
    rejectAllocation = true;
    try { for (; accepted < 256; ++accepted) cb->deferrer->post(cb, [] {}); }
    catch (const std::bad_alloc&) { caught = true; }
    rejectAllocation = false;
    CHECK(caught); CHECK(cb->pending.load() == int(accepted + 1));
    blocked.release.set(); syncOne(cb); CHECK(cb->pending == 0);
    hakios_metal_cb_commit(cb, nullptr, nullptr); hakios_metal_cb_wait(cb);
    CHECK(hakios_metal_cb_status(cb) == HAKIOS_METAL_ERROR);
    hakios_metal_cb_free(cb); close(q, d, events);
}
void errorToCaller() {
    Events events;
    auto* d = device(events); auto* q = queue(d); auto* cb = hakios_metal_cb_new(q);
    auto* b = hakios_metal_buffer_new(d, 64); CHECK(b);
    CHECK(hakios_metal_cb_fill(cb, b, 1, 4, 1) == -1);
    CHECK(std::strstr(hakios_metal_error(), "multiples of 4"));
    hakios_metal_cb_free(cb); hakios_metal_buffer_free(b); close(q, d, events);
}
void appendSource() {
    Events events;
    auto* d = device(events); auto* a = queue(d); auto* b = queue(d);
    auto* ca = hakios_metal_cb_new(a); auto* cb = hakios_metal_cb_new(b);
    auto* buffer = hakios_metal_buffer_new(d, 64); CHECK(buffer);
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    cb->deferrer->post(cb, [&] { CHECK(hakios_metal_cb_fill(cb, buffer, 0, 64, 0x78) == 0); });
    Signal started, appended;
    std::thread caller([&] { started.set(); CHECK(hakios_metal_cb_append(ca, cb) == 0); appended.set(); });
    CHECK(started.wait()); CHECK(!appended.wait(40ms));
    blocked.release.set(); CHECK(appended.wait()); caller.join();
    hakios_metal_cb_free(cb);
    hakios_metal_cb_commit(ca, nullptr, nullptr); hakios_metal_cb_wait(ca);
    CHECK(hakios_metal_cb_status(ca) == HAKIOS_METAL_COMPLETED);
    const auto* bytes = static_cast<const unsigned char*>(hakios_metal_buffer_contents(buffer));
    for (unsigned i = 0; i < 64; ++i) CHECK(bytes[i] == 0x78);
    hakios_metal_cb_free(ca); hakios_metal_buffer_free(buffer);
    hakios_metal_queue_free(a); close(b, d, events);
}
void queuedArguments() {
    Events events;
    auto* d = device(events); auto* q = queue(d); auto* cb = hakios_metal_cb_new(q);
    auto* texture = hakios_metal_texture_new(d, 2, 70, 4, 4, HAKIOS_METAL_TEXTURE_USAGE_RENDER_TARGET); CHECK(texture);
    hakios_metal_texture saved = *texture;
    Gate blocked;
    cb->deferrer->post(cb, [&] { blocked.block(); }); CHECK(blocked.entered.wait());
    hakios_metal_render_pass pass{};
    pass.color0 = texture; pass.load_action = 2; pass.store_action = 1;
    pass.clear_color[0] = 1; pass.clear_color[3] = 1;
    CHECK(hakios_metal_cb_clear(cb, &pass) == 0);
    hakios_metal_texture_free(texture); pass = {};
    blocked.release.set(); hakios_metal_cb_commit(cb, nullptr, nullptr); hakios_metal_cb_wait(cb);
    CHECK(hakios_metal_cb_status(cb) == HAKIOS_METAL_COMPLETED);
    unsigned char pixels[64]{};
    CHECK(hakios_metal_texture_read(&saved, 0, 0, 4, 4, pixels, 16) == 0);
    for (unsigned i = 0; i < 64; i += 4) CHECK(pixels[i] == 255 && pixels[i+1] == 0 && pixels[i+2] == 0 && pixels[i+3] == 255);
    saved.texture.reset(); hakios_metal_cb_free(cb); close(q, d, events);
}
} // namespace

int main(int argc, char** argv) {
    CHECK(argc == 2);
    const std::string scenario = argv[1];
    if (scenario.rfind("callback-", 0) == 0) {
        const bool deferred = scenario.find("deferred") != std::string::npos;
        int failure = 0;
        if (scenario.find("allocation") != std::string::npos) failure = 1;
        if (scenario.find("submission") != std::string::npos) failure = 2;
        if (scenario.find("refusal") != std::string::npos) failure = 3;
        callbackRelease(deferred, failure);
    } else if (scenario == "wrappers-first") wrappersFirst();
    else if (scenario == "external-free-success") externalFree(false);
    else if (scenario == "external-free-error") externalFree(true);
    else if (scenario == "different-recorders") differentRecorders();
    else if (scenario == "release-other-recorder") releaseOtherRecorder();
    else if (scenario == "fifo-encoding") fifoEncoding();
    else if (scenario == "mode-frozen") modeFrozen();
    else if (scenario == "worker-exception") workerException();
    else if (scenario == "synchronous-exception") synchronousException();
    else if (scenario == "nested-completion") nestedCompletion();
    else if (scenario == "ordered-indexed-refusal") orderedIndexedRefusal();
    else if (scenario == "enqueue-allocation") enqueueAllocation();
    else if (scenario == "error-to-caller") errorToCaller();
    else if (scenario == "append-source") appendSource();
    else if (scenario == "queued-arguments") queuedArguments();
    else { std::fprintf(stderr, "unknown scenario: %s\n", argv[1]); return 64; }
    std::printf("PASS %s: owners released, queues closed, no live BOs\n", argv[1]);
}
