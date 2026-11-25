#include "gauguin_cpufreq399.h"

#include <cassert>
#include <initializer_list>
#include <utility>

using RegisterValue = std::pair<unsigned, uint32_t>;

struct RegisterSequence {
    std::initializer_list<RegisterValue> values;
    unsigned next = 0;

    static uint32_t read(void *cookie, unsigned offset)
    {
        auto &self = *static_cast<RegisterSequence *>(cookie);
        assert(self.next < self.values.size());
        assert(offset < CPU399_DOMAIN_BYTES && !(offset % sizeof(uint32_t)));
        const auto &entry = self.values.begin()[self.next++];
        assert(entry.first == offset);
        return entry.second;
    }
};

static void check(std::initializer_list<RegisterValue> values, bool valid,
                  cpu399_domain_sample expected = {})
{
    RegisterSequence sequence{values};
    cpu399_domain_sample actual{97, 99, 101};
    assert(cpu399_sample_domain(RegisterSequence::read, &sequence, &actual) == valid);
    assert(sequence.next == sequence.values.size());
    if (valid) {
        assert(actual.index == expected.index && actual.frequency_row == expected.frequency_row &&
               actual.cycles == expected.cycles);
    } else {
        assert(actual.index == 97 && actual.frequency_row == 99 && actual.cycles == 101);
    }
}

int main()
{
    constexpr unsigned perf = CPU399_PERF_STATE;
    constexpr unsigned cyc = CPU399_CYCLES;
    constexpr unsigned last = CPU399_LUT + CPU399_LUT_STRIDE * (CPU399_LUT_ENTRIES - 1);
    check({{0, 1}, {perf, 0}, {CPU399_LUT, 0x00020000}, {cyc, 7}, {perf, 0}, {0, 1}}, true,
          {0, 0x00020000, 7});
    check({{0, 1}, {perf, 39}, {last, 0x40020072}, {cyc, UINT32_MAX}, {perf, 39}, {0, 1}}, true,
          {39, 0x40020072, UINT32_MAX});
    check({{0, 0}}, false);
    check({{0, UINT32_MAX}}, false);
    check({{0, 1}, {perf, 40}}, false);
    check({{0, 1}, {perf, UINT32_MAX}}, false);
    check({{0, 1}, {perf, 0}, {CPU399_LUT, UINT32_MAX}, {cyc, 1}}, false);
    check({{0, 1}, {perf, 0}, {CPU399_LUT, 0x40020000}, {cyc, 1}}, false);
    check({{0, 1}, {perf, 0}, {CPU399_LUT, 0x40020072}, {cyc, 1}, {perf, 1}}, false);
    check({{0, 1}, {perf, 0}, {CPU399_LUT, 0x40020072}, {cyc, 1}, {perf, 0}, {0, 0}}, false);
}
