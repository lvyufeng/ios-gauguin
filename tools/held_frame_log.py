"""Read held-frame counters and bounded rejection reasons, without qualifying UI.

Only record terminators are removed. Interleaved, missing or inconsistent
diagnostic records fail instead of being extracted from a damaged line.
"""
from collections import Counter
import re

from gpu_service_log import STOP


ENABLED = 'SWEET FB HOLD: enabled pending=1 active=1; original surfaces, prompt retirement'
HOLD_PREFIX = 'SWEET FB HOLD: submitted='
DETAIL_PREFIX = 'SWEET FB REJECT: '
COUNTS_PREFIX = 'SWEET FB REJECT COUNTS: '
HOLD_KEYS = ('submitted', 'replaced', 'consumed', 'retired', 'canceled', 'rejected', 'pending', 'active')
REASON_KEYS = ('null_owner', 'layer_mask', 'surface0', 'surface1', 'surface2', 'surface3', 'unregistered')
HOLD = re.compile(r'SWEET FB HOLD: submitted=(\d+) replaced=(\d+) consumed=(\d+) '
                  r'retired=(\d+) canceled=(\d+) rejected=(\d+) pending=([01]) active=([01])')
DETAIL = re.compile(r'SWEET FB REJECT: n=(\d+) reason=([1-7]) owner=([01]) registered=([01]) '
                    r'clients=(\d+) mask=0x([0-9a-f]+) ids=(\d+),(\d+),(\d+),(\d+)')
COUNTS = re.compile(r'SWEET FB REJECT COUNTS: null=(\d+) mask=(\d+) surface0=(\d+) '
                    r'surface1=(\d+) surface2=(\d+) surface3=(\d+) unregistered=(\d+)')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def records(text, prefix, pattern):
    rows, position = [], 0
    # Vertical tabs and other Unicode separators are data, not kernel record
    # boundaries. Only LF (optionally preceded by one CR) ends a record.
    for raw in text.split('\n'):
        line = raw[:-1] if raw.endswith('\r') else raw
        if prefix in line:
            match = pattern.fullmatch(line)
            need(match is not None, 'malformed/interleaved ' + prefix)
            rows.append((position, match.groups()))
        position += len(raw) + 1
    return rows


def unsigned(values, bits=64):
    result = tuple(map(int, values))
    need(all(0 <= value < 1 << bits for value in result), 'held counter integer overflow')
    return result


