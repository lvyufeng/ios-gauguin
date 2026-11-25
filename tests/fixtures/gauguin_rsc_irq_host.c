#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef uintptr_t vm_offset_t;
static vm_offset_t gicd_base;
static unsigned translations, reads, barriers, pending_read, bad_translation;
static uint32_t register_value;
static unsigned cases;
static const char *case_name;

#define CHECK(condition, reason) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL %s:%d [%s]: %s\n", __FILE__, __LINE__, case_name, reason); \
        exit(1); \
    } \
} while (0)

static vm_offset_t ml_vtophys(vm_offset_t address)
{
    ++translations;
    CHECK(address == gicd_base || address == gicd_base + 0x104u,
          "only the mapping endpoints used by the actual helper may translate");
    if (bad_translation == translations) return 0;
    return UINT64_C(0x17a00000) + address - gicd_base;
}

static uint32_t fake_gic_read(uint32_t offset)
{
    CHECK(offset == 0x104u, "only ISENABLER1 may be read");
    CHECK(translations == 2, "both translations must precede the register read");
    CHECK(pending_read == 0, "previous read requires its DMB");
    ++reads;
    pending_read = 1;
    return register_value;
}

static void fake_dmb(void)
{
    CHECK(pending_read == 1, "DMB must follow a register read");
    pending_read = 0;
    ++barriers;
}

#define gicd_read32(offset) fake_gic_read(offset)
/* There is deliberately no GIC write API. An added call must fail compilation. */

@RSC_HELPER@

static void reset(const char *name)
{
    case_name = name;
    ++cases;
    gicd_base = UINT64_C(0x10000000); /* synthetic token; never dereferenced */
    translations = reads = barriers = pending_read = bad_translation = 0;
    register_value = 0;
}

static void untouched(uint32_t output, unsigned expected_translations)
{
    CHECK(output == UINT32_C(0x11223344), "failure must leave output untouched");
    CHECK(translations == expected_translations, "translation short-circuit count");
    CHECK(reads == 0 && barriers == 0 && pending_read == 0,
          "rejected mapping must not read GIC or issue a read barrier");
}

int main(void)
{
    uint32_t output;
    reset("NULL output");
    CHECK(!sweet_rsc_irq_quiet(NULL), "NULL output rejected");
    CHECK(translations == 0 && reads == 0 && barriers == 0, "NULL has no platform access");

    reset("uninitialized GIC mapping");
    gicd_base = 0;
    output = UINT32_C(0x11223344);
    CHECK(!sweet_rsc_irq_quiet(&output), "missing mapping rejected");
    untouched(output, 0);

    for (unsigned endpoint = 1; endpoint <= 2; ++endpoint) {
        reset(endpoint == 1 ? "wrong base translation" : "wrong register translation");
        bad_translation = endpoint;
        output = UINT32_C(0x11223344);
        CHECK(!sweet_rsc_irq_quiet(&output), "wrong physical translation rejected");
        untouched(output, endpoint);
    }

    static const struct { uint32_t value; bool quiet; } vectors[] = {
        {0, true}, {1, true}, {2, true}, {3, true},
        {0x10, true}, {0x40, true}, {0x80000000u, true},
        {0xffffffdfu, true}, {0x20, false}, {0x21, false}, {UINT32_MAX, false},
    };
    for (unsigned i = 0; i < sizeof(vectors) / sizeof(vectors[0]); ++i) {
        reset("NS enable-bit vector");
        register_value = vectors[i].value;
        output = UINT32_C(0x11223344);
        CHECK(sweet_rsc_irq_quiet(&output) == vectors[i].quiet, "only INTID37 / bit5 blocks");
        CHECK(output == vectors[i].value, "actual raw value returned even when not quiet");
        CHECK(register_value == vectors[i].value, "synthetic GIC register unchanged");
        CHECK(translations == 2 && reads == 1 && barriers == 1 && pending_read == 0,
              "exactly two translations and one ordered read");
    }
    printf("PASS rsc-helper cases=%u\n", cases);
    return 0;
}
