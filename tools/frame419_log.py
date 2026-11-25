"""Join independently captured writer, copy and hardware scan deadlines."""

from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
import re
from statistics import median, quantiles

import frame344_log as frame


GPU, PROMOTE, COPY, DISPATCH = range(64, 68)
RAW_COMPLETION = 69
SECOND = 19_200_000
VERTICAL_TOTAL = 4910
FLIP_GUARD_LINES = 192
REQUEST_ALLOWANCE = 1920
U32_MASK = (1 << 32) - 1
ALIGN_TOLERANCE = SECOND // 1000


@dataclass(frozen=True)
class Row:
    seq: int
    tick: int
    kind: int
    id: int
    lane: int
    version: int
    a: int
    b: int
    c: int


def read_timeline(raw, limits):
    number, reason, lost, start, end = map(int, frame.one(
        r'^SWEET F419 H: count=(\d+) reason=(\d+) lost=(\d+) start=(\d+) end=(\d+)$',
        raw, 'deadline timeline header'))
    count, losses, size, overflow = map(int, frame.one(
        r'^SWEET F419 F: count=(\d+) lost=(\d+) bytes=(\d+) overflow=([01])$',
        raw, 'deadline timeline footer'))
    lines = re.findall(r'^F419E .*$', raw, re.M)
    frame.require(0 < number < limits['rows'] and reason == 1 and not lost and not overflow
                  and count == len(lines) == number and losses == 0
                  and size == sum(len(line) + 2 for line in lines) <= limits['wire_bytes']
                  and end - start == limits['duration_seconds'] * SECOND,
                  'deadline timeline stopped early or has missing records')
    rows = []
    for seq, line in enumerate(lines, 1):
        frame.require(re.fullmatch(r'F419E [0-9a-f]{1,16}(?: [0-9a-f]{1,16}){8}', line),
                      'malformed deadline event')
        row = Row(*(int(column, 16) for column in line[6:].split()))
        frame.require(row.seq == seq and start <= row.tick < end
                      and row.kind in ((1,) if seq == 1 else (GPU, PROMOTE, COPY, DISPATCH, RAW_COMPLETION)),
                      'invalid deadline event sequence or clock')
        rows.append(row)
    trigger = rows.pop(0)
    frame.require(trigger.id == 1 and trigger.lane == trigger.version == 0
                  and trigger.a == trigger.b <= trigger.tick and trigger.c == 1,
                  'deadline timeline start trigger differs')
    return rows, dict(records=number, wire_bytes=size, start=start, end=end)


def private_receipts(raw):
    capture = lambda pattern: ([int(value) for value in row] for row in re.findall(pattern, raw, re.M))
    staged = frame.indexed(capture(r'^SWEET F(?:382|384) P (\d+) ([12]) (\d+)$'), lambda row: row[0], 'staged attempt')
    requests = frame.indexed(capture(r'^SWEET F382 I (\d+) (\d+) ([12]) (\d+)(?: C)?$'), lambda row: row[0], 'private request')
    latches = frame.indexed(capture(r'^SWEET F382 L (\d+) (\d+) ([12]) (\d+)$'), lambda row: row[0], 'confirmed latch')
    frame.require(staged and bool(latches) and set(latches) == set(requests) <= set(staged),
                  'private flip issue/latch ledger is incomplete')
    for attempt, (_, scan, slot, confirmed) in latches.items():
        _, request_scan, request_slot, issue = requests[attempt]
        _, staged_slot, stored = staged[attempt]
        frame.require(slot == staged_slot == request_slot and scan == request_scan + 1
                      and stored <= issue <= confirmed, 'private flip ownership or timing differs')
    return staged, latches


