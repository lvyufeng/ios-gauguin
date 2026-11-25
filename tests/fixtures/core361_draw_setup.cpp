// Use the same synthetic shaders and fake GPU as the render regression suite.
#include "render_test.cpp"
#include <cassert>
#include <chrono>
#include <string_view>

namespace {
enum class Shape { ShortNames, LongNames, MaskedOutput, TwoTargets, DualSource };

struct Workload {
    explicit Workload(Shape shape)
        : color0(target(rig)), color1(target(rig)), program(handProgram()), draw(wholeDraw()) {
        pass.color0 = color0.get();
        if (shape != Shape::ShortNames) {
            program.vs.k.name = "synthetic_compositor_vertex_shader";
            program.fs.k.name = "synthetic_compositor_fragment_shader";
        }
        if (shape == Shape::MaskedOutput || shape == Shape::TwoTargets || shape == Shape::DualSource) {
            program.fs.numColorOutputs = 2;
            program.fs.colorRegid[1] = regid(1, 0);
        }
        if (shape == Shape::TwoTargets) pass.more[0].texture = color1.get();
        if (shape == Shape::DualSource) program.fs.dualSrcBlend = 1;
    }

    Rig rig;
    std::shared_ptr<Texture> color0, color1;
    Program program;
    RenderPass pass{};
    Draw draw;
};

void snapshot() {
    for (Shape shape : {Shape::ShortNames, Shape::LongNames, Shape::MaskedOutput, Shape::TwoTargets, Shape::DualSource}) {
        Workload w(shape);
        Encoded encoded(w.rig, w.program, w.pass, w.draw);
        assert(encoded.ok && encoded.error.empty() && encoded.stream.size() != 0);
        const auto& words = encoded.stream.words();
        const uint32_t count = uint32_t(words.size());
        assert(std::fwrite(&count, sizeof(count), 1, stdout) == 1);
        assert(std::fwrite(words.data(), sizeof(uint32_t), words.size(), stdout) == words.size());
        assert(std::fwrite(encoded.table->contents(), 1, render::kTableBytes, stdout) == render::kTableBytes);
    }
}

void benchmark(Shape shape) {
    Workload w(shape);
    Encoded buffers(w.rig, w.program, w.pass, w.draw);
    pm4::Stream packets;
    const Bindings bindings{};
    const render::Options options{};
    const auto draw = [&] {
        packets.clear();
        bool ok = render::encodeInPass(packets, w.program, w.pass, w.draw, bindings, bindings,
            buffers.vsProgram->gpuAddress(), buffers.fsProgram->gpuAddress(), buffers.table->gpuAddress(),
            static_cast<uint8_t*>(buffers.table->contents()), nullptr, options);
        assert(ok);
        return packets.size();
    };
    assert(buffers.ok);
    for (unsigned i = 0; i < 1000; ++i) draw();
    constexpr unsigned draws = 30'000;
    size_t words = 0;
    const auto start = std::chrono::steady_clock::now();
    for (unsigned i = 0; i < draws; ++i) words += draw();
    const auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now() - start).count();
    std::printf("%lld %u %zu\n", static_cast<long long>(duration), draws, words);
}
}  // namespace

int main(int argc, char** argv) {
    const std::string_view mode = argc == 2 ? argv[1] : "";
    if (mode == "snapshot") {
        snapshot();
    } else if (mode == "short") {
        benchmark(Shape::ShortNames);
    } else if (mode == "long") {
        benchmark(Shape::LongNames);
    } else if (mode == "masked") {
        benchmark(Shape::MaskedOutput);
    } else if (mode == "regressions") {
        for (const auto& entry : test::cases()) entry.run();
        std::printf("%zu render tests, %d failed checks\n", test::cases().size(), test::failures());
    } else {
        return 2;
    }
    return test::failures() != 0;
}
