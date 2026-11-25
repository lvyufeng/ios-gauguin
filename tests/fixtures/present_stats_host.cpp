// Host tests for the pure present-stats header. The Python driver injects the
// exact header under test at the marker below and compiles with ASan/UBSan.
#include <cstdint>
#include <cstdio>
#include <cstdlib>

@HEADER@

static unsigned checks;

static void
check_at(bool ok, const char *expression, int line)
{
    ++checks;
    if (!ok) {
        std::fprintf(stderr, "FAIL line %d: %s\n", line, expression);
        std::abort();
    }
}

#define CHECK(expression) check_at((expression), #expression, __LINE__)

static bool
stats_equal(const SweetPresentStats &a, const SweetPresentStats &b)
{
    if (a.attempts != b.attempts || a.copied != b.copied ||
        a.zeroBytes != b.zeroBytes || a.invalidTime != b.invalidTime ||
        a.bytes != b.bytes || a.layers != b.layers ||
        a.gpuGuards != b.gpuGuards || a.gpuRefusals != b.gpuRefusals ||
        a.waitSamples != b.waitSamples || a.copySamples != b.copySamples)
        return false;
    for (unsigned i = 0; i < 8; ++i) {
        if (a.waitHistogram[i] != b.waitHistogram[i] ||
            a.copyHistogram[i] != b.copyHistogram[i])
            return false;
    }
    return true;
}

static bool
stats_are_zero(const SweetPresentStats &stats)
{
    return stats_equal(stats, SweetPresentStats{});
}

static uint64_t
histogram_total(const uint64_t (&histogram)[8])
{
    uint64_t total = 0;
    for (unsigned i = 0; i < 8; ++i)
        total += histogram[i];
    return total;
}

static SweetPresentSample
sample(uint64_t copiedBytes, uint32_t copiedLayers, uint32_t gpuGuards,
    uint32_t gpuRefusals, bool timingValid)
{
    SweetPresentSample result = {};
    result.waitTicks = UINT64_C(0xfeedfacecafebeef);
    result.copyTicks = UINT64_C(0xdeadbeefcafebabe);
    result.copiedBytes = copiedBytes;
    result.copiedLayers = copiedLayers;
    result.gpuGuards = gpuGuards;
    result.gpuRefusals = gpuRefusals;
    result.timingValid = timingValid;
    return result;
}

/* Nearest-rank p95 bucket: rank = ceil(0.95 * total). Zero-work samples are
 * excluded from the histograms by the header, so they cannot lower this. */
static unsigned
histogram_p95_bin(const uint64_t (&histogram)[8])
{
    const uint64_t total = histogram_total(histogram);
    if (total == 0)
        return 8;
    const uint64_t rank = (total * 95 + 99) / 100;
    uint64_t cumulative = 0;
    for (unsigned i = 0; i < 8; ++i) {
        cumulative += histogram[i];
        if (cumulative >= rank)
            return i;
    }
    return 7;
}

static void
test_saturating_add(void)
{
    struct AddCase {
        uint64_t a, b, expected;
    };
    const AddCase cases[] = {
        {0, 0, 0},
        {0, 1, 1},
        {1, 2, 3},
        {12345, 67890, 80235},
        {UINT64_MAX - 5, 4, UINT64_MAX - 1},
        {UINT64_MAX - 5, 5, UINT64_MAX},
        {UINT64_MAX - 5, 6, UINT64_MAX},
        {UINT64_MAX, 0, UINT64_MAX},
        {0, UINT64_MAX, UINT64_MAX},
        {UINT64_MAX, 1, UINT64_MAX},
        {UINT64_MAX, UINT64_MAX, UINT64_MAX},
        {100, UINT64_MAX - 100, UINT64_MAX},
        {100, UINT64_MAX - 99, UINT64_MAX},
    };
    for (const AddCase &c : cases)
        CHECK(sweet_present_stats_saturating_add(c.a, c.b) == c.expected);
}