def cutoffs(previous, scan, end_line):
    period_low, period_high = scan.a - previous.b, scan.b - previous.a
    tail = VERTICAL_TOTAL - end_line + FLIP_GUARD_LINES
    return (scan.a - (period_high * tail + VERTICAL_TOTAL - 1) // VERTICAL_TOTAL - REQUEST_ALLOWANCE,
            scan.b - period_low * tail // VERTICAL_TOTAL - REQUEST_ALLOWANCE)


def where_late(eop, visible, begin, done, low, high):
    if visible > high:
        return 'GPU completion observed late' if eop > high else 'GPU visibility late'
    if done <= low:
        return 'copy finished before cutoff'
    if visible <= low and done > high:
        if begin > high:
            return 'copy started late after GPU visibility'
        if begin <= low:
            return 'copy crossed cutoff'
        return 'copy start overlaps cutoff'
    return 'timing overlaps cutoff'


def target_scan(target, edges, pulses, predicted):
    """Only associate a CA tag if the dispatch prediction and physical edge agree."""
    if not target:
        return None
    index = bisect_left(predicted, target - ALIGN_TOLERANCE)
    scans = []
    while index < len(predicted) and predicted[index] <= target + ALIGN_TOLERANCE:
        pulse = pulses[index]
        edge = edges.get(pulse.id)
        if edge and edge.a - ALIGN_TOLERANCE <= target <= edge.b + ALIGN_TOLERANCE:
            scans.append(edge.id)
        index += 1
    return scans[0] if len(scans) == 1 else None


def passive_words(raw, rows, config):
    if not config:
        frame.require(not rows, 'unexpected passive completion rows')
        return {}
    frame.require(raw.splitlines().count('SWEET F425: passive completion sampling only') == 1
                  and 0 < len(rows) <= config['maximum_raw_records'],
                  'passive observation was unavailable or exceeded its bound')
    for row in rows:
        frame.require(row.id >> 32 and row.id & U32_MASK and row.lane and row.version == 0
                      and ((0 <= row.a <= row.c <= row.b <= row.tick and row.b and row.c)
                           or (0 < row.a <= row.tick and row.b == row.c == 0)),
                      'native fence sample lacks its exclusive pending/matched observation')
    return frame.indexed(rows, lambda row:(row.id,row.lane), 'native display fence')


def native_bounds(writer, sample):
    issue = None
    if writer.c:
        offset = writer.c >> 32
        issue = [writer.a-offset,writer.a-offset+(writer.c & U32_MASK)]
        frame.require(0 < issue[0] <= issue[1] <= writer.a, 'native submit call bracket differs')
    low = max(issue[0] if issue else 0, sample.a if sample else 0)
    high = min(writer.a,sample.b) if sample and sample.b else writer.a
    frame.require(low <= high, 'native completion sample crossed guarded confirmation')
    return issue, [low,high] if low or sample else None


def native_deadline(timing, low, high):
    issue, eop = timing['native_submit_ticks'],timing['hardware_EOP_ticks']
    if issue and issue[0] > high:
        return 'native submit began after cutoff'
    if eop and eop[0] > high:
        if issue and issue[1] <= low:
            return 'native submit returned before cutoff and hardware still pending'
        return 'hardware still pending after cutoff with submit timing inconclusive'
    if eop and eop[1] <= low and timing['GPU_EOP_observed'] > high:
        return 'hardware completed before cutoff and guarded confirmation was late'
    if eop and eop[1] <= low:
        return 'hardware completed before cutoff'
    return 'hardware completion bracket overlaps cutoff'


def intervals(ticks):
    ordered = sorted(ticks)
    if not ordered:
        return {'samples':0}
    return dict(samples=len(ordered),p50_ms=median(ordered)/19200,
                p95_ms=quantiles(ordered,n=100,method='inclusive')[94]/19200 if len(ordered)>1 else ordered[0]/19200)


def measure(raw, score, plan):
    rows, metadata = read_timeline(raw, plan['deadline_timeline'])
    groups = {kind: [row for row in rows if row.kind == kind] for kind in (GPU, PROMOTE, COPY, DISPATCH)}
    gpu = frame.indexed(groups[GPU], lambda row: (row.id, row.lane, row.version), 'GPU writer version')
    promoted = frame.indexed(groups[PROMOTE], lambda row: (row.a, row.id & U32_MASK, row.version), 'promoted generation')
    copied = frame.indexed(groups[COPY], lambda row: row.id, 'private copy attempt')
    dispatch = frame.indexed(groups[DISPATCH], lambda row: row.id, 'dispatch scan')
    config = plan.get('completion_observer')
    hardware = passive_words(raw,[row for row in rows if row.kind == RAW_COMPLETION],config)
    frame.require(all(groups.values())
                  and all(r.id >> 32 and r.id & U32_MASK and r.lane and r.version
                          and 0 < r.a <= r.b <= r.tick and (config or r.c == 0) for r in gpu.values())
                  and all(r.id >> 32 == r.a and r.lane and r.version for r in promoted.values())
                  and all(r.lane and r.version and r.a and 0 < r.c <= r.tick for r in copied.values())
                  and all(r.id and r.lane == r.version == 0 and 0 < r.c < r.b < r.a
                          and r.c <= r.tick for r in dispatch.values()),
                  'deadline receipt payload differs')

    scan_rows = (frame.Event(*(int(col, 16) for col in fields.split()))
                 for fields in re.findall(r'^F344E (.*)$', raw, re.M))
    edges = frame.indexed((row for row in scan_rows if row.kind == frame.VBLANK), lambda row: row.id, 'DPU edge')
    pulses = sorted(dispatch.values(), key=lambda row: row.a)
    predicted = [row.a for row in pulses]
    end_line = int(frame.one(r'^SWEET F351 WINDOW: available=1 frame=\d+ end=(\d+)$',
                             raw, 'installed display cutoff'))
    frame.require(end_line == 4878, '0419 physical cutoff geometry differs')
    staged, latches = private_receipts(raw)
    by_scan = frame.indexed(latches.values(), lambda row: row[1], 'confirmed scan')
    scans = sorted(by_scan)
    chains = {}
    for attempt, row in copied.items():
        frame.require(attempt in staged and row.c <= staged[attempt][2] <= row.tick,
                      'copy timing does not bound the staged barrier')
        ready = promoted.get((row.a, row.lane, row.version))
        if not ready:
            continue
        writer = gpu.get((ready.id, ready.lane, ready.version))
        if not writer:
            continue
        frame.require(writer.b <= ready.tick <= row.c and ready.c == row.b,
                      'copy does not follow exact writer visibility and promotion')
        chain = dict(generation=row.a, surface=row.lane, version=row.version,
            writer_fence=writer.lane, writer_ticket=writer.id, GPU_EOP_observed=writer.a,
            GPU_cache_visible=writer.b, promoted_tick=ready.tick, copy_begin=row.c,
            copy_end=staged[attempt][2], CA_requested_tick=row.b,
            matched_target_scan=target_scan(row.b, edges, pulses, predicted))
        if config:
            sample = hardware.get((writer.id,writer.lane))
            submit, eop = native_bounds(writer,sample)
            chain.update(native_submit_ticks=submit,hardware_EOP_ticks=eop,
                         raw_matched=bool(sample and sample.b),raw_pending=bool(sample and sample.a))
        chains[attempt] = chain

    motion = score['motion']['first_tick']
    begin = score.get('score_begin_tick', motion + plan['sustained_motion']['score_after_seconds'] * SECOND)
    end = begin + score['score_seconds'] * SECOND
    in_score = [row for row in latches.values() if begin <= row[3] < end]
    with_timing = [chains[row[0]] for row in in_score if row[0] in chains]
    cohorts = {
        'exact_requested_target': Counter(),
        'next_latch_only': Counter(),
        'repeat_with_latch': Counter(),
        'missing_timing': Counter(),
    }
    native_cohorts = {key:Counter() for key in ('exact_requested_target','next_latch_only')}
    repeat_rows = []
    for repeated in score['repeated_scan_ids']:
        index = bisect_left(scans, repeated)
        following = by_scan[scans[index]] if index < len(scans) else None
        timing = chains.get(following[0]) if following else None
        if not timing:
            cohorts['missing_timing']['staged timeline not joined'] += 1
            if repeated in by_scan:
                cohorts['repeat_with_latch']['same output CRC after a confirmed latch'] += 1
            repeat_rows.append(dict(scan=repeated, latch_scan=following[1] if following else None,
                                    timing=None))
            continue
        low, high = cutoffs(edges[repeated - 1], edges[repeated], end_line)
        if repeated in by_scan:
            group, label = 'repeat_with_latch', 'same output CRC after a confirmed latch'
        else:
            group = 'exact_requested_target' if timing['matched_target_scan'] == repeated else 'next_latch_only'
            label = where_late(timing['GPU_EOP_observed'], timing['GPU_cache_visible'],
                               timing['copy_begin'], timing['copy_end'], low, high)
        cohorts[group][label] += 1
        detail = dict(scan=repeated,latch_scan=following[1],deadline_ticks=[low,high],
                      classification=label,association=group,timing=timing)
        if config and group in native_cohorts:
            finding = native_deadline(timing,low,high)
            native_cohorts[group][finding] += 1
            detail['native_deadline'] = finding
        if len(repeat_rows) < 512:
            repeat_rows.append(detail)
    result = dict(metadata, gpu_writers=len(gpu), promoted_generations=len(promoted), copy_attempts=len(copied),
                aligned_dispatches=len(dispatch), confirmed_latches_in_score=len(in_score),
                exact_writer_joins_in_score=len(with_timing),
                CA_targets_matched_in_score=sum(row['matched_target_scan'] is not None for row in with_timing),
                median_copy_ms=median((row['copy_end'] - row['copy_begin']) / 19_200 for row in with_timing)
                    if with_timing else None,
                classification={key: dict(value) for key, value in cohorts.items()},
                repeated_scans=repeat_rows)
    if config:
        result.update(native_deadline_comparison={key:dict(value) for key,value in native_cohorts.items()},
                      raw_matched=sum(row['raw_matched'] for row in with_timing),
                      raw_pending=sum(row['raw_pending'] for row in with_timing),
                      native_call=intervals([r['native_submit_ticks'][1]-r['native_submit_ticks'][0]
                                             for r in with_timing if r['native_submit_ticks']]),
                      submit_return_to_guard=intervals([r['GPU_EOP_observed']-r['native_submit_ticks'][1]
                                                        for r in with_timing if r['native_submit_ticks']]),
                      raw_match_to_guard=intervals([r['GPU_EOP_observed']-r['hardware_EOP_ticks'][1]
                                                    for r in with_timing if r['raw_matched']]))
    return result


def whole_interval(raw, score, plan):
    if score['completely_measured_seconds'] != score['score_seconds']:
        return None
    default_start = score['motion']['first_tick'] + plan['sustained_motion']['score_after_seconds'] * SECOND
    start = score.get('score_begin_tick', default_start)
    end = start + score['score_seconds'] * SECOND
    repeats = set(score['repeated_scan_ids'])
    edges = (frame.Event(*(int(col, 16) for col in fields.split()))
             for fields in re.findall(r'^F344E (.*)$', raw, re.M))
    changed = [row for row in edges if row.kind == frame.VBLANK and row.id not in repeats]
    return dict(confirmed_new=sum(start <= row.a and row.b < end for row in changed),
                maximum_new=sum(row.a < end and row.b >= start for row in changed))
