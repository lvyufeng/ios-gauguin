#include "Recording342.hpp"
#include "hakios-metal/a6xx.hpp"
#include "hakios-metal/command.hpp"
#include <cassert>
#include <chrono>
#include <cstdio>
#include <string_view>

namespace hakios::metal {
void appendStream(pm4::Stream&, const pm4::Stream&);
bool appendDeduped(pm4::Stream&, const pm4::Stream&, CommandBuffer::RegShadow&);
}

int main(int argc, char** argv) {
    using namespace hakios::metal;
    using namespace gauguin342;
    if (argc == 2 && std::string_view(argv[1]) == "--packet-benchmark") {
        pm4::Stream draw, out;
        CommandBuffer::RegShadow shadow;
        for (uint32_t reg = 0x8200; reg < 0x8400; reg += 4) {
            const uint32_t values[4] = {reg, reg + 1, reg + 2, reg + 3};
            draw.registers(reg, values, 4);
        }
        constexpr unsigned draws = 30'000;
        constexpr unsigned drawsPerPass = 64;
        size_t words = 0;
        const auto start = std::chrono::steady_clock::now();
        for (unsigned i = 0; i < draws; ++i) {
            if (i % drawsPerPass == 0) shadow.clear();
            out.clear();
            appendDeduped(out, draw, shadow);
            words += out.size();
        }
        const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now() - start).count();
        std::printf("%lld %u %zu\n", static_cast<long long>(elapsed), draws, words);
        return 0;
    }
    WorkMeter meter;
    meter.begin(100, Render);
    Values classes{};
#ifdef REFERENCE_0343
    const auto early = meter.snapshot(200);
    meter.finish(148);
    classes = meter.snapshotCategories(200);
    assert(early == 100 && sum(classes) == 48);
#else
    const auto early = meter.snapshot(200, &classes);
    assert(early == 100 && sum(classes) == early);
    meter.finish(148);
    const auto late = meter.snapshot(200, &classes);
    assert(late == 48 && sum(classes) == late);
#endif
    meter.retire(148);

    pm4::Stream all, dedup;
    CommandBuffer::RegShadow shadow;
    {
        pm4::Stream encoded;
        const uint32_t words[3] = {1, 2, 3};
        encoded.registers(a6xx::REG_A6XX_HLSQ_INVALIDATE_CMD - 1, words, 3);
        encoded.registers(a6xx::REG_A6XX_HLSQ_INVALIDATE_CMD - 1, words, 3);
        appendStream(all, encoded);
        assert(!appendDeduped(dedup, encoded, shadow));
        // The second write still contains the side-effectful register.
        assert(dedup.size() == 7);
        shadow.clear();
    }
    for (unsigned turn = 0; turn < 512; ++turn) {
        pm4::Stream encoded;
        uint32_t data[177];
        for (unsigned i = 0; i < 177; ++i)
            data[i] = i % 3 ? i * i : turn + i;
        encoded.registers(0x8200, data, 177);
        encoded.nop(turn % 4);
        encoded.waitForIdle();
        encoded.registers(0x8200, data, 177);
        if (turn % 7 == 0) {
            encoded.packet(0x43, data, 7); // resets the register shadow
            encoded.registers(0x8200, data, 177);
        }
        appendStream(all, encoded);
        const bool forgot = appendDeduped(dedup, encoded, shadow);
        assert(forgot == (turn % 7 == 0));
    }
    for (const auto* stream : {&all, &dedup})
        assert(std::fwrite(stream->words().data(), sizeof(uint32_t), stream->size(), stdout) == stream->size());
}
