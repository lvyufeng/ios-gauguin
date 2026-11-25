#include "hakios-metal/compiler.hpp"
#include "hakios-metal/a6xx.hpp"
#include "GauguinStageCacheTrace.hpp"
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <future>
#include <mutex>
#include <thread>

namespace hakios::metal {
namespace {
std::mutex gCompilerLock;
struct FakeCompiler { bool has_preamble = false; } fakeCompiler;
bool compilerAvailable = true, compileFails = false, spillFirst = false;
std::atomic<unsigned> compileCalls{0};
std::string fixturePath;
std::mutex gateMutex;
std::condition_variable gate;
bool blockCompile = false, compileEntered = false, releaseCompile = false;
FakeCompiler* theCompiler() { return compilerAvailable ? &fakeCompiler : nullptr; }
bool refuse(std::string* why, const std::string& message) { *why = message; return false; }
// EXTRACT_CACHE
std::unique_ptr<CompiledStage> compileStageOnce(const void*, size_t, std::string*, const FunctionConstants&, uint32_t, const KnownBuffer*) {
    ++compileCalls;
    if (blockCompile) {
        std::unique_lock<std::mutex> lock(gateMutex);
        compileEntered = true;
        gate.notify_all();
        gate.wait(lock, [] { return releaseCompile; });
    }
    if (compileFails) return nullptr;
    auto result = stageCacheLoad(fixturePath);
    assert(result);
    result->stage.k.pvtmemSize = spillFirst && fakeCompiler.has_preamble ? 64 : 0;
    return result;
}
} // namespace
bool preferWithoutPreamble(const Kernel& with, const Kernel& without) { return without.pvtmemSize < with.pvtmemSize; }
// EXTRACT_COMPILE
} // namespace hakios::metal

