/* The observer has stopped. Associate each retained member version with all
 * complete annotated swaps that included it during this swipe. */
#ifndef GAUGUIN_TRANSACTION393_H
#define GAUGUIN_TRANSACTION393_H

enum { F393_RECEIPTS = 32, F393_WIRE = 80 };
_Static_assert(F390_CAP <= 64, "snapshot mask holds each retained swap");

static bool
f393_same_member(const struct f393_member *a, const struct f393_member *b)
{
    return a->context == b->context && a->id == b->id && a->version == b->version;
}

static bool
f393_contains(const struct f393_members *members, const struct f393_member *key)
{
    for (unsigned i = 0; i < members->count; ++i) {
        if (f393_same_member(&members->entries[i], key)) return true;
    }
    return false;
}

static void
f393_drain_transactions(void)
{
    uint8_t packed[F393_RECEIPTS * F393_WIRE];
    char encoded[4 * ((F390_BLOCK * F393_WIRE + 2) / 3) + 1];
    char line[sizeof(encoded)+64];
    for (unsigned lane = 0; lane < f385_windows; ++lane) {
        const struct f385_gesture *g = &f385_gestures[lane];
        const struct f390_lane *swaps = &f390_lanes[lane];
        const unsigned retained = MIN(g->count, F385_GESTURE_CAP);
        const unsigned available = MIN(swaps->count, F390_CAP);
        unsigned count = 0, omitted = 0;
        if (g->count == retained && swaps->count == available) {
            for (unsigned i = 0; i < available; ++i) {
                const struct f393_members *members = &f393_versions[lane][i];
                for (unsigned m = 0; m < members->count; ++m) {
                    const struct f393_member *key = &members->entries[m];
                    unsigned first = i;
                    uint64_t membership = 0;
                    for (unsigned s = 0; s < available; ++s) {
                        if (!f393_contains(&f393_versions[lane][s], key)) continue;
                        membership |= UINT64_C(1) << s;
                        if (swaps->rows[s].tick < swaps->rows[first].tick) first = s;
                    }
                    if (membership & ((UINT64_C(1) << i) - 1)) continue;
                    struct f390_snapshot snap = swaps->rows[first];
                    snap.context = key->context;
                    snap.id = key->id;
                    snap.version = key->version;
                    snap.member = F390_PRESENT;
                    struct f390_commit_receipt receipt;
                    if (!f390_commit_for_snapshot(g->rows, retained, &snap, &receipt)) continue;
                    if (count == F393_RECEIPTS) {
                        ++omitted;
                        continue;
                    }
                    uint8_t *dst = packed + count++ * F393_WIRE;
                    f390_pack_transaction(dst, first, &receipt);
                    f374_le64(dst+56, key->context);
                    f372_le32(dst+64, key->id);
                    f372_le32(dst+68, key->version);
                    f374_le64(dst+72, membership);
                }
            }
        }
        printf("SWEET F393 Q %u %u %u %u %u\n", lane+1, retained, g->count-retained, count, omitted);
        for (unsigned i = 0; i < count; i += F390_BLOCK) {
            const unsigned n = MIN(count-i, F390_BLOCK);
            f372_base64(packed+i*F393_WIRE, n*F393_WIRE, encoded);
            const int size = snprintf(line, sizeof(line), "\nSWEET F393 B %u %u %u %s\n", lane+1, i, n, encoded);
            if (size > 0 && (size_t)size < sizeof(line)) sweet_log_append(line, size);
        }
    }
    printf("SWEET F393 F %u %u %u\n", (unsigned)(f385_source_slide && f385_receiver_slide), f385_windows,
        __atomic_load_n(&f385_dropped_puts, __ATOMIC_RELAXED));
}
#endif
