// SPDX-License-Identifier: MIT
// Link caller-selected actual AIR stages for the five formats exercised by227.
// This is host compiler/link coverage, not full descriptor or GPU qualification.
#include <charconv>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include "hakios-metal/compiler.hpp"
#include "hakios-metal/device_profile.hpp"
#include "hakios-metal/metallib.hpp"
using namespace hakios::metal;

static std::string quote(const std::string& value) {
    std::string result = "\"";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') { result += '\\'; result += char(c); }
        else if (c < 32) {
            char escaped[7]; std::snprintf(escaped, sizeof escaped, "\\u%04x", unsigned(c));
            result += escaped;
        } else result += char(c);
    }
    return result + '"';
}

struct Library {
    std::vector<uint8_t> bytes;
    MetalLibrary parsed;
    explicit Library(const char* path) {
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        const auto length = file.tellg();
        if (!file || length < 88 || length > 16 * 1024 * 1024)
            throw std::runtime_error("missing, short or oversized library");
        bytes.resize(static_cast<size_t>(length)); file.seekg(0);
        file.read(reinterpret_cast<char*>(bytes.data()), length);
        if (!file || !parsed.parse(bytes.data(), bytes.size()))
            throw std::runtime_error("library parse refused: " + parsed.why());
    }
    const MetalFunction& function(const char* text, uint8_t type) const {
        size_t index = 0; const std::string value(text);
        const auto result = std::from_chars(value.data(), value.data() + value.size(), index);
        if (result.ec != std::errc{} || result.ptr != value.data() + value.size() || index >= parsed.functions().size())
            throw std::runtime_error("invalid stage index");
        const auto& function = parsed.functions()[index];
        if (function.type != type) throw std::runtime_error("wrong stage type");
        return function;
    }
    std::shared_ptr<CompiledStage> compile(const MetalFunction& function, std::string& why, uint32_t base = 0) const {
        const uint8_t* code = nullptr; uint64_t length = 0;
        if (!parsed.bitcode(function, &code, &length) || !code || !length)
            throw std::runtime_error("missing AIR stage");
        return std::shared_ptr<CompiledStage>(compileStage(code, length, &why, {}, base));
    }
};

int main(int argc, char** argv) try {
    if (argc != 5) throw std::runtime_error("VS-library VS-index FS-library FS-index required");
    if (!hasCompiler() || device::kTarget.chipId != 0x06010900)
        throw std::runtime_error("real A619 compiler required");
    Library vertex(argv[1]), fragment(argv[3]);
    const auto& v = vertex.function(argv[2], MetalFunction::kVertex);
    const auto& f = fragment.function(argv[4], MetalFunction::kFragment);
    std::string why;
    const auto start = std::chrono::steady_clock::now();
    auto vs = vertex.compile(v, why);
    auto fs = vs ? fragment.compile(f, why, vs->stage.k.numIbos) : nullptr;
    const bool stages = bool(vs) && bool(fs);
    std::printf("{\"vertex\":%s,\"fragment\":%s,\"stages_compiled\":%s,\"stage_reason\":%s,\"formats\":[",
                quote(v.name).c_str(), quote(f.name).c_str(), stages ? "true" : "false", quote(why).c_str());
    const PixelFormat formats[] = {PixelFormat::kRGBA8Unorm, PixelFormat::kBGRA8Unorm,
        PixelFormat::kRGBA8UnormSrgb, PixelFormat::kBGRA8UnormSrgb, PixelFormat::kRGBA16Float};
    unsigned linked = 0;
    for (unsigned i = 0; i < 5; ++i) {
        why.clear(); auto program = stages ? linkProgram(vs, fs, formats[i], &why) : nullptr;
        if (program) ++linked;
        std::printf("%s{\"format\":%u,\"linked\":%s,\"reason\":%s}", i ? "," : "",
                    unsigned(formats[i]), program ? "true" : "false", quote(why).c_str());
    }
    const double milliseconds = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    std::printf("],\"linked\":%u,\"compile_link_ms\":%.6f,\"function_constants\":\"unsupplied\","
                "\"known_buffers\":false,\"full_descriptor_qualified\":false,\"GPU_executed\":false}\n", linked, milliseconds);
    return linked == 5 ? 0 : 3;
} catch (const std::exception& error) {
    std::fprintf(stderr, "pipeline census error: %s\n", error.what());
    return 2;
}