using namespace hakios::metal;
namespace fs = std::filesystem;
std::string writable;
unsigned checks = 0;
void check(bool ok) { ++checks; assert(ok); }
void validate(const CompiledStage& stage) {
    check(stage.stage.k.words == stage.words.data());
    check(stage.stage.k.numWords == stage.words.size());
    check(stage.stage.k.immediates == (stage.immediates.empty() ? nullptr : stage.immediates.data()));
    check(stage.stage.k.numImmediates == stage.immediates.size());
    check(stage.stage.k.name == stage.name.c_str());
    check(std::strcmp(stage.stage.k.source, "") == 0);
}
std::unique_ptr<CompiledStage> call(const std::string& input) {
    std::string why;
    return compileStage(input.data(), input.size(), &why, {}, 0, nullptr);
}
std::string pathFor(const std::string& input) {
    return stageCacheWritable(stageCacheName(input.data(), input.size(), {}, 0, nullptr));
}
void publish(const std::string& input) {
    auto stage = stageCacheLoad(fixturePath);
    assert(stage);
    stageCacheSave(pathFor(input), *stage);
}
int main(int argc, char** argv) {
    assert(argc == 3);
    fs::path root(argv[2]); fs::create_directory(root);
    writable = (root/"writable").string(); fs::create_directory(writable);
    check(setenv("HAKIOS_METAL_CACHE", writable.c_str(), 1) == 0);
    check(unsetenv("HAKIOS_METAL_CACHE_SEED") == 0);
    unsigned files = 0;
    for (auto const& entry : fs::directory_iterator(argv[1])) {
        if (entry.path().extension() != ".stage") continue;
        auto stage = stageCacheLoad(entry.path().string()); check(bool(stage)); validate(*stage);
        auto roundtrip = root/entry.path().filename(); stageCacheSave(roundtrip.string(), *stage);
        auto again = stageCacheLoad(roundtrip.string()); check(bool(again)); validate(*again);
        check(again->words == stage->words && again->immediates == stage->immediates && again->name == stage->name);
        if (fixturePath.empty()) fixturePath = entry.path().string();
        ++files;
    }
    check(files == 245);
    publish("warm");
    const unsigned initial = compileCalls;
    auto warm = call("warm"); check(bool(warm)); validate(*warm); check(compileCalls == initial);

    // A warm request must complete while another thread owns the compiler lock.
    // The original implementation is the negative control and remains blocked.
    std::unique_lock<std::mutex> held(gCompilerLock);
    std::promise<void> entered;
    auto worker = std::async(std::launch::async, [&] { entered.set_value(); return call("warm"); });
    entered.get_future().wait();
    auto state = worker.wait_for(std::chrono::milliseconds(SC323_PATCHED ? 2000 : 50));
    check((state == std::future_status::ready) == bool(SC323_PATCHED));
    held.unlock(); check(bool(worker.get())); check(compileCalls == initial);

    // Cold requests race with a writer. Only one actually compiles; waiters
    // recheck after locking, and no parser touches a partially published file.
    blockCompile = true; compileEntered = false; releaseCompile = false;
    auto writer = std::async(std::launch::async, [] { return call("cold"); });
    { std::unique_lock<std::mutex> g(gateMutex); gate.wait(g, [] { return compileEntered; }); }
    std::vector<std::future<std::unique_ptr<CompiledStage>>> readers;
    for (unsigned i = 0; i < 12; ++i) readers.push_back(std::async(std::launch::async, [] { return call("cold"); }));
    { std::lock_guard<std::mutex> g(gateMutex); releaseCompile = true; gate.notify_all(); }
    check(bool(writer.get()));
    for (auto& r : readers) { auto s = r.get(); check(bool(s)); validate(*s); }
    blockCompile = false; check(compileCalls == initial + 1);

    // Cache-disabled, seed-only and missing/corrupt cache paths retain fallback.
    fs::path seed = root/"seed"; fs::create_directory(seed);
    std::string seedName = stageCacheName("seed", 4, {}, 0, nullptr);
    auto stage = stageCacheLoad(fixturePath); stageCacheSave(seed.string()+seedName, *stage);
    unsetenv("HAKIOS_METAL_CACHE"); setenv("HAKIOS_METAL_CACHE_SEED", seed.c_str(), 1);
    check(bool(call("seed"))); check(compileCalls == initial + 1);
    unsetenv("HAKIOS_METAL_CACHE_SEED"); check(bool(call("disabled"))); check(compileCalls == initial + 2);
    setenv("HAKIOS_METAL_CACHE", writable.c_str(), 1);
    { FILE* f = fopen(pathFor("corrupt").c_str(), "wb"); assert(f); fwrite("bad!", 1, 4, f); fclose(f); }
    check(bool(call("corrupt"))); check(compileCalls == initial + 3);
    check(bool(call("corrupt"))); check(compileCalls == initial + 3);
    compileFails = true; check(!call("compile-fails")); check(!fs::exists(pathFor("compile-fails"))); compileFails = false;
    compilerAvailable = false; check(!call("warm")); compilerAvailable = true;
    spillFirst = true; fakeCompiler.has_preamble = true;
    auto spilled = call("preamble"); check(bool(spilled)); check(spilled->stage.k.pvtmemSize == 0);
    check(fakeCompiler.has_preamble); fakeCompiler.has_preamble = false; spillFirst = false;

    // Concurrent publication uses the actual writer's rename and reader's parser.
    const auto cachePath = pathFor("warm");
    std::atomic<bool> bad{false};
    std::thread publishing([&] {
        for (unsigned i = 0; i < 200; ++i) {
            std::lock_guard<std::mutex> g(gCompilerLock);
            auto s = stageCacheLoad(fixturePath); assert(s);
            s->name = i % 2 ? "publication-a" : "publication-b";
            stageCacheSave(cachePath, *s);
        }
    });
    std::vector<std::thread> concurrent;
    for (unsigned n = 0; n < 8; ++n) concurrent.emplace_back([&] {
        for (unsigned i = 0; i < 256; ++i) {
            auto s = call("warm");
            if (!s || s->stage.k.words != s->words.data() || s->stage.k.name != s->name.c_str()) bad = true;
        }
    });
    for (auto& t : concurrent) t.join(); publishing.join(); check(!bad);
    printf("{\"state\":\"actual-cache-parser-and-lock-contract-passed\",\"patched\":%u,\"real_cache_files\":%u,\"checks\":%u,\"concurrent_reads\":2048,\"atomic_publications\":200,\"device_commands\":0}\n", unsigned(SC323_PATCHED), files, checks);
}