static void
test_add_ticks(void)
{
    uint64_t total = 0;
    CHECK(!sweet_present_sample_add_ticks(nullptr, 10, 20));

    CHECK(sweet_present_sample_add_ticks(&total, 10, 20));
    CHECK(total == 10);

    total = 41;
    CHECK(!sweet_present_sample_add_ticks(&total, 20, 10));
    CHECK(total == 41);

    total = UINT64_MAX - 5;
    CHECK(!sweet_present_sample_add_ticks(&total, 100, 106));
    CHECK(total == UINT64_MAX - 5);

    total = UINT64_MAX - 6;
    CHECK(sweet_present_sample_add_ticks(&total, 100, 106));
    CHECK(total == UINT64_MAX);

    total = 9;
    CHECK(sweet_present_sample_add_ticks(&total, 4, 4));
    CHECK(total == 9);

    total = UINT64_MAX;
    CHECK(!sweet_present_sample_add_ticks(&total, 3, 4));
    CHECK(total == UINT64_MAX);

    total = 0;
    CHECK(sweet_present_sample_add_ticks(&total, 0, UINT64_MAX));
    CHECK(total == UINT64_MAX);

    total = 1;
    CHECK(!sweet_present_sample_add_ticks(&total, 0, UINT64_MAX));
    CHECK(total == 1);
}

static void
test_histogram_bins(void)
{
    struct BinCase {
        uint64_t nanoseconds;
        unsigned expected;
    };
    const BinCase cases[] = {
        {0, 0},
        {1, 0},
        {499998, 0},
        {499999, 0},
        {500000, 1},
        {500001, 1},
        {999998, 1},
        {999999, 1},
        {1000000, 2},
        {1000001, 2},
        {1999998, 2},
        {1999999, 2},
        {2000000, 3},
        {2000001, 3},
        {3999998, 3},
        {3999999, 3},
        {4000000, 4},
        {4000001, 4},
        {7999998, 4},
        {7999999, 4},
        {8000000, 5},
        {8000001, 5},
        {15999998, 5},
        {15999999, 5},
        {16000000, 6},
        {16000001, 6},
        {33333332, 6},
        {33333333, 7},
        {33333334, 7},
        {UINT64_MAX, 7},
    };
    for (const BinCase &c : cases)
        CHECK(sweet_present_stats_bin(c.nanoseconds) == c.expected);
}

static void
test_empty_and_null_inputs(void)
{
    SweetPresentStats empty = {};
    CHECK(stats_are_zero(empty));

    SweetPresentSample emptySample = {};
    CHECK(sweet_present_stats_record(&empty, &emptySample, 0, 0));
    CHECK(empty.attempts == 1);
    CHECK(empty.copied == 0);
    CHECK(empty.zeroBytes == 1);
    CHECK(empty.invalidTime == 1);
    CHECK(empty.bytes == 0);
    CHECK(empty.layers == 0);
    CHECK(empty.gpuGuards == 0);
    CHECK(empty.gpuRefusals == 0);
    CHECK(empty.waitSamples == 0);
    CHECK(empty.copySamples == 0);
    CHECK(histogram_total(empty.waitHistogram) == 0);
    CHECK(histogram_total(empty.copyHistogram) == 0);

    SweetPresentStats guarded = {};
    guarded.attempts = 9;
    guarded.copied = 4;
    guarded.zeroBytes = 5;
    guarded.invalidTime = 2;
    guarded.bytes = 1234;
    guarded.layers = 7;
    guarded.gpuGuards = 3;
    guarded.gpuRefusals = 3;
    guarded.waitSamples = 6;
    guarded.copySamples = 5;
    guarded.waitHistogram[2] = 6;
    guarded.copyHistogram[5] = 6;
    const SweetPresentStats before = guarded;

    CHECK(!sweet_present_stats_record(nullptr, &emptySample, 0, 0));
    CHECK(!sweet_present_stats_record(&guarded, nullptr, 0, 0));
    CHECK(!sweet_present_stats_record(nullptr, nullptr, 0, 0));
    CHECK(stats_equal(guarded, before));
}

