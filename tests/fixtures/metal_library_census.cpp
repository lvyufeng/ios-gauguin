// SPDX-License-Identifier: MIT
// Inspect or compile ONE function in a caller-provided library with the actual
// A619 compiler. Run each function in a fresh process to retain individual
// refusals, compiler crashes, timings and host memory measurements.
// No GPU transport, shader replacement, resource binding or rendering occurs.
#include <charconv>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <vector>
#include "hakios-metal/compiler.hpp"
#include "hakios-metal/device_profile.hpp"
#include "hakios-metal/metallib.hpp"

using namespace hakios::metal;

static std::string quote(const std::string& value) {
    std::string result = "\"";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') { result += '\\'; result += char(c); }
        else if (c < 0x20) {
            char escaped[7]; std::snprintf(escaped, sizeof escaped, "\\u%04x", c);
            result += escaped;
        } else result += char(c);
    }
    return result + '"';
}

static uint64_t peakResidentBytes() {
    struct rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage)) throw std::runtime_error("getrusage failed");
#ifdef __APPLE__
    return uint64_t(usage.ru_maxrss);
#else
    return uint64_t(usage.ru_maxrss) * 1024;
#endif
}

static uint64_t wordsHash(const std::vector<uint32_t>& words) {
    uint64_t value = 0xcbf29ce484222325ull;
    for (uint32_t word : words) for (unsigned shift = 0; shift < 32; shift += 8)
        value = (value ^ uint8_t(word >> shift)) * 0x100000001b3ull;
    return value;
}

int main(int argc, char** argv) try {
    if (argc != 3 && argc != 4) throw std::runtime_error("library --list | library --function INDEX");
    std::ifstream file(argv[1], std::ios::binary | std::ios::ate);
    const auto length = file.tellg();
    if (!file || length < 88 || length > 16 * 1024 * 1024)
        throw std::runtime_error("missing, short or oversized library");
    std::vector<uint8_t> data(static_cast<size_t>(length));
    file.seekg(0); file.read(reinterpret_cast<char*>(data.data()), length);
    if (!file) throw std::runtime_error("short library read");
    MetalLibrary library;
    if (!library.parse(data.data(), data.size())) throw std::runtime_error(library.why());
    if (library.functions().empty() || library.functions().size() > 4096)
        throw std::runtime_error("function count outside census bound");
    if (!hasCompiler() || device::kTarget.chipId != 0x06010900)
        throw std::runtime_error("real A619 compiler required");
    if (argc == 3 && std::string(argv[2]) == "--list") {
        std::printf("{\"state\":\"parsed-library-only\",\"functions\":[");
        for (size_t i = 0; i < library.functions().size(); ++i) {
            const auto& f = library.functions()[i];
            std::printf("%s{\"index\":%zu,\"name\":%s,\"type\":%u,\"module_bytes\":%llu}",
                i ? "," : "", i, quote(f.name).c_str(), f.type,
                static_cast<unsigned long long>(f.moduleSize));
        }
        std::printf("],\"hardware_qualified\":false}\n");
        return 0;
    }
    if (argc != 4 || std::string(argv[2]) != "--function")
        throw std::runtime_error("unknown census action");
    const std::string indexText(argv[3]); size_t index = 0;
    const auto parsed = std::from_chars(indexText.data(), indexText.data() + indexText.size(), index);
    if (parsed.ec != std::errc{} || parsed.ptr != indexText.data() + indexText.size() || index >= library.functions().size())
        throw std::runtime_error("invalid function index");
    const auto& function = library.functions()[index];
    const uint8_t* code = nullptr; uint64_t bytes = 0;
    if (!library.bitcode(function, &code, &bytes) || !code || !bytes)
        throw std::runtime_error("missing function bitcode");
    std::string why;
    const auto start = std::chrono::steady_clock::now();
    std::unique_ptr<CompiledKernel> compute;
    std::unique_ptr<CompiledStage> stage;
    if (function.type == MetalFunction::kKernel) compute = compileAir(code, bytes, &why);
    else if (function.type == MetalFunction::kVertex || function.type == MetalFunction::kFragment)
        stage = compileStage(code, bytes, &why);
    else why = "function type has no compute/vertex/fragment entry point";
    const double milliseconds = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    const bool compiled = bool(compute) || bool(stage);
    std::printf("{\"state\":%s,\"index\":%zu,\"name\":%s,\"type\":%u,\"AIR_bytes\":%llu,"
                "\"function_constants\":\"unsupplied\",\"known_buffers\":false,\"compile_ms\":%.6f,"
                "\"host_peak_resident_bytes\":%llu,\"reason\":%s",
        quote(compiled ? "compiled-A619-stage-only" : "refused-A619-stage").c_str(), index,
        quote(function.name).c_str(), function.type, static_cast<unsigned long long>(bytes), milliseconds,
        static_cast<unsigned long long>(peakResidentBytes()), quote(why).c_str());
    if (compiled) {
        const Kernel& kernel = compute ? compute->kernel : stage->stage.k;
        const auto& words = compute ? compute->words : stage->words;
        const auto& resources = compute ? compute->resources : stage->resources;
        if (words.empty()) throw std::runtime_error("compiler returned empty code");
        std::printf(",\"code_words\":%zu,\"code_fnv64\":\"%016llx\",\"full_regs\":%d,\"half_regs\":%d,"
                    "\"private_bytes_per_fiber\":%u,\"constant_vec4s\":%u,\"resources\":%zu",
            words.size(), static_cast<unsigned long long>(wordsHash(words)), kernel.maxReg + 1,
            kernel.maxHalfReg + 1, kernel.pvtmemSize, kernel.constlen, resources.size());
        if (stage) std::printf(",\"attributes\":%u,\"color_outputs\":%u,\"framebuffer_fetch\":%s",
            stage->stage.numAttributes, stage->stage.numColorOutputs, stage->stage.fbRead ? "true" : "false");
    }
    std::printf(",\"program_linked\":false,\"hardware_qualified\":false}\n");
    return compiled ? 0 : 3;
} catch (const std::exception& error) {
    std::fprintf(stderr, "census error: %s\n", error.what());
    return 2;
}
