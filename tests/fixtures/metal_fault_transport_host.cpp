/* Exercise the ACTUAL patched IOKit transport, with every IOKit entry mocked. */
#include <IOKit/IOKitLib.h>
#include <mach/mach_time.h>
#include <atomic>
#include <cassert>
#include <condition_variable>
#include <cstdio>
#include <cstring>
#include <deque>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

struct Reply {
    kern_return_t code;
    uint64_t value = 0;
    size_t length = 0;
};
struct Backend {
    std::mutex lock;
    std::condition_variable changed;
    std::deque<Reply> replies;
    kern_return_t defaultCode = kIOReturnUnsupported;
    uint64_t nextValue = 100;
    unsigned calls = 0, maps = 0, unmaps = 0, closes = 0;
    unsigned barrierTarget = 0, arrived = 0;
    bool holdSecond = false, releaseHeld = false;
};
static std::mutex registryLock;
static std::map<io_connect_t, std::shared_ptr<Backend>> registry;
static io_connect_t nextConnection = 1, lastConnection;
static std::atomic<unsigned> checks{0};
static void check(bool value) { assert(value); ++checks; }
static std::shared_ptr<Backend> backend(io_connect_t c) {
    std::lock_guard<std::mutex> guard(registryLock);
    return registry.at(c);
}
static CFMutableDictionaryRef fq_matching(const char* name) {
    check(!std::strcmp(name, "HakiosGPU"));
    return reinterpret_cast<CFMutableDictionaryRef>(uintptr_t(1));
}
static io_service_t fq_service(mach_port_t, CFDictionaryRef) { return 1; }
static kern_return_t fq_open(io_service_t, task_port_t, uint32_t, io_connect_t* out) {
    std::lock_guard<std::mutex> guard(registryLock);
    *out = lastConnection = nextConnection++;
    registry[*out] = std::make_shared<Backend>();
    return KERN_SUCCESS;
}
static kern_return_t fq_release(io_object_t) { return KERN_SUCCESS; }
static kern_return_t fq_close(io_connect_t c) {
    auto b = backend(c);
    std::lock_guard<std::mutex> guard(b->lock);
    ++b->closes;
    return KERN_SUCCESS;
}
static kern_return_t fq_call(io_connect_t c, uint32_t request, const void* input,
                             size_t size, void* output, size_t* returned) {
    auto b = backend(c);
    std::unique_lock<std::mutex> guard(b->lock);
    const unsigned index = b->calls++;
    Reply reply{b->defaultCode, b->nextValue++};
    if (!b->replies.empty()) { reply = b->replies.front(); b->replies.pop_front(); }
    if (b->barrierTarget) {
        ++b->arrived;
        b->changed.notify_all();
        b->changed.wait(guard, [&] { return b->arrived >= b->barrierTarget; });
        if (b->holdSecond && index == 1)
            b->changed.wait(guard, [&] { return b->releaseHeld; });
    }
    guard.unlock();
    *returned = reply.length ? reply.length : size;
    if (reply.code == KERN_SUCCESS && request == 0x40 && input && output && size == 24) {
        unsigned char bytes[24];
        std::memcpy(bytes, input, sizeof(bytes));
        std::memcpy(bytes+8, &reply.value, sizeof(reply.value));
        std::memcpy(output, bytes, *returned < sizeof(bytes) ? *returned : sizeof(bytes));
    }
    return reply.code;
}
static kern_return_t fq_map(io_connect_t c, uint32_t, mach_port_t,
                            mach_vm_address_t* address, mach_vm_size_t* size, IOOptionBits) {
    auto b = backend(c); std::lock_guard<std::mutex> guard(b->lock);
    ++b->maps; *address = 0x100000; *size = 16384; return KERN_SUCCESS;
}
static kern_return_t fq_unmap(io_connect_t c, uint32_t, mach_port_t, mach_vm_address_t) {
    auto b = backend(c); std::lock_guard<std::mutex> guard(b->lock);
    ++b->unmaps; return KERN_SUCCESS;
}

