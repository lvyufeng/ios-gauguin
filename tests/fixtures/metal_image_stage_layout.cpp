// SPDX-License-Identifier: MIT
// Compile actual AIR with a device-buffer VS and an image-only FS. This catches
// losing the FS reserved base when it originally declared zero SSBOs. No GPU IO.
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <vector>
#include "hakios-metal/compiler.hpp"
#include "hakios-metal/metallib.hpp"
#include "fixtures/tri_dpos_vs_bc.hpp"
using namespace hakios::metal;
static void need(bool ok, const std::string& why) { if (!ok) throw std::runtime_error(why); }
int main(int argc, char** argv) try {
    need(argc == 2, "actual default.metallib path required");
    std::ifstream file(argv[1], std::ios::binary | std::ios::ate);
    const auto size = file.tellg();
    need(file && size > 88 && size < 16 * 1024 * 1024, "bounded library");
    std::vector<uint8_t> data(static_cast<size_t>(size)); file.seekg(0);
    file.read(reinterpret_cast<char*>(data.data()), size); need(bool(file), "full library read");
    MetalLibrary lib; need(lib.parse(data.data(), data.size()), lib.why());
    const MetalFunction* selected = nullptr;
    for (const auto& f : lib.functions()) if (f.name == "inplace_copy_lph") selected = &f;
    need(selected && selected->type == MetalFunction::kFragment, "image FS missing");
    const uint8_t* air = nullptr; uint64_t length = 0;
    need(lib.bitcode(*selected, &air, &length) && air && length, "FS AIR");
    std::string why;
    auto vs = compileStage(kernels::tri_dpos_vs_bc, kernels::tri_dpos_vs_bc_size, &why);
    need(bool(vs), why);
    need(vs->stage.k.numSsbos == 1 && vs->stage.k.numIbos == 1, "fixture VS extent must be one");
    auto original = compileStage(air, length, &why);
    need(bool(original), why);
    need(original->stage.k.numSsbos == 0 && original->stage.k.textures[3].kind == kTexImage,
         "actual FS must have an image at3 and zero SSBOs");
    for (uint32_t base : {1u, 4u, 31u}) {
        auto shifted = compileStage(air, length, &why, {}, base);
        need(bool(shifted), why);
        need(shifted->iboBase == base, "reserved FS base lost");
        need(shifted->stage.k.numSsbos == base, "image base must reserve all earlier-stage IBOs");
        need(shifted->stage.k.numIbos == original->stage.k.numIbos + base, "image extent not shifted");
        need(shifted->stage.k.textures[3].kind == kTexImage, "image metadata changed");
        std::printf("PASS FS-layout base=%u originalSSBOs=0 image3_slot=%u extent=%u GPU=0\n",
                    base, shifted->stage.k.numSsbos + 3, shifted->stage.k.numIbos);
    }
    return 0;
} catch (const std::exception& e) {
    std::fprintf(stderr, "image layout FAIL: %s\n", e.what()); return 1;
}
