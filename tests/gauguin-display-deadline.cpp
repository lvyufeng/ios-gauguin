#include "gauguin_frame380_phase.h"

#include <cassert>
#include <iostream>

#ifndef BASELINE
#include "gauguin_frame388_receipts.h"

static void
check_receipts()
{
    f388_receipts capture{};
    capture.gate = F388_UNARMED;
    const f380_dispatch sample{{12000, 13000, 11000, 8, 7}, 12800, F380_VTOTAL_60};
    f388_record(&capture, F380_SOFTWARE, 10000, nullptr);
    assert(!f388_close(&capture));
    f388_arm(&capture, 10000, 20000);
    f388_arm(&capture, 10000, 40000);
    assert(capture.start == 10000 && capture.end == 20000);
    f388_record(&capture, F380_SOFTWARE, 9999, nullptr);
    f388_record(&capture, F380_SOFTWARE, 10000, nullptr);
    f388_record(&capture, F380_MISSED, 11000, nullptr);
    for (unsigned index = 0; index < 4096; ++index)
        f388_record(&capture, F380_ALIGNED, 12000 + index, &sample);
    f388_record(&capture, F380_SOFTWARE, 19999, nullptr);
    f388_record(&capture, F380_SOFTWARE, 20000, nullptr);
    assert(capture.aligned == 4096 && capture.first == 12000 && capture.last == 16095);
    assert(capture.software == 2 && capture.fallback == 1 && capture.missed == 1);
    assert(capture.count == F380_SAMPLES && capture.rows[0].sequence == F380_FIRST_SAMPLE &&
           capture.rows[1].sequence == F380_SAMPLE_STEP && capture.rows[0].dispatch.ready == sample.ready);

    // An in-flight writer makes the first drain retry.
    __atomic_store_n(&capture.gate, 1, __ATOMIC_RELAXED);
    assert(!f388_close(&capture));
    __atomic_fetch_sub(&capture.gate, 1, __ATOMIC_RELEASE);
    assert(f388_close(&capture));
    f388_record(&capture, F380_SOFTWARE, 19999, nullptr);
    assert(capture.software == 2);
}

