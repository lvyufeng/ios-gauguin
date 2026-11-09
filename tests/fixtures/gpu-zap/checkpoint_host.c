#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauguin_gpu_zap.h"
#include "gauguin_wdt_lease.h"

enum gpzb_reason { PZB_WDT = 4 };
static struct gauguin_wdt_refresh_record gpzb_boot_refresh;
static bool enabled, refresh_ok;
static uint32_t returned_sequence;
static unsigned refresh_calls, records, rejects, checks;

static void check(bool condition, unsigned line)
{
    ++checks;
    if (!condition) {
        fprintf(stderr, "checkpoint assertion failed at line %u\n", line);
        exit(1);
    }
}
#define CHECK(condition) check(!!(condition), __LINE__)

static bool sweet_gpu_service_requested(void)
{
    return enabled;
}

bool gauguin_wdt_lease_refresh(struct gauguin_wdt_refresh_record *out)
{
    ++refresh_calls;
    *out = (struct gauguin_wdt_refresh_record){100, returned_sequence, 420000, 2};
    return refresh_ok;
}

static bool gpzb_reject(enum gpz_phase phase, enum gpz_scope scope, enum gpzb_reason reason)
{
    CHECK(phase == GPZ_SEAL && scope == GPZ_LIVE && reason == PZB_WDT);
    ++rejects;
    return false;
}

static void gmb_record(const char *line)
{
    CHECK(strcmp(line, "SWEET GPU WDT: pre-ZAP checkpoint seq=1 before=420000 after=2; "
                      "CP idle/EOP/fault/routes/power verified") == 0);
    ++records;
}

@CHECKPOINT@

static void reset(void)
{
    memset(&gpzb_boot_refresh, 0, sizeof(gpzb_boot_refresh));
    enabled = refresh_ok = true;
    returned_sequence = 1;
    refresh_calls = records = rejects = 0;
}

int main(void)
{
    reset();
    enabled = false;
    CHECK(gpzb_checkpoint(GPZ_SEAL));
    CHECK(refresh_calls == 0 && records == 0 && gpzb_boot_refresh.sequence == 0);
    enabled = true;
    const enum gpz_phase phases[] = {GPZ_INIT, GPZ_MEM, GPZ_COPY, GPZ_AUTH, GPZ_FINAL, GPZ_DONE};
    for (unsigned i = 0; i < sizeof(phases) / sizeof(phases[0]); ++i) {
        CHECK(gpzb_checkpoint(phases[i]));
        CHECK(refresh_calls == 0 && records == 0 && rejects == 0);
    }
    CHECK(gpzb_checkpoint(GPZ_SEAL));
    CHECK(refresh_calls == 1 && records == 1 && rejects == 0);
    CHECK(gpzb_boot_refresh.sequence == 1 && gpzb_boot_refresh.refreshed_at_ticks == 100);
    CHECK(gpzb_boot_refresh.before_count == 420000 && gpzb_boot_refresh.after_count == 2);
    refresh_ok = false;
    CHECK(gpzb_checkpoint(GPZ_SEAL));
    CHECK(refresh_calls == 1 && records == 1 && rejects == 0);
    reset();
    refresh_ok = false;
    CHECK(!gpzb_checkpoint(GPZ_SEAL));
    CHECK(refresh_calls == 1 && rejects == 1 && records == 0 && gpzb_boot_refresh.sequence == 0);
    const uint32_t invalid[] = {0, 2, UINT32_MAX};
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        reset();
        returned_sequence = invalid[i];
        CHECK(!gpzb_checkpoint(GPZ_SEAL));
        CHECK(refresh_calls == 1 && rejects == 1 && records == 0 && gpzb_boot_refresh.sequence == 0);
    }
    printf("PASS %u actual pre-ZAP checkpoint assertions and live-guard placement\n", checks);
    return 0;
}
