// Exercise the recording path through the host Core and its GPU simulator.
#include "render_test.cpp"

#include <chrono>
#include <cstdlib>
#include <string_view>

namespace hakios::metal {
bool appendDeduped(pm4::Stream&, const pm4::Stream&, CommandBuffer::RegShadow&);
}

namespace {
void require(bool condition) {
    if (!condition) std::abort();
}

void writePackets(const pm4::Stream& stream) {
    const auto& words = stream.words();
    const auto count = uint32_t(words.size());
    require(std::fwrite(&count, sizeof count, 1, stdout) == 1);
    require(std::fwrite(words.data(), sizeof(uint32_t), count, stdout) == count);
}

void snapshot() {
    using namespace a6xx;
    CommandBuffer::RegShadow registers;
    pm4::Stream actual, source;
    const auto check = [&](bool forgets) {
        require(appendDeduped(actual, source, registers) == forgets);
        writePackets(actual);
        source.clear();
        actual.clear();
    };
    // Include complete and partial omissions, a type-4 count boundary,
    // overlapping writes, and a command register that must always be written.
    std::array<uint32_t, 129> initial{};
    for (unsigned i = 0; i < initial.size(); ++i) initial[i] = i + 0x19;
    for (unsigned pass = 0; pass < 4; ++pass) {
        source.packet(pm4::kWaitForIdle, nullptr, 0);
        source.registers(0x8000, initial.data(), uint32_t(initial.size()));
        source.registers(REG_A6XX_HLSQ_INVALIDATE_CMD, initial.data(), 1);
        check(false);
        initial[pass * 2 + 1] ^= 0x10;
        initial[127] ^= 0x20;
    }
    source.registers(0x8070, initial.data() + 17, 23);
    check(false);
    source.packet(CP_SET_DRAW_STATE, initial.data(), 3);
    check(true);
    source.registers(0x8000, initial.data(), uint32_t(initial.size()));
    check(false);

    // Deterministic overlaps and state-changing packets across independent
    // append calls. Replay both high and low register addresses.
    uint32_t random = 0x4f142a12;
    const auto next = [&] {
        random = random * 1664525u + 1013904223u;
        return random;
    };
    for (unsigned pass = 0; pass < 257; ++pass) {
        bool forgets = pass % 31 == 0;
        for (unsigned n = 0; n < 9; ++n) {
            const auto first = next() % 701;
            const auto count = 1 + next() % 129;
            const auto start = (n % 2 == 0 ? 0x400u : 0x3f800u) + first;
            for (uint32_t i = 0; i < count; ++i) initial[i] = (start + i) ^ (pass % 5 == 0 ? 1 : 0);
            source.registers(start, initial.data(), count);
            if (forgets && n == 4) source.packet(CP_SET_DRAW_STATE, initial.data(), 3);
        }
        check(forgets);
    }
}

void record(bool mixed) {
    Rig rig;
    auto color0 = target(rig);
    auto color1 = target(rig);
    const Program p = flatProgram();
    const Bindings bindings{};
    render::Options options{};
    // Use the normal command recording entry. Mixed mode varies passes and
    // viewport/scissor state while keeping the workload identical per build.
    options.gmem = false;
    options.dedupRegs = true;
    constexpr unsigned blocks = 400, draws = 80;
    uint64_t words = 0;
    const auto start = std::chrono::steady_clock::now();
    for (unsigned block = 0; block < blocks; ++block) {
        auto cb = rig.queue->commandBuffer();
        RenderPass pass{};
        Draw draw = wholeDraw();
        for (unsigned n = 0; n < draws; ++n) {
            pass.color0 = mixed && n % 19 < 9 ? color1.get() : color0.get();
            if (mixed) draw.scissor = Scissor{n % 3, n % 5, 58, 56};
            require(cb->draw(p, pass, draw, bindings, bindings, options));
        }
        words += cb->streamWords();
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now() - start).count();
    std::printf("%lld %u %llu\n", static_cast<long long>(elapsed), blocks * draws,
                static_cast<unsigned long long>(words));
}
}

int main(int argc, char** argv) {
    const std::string_view mode = argc == 2 ? argv[1] : "";
    if (mode == "snapshot") snapshot();
    else if (mode == "repeat" || mode == "mixed") record(mode == "mixed");
    else if (mode == "regressions") {
        for (const auto& entry : test::cases()) entry.run();
        std::printf("%zu render tests, %d failed checks\n", test::cases().size(), test::failures());
    } else {
        return 2;
    }
    return test::failures() != 0;
}