static void
check_mode(uint32_t total, uint64_t period)
{
    const uint64_t origin = 10000000;
    const uint32_t start = UINT32_MAX - 8;
    f380_fit fit{};
    f380_prediction prediction{};
    for (unsigned i = 0; i < F380_HISTORY; ++i) {
        const uint64_t edge = origin + i * period;
        assert(f380_fit_add_mode(&fit, total, start + i, edge - 500, edge + 500, &prediction)
               == (i + 1 == F380_HISTORY));
    }
    assert(prediction.period == period);
    assert(prediction.edge == origin + F380_HISTORY * period);
    assert(prediction.frame == start + F380_HISTORY - 1);
    assert(!f380_fit_add_mode(&fit, F380_VTOTAL_90 + 1, prediction.frame + 1,
                              prediction.edge - 500, prediction.edge + 500, &prediction));
    assert(fit.count == 0);

    const uint64_t ready = f380_ready_ticks(&prediction, total, 224);
    assert(ready * total >= period * 224);
    assert((ready - 1) * total < period * 224);
    assert(!f380_ready_ticks(&prediction, total, 0));
    const f380_budget budget{period / 2, ready};
    const uint64_t arm = prediction.edge - budget.work - budget.ready;
    const f380_sent none{};
    f380_dispatch first{}, later{};
    assert(f380_pick_deadline(&prediction, &none, total, arm, 0, budget, &first));
    assert(first.pulse.wake == arm && first.ready == prediction.edge - ready);
    assert(first.pulse.scan == prediction.frame + 1 && first.pulse.edge == prediction.edge);
    assert(f380_dispatch_due(&prediction, &none, total, &first, arm));
    assert(!f380_dispatch_due(&prediction, &none, total, &first, arm - 1));
    assert(!f380_dispatch_due(&prediction, &none, total, &first, prediction.edge));
    const uint32_t other = total == F380_VTOTAL_60 ? F380_VTOTAL_90 : F380_VTOTAL_60;
    const f380_prediction other_phase{prediction.edge, prediction.observed,
                                      f380_scale(318700, other), prediction.frame};
    assert(!f380_dispatch_due(&other_phase, &none, other, &first, arm));
    const f380_sent sent{arm, first.pulse.scan, true};
    assert(!f380_dispatch_due(&prediction, &sent, total, &first, arm));
    assert(f380_pick_deadline(&prediction, &sent, total, arm, 0, budget, &later));
    assert(later.pulse.scan == first.pulse.scan + 1);
    assert(f380_pick_deadline(&prediction, &none, total, arm, prediction.edge + 1, budget, &later));
    assert(later.pulse.edge == prediction.edge + period);
    assert(f380_pick_deadline(&prediction, &none, total, arm + 1, 0, budget, &later));
    assert(later.pulse.edge == prediction.edge + period);
    assert(!f380_pick_deadline(&prediction, &none, total, arm, 0, {UINT64_MAX, 1}, &later));
    assert(!f380_pick_deadline(&prediction, &none, total, arm, 0, {UINT64_MAX, 0}, &later));
    assert(!f380_pick_deadline(&prediction, &none, total, arm, UINT64_MAX, budget, &later));
    assert(!f380_pick_deadline(&prediction, &none, total, prediction.observed - 1, 0, budget, &later));
    assert(!f380_pick_deadline(&prediction, &none, total, prediction.observed + 768001, 0, budget, &later));
    assert(f380_can_send_mode(&sent, total, arm + period));
    assert(!f380_can_send_mode(&sent, total, arm + 1));

    // More than one cycle of work can target a later scan. Consecutive
    // callbacks can still be a single scan apart.
    assert(f380_pick_deadline(&prediction, &none, total, arm, 0, {period, ready}, &later));
    assert(later.pulse.edge == prediction.edge + period);
}
#endif

int
main()
{
#ifndef BASELINE
    check_mode(F380_VTOTAL_60, 318700);
    check_mode(F380_VTOTAL_90, 213290);
    check_mode(F380_VTOTAL_120, 158702);
    check_receipts();
#endif
    f380_fit fit{};
    uint32_t frame, step, tail;
    uint64_t lo, hi;
    while (std::cin >> frame >> step >> lo >> hi >> tail) {
        if (step != 1) {
            fit.count = fit.next = 0;
            continue;
        }
        f380_prediction prediction{};
        if (!f380_fit_add(&fit, frame, lo, hi, &prediction)) continue;
        for (const auto offset : {0, 76800, 153600, 230400, 307200}) {
            const uint64_t now = prediction.observed + offset;
            for (const f380_sent sent : {f380_sent{}, f380_sent{hi, frame + 1, true}}) {
                f380_wake pulse{};
                bool selected;
#ifdef BASELINE
                selected = f380_pick(&prediction, &sent, now, &pulse);
#else
                const uint64_t ready = f380_ready_ticks(&prediction, F380_VTOTAL_60, tail);
                assert(ready && ready < F380_LEAD);
                const f380_budget budget{F380_LEAD - ready, ready};
                f380_dispatch dispatch{};
                selected = f380_pick_deadline(&prediction, &sent, F380_VTOTAL_60, now, 0, budget, &dispatch);
                pulse = dispatch.pulse;
                assert(!selected || (pulse.wake + budget.work == dispatch.ready &&
                                     dispatch.ready + ready == pulse.edge));
#endif
                std::cout << frame << ' ' << prediction.period << ' ' << now << ' ' << selected;
                if (selected) {
                    std::cout << ' ' << pulse.wake << ' ' << pulse.edge << ' ' << pulse.scan
                              << ' ' << f380_due(&prediction, &sent, &pulse, pulse.wake)
                              << ' ' << f380_due(&prediction, &sent, &pulse, pulse.edge - 1);
                }
                std::cout << '\n';
            }
        }
    }
    return std::cin.eof() ? 0 : 1;
}