static void
test_mixed_samples(void)
{
    struct RunCase {
        SweetPresentSample sample;
        uint64_t wait_ns;
        uint64_t copy_ns;
    };
    const RunCase cases[] = {
        {sample(100, 2, 1, 0, true), 499999, 500000},
        {sample(0, 0, 1, 1, true), 500000, 999999},
        {sample(200, 1, 1, 0, true), 1000000, 1999999},
        {sample(300, 3, 1, 2, true), 2000000, 3999999},
        {sample(0, 0, 1, 1, true), 4000000, 7999999},
        {sample(400, 1, 1, 0, true), 8000000, 15999999},
        {sample(500, 2, 1, 1, true), 16000000, 33333332},
        {sample(600, 1, 1, 0, true), 33333333, 33333333},
        {sample(700, 2, 1, 3, false), 0, 0},
        {sample(0, 0, 1, 4, false), UINT64_MAX, UINT64_MAX},
        {sample(0, 0, 1, 0, true), 0, UINT64_MAX},
    };

    SweetPresentStats stats = {};
    uint64_t expectedWaitSamples = 0;
    uint64_t expectedCopySamples = 0;
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        CHECK(sweet_present_stats_record(&stats, &cases[i].sample,
            cases[i].wait_ns, cases[i].copy_ns));
        CHECK(stats.attempts == uint64_t(i + 1));
        CHECK(stats.copied + stats.zeroBytes == stats.attempts);
        if (cases[i].sample.timingValid) {
            if (cases[i].sample.gpuGuards != 0)
                ++expectedWaitSamples;
            if (cases[i].sample.copiedBytes != 0)
                ++expectedCopySamples;
        }
        CHECK(histogram_total(stats.waitHistogram) == expectedWaitSamples);
        CHECK(histogram_total(stats.copyHistogram) == expectedCopySamples);
    }

    const uint64_t expectedWait[8] = {2, 1, 1, 1, 1, 1, 1, 1};
    const uint64_t expectedCopy[8] = {0, 1, 1, 1, 0, 1, 1, 1};
    for (unsigned i = 0; i < 8; ++i) {
        CHECK(stats.waitHistogram[i] == expectedWait[i]);
        CHECK(stats.copyHistogram[i] == expectedCopy[i]);
    }

    CHECK(stats.attempts == 11);
    CHECK(stats.copied == 7);
    CHECK(stats.zeroBytes == 4);
    CHECK(stats.invalidTime == 2);
    CHECK(stats.bytes == 2800);
    CHECK(stats.layers == 12);
    CHECK(stats.gpuGuards == 11);
    CHECK(stats.gpuRefusals == 12);
    CHECK(stats.waitSamples == 9);
    CHECK(stats.copySamples == 6);
    CHECK(histogram_total(stats.waitHistogram) == 9);
    CHECK(histogram_total(stats.copyHistogram) == 6);
}

static void
test_zero_work_percentile_and_mixed_exclusion(void)
{
    const uint64_t slow_ns = UINT64_C(40000000);
    SweetPresentStats stats = {};
    bool recorded = true;
    for (unsigned i = 0; i < 10; ++i) {
        SweetPresentSample real = sample(100, 1, 1, 0, true);
        recorded = sweet_present_stats_record(&stats, &real, slow_ns, slow_ns)
            && recorded;
    }
    CHECK(recorded);
    CHECK(stats.attempts == 10);
    CHECK(stats.copied == 10);
    CHECK(stats.zeroBytes == 0);
    CHECK(stats.bytes == 1000);
    CHECK(stats.layers == 10);
    CHECK(stats.gpuGuards == 10);
    CHECK(stats.waitSamples == 10);
    CHECK(stats.copySamples == 10);
    CHECK(histogram_p95_bin(stats.waitHistogram) == 7);
    CHECK(histogram_p95_bin(stats.copyHistogram) == 7);
    CHECK(histogram_total(stats.waitHistogram) == 10);
    CHECK(histogram_total(stats.copyHistogram) == 10);

    /* If the 200 zero-work frames were binned at ~1 ns, p95 would fall into
     * bucket 0. The header excludes them, so the real p95 stays in bucket 7. */
    const uint64_t wouldBeBiased[8] = {200, 0, 0, 0, 0, 0, 0, 10};
    CHECK(histogram_p95_bin(wouldBeBiased) == 0);

    SweetPresentSample zeroWork = sample(0, 0, 0, 0, true);
    recorded = true;
    for (unsigned i = 0; i < 200; ++i)
        recorded = sweet_present_stats_record(&stats, &zeroWork, 1, 1)
            && recorded;
    CHECK(recorded);
    CHECK(stats.attempts == 210);
    CHECK(stats.copied == 10);
    CHECK(stats.zeroBytes == 200);
    CHECK(stats.bytes == 1000);
    CHECK(stats.layers == 10);
    CHECK(stats.gpuGuards == 10);
    CHECK(stats.waitSamples == 10);
    CHECK(stats.copySamples == 10);
    CHECK(histogram_total(stats.waitHistogram) == 10);
    CHECK(histogram_total(stats.copyHistogram) == 10);
    CHECK(histogram_p95_bin(stats.waitHistogram) == 7);
    CHECK(histogram_p95_bin(stats.copyHistogram) == 7);

    SweetPresentSample zeroCopy = sample(0, 0, 1, 0, true);
    CHECK(sweet_present_stats_record(&stats, &zeroCopy, 500000, UINT64_MAX));
    CHECK(stats.attempts == 211);
    CHECK(stats.copied == 10);
    CHECK(stats.zeroBytes == 201);
    CHECK(stats.waitSamples == 11);
    CHECK(stats.copySamples == 10);
    CHECK(stats.waitHistogram[1] == 1);
    CHECK(histogram_total(stats.waitHistogram) == 11);
    CHECK(histogram_total(stats.copyHistogram) == 10);
    CHECK(stats.copyHistogram[7] == 10);

    SweetPresentSample invalid = sample(250, 2, 2, 1, false);
    CHECK(sweet_present_stats_record(&stats, &invalid, UINT64_MAX, UINT64_MAX));
    CHECK(stats.attempts == 212);
    CHECK(stats.copied == 11);
    CHECK(stats.zeroBytes == 201);
    CHECK(stats.bytes == 1250);
    CHECK(stats.layers == 12);
    CHECK(stats.gpuGuards == 13);
    CHECK(stats.gpuRefusals == 1);
    CHECK(stats.invalidTime == 1);
    CHECK(stats.waitSamples == 11);
    CHECK(stats.copySamples == 10);
    CHECK(histogram_total(stats.waitHistogram) == 11);
    CHECK(histogram_total(stats.copyHistogram) == 10);
    CHECK(stats.waitHistogram[7] == 10);
    CHECK(stats.copyHistogram[7] == 10);
    CHECK(histogram_p95_bin(stats.waitHistogram) == 7);
    CHECK(histogram_p95_bin(stats.copyHistogram) == 7);
}