#define IOServiceMatching fq_matching
#define IOServiceGetMatchingService fq_service
#define IOServiceOpen fq_open
#define IOObjectRelease fq_release
#define IOServiceClose fq_close
#define IOConnectCallStructMethod fq_call
#define IOConnectMapMemory64 fq_map
#define IOConnectUnmapMemory64 fq_unmap
#include FQ_TRANSPORT_SOURCE
#undef IOServiceMatching
#undef IOServiceGetMatchingService
#undef IOServiceOpen
#undef IOObjectRelease
#undef IOServiceClose
#undef IOConnectCallStructMethod
#undef IOConnectMapMemory64
#undef IOConnectUnmapMemory64

using namespace hakios::metal;
struct Client {
    std::unique_ptr<Transport> transport;
    std::shared_ptr<Backend> wire;
};
static Client client() {
    std::string why;
    auto t = openKernelGpu(&why);
    check(t && why.empty());
    return {std::move(t), backend(lastConnection)};
}
static MsmParam faultParam() { return {kPipe3D, kParamFaults, 0, 0, 0}; }
static int faults(Client& c, uint64_t* value = nullptr) {
    auto p = faultParam();
    const int error = c.transport->call(kGetParam, &p, sizeof(p));
    if (!error && value) *value = p.value;
    return error;
}
static void race(bool successFirst) {
    auto c = client();
    c.wire->barrierTarget = 2; c.wire->holdSecond = true;
    c.wire->defaultCode = KERN_SUCCESS;
    const Reply yes{KERN_SUCCESS, 17}, no{kIOReturnUnsupported};
    c.wire->replies = successFirst ? std::deque<Reply>{yes, no} : std::deque<Reply>{no, yes};
    std::thread first([&] { check(faults(c) == (successFirst ? 0 : ENOSYS)); });
    {
        std::unique_lock<std::mutex> guard(c.wire->lock);
        c.wire->changed.wait(guard, [&] { return c.wire->arrived == 1; });
    }
    std::thread second([&] { check(faults(c) == (successFirst ? ENOSYS : 0)); });
    first.join();
    if (!successFirst) { check(faults(c) == ENOSYS); check(c.wire->calls == 2); }
    {
        std::lock_guard<std::mutex> guard(c.wire->lock);
        c.wire->releaseHeld = true; c.wire->changed.notify_all();
    }
    second.join();
    check(faults(c) == 0 && c.wire->calls == 3);
    c.wire->replies.push_back({kIOReturnUnsupported});
    check(faults(c) == ENOSYS && c.wire->calls == 4);
    check(faults(c) == 0 && c.wire->calls == 5);
}

