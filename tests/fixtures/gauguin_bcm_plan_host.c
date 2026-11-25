#include "cmd_db_snapshot.h"
#include "gauguin_bcm_plan.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Six synthetic ndb_entry records carrying the verified observed aux bytes.
 * The production decoder/planner is exercised through its public API only;
 * expected packets are computed here from the native BCM_TCS_CMD macro. */

/* Native BCM_TCS_CMD(commit, valid, vote_x, vote_y), msm_bus_fabric_rpmh.c:35. */
#define NATIVE_BCM_TCS_CMD(commit, valid, vote_x, vote_y) \
    (((commit & 0x1) << 30) | ((valid & 0x1) << 29) | \
     ((vote_x & 0x3fff) << 14) | ((vote_y & 0x3fff) << 0))
#define NATIVE_ACV_APPS 0x8

static const struct {
    const char *name;
    uint32_t address, unit;
    uint16_t width;
    uint8_t vcd;
    uint16_t bank_version;
} board[6] = {
    {"MC0", 0x50000, 2050000, 16,  0, 0},
    {"SH0", 0x50004, 3650000, 32,  1, 0},
    {"SN0", 0x5002c,  530000, 16,  3, 0},
    {"SN6", 0x50044,  530000, 16,  3, 0},
    {"CE0", 0x5006c,    7935,  8,  6, 0},
    {"ACV", 0x50080,       1,  0, 11, 0},
};

static void make_entry(struct ndb_entry *e, const char *name, uint32_t address,
    uint32_t unit, uint16_t width, uint8_t vcd, uint8_t reserved,
    uint16_t aux_length)
{
    memset(e, 0, sizeof(*e));
    memcpy(e->name, name, strlen(name));
    e->address = address;
    e->owner_slave = 5;
    e->bank_version = 0;
    e->aux_length = aux_length;
    /* Observed 8-byte aux, little endian: LE u32 unit, u16 width, u8 VCD, u8 reserved. */
    e->aux[0] = (uint8_t)unit;
    e->aux[1] = (uint8_t)(unit >> 8);
    e->aux[2] = (uint8_t)(unit >> 16);
    e->aux[3] = (uint8_t)(unit >> 24);
    e->aux[4] = (uint8_t)width;
    e->aux[5] = (uint8_t)(width >> 8);
    e->aux[6] = vcd;
    e->aux[7] = reserved;
}

/* Zeroed 8-byte key, then the literal's characters; never reads past it. */
static void set_name(struct ndb_entry *e, const char *literal)
{
    memset(e->name, 0, 8);
    memcpy(e->name, literal, strlen(literal));
}

static void make_all(struct ndb_entry e[6])
{
    for (unsigned i = 0; i < 6; ++i) {
        make_entry(&e[i], board[i].name, board[i].address, board[i].unit,
            board[i].width, board[i].vcd, 0, 8);
    }
}

/* Expected-data formulas independent of the planner: native macro and a
 * hand-written bit expression (x and y both 14-bit, inputs below the mask). */
#define SIMPLE_TCS_CMD(commit, x, y) ((uint32_t)(commit) << 30 | 0x20000000u | \
    (uint32_t)(x) << 14 | (uint32_t)(y))
#define ENCODE_RULE(last, acv) ((last ? 0x40000000u : 0) | 0x20000000u | \
    ((acv ? 0 : 0x3fffu) << 14) | (acv ? 8u : 0x3fffu))

/* Build must return rc and leave the output byte-identical; no retry. */
static void rejects_at(const struct ndb_entry *e, size_t count,
    enum gbcm_result rc, int line)
{
    struct gbcm_plan out, before;
    memset(&out, 0xa5, sizeof(out));
    before = out;
    enum gbcm_result got = gbcm_build(e, count, &out);
    if (got != rc || memcmp(&before, &out, sizeof(out))) {
        printf("REJECT MISMATCH line %d: expected %d got %d\n", line, rc, got);
        assert(0);
    }
}
#define REJECT(entries, code, mutate) do { \
        struct ndb_entry m[6]; \
        memcpy(m, (entries), sizeof(m)); \
        mutate; \
        rejects_at(m, 6, (code), __LINE__); \
    } while (0)
#define REJECT_COUNT(entries, code, n) do { \
        struct ndb_entry m[6]; \
        memcpy(m, (entries), sizeof(m)); \
        rejects_at(m, (n), (code), __LINE__); \
    } while (0)