static void
test_record_saturation(void)
{
    SweetPresentStats stats = {};
    stats.attempts = UINT64_MAX - 1;
    stats.copied = UINT64_MAX - 1;
    stats.zeroBytes = UINT64_MAX - 1;
    stats.invalidTime = UINT64_MAX - 1;
    stats.bytes = UINT64_MAX - 9;
    stats.layers = UINT64_MAX - 1;
    stats.gpuGuards = UINT64_MAX - 1;
    stats.gpuRefusals = UINT64_MAX - 2;
    stats.waitSamples = UINT64_MAX - 1;
    stats.copySamples = UINT64_MAX - 1;
    stats.waitHistogram[0] = UINT64_MAX - 1;
    stats.copyHistogram[7] = UINT64_MAX - 1;

    SweetPresentSample copied = sample(10, 2, 1, 3, true);
    CHECK(sweet_present_stats_record(&stats, &copied, 0, UINT64_MAX));
    CHECK(stats.attempts == UINT64_MAX);
    CHECK(stats.copied == UINT64_MAX);
    CHECK(stats.zeroBytes == UINT64_MAX - 1);
    CHECK(stats.invalidTime == UINT64_MAX - 1);
    CHECK(stats.bytes == UINT64_MAX);
    CHECK(stats.layers == UINT64_MAX);
    CHECK(stats.gpuGuards == UINT64_MAX);
    CHECK(stats.gpuRefusals == UINT64_MAX);
    CHECK(stats.waitSamples == UINT64_MAX);
    CHECK(stats.copySamples == UINT64_MAX);
    CHECK(stats.waitHistogram[0] == UINT64_MAX);
    CHECK(stats.copyHistogram[7] == UINT64_MAX);

    SweetPresentSample invalidZero = sample(0, 1, 1, 1, false);
    CHECK(sweet_present_stats_record(&stats, &invalidZero, 1, 2));
    CHECK(stats.attempts == UINT64_MAX);
    CHECK(stats.copied == UINT64_MAX);
    CHECK(stats.zeroBytes == UINT64_MAX);
    CHECK(stats.invalidTime == UINT64_MAX);
    CHECK(stats.bytes == UINT64_MAX);
    CHECK(stats.layers == UINT64_MAX);
    CHECK(stats.gpuGuards == UINT64_MAX);
    CHECK(stats.gpuRefusals == UINT64_MAX);
    CHECK(stats.waitSamples == UINT64_MAX);
    CHECK(stats.copySamples == UINT64_MAX);
    CHECK(stats.waitHistogram[0] == UINT64_MAX);
    CHECK(stats.copyHistogram[7] == UINT64_MAX);
    CHECK(histogram_total(stats.waitHistogram) == UINT64_MAX);
    CHECK(histogram_total(stats.copyHistogram) == UINT64_MAX);
}

int
main(void)
{
    test_saturating_add();
    test_add_ticks();
    test_histogram_bins();
    test_empty_and_null_inputs();
    test_mixed_samples();
    test_zero_work_percentile_and_mixed_exclusion();
    test_record_saturation();
    std::printf("PASS present-stats host checks=%u; CPU-side header arithmetic only; "
        "no kernel, hardware, overhead, FPS or panel claim\n", checks);
    return 0;
}