int main() {
    unsigned cases = 0;
    {
        auto c = client();
        for (unsigned i = 0; i < 1000; ++i) check(faults(c) == ENOSYS);
        check(c.wire->calls == 1);
        auto other = faultParam(); other.param = kParamChipId;
        for (unsigned i = 0; i < 4; ++i)
            check(c.transport->call(kGetParam, &other, sizeof(other)) == ENOSYS);
        check(c.wire->calls == 5);
        MsmWaitFence wait{};
        c.wire->replies.push_back({kIOReturnTimeout});
        check(c.transport->call(kWaitFence, &wait, sizeof(wait)) == ETIMEDOUT);
        MsmGemSubmit submit{};
        c.wire->replies.push_back({kIOReturnNotReady});
        check(c.transport->call(kGemSubmit, &submit, sizeof(submit)) == EIO);
        auto address = c.transport->map(8, 4096);
        check(address == reinterpret_cast<void*>(uintptr_t(0x100000)));
        c.transport->unmap(8, address);
        check(c.wire->maps == 1 && c.wire->unmaps == 1);
        c.transport.reset(); check(c.wire->closes == 1);
        ++cases;
    }
    {
        auto c = client(); c.wire->defaultCode = KERN_SUCCESS;
        uint64_t previous = 0;
        for (unsigned i = 0; i < 1000; ++i) {
            uint64_t value = 0; check(faults(c, &value) == 0 && value > previous); previous = value;
        }
        check(c.wire->calls == 1000);
        c.wire->replies.push_back({kIOReturnUnsupported});
        check(faults(c) == ENOSYS);
        check(faults(c) == 0 && c.wire->calls == 1002);
        ++cases;
    }
    const Reply transient[] = {{kIOReturnNoMemory}, {kIOReturnBadArgument},
        {kIOReturnTimeout}, {kIOReturnBusy}, {kIOReturnNotFound}, {kIOReturnNotReady}};
    const int errors[] = {ENOMEM, EINVAL, ETIMEDOUT, EBUSY, ENOENT, EIO};
    for (unsigned i = 0; i < sizeof(transient)/sizeof(transient[0]); ++i) {
        auto c = client(); c.wire->replies.push_back(transient[i]);
        check(faults(c) == errors[i]);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        ++cases;
    }
    {
        auto c = client(); auto p = faultParam(); p.param = kParamChipId;
        c.wire->replies.push_back({KERN_SUCCESS, 619});
        check(c.transport->call(kGetParam, &p, sizeof(p)) == 0 && p.value == 619);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        ++cases;
    }
    {
        auto c = client(); c.wire->replies.push_back({KERN_SUCCESS, 99, 23});
        check(faults(c) == EPROTO);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        ++cases;
    }
    for (unsigned i = 0; i < 11; ++i) {
        auto c = client(); auto p = faultParam(); uint32_t request = kGetParam;
        size_t size = sizeof(p); void* data = &p;
        switch (i) {
        case 0: request++; break; case 1: data = nullptr; break;
        case 2: size = 0; break; case 3: size = 23; break; case 4: size = 25; break;
        case 5: p.pipe++; break; case 6: p.param = kParamChipId; break;
        case 7: p.value = 1; break; case 8: p.len = 1; break; case 9: p.pad = 1; break;
        case 10: request = UINT32_MAX; break;
        }
        check(c.transport->call(request, data, size) == ENOSYS);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        check(faults(c) == ENOSYS && c.wire->calls == 2);
        ++cases;
    }
    {
        auto c = client(); auto p = faultParam(); unsigned char bytes[sizeof(p)+1];
        std::memcpy(bytes+1, &p, sizeof(p));
        check(c.transport->call(kGetParam, bytes+1, sizeof(p)) == ENOSYS);
        check(faults(c) == ENOSYS && c.wire->calls == 1);
        ++cases;
    }
    {
        auto c = client(); c.wire->barrierTarget = 8;
        std::vector<std::thread> threads;
        for (unsigned i = 0; i < 8; ++i) threads.emplace_back([&] { check(faults(c) == ENOSYS); });
        for (auto& t : threads) t.join();
        check(c.wire->calls == 8); threads.clear();
        for (unsigned i = 0; i < 8; ++i) threads.emplace_back([&] {
            for (unsigned n = 0; n < 1000; ++n) check(faults(c) == ENOSYS);
        });
        for (auto& t : threads) t.join();
        check(c.wire->calls == 8);
        ++cases;
    }
    race(false); ++cases;
    race(true); ++cases;
    std::printf("{\"state\":\"passed-real-FQ322-transport-with-mocked-IOKit\",\"cases\":%u,\"checks\":%u,"
                "\"concurrent_cached_calls\":8000,\"both_success_race_orders\":true,"
                "\"supported_counters_stay_live\":true,\"transient_errors_not_cached\":true,"
                "\"invalid_shapes_not_cached\":true,\"connections_independent\":true,"
                "\"submit_wait_map_errors_preserved\":true,\"actual_IOKit_calls\":0}\n",
                cases, checks.load());
}
