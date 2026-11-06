#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>

static bool flag_present;
static int flag_value;
static unsigned parses, fallback_calls, fallback_lock_markers, fallback_map_markers;
static unsigned cases;
static const char *case_name;
static const char *fallback_resource;
static unsigned fallback_mv;
enum { FALLBACK_RESULT = 24601 };

#define CHECK(condition, reason) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL %s:%d [%s]: %s\n", __FILE__, __LINE__, case_name, reason); \
        exit(1); \
    } \
} while (0)

static bool PE_parse_boot_argn(const char *name, void *value, int bytes)
{
    CHECK(strcmp(name, "sweetbusvote") == 0, "actual selector parses the intended flag");
    CHECK(bytes == (int)sizeof(flag_value), "actual selector uses an int flag");
    ++parses;
    if (!flag_present) return false;
    memcpy(value, &flag_value, sizeof(flag_value));
    return true;
}

/* These counters mark reaching the omitted legacy body. They are NOT an
 * execution model or test of its real validation, locking or MMIO behavior. */
static int legacy_fallback(const char *resource, unsigned mv)
{
    ++fallback_calls;
    ++fallback_lock_markers;
    ++fallback_map_markers;
    fallback_resource = resource;
    fallback_mv = mv;
    return FALLBACK_RESULT;
}

@ACTUAL_FLAG_SELECTOR@

/* Actual function prefix through the first matching #endif, followed only by
 * the explicit fallback sentinel. No legacy register code is compiled here. */
@ACTUAL_LEGACY_ENTRY@

static void run_case(const char *name, bool present, int value,
                     const char *resource, unsigned mv)
{
    case_name = name;
    ++cases;
    flag_present = present;
    flag_value = value;
    parses = fallback_calls = fallback_lock_markers = fallback_map_markers = 0;
    fallback_resource = NULL;
    fallback_mv = 0;
#if defined(GAUGUIN)
    const bool denied = present && value == 1;
    const unsigned expected_parses = 1;
#else
    const bool denied = false;
    const unsigned expected_parses = 0;
#endif
    int result = sweet_rpmh_vreg_enable(resource, mv);
    CHECK(parses == expected_parses, "non-GAUGUIN path must not consult the flag");
    if (denied) {
        CHECK(result == EBUSY, "exact busvote1 rejects with EBUSY");
        CHECK(fallback_calls == 0 && fallback_lock_markers == 0 && fallback_map_markers == 0,
              "deny before any omitted legacy-body/lock/map marker");
    } else {
        CHECK(result == FALLBACK_RESULT, "default path reaches the unchanged-body boundary");
        CHECK(fallback_calls == 1 && fallback_lock_markers == 1 && fallback_map_markers == 1,
              "exactly one fallback sentinel");
        CHECK(fallback_resource == resource && fallback_mv == mv, "arguments preserved");
    }
}

int main(void)
{
    run_case("absent", false, 0, "ldoa6", 2700);
    run_case("explicit zero", true, 0, "ldoa6", 2700);
    run_case("exact one", true, 1, "ldoa6", 2700);
    run_case("other positive", true, 2, "ldoa6", 2700);
    run_case("negative", true, -1, "ldoa6", 2700);
    run_case("large positive", true, INT_MAX, "ldoa6", 2700);
    run_case("deny precedes NULL/voltage validation", true, 1, NULL, 0);
    run_case("deny precedes wrong resource validation", true, 1, "other", UINT_MAX);
#if defined(GAUGUIN)
    printf("PASS legacy-gate-gauguin cases=%u\n", cases);
#else
    printf("PASS legacy-gate-other cases=%u\n", cases);
#endif
    return 0;
}
