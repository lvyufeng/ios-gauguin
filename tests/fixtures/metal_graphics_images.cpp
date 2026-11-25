// SPDX-License-Identifier: MIT
// Actual encoder/descriptor checks using allocated fake BOs. No submission or
// rasterization: GPU visibility and pixel semantics require a later phone trial.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <vector>
#include "hakios-metal/a6xx.hpp"
#include "hakios-metal/fake_gpu.hpp"
#include "hakios-metal/render.hpp"
#include "hakios-metal/texture.hpp"
#include "fixtures/tri_flat_vs_air.hpp"
#include "fixtures/tri_flat_fs_air.hpp"
using namespace hakios::metal;
static unsigned checks;
static void check(bool ok, const char* why) {
    ++checks;
    if (!ok) { std::fprintf(stderr, "graphics image check failed: %s\n", why); std::exit(1); }
}
static uint32_t reg(const pm4::Stream& stream, uint32_t address) {
    uint32_t value = ~0u;
    const auto& words = stream.words();
    for (size_t i = 0; i < words.size();) {
        const auto h = pm4::decode(words[i]);
        if (h.kind == pm4::Header::kRegisters && h.reg <= address && address < h.reg + h.count)
            value = words[i + 1 + address - h.reg];
        i += h.count + 1;
    }
    return value;
}
static KernelTexture image() {
    KernelTexture k{}; k.kind = kTexImage; k.dim = kTexDim2D; k.element = kElemFloat; k.write = 1;
    return k;
}
int main() {
    Gpu gpu(std::make_unique<FakeGpu>());
    std::string why;
    auto make = [&](uint32_t usage) {
        TextureDesc d; d.width = d.height = 64; d.usage = usage;
        auto t = Texture::make(gpu, d, &why); check(t != nullptr, why.c_str()); return t;
    };
    auto rt = make(kTextureUsageRenderTarget | kTextureUsageRead | kTextureUsageWrite);
    auto a = make(kTextureUsageRead | kTextureUsageWrite);
    auto b = make(kTextureUsageRead | kTextureUsageWrite);
    auto readonly = make(kTextureUsageRead);
    Program base{kernels::tri_flat_vs_air, kernels::tri_flat_fs_air, Linkage{}, "image-tables"};
    base.fs.k.numIbos = 4; base.fs.k.numSamp = 4; base.fs.k.textures[3] = image();
    RenderPass pass; pass.color0 = rt.get(); pass.load = LoadAction::kClear;
    Draw draw; draw.vertexCount = 3; draw.viewport = Viewport{0, 0, 64, 64, 0, 1};
    Bindings vs, fs; fs.textures.resize(4); fs.textures[3] = b.get();
    auto encode = [&](const Program& p, const Bindings& v, const Bindings& f, const render::Options& o,
                      pm4::Stream& stream, std::vector<uint8_t>& table) {
        why.clear();
        return render::encode(stream, p, pass, draw, v, f, 0x100000, 0x200000,
                              0x300000, table.data(), &why, o);
    };
    render::Options options;
    pm4::Stream first; std::vector<uint8_t> table(render::kTableBytes, 0xa5);
    check(encode(base, vs, fs, options, first, table), why.c_str());
    const auto descriptor = b->storageDescriptor();
    check(!std::memcmp(table.data() + render::kTableVsAt + 3 * 64, descriptor.dword, 64), "FS image descriptor must use slot3");
    check(reg(first, a6xx::REG_A6XX_SP_IBO_COUNT) == 4, "shared IBO extent");
    check((reg(first, a6xx::REG_A6XX_SP_FS_CONFIG) & a6xx::A6XX_SP_FS_CONFIG_NIBO__MASK) >>
          a6xx::A6XX_SP_FS_CONFIG_NIBO__SHIFT == 4, "FS NIBO includes images");
    Program both = base;
    both.vs.k.numIbos = 4; both.vs.k.numSamp = 4; both.vs.k.textures[3] = image();
    both.fsIboBase = 4; both.fs.k.numSsbos = 4; both.fs.k.numIbos = 8;
    vs.textures.resize(4); vs.textures[3] = a.get();
    pm4::Stream second; std::vector<uint8_t> table2(render::kTableBytes, 0xa5);
    check(encode(both, vs, fs, options, second, table2), why.c_str());
    const auto vd = a->storageDescriptor();
    check(!std::memcmp(table2.data() + render::kTableVsAt + 3 * 64, vd.dword, 64), "VS slot isolated");
    check(!std::memcmp(table2.data() + render::kTableVsAt + 7 * 64, descriptor.dword, 64), "FS shifted past all VS IBOs");
    check(reg(second, a6xx::REG_A6XX_SP_IBO_COUNT) == 8, "combined IBO extent");
    auto refuse = [&](Program p, Bindings bindings, render::Options o, const char* reason) {
        pm4::Stream s; std::vector<uint8_t> t(render::kTableBytes, 0xa5);
        check(!encode(p, {}, bindings, o, s, t), "invalid image must refuse");
        check(why.find(reason) != std::string::npos, why.c_str());
        check(s.words().empty(), "no packet emitted on refusal");
        check(t == std::vector<uint8_t>(render::kTableBytes, 0xa5), "no descriptor touched on refusal");
    };
    Bindings bad = fs; bad.textures[3] = nullptr; refuse(base, bad, options, "no image bound");
    bad = fs; bad.textures[3] = readonly.get(); refuse(base, bad, options, "lacks shader");
    bad = fs; bad.textures[3] = rt.get(); refuse(base, bad, options, "aliases a color attachment");
    auto wrong = base; wrong.fs.k.textures[3].element = kElemUint; refuse(wrong, fs, options, "format/layout");
    wrong = base; wrong.fs.k.textures[3].dim = kTexDim3D; refuse(wrong, fs, options, "shape/type");
    auto noFlush = options; noFlush.tailCacheFlush = false; refuse(base, fs, noFlush, "complete cache synchronization");
    wrong = base; wrong.fs.k.numIbos = 49; refuse(wrong, fs, options, "extent exceeds");
    wrong = base; wrong.fs.k.numIbos = 3; refuse(wrong, fs, options, "outside its IBO extent");
    std::printf("PASS graphics-image-encoder assertions=%u submitted=0 GPU_pixels_qualified=0\n", checks);
}
