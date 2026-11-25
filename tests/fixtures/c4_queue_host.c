#include <assert.h>
#include <limits.h>
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const char *test_name = "backboardd", *test_mode = "edr-default318";
static uid_t test_uid = 501, test_euid = 501;
static const char *test_getprogname(void) { return test_name; }
static char *test_getenv(const char *name) {
    assert(!strcmp(name, "GAUGUIN_EAGL_MODE"));
    return (char *)test_mode;
}
static uid_t test_getuid(void) { return test_uid; }
static uid_t test_geteuid(void) { return test_euid; }
#define getprogname test_getprogname
#define getenv test_getenv
#define getuid test_getuid
#define geteuid test_geteuid
#include "../../graphics/gauguin-c4-queue/GauguinC4QueueTrace.h"
#undef getprogname
#undef getenv
#undef getuid
#undef geteuid

static void *worker(void *object) {
    for (unsigned i = 0; i < 8000; ++i)
        gauguin_c4_queue_trace(i % 8, object, 250, 251, 0);
    return NULL;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    if (!strcmp(argv[1], "concurrent")) {
        pthread_t threads[8];
        for (unsigned i = 0; i < 8; ++i)
            assert(!pthread_create(&threads[i], NULL, worker, (void *)(uintptr_t)(i+1)));
        for (unsigned i = 0; i < 8; ++i) assert(!pthread_join(threads[i], NULL));
        assert(gcq_records == GCQ_LIMIT + 1);
        for (unsigned i = 0; i < 1000; ++i) worker((void *)(uintptr_t)1);
        assert(gcq_records == GCQ_LIMIT + 1);
        puts("{\"case\":\"concurrent\",\"attempts\":8064000,\"records\":32768,\"markers\":1}");
        return 0;
    }
    if (!strcmp(argv[1], "boundaries")) {
        const double bad[] = {-INFINITY, -1, 0, 219.999999, 270, INFINITY, NAN};
        for (unsigned i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i)
            gauguin_c4_queue_trace(0, (void *)1, bad[i], 300, 0);
        const double ends[] = {-INFINITY, 0, 219, 900, INFINITY, NAN};
        for (unsigned i = 0; i < sizeof(ends)/sizeof(ends[0]); ++i)
            gauguin_c4_queue_trace(0, (void *)1, 220, ends[i], 0);
        gauguin_c4_queue_trace(10, (void *)1, 220, 220, 0);
        gauguin_c4_queue_trace(UINT_MAX, (void *)1, 220, 220, 0);
        gauguin_c4_queue_trace(0, NULL, 220, 220, 0);
        assert(gcq_records == 0 && gcq_scope == -1);
        for (unsigned i = 0; i < 10; ++i)
            gauguin_c4_queue_trace(i, (void *)UINTPTR_MAX, 269.999999999,
                                   899.999999999, UINT_MAX);
        assert(gcq_records == 10);
        gcq_records = UINT_MAX;
        gauguin_c4_queue_trace(0, (void *)1, 220, 220, 0);
        assert(gcq_records == UINT_MAX);
        puts("{\"case\":\"boundaries\",\"invalid_checks\":16,\"records\":10,\"saturation_checked\":true}");
        return 0;
    }
    if (!strcmp(argv[1], "scope")) {
        for (unsigned i = 0; i < 6; ++i) {
            test_name = i == 0 ? NULL : i == 1 ? "SpringBoard" : "backboardd";
            test_uid = i == 2 ? 0 : 501;
            test_euid = i == 3 ? 0 : 501;
            test_mode = i == 4 ? NULL : i == 5 ? "edr-default317" : "edr-default318";
            gcq_scope = -1;
            gauguin_c4_queue_trace(0, (void *)1, 220, 220, 0);
            assert(gcq_scope == 0 && gcq_records == 0);
        }
        puts("{\"case\":\"scope\",\"refusals\":6,\"records\":0}");
        return 0;
    }
    assert(!"unknown case");
}