def parse_held_frames(text, *, require_reasons=True):
    """A scoped presentation diagnostic, separate from GPU execution and pixels.

    require_reasons=False permits historical counters without 0216 records.
    It never invents a cause for those old rejections or repairs other traces.
    """
    need(type(text) is str and type(require_reasons) is bool, 'invalid parser arguments')
    enabled = records(text, 'SWEET FB HOLD: enabled ', re.compile(re.escape(ENABLED)))
    stop = records(text, 'SWEET GPU SERVICE: test deadline ', re.compile(re.escape(STOP)))
    need(len(enabled) == len(stop) == 1 and enabled[0][0] < stop[0][0],
         'missing/duplicate or reordered held enable/service stop')
    samples, previous = [], (0,) * 8
    for position, values in records(text, HOLD_PREFIX, HOLD):
        row = unsigned(values)
        need(enabled[0][0] < position, 'held counter before enable')
        need(all(now >= old for now, old in zip(row[:6], previous[:6])), 'held counters decreased')
        submitted, replaced, consumed, retired, canceled, rejected, pending, active = row
        need(submitted == replaced + consumed + canceled + pending and consumed == retired + active,
             'held frame ownership accounting differs')
        samples.append((position, dict(zip(HOLD_KEYS, row))))
        previous = row
    need(bool(samples), 'no held counter snapshots')

    details = []
    for position, values in records(text, DETAIL_PREFIX, DETAIL):
        n, reason, owner, registered, clients = unsigned(values[:5], 32)
        mask, ids = int(values[5], 16), unsigned(values[6:], 32)
        need(mask < 1 << 32 and n == len(details) + 1 and n <= 8, 'unbounded/reordered rejection detail')
        need(enabled[0][0] < position, 'rejection detail before enable')
        need(not registered or clients > 0, 'registered owner with empty client list')
        if reason == 7:
            need(registered == 0, 'unregistered reason with registered owner')
        elif reason == 1:
            need(owner == 0 and registered == 1, 'null-owner branch differs')
        else:
            need(owner == registered == 1, 'prepare branch without registered owner')
            if reason == 2:
                need(mask & ~15 != 0, 'mask reason with supported mask')
            else:
                layer = reason - 3
                need(mask <= 15 and mask & (1 << layer) and ids[layer] != 0,
                     'surface-hold reason without selected nonzero surface')
        details.append(dict(position=position, n=n, reason=reason, cause=REASON_KEYS[reason - 1],
                            owner=owner, registered=registered, clients=clients, mask=mask, ids=list(ids)))

    strict_new = require_reasons or bool(details)
    if strict_new:
        for position, row in samples:
            count = sum(detail['position'] < position for detail in details)
            need(count == min(row['rejected'], 8), 'rejection detail/held snapshot order differs')
        for detail in details:
            earlier = [row for position, row in samples if position < detail['position']]
            need(not earlier or detail['n'] > earlier[-1]['rejected'],
                 'rejection detail follows a snapshot that already counted it')

    totals, prior_counts, paired = [], (0,) * 7, set()
    for position, values in records(text, COUNTS_PREFIX, COUNTS):
        counts = unsigned(values)
        need(all(now >= old for now, old in zip(counts, prior_counts)), 'rejection reason counters decreased')
        earlier = [(offset, row) for offset, row in samples if offset < position]
        need(bool(earlier), 'reason totals without preceding held snapshot')
        sample_position, sample = earlier[-1]
        need(sample_position not in paired, 'duplicate reason totals for one held snapshot')
        need(sample['rejected'] > 0 and sum(counts) == sample['rejected'],
             'reason total differs from held rejections')
        paired.add(sample_position)
        prefix = Counter(row['reason'] for row in details if row['position'] < position)
        need(all(counts[reason - 1] >= n for reason, n in prefix.items()), 'reason totals omit detailed rejection')
        # STOP may be printed by another thread between HOLD and COUNTS.
        # Both lines describe the preceding HOLD snapshot under fLock.
        totals.append((sample_position, dict(zip(REASON_KEYS, counts)), position))
        prior_counts = counts
    last = samples[-1][1]
    if require_reasons or details or totals:
        need(all(position in paired for position, row in samples if row['rejected']),
             'held rejection snapshot missing its reason totals')
    if require_reasons and last['rejected']:
        need(len(details) >= min(last['rejected'], 8) and bool(totals), 'missing bounded rejection evidence')
    need(not totals or bool(details), 'reason totals without detailed rejections')
    before = [row for position, row in samples if position < stop[0][0]]
    after = [row for position, row in samples if position > stop[0][0]]
    before_totals = [row for position, row, _ in totals if position < stop[0][0]]
    after_totals = [row for position, row, _ in totals if position > stop[0][0]]
    return dict(state='held-frame-diagnostic-records-consistent',
                last_before_planned_stop=before[-1] if before else None,
                last_after_planned_stop=after[-1] if after else None,
                reasons_before_planned_stop=before_totals[-1] if before_totals else None,
                reasons_after_planned_stop=after_totals[-1] if after_totals else None,
                reason_snapshot_positions=[dict(held=position, counts=record) for position, _, record in totals],
                detailed_rejections=details, reason_records_present=bool(details),
                rejection_cause_observed=bool(details and totals),
                GPU_execution_qualified=False, desktop_pixels_qualified=False,
                FPS_qualified=False, high_refresh_qualified=False, daily_use_qualified=False)
