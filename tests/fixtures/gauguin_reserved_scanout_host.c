#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "gauguin_linear_scanout411.h"

enum { kSuccess, F382_FRONT = 0, F382_FIRST = 1, F382_SECOND = 2 };
enum { F344_PAGE = 0x4000, F382_SLOT_BYTES = 0x9e4000 };
typedef void *DTEntry;
typedef uintptr_t vm_offset_t;
struct scan381_state { bool route; };

static struct {
    vm_offset_t map[3];
    uint32_t address[3], requests;
    volatile uint32_t *source, *pitch, *sourceXY, *flush;
    bool enabled, padded;
} scan382;

static uint64_t owner[4], pas[16];
static uint32_t vig[4096], ctl[4096];
static uintptr_t cpuSlots[] = { UINT64_C(0x120000000000), UINT64_C(0x130000000000) };
static unsigned mappings, discards;
static bool forceManaged, brokenTranslation, failMapping, routeValid;

static int SecureDTLookupEntry(DTEntry root, const char *name, DTEntry *entry)
{
    assert(!root && !strcmp(name, "/chosen"));
    *entry = &owner;
    return kSuccess;
}

static int SecureDTGetProperty(DTEntry entry, const char *name, const void **data, unsigned *size)
{
    assert(entry == &owner);
    if (!strcmp(name, "DPUPrivateBuffers")) {
        *data = owner;
        *size = sizeof(owner);
    } else {
        assert(!strcmp(name, "LowPASReservation"));
        *data = pas;
        *size = sizeof(pas);
    }
    return kSuccess;
}

static bool scan382_route(const struct scan381_state *state) { return state->route; }

static bool scan382_live_route(uint32_t pitch, uint32_t sourceXY)
{
    return routeValid && pitch == F411_PANEL_PITCH && !sourceXY;
}

static bool pmap_valid_address(uint64_t pa)
{
    return forceManaged && pa == owner[0] + 2 * F344_PAGE;
}

static bool sweet_fb383_map(uint32_t pa, uint32_t size, uintptr_t slots[2])
{
    assert(pa == owner[0] && size == owner[1]);
    ++mappings;
    if (failMapping) return false;
    memcpy(slots, cpuSlots, sizeof(cpuSlots));
    return true;
}

static void sweet_fb383_discard(void) { ++discards; }

static uint64_t ml_vtophys(vm_offset_t address)
{
    for (unsigned i = 0; i < 2; ++i) {
        if (address >= cpuSlots[i] && address - cpuSlots[i] < owner[1]) {
            const uint64_t offset = address - cpuSlots[i];
            if (brokenTranslation && i == 1 && offset == 2 * F344_PAGE) return 0;
            return owner[0] + i * owner[1] + offset;
        }
    }
    assert(false);
    return 0;
}

static vm_offset_t scan382_map_registers(uint32_t pa, uint32_t size)
{
    assert(size == F344_PAGE);
    if (pa == 0x0ae04000) return (vm_offset_t)vig;
    assert(pa == 0x0ae00000);
    return (vm_offset_t)ctl;
}

#include "gauguin_reserved_prepare.inc"

static void setup(uint32_t bytes)
{
    memset(&scan382, 0, sizeof(scan382));
    memset(pas, 0, sizeof(pas));
    memcpy(pas, "LPASOWN1", 8);
    owner[0] = 0xa9000000;
    owner[1] = bytes;
    owner[2] = pas[10] = 0xa8000000;
    owner[3] = pas[11] = 0x5000000;
    pas[2] = 0x4000000;
    pas[8] = 0xac000000;
    mappings = discards = 0;
    vig[0x1014 / 4] = 0xa0000000;
    vig[0x1024 / 4] = F411_PANEL_PITCH;
    vig[0x1008 / 4] = ctl[0x2018 / 4] = 0;
    forceManaged = brokenTranslation = failMapping = false;
    routeValid = true;
}

int main(void)
{
    const struct scan381_state state = {true};
    setup(F382_SLOT_BYTES);
    assert(scan382_prepare(&state) && mappings == 1 && !discards && scan382.enabled && !scan382.padded);
    setup(F411_SLOT_BYTES);
    assert(scan382_prepare(&state) && mappings == 1 && !discards && scan382.enabled && scan382.padded);
    assert(scan382.map[F382_FIRST] == cpuSlots[0] && scan382.address[F382_SECOND] == owner[0] + owner[1]);

    setup(F411_SLOT_BYTES - F344_PAGE);
    assert(!scan382_prepare(&state) && !mappings);
    setup(F411_SLOT_BYTES);
    pas[8] = owner[0] + 2 * owner[1] - 1;
    assert(!scan382_prepare(&state) && !mappings);
    setup(F411_SLOT_BYTES);
    forceManaged = true;
    assert(!scan382_prepare(&state) && !mappings);
    setup(F411_SLOT_BYTES);
    brokenTranslation = true;
    assert(!scan382_prepare(&state) && mappings == 1 && discards == 1 && !scan382.enabled);
    setup(F411_SLOT_BYTES);
    vig[0x1008 / 4] = 1;
    assert(!scan382_prepare(&state) && mappings == 1 && discards == 1 && !scan382.enabled);
    setup(F411_SLOT_BYTES);
    failMapping = true;
    assert(!scan382_prepare(&state) && mappings == 1 && !scan382.enabled);
}
