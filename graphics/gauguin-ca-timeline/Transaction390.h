/* Compact receipts from captured values. Run after the CA observer gate closes. */
#ifndef GAUGUIN_TRANSACTION390_H
#define GAUGUIN_TRANSACTION390_H

struct f390_commit_receipt {
	const struct f385_row *commit, *encoded, *send, *receive, *command, *apply;
	uint64_t before, after;
};

/* The optional native markers prove a first inclusion only when the entry
 * saw an empty membership and the exit saw the exact stored version. */
static void
f390_inclusion(const struct f385_row *rows, unsigned count, const struct f390_snapshot *snap,
    struct f390_commit_receipt *receipt)
{
	const uint64_t key = ((uint64_t)snap->seed << 32) | snap->id;
	const uint64_t version = (UINT64_C(1) << 32) | snap->version;
	const struct f385_row *entry = NULL, *exit = NULL;
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->thread != snap->thread || row->a != snap->update || row->b != snap->context || row->c != key ||
		    row->tick < receipt->apply->tick || row->tick >= snap->tick)
			continue;
		if (row->kind == F385_BEFORE_INCLUDE && row->d == 0) {
			if (entry) return;
			entry = row;
		} else if (row->kind == F385_AFTER_INCLUDE && row->d == version) {
			if (exit) return;
			exit = row;
		}
	}
	if (entry && exit && entry->tick < exit->tick) {
		receipt->before = entry->tick;
		receipt->after = exit->tick;
	}
}

static bool
f390_commit_for_snapshot(const struct f385_row *rows, unsigned count,
    const struct f390_snapshot *snap, struct f390_commit_receipt *result)
{
	if (snap->member != F390_PRESENT) return false;
	const uint64_t version = ((uint64_t)snap->id << 32) | snap->version;
	struct f390_commit_receipt r = {0};
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->kind == F385_APPLY && row->c == snap->context && row->d == version && row->tick < snap->tick) {
			if (r.apply) return false;
			r.apply = row;
		}
	}
	if (!r.apply) return false;
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->kind != F385_COMMAND || row->thread != r.apply->thread || row->a != r.apply->a ||
		    row->tick >= r.apply->tick)
			continue;
		if (r.command && r.command->tick == row->tick) return false;
		if (!r.command || r.command->tick < row->tick) r.command = row;
	}
	if (!r.command || r.command->b != r.apply->b || r.command->c != r.apply->c ||
	    (r.command->d >> 32) != snap->id || (uint32_t)(r.command->d + 1) != snap->version ||
	    !r.apply->b || r.apply->b > UINT16_MAX)
		return false;
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->kind == F385_RECEIVE && row->b == r.apply->b) {
			if (r.receive) return false;
			r.receive = row;
		} else if (row->kind == F385_SEND && row->a == r.apply->b) {
			if (r.send) return false;
			r.send = row;
		}
	}
	if (!r.receive || !r.send || !r.send->b || r.receive->c != r.send->c || !f385_packet((uint32_t)r.send->c) ||
	    r.send->tick > r.receive->tick || r.receive->tick >= r.command->tick)
		return false;
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->thread == r.send->thread && row->a == r.send->b && row->tick < r.send->tick &&
		    (row->kind == F385_SOURCE || row->kind == F385_ENCODED)) {
			if (r.commit && r.commit->tick == row->tick) return false;
			if (!r.commit || r.commit->tick < row->tick) r.commit = row;
		}
	}
	if (!r.commit || r.commit->kind != F385_SOURCE || r.commit->b != snap->id) return false;
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->thread == r.send->thread && row->a == r.send->b && row->tick > r.send->tick &&
		    (row->kind == F385_SOURCE || row->kind == F385_ENCODED)) {
			if (r.encoded && r.encoded->tick == row->tick) return false;
			if (!r.encoded || row->tick < r.encoded->tick) r.encoded = row;
		} else if (row->kind == F385_SEND && row != r.send && row->thread == r.send->thread &&
		    row->b == r.send->b && r.commit->tick < row->tick && row->tick < r.send->tick) {
			return false;
		}
	}
	if (!r.encoded || r.encoded->kind != F385_ENCODED || r.encoded->b != snap->id) return false;
	for (unsigned i = 0; i < count; ++i) {
		const struct f385_row *row = &rows[i];
		if (row->kind == F385_SEND && row != r.send && row->thread == r.send->thread && row->b == r.send->b &&
		    r.send->tick <= row->tick && row->tick <= r.encoded->tick)
			return false;
	}
	f390_inclusion(rows, count, snap, &r);
	*result = r;
	return true;
}

enum { F390_TRANSACTION_WIRE = 56 };

static void
f390_pack_transaction(uint8_t *out, unsigned index, const struct f390_commit_receipt *r)
{
	const struct f385_row *parts[] = {r->commit, r->encoded, r->send, r->receive, r->command, r->apply};
	f372_le32(out, index);
	f372_le32(out+4, (uint32_t)(r->send->a | (r->send->c << 16)));
	for (unsigned i = 0; i < sizeof(parts)/sizeof(parts[0]); ++i)
		f372_le32(out+8+4*i, (uint32_t)(parts[i]->tick - f374_start));
	f374_le64(out+32, r->send->thread);
	f374_le64(out+40, r->receive->thread);
	f372_le32(out+48, r->before ? (uint32_t)(r->before - f374_start) : 0);
	f372_le32(out+52, r->after ? (uint32_t)(r->after - f374_start) : 0);
}

static void
f390_drain_transactions(void)
{
	uint8_t packed[F390_CAP * F390_TRANSACTION_WIRE];
	char encoded[4 * ((F390_BLOCK*F390_TRANSACTION_WIRE+2)/3)+1];
	char line[4*((F390_BLOCK*F390_TRANSACTION_WIRE+2)/3)+64];
	for (unsigned lane = 0; lane < f385_windows; ++lane) {
		const struct f385_gesture *g = &f385_gestures[lane];
		const unsigned seen = g->count, retained = MIN(seen, F385_GESTURE_CAP);
		const unsigned available = MIN(f390_lanes[lane].count, F390_CAP);
		unsigned count = 0;
		if (seen == retained) {
			for (unsigned i = 0; i < available; ++i) {
				struct f390_commit_receipt receipt;
				if (f390_commit_for_snapshot(g->rows, retained, &f390_lanes[lane].rows[i], &receipt)) {
					f390_pack_transaction(packed+count*F390_TRANSACTION_WIRE, i, &receipt);
					++count;
				}
			}
		}
		printf("SWEET F390 TX Q %u %u %u %u\n", lane+1, retained, seen-retained, count);
		for (unsigned i = 0; i < count; i += F390_BLOCK) {
			const unsigned n = MIN(count-i, F390_BLOCK);
			f372_base64(packed+i*F390_TRANSACTION_WIRE, n*F390_TRANSACTION_WIRE, encoded);
			const int size = snprintf(line, sizeof(line), "\nSWEET F390 TX B %u %u %u %s\n", lane+1, i, n, encoded);
			if (size > 0 && (size_t)size < sizeof(line)) sweet_log_append(line, size);
		}
	}
	printf("SWEET F390 TX F %u %u %u\n", (unsigned)(f385_source_slide && f385_receiver_slide), f385_windows,
	    __atomic_load_n(&f385_dropped_puts, __ATOMIC_RELAXED));
}
#endif