int main(void)
{
    struct ndb_entry e[6];
    struct gbcm_plan plan;
    struct gbcm_db db;

    /* Expected packets, independent of the production encoder. */
    static const uint32_t expect_address[6] = {
        0x50000, 0x50004, 0x5002c, 0x50044, 0x5006c, 0x50080};
    static const uint32_t expect_data[6] = {
        0x6fffffff, 0x6fffffff, 0x2fffffff, 0x6fffffff, 0x6fffffff, 0x60000008};
    static const uint8_t expect_wait[6] = {1, 1, 0, 1, 1, 1};

    make_all(e);

    /* Encoder equals native macro for both row kinds; expected constants are
     * produced by a second, hand-written expression, not by the planner. */
    for (unsigned i = 0; i < 6; ++i) {
        int last = i != 2; /* commit iff i != 2: SN0 shares VCD3 with SN6 */
        uint32_t data = i == 5 ? NATIVE_BCM_TCS_CMD(last, 1, 0, NATIVE_ACV_APPS)
                               : NATIVE_BCM_TCS_CMD(last, 1, 0x3fff, 0x3fff);
        assert(data == expect_data[i]);
        assert(data == ENCODE_RULE(last, i == 5));
        assert(data == (i == 5 ? SIMPLE_TCS_CMD(last, 0, 8)
                               : SIMPLE_TCS_CMD(last, 0x3fff, 0x3fff)));
        assert(last == expect_wait[i]);
    }
    assert(0x60000008 == (0x40000000u | 0x20000000u | 0x8u)); /* ACV: no x clamp */

    memset(&plan, 0xa5, sizeof(plan));
    assert(gbcm_build(e, 6, &plan) == GBCM_OK);
    assert(plan.wait_mask == 0x3b && GBCM_EXPECT_WAIT_MASK == 0x3b);
    for (unsigned i = 0; i < 6; ++i) {
        assert(plan.db[i].address == board[i].address && plan.db[i].unit == board[i].unit &&
            plan.db[i].width == board[i].width && plan.db[i].vcd == board[i].vcd &&
            plan.db[i].reserved == 0);
        assert(plan.cmd[i].address == expect_address[i]);
        assert(plan.cmd[i].data == expect_data[i]);
        assert(plan.cmd[i].wait == expect_wait[i]);
        /* Commit only on the last row of each VCD. */
        assert(((plan.cmd[i].data >> 30) & 1) == expect_wait[i]);
        assert(((plan.cmd[i].data >> 29) & 1) == 1);
        assert(((plan.wait_mask >> i) & 1) == expect_wait[i]);
    }
    /* VCD3 grouping: SN0 then SN6, only SN6 commits (commit is on data bit30,
     * so i != 2); ACV keeps x=0,y=APPS mask8. */
    assert(!strcmp(board[2].name, "SN0") && !strcmp(board[3].name, "SN6"));
    assert(!(plan.cmd[2].data & 0x40000000) && (plan.cmd[3].data & 0x40000000));
    assert((plan.cmd[5].data >> 14 & 0x3fff) == 0 && (plan.cmd[5].data & 0x3fff) == 8);
    for (unsigned i = 0; i < 5; ++i) {
        assert((plan.cmd[i].data >> 14 & 0x3fff) == 0x3fff && (plan.cmd[i].data & 0x3fff) == 0x3fff);
    }

    /* Decode alone: LE fields, observed bank_version preserved (no gate). */
    make_entry(&e[0], "MC0", 0x50004, 0x12345678, 0xabcd, 15, 0, 8);
    e[0].bank_version = 0x0777;
    memset(&db, 0, sizeof(db));
    assert(gbcm_decode(&e[0], &db) == GBCM_OK);
    assert(db.address == 0x50004 && db.unit == 0x12345678 && db.width == 0xabcd &&
        db.vcd == 15 && db.bank_version == 0x0777 && db.reserved == 0);
    assert(gbcm_decode(NULL, &db) == GBCM_ARGUMENT);
    assert(gbcm_decode(&e[0], NULL) == GBCM_ARGUMENT);

    /* A different observed bank_version does not affect build/plan. */
    make_all(e);
    for (unsigned i = 0; i < 6; ++i) e[i].bank_version = 0x1234;
    {
        struct gbcm_plan other;
        assert(gbcm_build(e, 6, &other) == GBCM_OK);
        assert(!memcmp(other.cmd, plan.cmd, sizeof(plan.cmd)) && other.wait_mask == plan.wait_mask);
        assert(other.wait_mask == 0x3b);
        for (unsigned i = 0; i < 6; ++i) assert(other.db[i].bank_version == 0x1234);
    }

    /* Output unchanged on every failure. */
    make_all(e);
    REJECT_COUNT(e, GBCM_ARGUMENT, 0);
    REJECT_COUNT(e, GBCM_ARGUMENT, 5);
    REJECT_COUNT(e, GBCM_ARGUMENT, 7);
    rejects_at(NULL, 6, GBCM_ARGUMENT, __LINE__);
    {
        struct gbcm_plan out;
        memset(&out, 0xa5, sizeof(out));
        struct gbcm_plan before = out;
        assert(gbcm_build(e, 6, NULL) == GBCM_ARGUMENT);
        assert(!memcmp(&before, &out, sizeof(out)));
    }
    /* Wrong names (padded, unpadded, case, space, swap) are MISMATCH; the
     * duplicate-name check runs after the per-row comparison, so a duplicate
     * name at another position is also reported as MISMATCH. */
    REJECT(e, GBCM_MISMATCH, set_name(&m[0], "MC0X"));                  /* non-padded */
    REJECT(e, GBCM_MISMATCH, set_name(&m[1], "SH"));
    REJECT(e, GBCM_MISMATCH, set_name(&m[5], "acv"));                   /* lower case */
    REJECT(e, GBCM_MISMATCH, set_name(&m[4], " CE0"));
    REJECT(e, GBCM_MISMATCH, set_name(&m[0], "SH0"));                  /* name swap */
    REJECT(e, GBCM_MISMATCH, set_name(&m[4], "MC0"));                   /* duplicate */
    /* Decode validates only for owner_slave 5: every other value is NOT_BCM
     * before any board comparison. */
    REJECT(e, GBCM_NOT_BCM, m[0].owner_slave = 0);
    REJECT(e, GBCM_NOT_BCM, m[2].owner_slave = 6);
    REJECT(e, GBCM_NOT_BCM, m[0].owner_slave = 3);
    REJECT(e, GBCM_NOT_BCM, m[5].owner_slave = 4);
    REJECT(e, GBCM_NOT_BCM, (m[1].address = (m[1].address & 0xffff) | 0x40000)); /* bank4 */
    REJECT(e, GBCM_NOT_BCM, m[1].address = 0x40004);
    REJECT(e, GBCM_NOT_BCM, m[0].address = 0);                               /* nonzero */
    REJECT(e, GBCM_NOT_BCM, m[3].address = 0x50046);                         /* alignment */
    REJECT(e, GBCM_NOT_BCM, m[0].address = 0x50001);
    REJECT(e, GBCM_MISMATCH, m[3].address = 0x5002c);                        /* wrong row address */
    REJECT(e, GBCM_MALFORMED, (m[2].aux[0] = m[2].aux[1] = m[2].aux[2] = m[2].aux[3] = 0)); /* unit 0 */
    REJECT(e, GBCM_MISMATCH, m[2].aux[1] = 0x10);                            /* wrong unit */
    REJECT(e, GBCM_MISMATCH, m[0].aux[0] = 0x01);
    REJECT(e, GBCM_MISMATCH, m[1].aux[4] = 0x00);                            /* wrong width */
    REJECT(e, GBCM_MISMATCH, m[1].aux[5] = 0x01);
    REJECT(e, GBCM_MISMATCH, m[0].aux[6] = 1);                               /* wrong VCD */
    REJECT(e, GBCM_MALFORMED, m[3].aux[6] = 16);                             /* VCD out of range */
    for (unsigned i = 0; i < 6; ++i) {
        REJECT(e, GBCM_MALFORMED, m[i].aux[6] = 0xff);
        REJECT(e, GBCM_MALFORMED, m[i].aux[7] = 1);                          /* reserved */
        REJECT(e, GBCM_MALFORMED, m[i].aux_length = 7);                      /* aux length */
        REJECT(e, GBCM_MALFORMED, m[i].aux_length = 9);
    }
    /* A late failure (row5) still leaves the output byte-identical. */
    REJECT(e, GBCM_MALFORMED, m[5].aux_length = 6);
    REJECT(e, GBCM_MISMATCH, set_name(&m[5], "ACX"));                     /* last row */

    /* Exhaustive single-byte aux sweep: only the exact record is accepted and
     * a failing build never changes its output. */
    unsigned accepted = 0;
    for (unsigned which = 0; which < 6; ++which) {
        for (unsigned b = 0; b < 8; ++b) {
            for (unsigned v = 0; v < 256; ++v) {
                make_all(e);
                if (v == e[which].aux[b]) continue;
                e[which].aux[b] = (uint8_t)v;
                struct gbcm_plan out;
                memset(&out, 0xa5, sizeof(out));
                struct gbcm_plan before = out;
                if (gbcm_build(e, 6, &out) == GBCM_OK) {
                    ++accepted;
                } else {
                    assert(!memcmp(&before, &out, sizeof(out)));
                }
            }
        }
    }
    assert(accepted == 0);

    printf("PASS: gbcm_decode/gbcm_build PLAN ONLY; six observed aux records, native "
           "BCM_TCS_CMD macro arithmetic, exact addresses/data/waitmask0x3b, VCD3 SN0->SN6 "
           "commit only on SN6, ACV x0/APPS-mask8, bank_version preserved, and no output "
           "change for count/null/name/owner(not5)/bank/address/unit/width/VCD/reserved/"
           "aux-length failures or %u-byte aux sweep\n", 6u * 8u * 256u);
    return 0;
}
