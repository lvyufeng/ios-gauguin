#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_runtime.h"

static struct ggr_context ggrb_context;
static bool ggrb_service, ready;
static uint64_t ggrb_root;
static enum ggr_error next_result;
static unsigned calls, records, checks;
static const uint64_t addresses[] = {0x40000000};
static const uint32_t words[] = {8};

static void check(bool condition, unsigned line)
{
    ++checks;
    if (!condition) {
        fprintf(stderr, "submission record assertion failed at line %u\n", line);
        exit(1);
    }
}
#define CHECK(condition) check(!!(condition), __LINE__)

bool sweet_gpu_runtime_ready(void)
{
    return ready;
}

enum ggr_error ggr_submit(struct ggr_context *context, const uint64_t *a,
                         const uint32_t *w, uint32_t count, uint32_t *fence)
{
    CHECK(context == &ggrb_context && a == addresses && w == words && count == 1 && fence != NULL);
    ++calls;
    if (next_result == GGR_OK) {
        ++context->submitted;
        ++context->completed;
        context->wptr = (context->wptr + 12) % 8192;
        ++context->polls;
        *fence = context->completed;
    }
    return next_result;
}

static void gmb_record(const char *line)
{
    unsigned rc, count, submitted, completed, shadow, polls;
    CHECK(sscanf(line, "SWEET GPU USER: submit rc=%u ibs=%u submitted=%u completed=%u shadow=%u polls=%u",
                 &rc, &count, &submitted, &completed, &shadow, &polls) == 6);
    CHECK(rc == (unsigned)next_result && count == 1);
    CHECK(submitted == ggrb_context.submitted && completed == ggrb_context.completed);
    CHECK(shadow == ggrb_context.wptr && polls == ggrb_context.polls);
    ++records;
}

@SUBMIT@

static void reset(bool service)
{
    memset(&ggrb_context, 0, sizeof(ggrb_context));
    ggrb_context.wptr = 20;
    ggrb_service = service;
    ready = true;
    ggrb_root = 1;
    next_result = GGR_OK;
    calls = records = 0;
}

int main(void)
{
    uint32_t fence = 0;
    reset(true);
    for (unsigned i = 1; i <= 2048; ++i) {
        unsigned before = records;
        CHECK(sweet_gpu_runtime_submit(addresses, words, 1, &fence));
        CHECK(fence == i && ggrb_context.submitted == i && ggrb_context.completed == i && calls == i);
        CHECK(records == before + (i <= 16 || i % 120 == 0));
    }
    CHECK(records == 16 + 2048 / 120);
    unsigned before = records;
    next_result = GGR_IO;
    fence = 0xfeed;
    CHECK(!sweet_gpu_runtime_submit(addresses, words, 1, &fence));
    CHECK(records == before + 1 && fence == 0xfeed && calls == 2049);
    next_result = GGR_UNAVAILABLE;
    CHECK(!sweet_gpu_runtime_submit(addresses, words, 1, &fence));
    CHECK(records == before + 2 && ggrb_context.completed == 2048);
    reset(false);
    for (unsigned i = 1; i <= 250; ++i) {
        CHECK(sweet_gpu_runtime_submit(addresses, words, 1, &fence));
        CHECK(records == i && fence == i);
    }
    reset(true);
    ggrb_root = 0;
    CHECK(!sweet_gpu_runtime_submit(addresses, words, 1, &fence) && !calls && !records);
    ggrb_root = 1;
    ready = false;
    CHECK(!sweet_gpu_runtime_submit(addresses, words, 1, &fence) && !calls && !records);
    printf("PASS %u actual submit/fence/startup/stream/failure-record assertions\n", checks);
    return 0;
}
